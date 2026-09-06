//! `harness` — CLI over blindside-harness.
//!
//! Exit codes: 0 success; 1 a determinism failure was detected (canary divergence,
//! replay hash mismatch); 2 could not run (bad arguments, unreadable or invalid files).

use std::path::{Path, PathBuf};
use std::process::ExitCode;

use clap::{Parser, Subcommand};

use blindside_harness::bisect::{self, Located};
use blindside_harness::canary::{self, Divergence, Inject};
use blindside_harness::record::{HashLog, MatchRecord};
use blindside_harness::runner::{self, VerifyOutcome};

const DEFAULT_SEED: u64 = 0xDEAD_BEEF;

#[derive(Parser)]
#[command(
    name = "harness",
    version,
    about = "BLINDSIDE headless runner, desync canary and replay tooling"
)]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Load a MatchRecord, run it to its tick count, print the final hash and throughput.
    Run {
        /// Path to replay.json
        replay: PathBuf,
    },
    /// Two sims from identical inputs, stepped in lockstep, hashes compared every tick.
    Canary {
        /// Number of ticks to run
        #[arg(long)]
        ticks: u64,
        /// Seed for both instances
        #[arg(long, default_value_t = DEFAULT_SEED)]
        seed: u64,
        /// Deliberately perturb instance B on one tick using a HashMap iteration order,
        /// to prove the canary catches it in that tick
        #[arg(long)]
        inject: bool,
        /// Tick on which to inject (default: ticks / 2). Requires --inject.
        #[arg(long, requires = "inject")]
        inject_tick: Option<u64>,
        /// Where to write the divergence report (tick, both hashes, diff) on failure.
        /// Feed it to `bisect --from-divergence`.
        #[arg(long, default_value = "divergence.json")]
        divergence: PathBuf,
    },
    /// Run a match and write replay.json plus a per-tick hash sidecar.
    Record {
        #[arg(long)]
        seed: u64,
        #[arg(long)]
        ticks: u64,
        /// Where to write the MatchRecord
        #[arg(long)]
        out: PathBuf,
        /// Where to write the per-tick hashes (default: <out stem>.hashes.json)
        #[arg(long)]
        hashes: Option<PathBuf>,
    },
    /// Re-run a replay and check every per-tick hash against the sidecar.
    Verify { replay: PathBuf, hashes: PathBuf },
    /// Re-run a replay locally, binary-search the first tick whose hash differs from a
    /// hash log recorded elsewhere, and dump the state diff at that tick.
    Bisect {
        /// Path to replay.json
        #[arg(
            required_unless_present = "from_divergence",
            conflicts_with = "from_divergence"
        )]
        replay: Option<PathBuf>,
        /// Path to the per-tick hash log recorded on the other side
        #[arg(
            required_unless_present = "from_divergence",
            conflicts_with = "from_divergence"
        )]
        hashes: Option<PathBuf>,
        /// Reproduce a `divergence.json` written by `canary` instead of bisecting a log
        #[arg(long)]
        from_divergence: Option<PathBuf>,
    },
    /// Run N sequential matches of T ticks and report matches per hour.
    Batch {
        #[arg(long)]
        matches: u64,
        #[arg(long)]
        ticks: u64,
        /// Seed of the first match; match i uses seed + i
        #[arg(long, default_value_t = DEFAULT_SEED)]
        seed: u64,
    },
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

fn dispatch(cli: Cli) -> Result<ExitCode, String> {
    match cli.cmd {
        Cmd::Run { replay } => cmd_run(&replay),
        Cmd::Canary {
            ticks,
            seed,
            inject,
            inject_tick,
            divergence,
        } => cmd_canary(seed, ticks, inject, inject_tick, &divergence),
        Cmd::Record {
            seed,
            ticks,
            out,
            hashes,
        } => cmd_record(seed, ticks, &out, hashes),
        Cmd::Verify { replay, hashes } => cmd_verify(&replay, &hashes),
        Cmd::Bisect {
            replay,
            hashes,
            from_divergence,
        } => match (from_divergence, replay, hashes) {
            (Some(div), _, _) => cmd_bisect_divergence(&div),
            (None, Some(replay), Some(hashes)) => cmd_bisect(&replay, &hashes),
            _ => Err("bisect needs <REPLAY> <HASHES> or --from-divergence".into()),
        },
        Cmd::Batch {
            matches,
            ticks,
            seed,
        } => Ok(cmd_batch(seed, matches, ticks)),
    }
}

fn cmd_run(replay: &Path) -> Result<ExitCode, String> {
    let rec = MatchRecord::load(replay)?;
    let out = runner::run(&rec);
    println!("replay: {}", replay.display());
    println!("seed: {}  ticks: {}", rec.seed, out.ticks);
    println!("final hash: {}", out.final_hash);
    println!("recorded  : {}", rec.final_hash);
    println!(
        "ticks/s: {:.0}  (elapsed {:.3}s)",
        out.ticks_per_second(),
        out.elapsed.as_secs_f64()
    );
    if out.final_hash == rec.final_hash {
        println!("OK: final hash matches record");
        Ok(ExitCode::SUCCESS)
    } else {
        println!("MISMATCH: final hash differs from record");
        Ok(ExitCode::from(1))
    }
}

