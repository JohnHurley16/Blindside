//! `harness` — CLI over blindside-harness.
//!
//! Exit codes, the same for every subcommand and what CI and `git bisect run` key off:
//! 0 ran and everything that was compared agreed; 1 a determinism failure was detected
//! (canary divergence, replay hash mismatch, a located or reproduced desync, two dumps
//! that differ); 2 could not run (bad arguments, unreadable or invalid files, a record
//! from another content pack or schema, `--injected` on a build without the fixture).
//! Exit 2 is never a determinism result: nothing was compared.

use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::time::Duration;

use clap::{ArgGroup, Args, Parser, Subcommand};

use blindside_harness::bisect::{self, Foreign, Located};
use blindside_harness::canary::{self, DiffText, Divergence, Inject};
use blindside_harness::dump::{self, Dump};
use blindside_harness::golden;
use blindside_harness::record::{content_hash_of, default_content_dir, HashLog, MatchRecord};
use blindside_harness::runner::{self, TICKS_PER_MATCH};

/// BLD-35: the injection tick defaults to 5,000.
const DEFAULT_INJECT_TICK: u64 = 5000;

const EXIT_CODES: &str = "\
Exit codes:
  0  ran, and everything that was compared agreed
  1  a determinism failure: canary divergence, hash mismatch, located or reproduced
     desync, differing dumps
  2  could not run: bad arguments, unreadable file, or a file that does not belong
     (wrong schema, wrong content hash, --injected without the inject-desync feature)";

const BISECT_HELP: &str = "\
Exactly one foreign side: --hash-log (a plain `tick,hash` log recorded elsewhere, at any
cadence), --injected (the BLD-35 fixture armed in both instances; the foreign side is an
armed instance's checkpoint log every --hash-every ticks, then the window is walked in
lockstep to the exact tick), or --from-divergence (re-run a canary's divergence.json).

Exit codes:
  0  no divergence (or a recorded injection that no longer reproduces)
  1  divergence located (or reproduced) -- tick, both hashes and the state diff printed,
     the local state dumped to <record stem>.tick<N>.dump
  2  usage or error: nothing was compared

The codes are `git bisect run` compatible, so with a foreign log from a known-good build
the culprit commit is found by:
  git bisect start <bad> <good>
  git bisect run cargo run -p blindside-harness --release -- bisect \\
      --record fixtures/phase0-empty-10k.record --hash-log good.hashlog";

#[derive(Parser)]
#[command(
    name = "harness",
    version,
    about = "BLINDSIDE headless runner, desync canary and replay tooling",
    after_help = EXIT_CODES
)]
struct Cli {
    /// Content pack directory records are validated against (default: <workspace>/content,
    /// which may be absent -- that is the empty pack). A directory named here must exist.
    #[arg(long, global = true, value_name = "DIR")]
    content: Option<PathBuf>,
    #[command(subcommand)]
    cmd: Cmd,
}

/// The hash-log flags shared by run, record, verify and canary.
#[derive(Args)]
struct LogArgs {
    /// Write the hash log here: plain text, one `tick,hash` line per logged tick, so
    /// `diff` works. verify and canary write one by default (<record stem>.hashlog in the
    /// current directory); run and record only when asked.
    #[arg(long, value_name = "PATH")]
    hash_log: Option<PathBuf>,
    /// Hash and log every N ticks instead of every tick. Tick 0 and the final tick are
    /// always kept. (The canary still compares every tick; this thins only its log.)
    #[arg(long, value_name = "N", default_value_t = 1)]
    hash_every: u64,
}

#[derive(Subcommand)]
enum Cmd {
    /// Run a record to its tick count with no renderer; print final tick, final hash,
    /// wall-clock, ticks/s, hash cost per tick and the matches/hour extrapolation.
    Run {
        /// Path to the MatchRecord
        record: PathBuf,
        #[command(flatten)]
        log: LogArgs,
        /// Write diagnostics::dump of the state at this tick to <record stem>.tick<N>.dump
        #[arg(long, value_name = "TICK")]
        dump_state_at: Option<u64>,
    },
    /// Run a fresh empty match and write its MatchRecord with final_hash filled in.
    Record {
        #[arg(long)]
        seed: u64,
        #[arg(long)]
        ticks: u64,
        /// Where to write the MatchRecord
        #[arg(long)]
        out: PathBuf,
        #[command(flatten)]
        log: LogArgs,
    },
    /// Re-run a record and compare the final state hash to the recorded one; refuses a
    /// record from another content pack. Writes the hash log by default.
    Verify {
        record: PathBuf,
        #[command(flatten)]
        log: LogArgs,
    },
    /// Two sims from one record via Sim::new, stepped in lockstep, hashes compared every
    /// tick. Writes instance A's hash log by default.
    Canary {
        /// The MatchRecord both instances are built from
        #[arg(long)]
        record: PathBuf,
        #[command(flatten)]
        log: LogArgs,
        /// Arm the BLD-35 fixture in both instances: on the injection tick each folds a
        /// fresh HashMap's iteration order into hashed state. Needs a build with the
        /// sim's `inject-desync` feature (exit 2 otherwise). Proves the canary catches
        /// the classic desync in the tick it happens.
        #[arg(long)]
        injected: bool,
        /// Tick on which to inject (default: 5000). Requires --injected.
        #[arg(long, requires = "injected")]
        inject_tick: Option<u64>,
        /// Where to write the divergence report (record, tick, both hashes, diff) on
        /// failure. Feed it to `bisect --from-divergence`.
        #[arg(long, default_value = "divergence.json")]
        divergence: PathBuf,
    },
    /// Re-run a record locally and find the first tick whose hash differs from a foreign
    /// side; dump the local state there.
    #[command(after_help = BISECT_HELP, group = ArgGroup::new("side").required(true).multiple(false))]
    Bisect {
        /// Path to the MatchRecord (not needed with --from-divergence, which carries it)
        #[arg(long, required_unless_present = "from_divergence")]
        record: Option<PathBuf>,
        /// The foreign side: a plain `tick,hash` log recorded elsewhere, at any cadence
        #[arg(long, group = "side", value_name = "PATH")]
        hash_log: Option<PathBuf>,
        /// The foreign side: the BLD-35 fixture (canary in bisect mode). Needs a build
        /// with the sim's `inject-desync` feature.
        #[arg(long, group = "side")]
        injected: bool,
        /// Tick on which to inject (default: 5000). Requires --injected.
        #[arg(long, requires = "injected")]
        inject_tick: Option<u64>,
        /// With --injected: record the foreign checkpoint log every N ticks, so the
        /// checkpoint-then-linear narrowing is exercised (default: every tick).
        #[arg(long, requires = "injected", value_name = "N", default_value_t = 1)]
        hash_every: u64,
        /// Reproduce a `divergence.json` written by `canary`
        #[arg(long, group = "side", value_name = "PATH")]
        from_divergence: Option<PathBuf>,
    },
    /// Print the field-level diff of two state dumps (from `run --dump-state-at` or
    /// `bisect`), typically from two machines.
    DiffDumps { a: PathBuf, b: PathBuf },
    /// One empty match per seed, at most J in parallel; write a `seed,final_hash` table
    /// sorted by seed and report throughput.
    Batch {
        /// Seed range: `A..B` (B excluded, as in Rust) or `A..=B` (B included)
        #[arg(long, value_name = "A..B")]
        seeds: String,
        /// Ticks per match (default: one Phase 1 match, 20 Hz x 480 s)
        #[arg(long, default_value_t = TICKS_PER_MATCH)]
        ticks: u64,
        /// Matches to run at once (default: the machine's parallelism)
        #[arg(long, value_name = "J")]
        jobs: Option<usize>,
        /// Where to write the table
        #[arg(long)]
        out: PathBuf,
    },
    /// Print crates/blindside-sim/src/golden_tables.rs (RNG and Fx golden tables) to
    /// stdout. Redirect it over the checked-in file, then `cargo fmt --all`.
    Golden,
}

fn main() -> ExitCode {
    match dispatch(Cli::parse()) {
        Ok(code) => code,
        Err(msg) => {
            eprintln!("harness: error: {msg}");
            ExitCode::from(2)
        }
    }
}