fn cmd_canary(
    seed: u64,
    ticks: u64,
    inject: bool,
    inject_tick: Option<u64>,
    divergence_path: &Path,
) -> Result<ExitCode, String> {
    let inject = if inject {
        let t = inject_tick.unwrap_or(ticks / 2);
        if t > ticks {
            return Err(format!("--inject-tick {t} is past --ticks {ticks}"));
        }
        Some(Inject {
            tick: t,
            order: None,
        })
    } else {
        None
    };
    println!("canary: seed {seed}, {ticks} ticks, two instances in lockstep");
    let result = canary::run(seed, ticks, inject, |t, order, touched| {
        println!(
            "injected at tick {t}: perturbed instance B with HashMap iteration order \
             {order:?} ({touched} agent(s) touched)"
        );
    });
    match result {
        Ok(ok) => {
            println!("OK: {} ticks, hashes identical every tick", ok.ticks);
            println!("final hash: {}", ok.final_hash);
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
            Ok(ExitCode::from(1))
        }
    }
}

fn cmd_bisect(replay: &Path, hashes: &Path) -> Result<ExitCode, String> {
    let rec = MatchRecord::load(replay)?;
    let log = HashLog::load(hashes)?;
    println!(
        "bisect: seed {}, {} ticks, local re-run vs {}",
        rec.seed,
        rec.ticks,
        hashes.display()
    );
    match bisect::locate(&rec, &log)? {
        Located::Clean { ticks } => {
            println!("OK: {ticks} ticks, no tick differs from the recorded hashes");
            Ok(ExitCode::SUCCESS)
        }
        Located::Divergent {
            tick,
            recorded,
            local,
            mode,
            probes,
        } => {
            println!("DIVERGENCE at tick {tick}  (found by {mode}, {probes} re-run(s))");
            println!("  recorded: {recorded}");
            println!("  local   : {local}");
            if tick > 0 {
                println!("  tick {} matched on both sides", tick - 1);
            }
            let state = bisect::replay_to(&rec, tick);
            debug_assert_eq!(state.hash, local);
            print!("{state}");
            println!(
                "the recorded side supplied hashes only; the diff above is the local \
                 instance's change across the divergent tick"
            );
            Ok(ExitCode::from(1))
        }
    }
}

fn cmd_bisect_divergence(path: &Path) -> Result<ExitCode, String> {
    let div = Divergence::load(path)?;
    println!(
        "bisect: reproducing {} (seed {}, {} ticks, divergence at tick {})",
        path.display(),
        div.seed,
        div.ticks,
        div.tick
    );
    match &div.injection {
        Some(inj) => println!(
            "  recorded injection at tick {} with order {:?}",
            inj.tick, inj.order
        ),
        None => println!("  no injection recorded: a real desync between two instances"),
    }
    let repro = bisect::reproduce(&div);
    println!("recorded divergence:");
    print!("{div}");
    println!(
        "fresh local instance at tick {}: hash {}  (matches A: {}, matches B: {})",
        div.tick, repro.local.hash, repro.matches_a, repro.matches_b
    );
    let reproduced = repro.reproduced(&div);
    if let Some(rerun) = &repro.rerun {
        match rerun {
            Err(again) => {
                println!("re-run with the recorded injection:");
                print!("{again}");
                if again.diff == div.diff {
                    println!("  diff identical to the recorded one");
                }
            }
            Ok(ok) => println!(
                "re-run with the recorded injection did NOT diverge ({} ticks, final hash {})",
                ok.ticks, ok.final_hash
            ),
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

fn default_hashes_path(out: &Path) -> PathBuf {
    let stem = out
        .file_stem()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_else(|| "replay".to_string());
    out.with_file_name(format!("{stem}.hashes.json"))
}

fn cmd_record(
    seed: u64,
    ticks: u64,
    out: &Path,
    hashes: Option<PathBuf>,
) -> Result<ExitCode, String> {
    let hashes = hashes.unwrap_or_else(|| default_hashes_path(out));
    let (rec, log) = runner::record(seed, ticks);
    rec.save(out)?;
    log.save(&hashes)?;
    println!("recorded seed {seed}, {ticks} ticks");
    println!("replay: {}", out.display());
    println!(
        "hashes: {}  ({} entries, ticks 0..={})",
        hashes.display(),
        log.hashes.len(),
        ticks
    );
    println!("content hash: {}", rec.content_hash);
    println!("final hash: {}", rec.final_hash);
    Ok(ExitCode::SUCCESS)
}

fn cmd_verify(replay: &Path, hashes: &Path) -> Result<ExitCode, String> {
    let rec = MatchRecord::load(replay)?;
    let log = HashLog::load(hashes)?;
    match runner::verify(&rec, &log)? {
        VerifyOutcome::Ok { ticks, final_hash } => {
            println!("OK: {ticks} ticks, every per-tick hash matches");
            println!("final hash: {final_hash}");
            Ok(ExitCode::SUCCESS)
        }
        VerifyOutcome::Mismatch {
            tick,
            expected,
            actual,
        } => {
            println!("MISMATCH at tick {tick}");
            println!("  expected: {expected}");
            println!("  actual  : {actual}");
            Ok(ExitCode::from(1))
        }
    }
}

fn cmd_batch(seed: u64, matches: u64, ticks: u64) -> ExitCode {
    let out = runner::batch(seed, matches, ticks);
    println!(
        "batch: {} matches x {} ticks, seeds {}..={}",
        out.matches,
        out.ticks_per_match,
        seed,
        seed.wrapping_add(matches.saturating_sub(1))
    );
    println!("elapsed: {:.3}s", out.elapsed.as_secs_f64());
    println!("matches/hour: {:.0}", out.matches_per_hour());
    println!("ticks/s: {:.0}", out.ticks_per_second());
    println!("digest: {}", out.digest);
    ExitCode::SUCCESS
}