/// Where the content pack is for this invocation.
///
/// DEFAULT (awaiting designer): an explicit `--content DIR` naming a directory that does
/// not exist is a usage error (exit 2), while the built-in default path may be absent.
/// The asymmetry is deliberate. Phase 0 ships no `content/` directory and the empty pack
/// IS the pack, so the default must stay lenient (blindside-content: "a pack root that
/// does not exist on disk loads as the empty pack"). But a path a human typed is a
/// claim that the pack is there: from Phase 3 a typo would be indistinguishable from
/// "no content", and the record would be validated -- and pass -- against the wrong pack.
/// Today that is harmless because every absent pack is the empty pack; it is cheap now
/// and impossible to retrofit once fixtures exist for several packs.
fn content_dir(flag: Option<PathBuf>) -> Result<PathBuf, String> {
    match flag {
        Some(dir) if !dir.is_dir() => Err(format!(
            "--content {}: no such directory. (The built-in default may be absent -- \
             that is the empty pack -- but a directory named on the command line must \
             exist.)",
            dir.display()
        )),
        Some(dir) => Ok(dir),
        None => Ok(default_content_dir()),
    }
}

fn dispatch(cli: Cli) -> Result<ExitCode, String> {
    let content = content_dir(cli.content)?;
    match cli.cmd {
        Cmd::Run {
            record,
            log,
            dump_state_at,
        } => cmd_run(&content, &record, &log, dump_state_at),
        Cmd::Record {
            seed,
            ticks,
            out,
            log,
        } => cmd_record(&content, seed, ticks, &out, &log),
        Cmd::Verify { record, log } => cmd_verify(&content, &record, &log),
        Cmd::Canary {
            record,
            log,
            injected,
            inject_tick,
            divergence,
        } => {
            let inject = injected.then(|| Inject {
                tick: inject_tick.unwrap_or(DEFAULT_INJECT_TICK),
            });
            cmd_canary(&content, &record, &log, inject, &divergence)
        }
        Cmd::Bisect {
            record,
            hash_log,
            injected,
            inject_tick,
            hash_every,
            from_divergence,
        } => match (from_divergence, record, hash_log, injected) {
            (Some(div), _, _, _) => cmd_bisect_divergence(&div),
            (None, Some(record), Some(log), false) => cmd_bisect_log(&content, &record, &log),
            (None, Some(record), None, true) => cmd_bisect_injected(
                &content,
                &record,
                inject_tick.unwrap_or(DEFAULT_INJECT_TICK),
                hash_every,
            ),
            _ => Err(
                "bisect needs --record with --hash-log or --injected, or --from-divergence".into(),
            ),
        },
        Cmd::DiffDumps { a, b } => cmd_diff_dumps(&a, &b),
        Cmd::Batch {
            seeds,
            ticks,
            jobs,
            out,
        } => cmd_batch(&content, &seeds, ticks, jobs, &out),
        Cmd::Golden => {
            print!("{}", golden::render());
            Ok(ExitCode::SUCCESS)
        }
    }
}

fn secs(d: Duration) -> String {
    format!("{:.3}s", d.as_secs_f64())
}

fn brief(d: Duration) -> String {
    let ns = d.as_nanos();
    if ns < 10_000 {
        format!("{ns} ns")
    } else if ns < 10_000_000 {
        format!("{:.1} us", ns as f64 / 1e3)
    } else {
        format!("{:.1} ms", ns as f64 / 1e6)
    }
}

fn stem(path: &Path) -> String {
    path.file_stem()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_else(|| "record".to_string())
}

/// `<record stem>.hashlog` in the current directory.
fn default_log_path(record: &Path) -> PathBuf {
    PathBuf::from(format!("{}.hashlog", stem(record)))
}

/// `<record stem>.tick<N>.dump` in the current directory.
fn dump_path(record: &Path, tick: u64) -> PathBuf {
    PathBuf::from(format!("{}.tick{tick}.dump", stem(record)))
}

fn save_log(log: &HashLog, path: &Path) -> Result<(), String> {
    log.save(path)?;
    println!(
        "hash log: {}  ({} line(s), {})",
        path.display(),
        log.len(),
        log.describe()
    );
    Ok(())
}

fn cmd_run(
    content: &Path,
    record: &Path,
    log: &LogArgs,
    dump_state_at: Option<u64>,
) -> Result<ExitCode, String> {
    let rec = MatchRecord::load(record, content)?;
    let sim_rec = rec.to_sim()?;
    if let Some(t) = dump_state_at {
        if t > rec.ticks {
            return Err(format!(
                "--dump-state-at {t} is past the record's {} ticks",
                rec.ticks
            ));
        }
    }
    let out = runner::run_measured(&sim_rec, log.hash_every, dump_state_at);
    let step_time = out.step_time.expect("measured");
    println!(
        "record: {}  (seed {}, {} ticks)",
        record.display(),
        rec.seed,
        rec.ticks
    );
    println!("final tick: {}", out.ticks);
    println!("final hash: {}", out.final_hash);
    println!("recorded  : {}", rec.final_hash);
    println!(
        "wall-clock: {}  (step-only pass {}, hashing pass {})",
        secs(step_time + out.hashed_time),
        secs(step_time),
        secs(out.hashed_time)
    );
    println!(
        "ticks/s: {:.0}  => {:.0} matches/hour at {TICKS_PER_MATCH} ticks/match",
        out.ticks_per_second(),
        out.matches_per_hour()
    );
    println!(
        "hash cost per tick: {}  ({} hashes, {}; {} of the hashing pass)",
        brief(out.hash_cost().expect("measured")),
        out.hashes,
        out.cadence,
        secs(out.hashed_time.saturating_sub(step_time))
    );
    if let Some(path) = &log.hash_log {
        save_log(&out.log, path)?;
    }
    if let Some((tick, text)) = &out.dump {
        let path = dump_path(record, *tick);
        std::fs::write(&path, text).map_err(|e| format!("cannot write {}: {e}", path.display()))?;
        println!("state at tick {tick} written to {}:", path.display());
        for line in text.lines() {
            println!("  {line}");
        }
    }
    if out.final_hash == rec.final_hash {
        println!("OK: final hash matches record");
        Ok(ExitCode::SUCCESS)
    } else {
        println!("MISMATCH: final hash differs from record");
        Ok(ExitCode::from(1))
    }
}

fn cmd_record(
    content: &Path,
    seed: u64,
    ticks: u64,
    out: &Path,
    log: &LogArgs,
) -> Result<ExitCode, String> {
    let content_hash = content_hash_of(content)?;
    let (rec, hashes) = runner::record(seed, ticks, log.hash_every, content_hash);
    rec.save(out)?;
    println!("recorded seed {seed}, {ticks} ticks");
    println!("record: {}", out.display());
    println!("content hash: {}", rec.content_hash);
    println!("final hash: {}", rec.final_hash);
    if let Some(path) = &log.hash_log {
        save_log(&hashes, path)?;
    }
    Ok(ExitCode::SUCCESS)
}

fn cmd_verify(content: &Path, record: &Path, log: &LogArgs) -> Result<ExitCode, String> {
    let rec = MatchRecord::load(record, content)?;
    let sim_rec = rec.to_sim()?;
    let out = runner::run(&sim_rec, log.hash_every, None);
    println!(
        "verify: {}  (seed {}, {} ticks)",
        record.display(),
        rec.seed,
        rec.ticks
    );
    println!("final hash: {}", out.final_hash);
    println!("recorded  : {}", rec.final_hash);
    println!("wall-clock: {}", secs(out.hashed_time));
    let path = log
        .hash_log
        .clone()
        .unwrap_or_else(|| default_log_path(record));
    save_log(&out.log, &path)?;
    if out.final_hash == rec.final_hash {
        println!("OK: final hash matches record");
        Ok(ExitCode::SUCCESS)
    } else {
        println!("MISMATCH: final hash differs from record");
        Ok(ExitCode::from(1))
    }
}

fn cmd_canary(
    content: &Path,
    record: &Path,
    log: &LogArgs,
    inject: Option<Inject>,
    divergence_path: &Path,
) -> Result<ExitCode, String> {
    let rec = MatchRecord::load(record, content)?;
    println!(
        "canary: {}  (seed {}, {} ticks), two instances in lockstep",
        record.display(),
        rec.seed,
        rec.ticks
    );
    let run = canary::run(&rec, inject, log.hash_every, |t| {
        println!(
            "injected at tick {t}: both instances folded a fresh HashMap's iteration order \
             into World.inject_fold"
        );
    })
    .map_err(|e| e.to_string())?;
    let log_path = log
        .hash_log
        .clone()
        .unwrap_or_else(|| default_log_path(record));
    match run.outcome {
        Ok(ok) => {
            println!("OK: {} ticks, hashes identical every tick", ok.ticks);
            println!("final hash: {}", ok.final_hash);
            println!("wall-clock: {}", secs(run.elapsed));
            save_log(&run.log, &log_path)?;
            Ok(ExitCode::SUCCESS)
        }
        Err(div) => {
            print!("{div}");
            div.save(divergence_path)?;
            println!("divergence written to {}", divergence_path.display());
            println!(
                "reproduce with: harness bisect --from-divergence {}",
                divergence_path.display()
            );
            println!("wall-clock: {}", secs(run.elapsed));
            save_log(&run.log, &log_path)?;
            Ok(ExitCode::from(1))
        }
    }
}

fn report_located(record: &Path, located: Located) -> Result<ExitCode, String> {
    match located {
        Located::Clean { ticks, checkpoints } => {
            println!("OK: {ticks} ticks, none of {checkpoints} checkpoint(s) differs from the recorded hashes");
            Ok(ExitCode::SUCCESS)
        }
        Located::Divergent(d) => {
            print!("{d}");
            let path = dump_path(record, d.tick);
            std::fs::write(&path, &d.state.dump)
                .map_err(|e| format!("cannot write {}: {e}", path.display()))?;
            println!(
                "dump of the local state at tick {} written to {}",
                d.tick,
                path.display()
            );
            Ok(ExitCode::from(1))
        }
    }
}

fn cmd_bisect_log(content: &Path, record: &Path, hash_log: &Path) -> Result<ExitCode, String> {
    let rec = MatchRecord::load(record, content)?;
    let log = HashLog::load(hash_log)?;
    println!(
        "bisect: {}  (seed {}, {} ticks), local re-run vs {}  ({})",
        record.display(),
        rec.seed,
        rec.ticks,
        hash_log.display(),
        log.describe()
    );
    let located = bisect::locate(&rec, Foreign::Log(&log))?;
    report_located(record, located)
}

fn cmd_bisect_injected(
    content: &Path,
    record: &Path,
    tick: u64,
    every: u64,
) -> Result<ExitCode, String> {
    let rec = MatchRecord::load(record, content)?;
    println!(
        "bisect: {}  (seed {}, {} ticks), both instances armed for tick {tick}; foreign \
         checkpoints every {} tick(s)",
        record.display(),
        rec.seed,
        rec.ticks,
        every.max(1)
    );
    let located = bisect::locate(&rec, Foreign::Injected { tick, every })?;
    report_located(record, located)
}

fn cmd_bisect_divergence(path: &Path) -> Result<ExitCode, String> {
    let div = Divergence::load(path)?;
    println!(
        "bisect: reproducing {} (seed {}, {} ticks, divergence at tick {})",
        path.display(),
        div.record.seed,
        div.record.ticks,
        div.tick
    );
    match &div.injection {
        Some(inj) => println!("  recorded injection at tick {}", inj.tick),
        None => println!("  no injection recorded: a real desync between two instances"),
    }
    let repro = bisect::reproduce(&div)?;
    println!("recorded divergence:");
    print!("{div}");
    println!(
        "fresh local instance at tick {}: hash {}  (matches A: {}, matches B: {})",
        div.tick, repro.local.hash, repro.matches_a, repro.matches_b
    );
    let reproduced = repro.reproduced(&div);
    if let Some(rerun) = &repro.rerun {
        match rerun {
            Ok(run) => match &run.outcome {
                Err(again) => {
                    println!("re-run with the recorded injection:");
                    print!("{again}");
                    println!(
                        "  (fresh HashMap orders on both sides, so the hashes are new; the tick is \
                         what must repeat)"
                    );
                }
                Ok(ok) => println!(
                    "re-run with the recorded injection did NOT diverge ({} ticks, final hash {})",
                    ok.ticks, ok.final_hash
                ),
            },
            Err(e) => println!("re-run with the recorded injection failed: {e}"),
        }
    }
    if reproduced {
        println!("REPRODUCED: divergence at tick {}", div.tick);
        Ok(ExitCode::from(1))
    } else {
        println!(
            "NOT REPRODUCED: the recorded injection no longer diverges at tick {}",
            div.tick
        );
        Ok(ExitCode::SUCCESS)
    }
}

fn cmd_diff_dumps(a: &Path, b: &Path) -> Result<ExitCode, String> {
    let da = Dump::load(a)?;
    let db = Dump::load(b)?;
    let d = dump::diff(&da, &db);
    println!("diff-dumps: A = {}  B = {}", a.display(), b.display());
    if d.is_empty() {
        println!("OK: identical ({} field(s))", da.fields.len());
        Ok(ExitCode::SUCCESS)
    } else {
        println!("{} differing field(s):", d.len());
        print!("{}", DiffText(&d, "A", "B"));
        Ok(ExitCode::from(1))
    }
}

/// `A..B` (B excluded) or `A..=B` (B included), non-empty.
fn parse_seed_range(s: &str) -> Result<Vec<u64>, String> {
    let (a, b, inclusive) = if let Some((a, b)) = s.split_once("..=") {
        (a, b, true)
    } else if let Some((a, b)) = s.split_once("..") {
        (a, b, false)
    } else {
        return Err(format!("--seeds {s}: expected A..B or A..=B"));
    };
    let first: u64 = a
        .trim()
        .parse()
        .map_err(|e| format!("--seeds {s}: bad start `{a}`: {e}"))?;
    let end: u64 = b
        .trim()
        .parse()
        .map_err(|e| format!("--seeds {s}: bad end `{b}`: {e}"))?;
    let last = if inclusive {
        Some(end)
    } else {
        end.checked_sub(1)
    };
    match last {
        Some(last) if last >= first => Ok((first..=last).collect()),
        _ => Err(format!("--seeds {s}: empty range")),
    }
}

fn cmd_batch(
    content: &Path,
    seeds: &str,
    ticks: u64,
    jobs: Option<usize>,
    out: &Path,
) -> Result<ExitCode, String> {
    let seeds = parse_seed_range(seeds)?;
    let jobs = jobs.unwrap_or_else(|| {
        std::thread::available_parallelism()
            .map(|n| n.get())
            .unwrap_or(1)
    });
    let content_hash = content_hash_of(content)?;
    let result = runner::batch(&seeds, ticks, jobs, content_hash);
    std::fs::write(out, result.table())
        .map_err(|e| format!("cannot write {}: {e}", out.display()))?;
    println!(
        "batch: {} seed(s) {}..={} x {} ticks, {} job(s)",
        seeds.len(),
        seeds[0],
        seeds[seeds.len() - 1],
        ticks,
        result.jobs
    );
    println!("elapsed: {}", secs(result.elapsed));
    println!(
        "matches/hour: {:.0}  aggregate ticks/s: {:.0}",
        result.matches_per_hour(),
        result.ticks_per_second()
    );
    println!(
        "table: {}  ({} line(s), seed,final_hash sorted by seed)",
        out.display(),
        result.rows.len()
    );
    Ok(ExitCode::SUCCESS)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn seed_ranges_follow_rust_syntax() {
        assert_eq!(parse_seed_range("0..3").unwrap(), [0, 1, 2]);
        assert_eq!(parse_seed_range("0..=3").unwrap(), [0, 1, 2, 3]);
        assert_eq!(parse_seed_range("7..=7").unwrap(), [7]);
        assert!(parse_seed_range("3..3").unwrap_err().contains("empty"));
        assert!(parse_seed_range("5..=4").unwrap_err().contains("empty"));
        assert!(parse_seed_range("5").unwrap_err().contains("A..B"));
        assert!(parse_seed_range("x..3").is_err());
    }

    #[test]
    fn default_paths_are_named_after_the_record_stem() {
        let r = Path::new("fixtures/phase0-empty-10k.record");
        assert_eq!(
            default_log_path(r),
            PathBuf::from("phase0-empty-10k.hashlog")
        );
        assert_eq!(
            dump_path(r, 42),
            PathBuf::from("phase0-empty-10k.tick42.dump")
        );
    }

    #[test]
    fn durations_print_briefly() {
        assert_eq!(brief(Duration::from_nanos(312)), "312 ns");
        assert_eq!(brief(Duration::from_nanos(12_500)), "12.5 us");
        assert_eq!(brief(Duration::from_millis(31)), "31.0 ms");
    }
}
