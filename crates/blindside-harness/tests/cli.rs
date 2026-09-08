//! End-to-end tests of the `harness` binary, driven through its CLI exactly the way CI
//! will drive it. The binary under test is built with the sim's `inject-desync` feature
//! (through this crate's dev-dependency), so `--injected` exercises the real fixture.
//!
//! Every test runs in its own scratch directory, which is also the working directory of
//! the harness it spawns, so the default output names (`<stem>.hashlog`,
//! `<stem>.tick<N>.dump`, `divergence.json`) land there and are removed afterwards.

use std::path::{Path, PathBuf};
use std::process::{Command, Output};

fn harness() -> Command {
    Command::new(env!("CARGO_BIN_EXE_harness"))
}

fn text(out: &Output) -> String {
    format!(
        "{}{}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    )
}

/// First integer following `prefix` in `s`.
fn number_after(s: &str, prefix: &str) -> Option<u64> {
    let i = s.find(prefix)? + prefix.len();
    let digits: String = s[i..].chars().take_while(|c| c.is_ascii_digit()).collect();
    digits.parse().ok()
}

/// First decimal number following `prefix` in `s`.
fn float_after(s: &str, prefix: &str) -> Option<f64> {
    let i = s.find(prefix)? + prefix.len();
    let digits: String = s[i..]
        .chars()
        .take_while(|c| c.is_ascii_digit() || *c == '.')
        .collect();
    digits.parse().ok()
}

fn fixture() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("fixtures")
        .join("phase0-empty-10k.record")
}

/// Fresh scratch directory per test; removed on drop.
struct Scratch(PathBuf);

impl Scratch {
    fn new(name: &str) -> Scratch {
        let dir = std::env::temp_dir().join(format!(
            "blindside-harness-test-{}-{name}",
            std::process::id()
        ));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        Scratch(dir)
    }

    fn path(&self, file: &str) -> PathBuf {
        self.0.join(file)
    }

    /// The harness with this directory as its working directory.
    fn harness(&self) -> Command {
        let mut c = harness();
        c.current_dir(&self.0);
        c
    }

    /// `record --seed S --ticks N --out <name>` here; returns the record's path.
    fn record(&self, name: &str, seed: u64, ticks: u64) -> PathBuf {
        let path = self.path(name);
        let out = self
            .harness()
            .args([
                "record",
                "--seed",
                &seed.to_string(),
                "--ticks",
                &ticks.to_string(),
            ])
            .arg("--out")
            .arg(&path)
            .output()
            .unwrap();
        assert!(out.status.success(), "record failed:\n{}", text(&out));
        path
    }
}

impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn read(path: &Path) -> String {
    std::fs::read_to_string(path).unwrap_or_else(|e| panic!("{}: {e}", path.display()))
}

fn json(path: &Path) -> serde_json::Value {
    serde_json::from_str(&read(path)).unwrap()
}

fn write_json(path: &Path, v: &serde_json::Value) {
    std::fs::write(path, serde_json::to_string_pretty(v).unwrap()).unwrap();
}

/// Flip the first hex digit of every `tick,hash` line whose tick is at least `from`.
fn tamper_log(path: &Path, from: u64) {
    let tampered: String = read(path)
        .lines()
        .map(|line| {
            let (tick, hash) = line.split_once(',').unwrap();
            if tick.parse::<u64>().unwrap() >= from {
                let flipped = if hash.starts_with('0') { "1" } else { "0" };
                format!("{tick},{flipped}{}\n", &hash[1..])
            } else {
                format!("{line}\n")
            }
        })
        .collect();
    std::fs::write(path, tampered).unwrap();
}

// ---- run ----------------------------------------------------------------------------

#[test]
fn run_prints_the_throughput_numbers_and_matches_the_fixture() {
    let s = Scratch::new("run");
    let out = s.harness().arg("run").arg(fixture()).output().unwrap();
    let t = text(&out);
    assert!(out.status.success(), "{t}");
    assert!(t.contains("final tick: 10000"), "{t}");
    assert!(
        t.contains("final hash: 653b9057c4dd809407213920a217794adafd41c7ea92976e6bf344b76a5639bc"),
        "{t}"
    );
    assert!(t.contains("wall-clock: "), "{t}");
    assert!(t.contains("ticks/s: "), "{t}");
    assert!(t.contains("matches/hour at 9600 ticks/match"), "{t}");
    assert!(t.contains("hash cost per tick: "), "{t}");
    assert!(t.contains("10001 hashes, every tick"), "{t}");
    assert!(t.contains("OK: final hash matches record"), "{t}");
    // No hash log unless asked.
    assert!(!s.path("phase0-empty-10k.hashlog").exists());
}

#[test]
fn run_writes_a_plain_hash_log_on_the_requested_cadence_and_a_dump() {
    let s = Scratch::new("run-log");
    let log = s.path("dense.hashlog");
    let out = s
        .harness()
        .arg("run")
        .arg(fixture())
        .arg("--hash-log")
        .arg(&log)
        .args(["--dump-state-at", "42"])
        .output()
        .unwrap();
    let t = text(&out);
    assert!(out.status.success(), "{t}");
    let lines: Vec<String> = read(&log).lines().map(str::to_string).collect();
    assert_eq!(
        lines.len(),
        10_001,
        "one `tick,hash` line per tick 0..=10000"
    );
    assert!(lines[0].starts_with("0,"), "{}", lines[0]);
    assert_eq!(lines[0].len(), 2 + 64);
    assert!(lines[1000].starts_with("1000,"));
    assert_eq!(
        lines[1000],
        format!("1000,{}", blindside_harness::PIN_SEED_DEADBEEF_TICK_1000)
    );
    assert!(
        lines[10_000].ends_with("653b9057c4dd809407213920a217794adafd41c7ea92976e6bf344b76a5639bc")
    );
    assert!(!read(&log).contains('{'), "plain text, not JSON");
    let dump = s.path("phase0-empty-10k.tick42.dump");
    assert!(dump.is_file(), "{t}");
    let d = read(&dump);
    assert!(d.contains("tick = 42\n"), "{d}");
    assert!(d.contains("seed = 3735928559\n"), "{d}");
    assert!(t.contains("state at tick 42 written to "), "{t}");

    let sparse = s.path("sparse.hashlog");
    let out = s
        .harness()
        .arg("run")
        .arg(fixture())
        .arg("--hash-log")
        .arg(&sparse)
        .args(["--hash-every", "100"])
        .output()
        .unwrap();
    let t = text(&out);
    assert!(out.status.success(), "{t}");
    assert!(
        t.contains("101 hashes, every 100 ticks plus the final tick"),
        "{t}"
    );
    let sparse_lines: Vec<String> = read(&sparse).lines().map(str::to_string).collect();
    assert_eq!(sparse_lines.len(), 101);
    assert_eq!(sparse_lines[10], lines[1000]);
    assert_eq!(sparse_lines[100], lines[10_000]);
}

#[test]
fn run_refuses_a_dump_tick_past_the_record() {
    let s = Scratch::new("run-dump-range");
    let out = s
        .harness()
        .arg("run")
        .arg(fixture())
        .args(["--dump-state-at", "10001"])
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(2), "{}", text(&out));
}

// ---- record / verify --------------------------------------------------------------------

#[test]
fn record_writes_the_sorted_commands_form_and_verify_accepts_it() {
    let s = Scratch::new("record-verify");
    let replay = s.record("replay.json", 3735928559, 1000);
    // No hash log unless asked.
    assert!(!s.path("replay.hashlog").exists());

    let rec = json(&replay);
    assert_eq!(rec["seed"], 3735928559u64);
    assert_eq!(rec["ticks"], 1000);
    assert_eq!(rec["schema"], 0);
    assert_eq!(rec["loadouts"], serde_json::json!([]));
    assert_eq!(rec["policies"], serde_json::json!([]));
    assert_eq!(rec["commands"], serde_json::json!([]));
    let empty: String = blindside_content::EMPTY_PACK_HASH
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect();
    assert_eq!(rec["content_hash"], empty);
    assert_eq!(
        rec["final_hash"],
        blindside_harness::PIN_SEED_DEADBEEF_TICK_1000
    );
    assert!(!read(&replay).contains('\r'));

    let out = s.harness().arg("verify").arg(&replay).output().unwrap();
    let t = text(&out);
    assert!(out.status.success(), "{t}");
    assert!(t.contains("OK: final hash matches record"), "{t}");
    assert!(t.contains("wall-clock: "), "{t}");
    // verify writes the hash log by default, named after the record.
    let log = s.path("replay.hashlog");
    assert!(log.is_file(), "{t}");
    assert!(
        t.contains("hash log: replay.hashlog  (1001 line(s), 1001 entries, every tick to 1000)"),
        "{t}"
    );
    assert_eq!(read(&log).lines().count(), 1001);

    let out = s
        .harness()
        .arg("verify")
        .arg(&replay)
        .args(["--hash-every", "250", "--hash-log", "coarse.hashlog"])
        .output()
        .unwrap();
    assert!(out.status.success(), "{}", text(&out));
    assert_eq!(read(&s.path("coarse.hashlog")).lines().count(), 5);
}

#[test]
fn record_can_write_a_hash_log_too() {
    let s = Scratch::new("record-log");
    let replay = s.path("replay.json");
    let out = s
        .harness()
        .args(["record", "--seed", "7", "--ticks", "500", "--out"])
        .arg(&replay)
        .args(["--hash-log", "seven.hashlog"])
        .output()
        .unwrap();
    let t = text(&out);
    assert!(out.status.success(), "{t}");
    assert!(t.contains("hash log: seven.hashlog  (501 line(s)"), "{t}");
    let last = read(&s.path("seven.hashlog"))
        .lines()
        .last()
        .unwrap()
        .to_string();
    assert_eq!(
        last,
        format!("500,{}", json(&replay)["final_hash"].as_str().unwrap())
    );
}

#[test]
fn verify_reports_both_hashes_on_a_mismatch_and_exits_one() {
    let s = Scratch::new("verify-mismatch");
    let replay = s.record("replay.json", 9, 200);
    let mut rec = json(&replay);
    let orig = rec["final_hash"].as_str().unwrap().to_string();
    let flipped = if orig.starts_with('0') { "1" } else { "0" };
    let tampered = format!("{flipped}{}", &orig[1..]);
    rec["final_hash"] = serde_json::Value::String(tampered.clone());
    write_json(&replay, &rec);

    let out = s.harness().arg("verify").arg(&replay).output().unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(1), "{t}");
    assert!(
        t.contains("MISMATCH: final hash differs from record"),
        "{t}"
    );
    assert!(t.contains(&format!("final hash: {orig}")), "{t}");
    assert!(t.contains(&format!("recorded  : {tampered}")), "{t}");
}

#[test]
fn verify_rejects_a_record_with_a_foreign_content_hash() {
    let s = Scratch::new("content-hash");
    let replay = s.record("replay.json", 9, 20);
    let mut rec = json(&replay);
    rec["content_hash"] = serde_json::Value::String("00".repeat(32));
    write_json(&replay, &rec);

    let out = s.harness().arg("verify").arg(&replay).output().unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(2), "{t}");
    assert!(t.contains("content hash mismatch"), "{t}");
    assert!(t.contains(&"00".repeat(32)), "both hashes printed:\n{t}");
    let empty: String = blindside_content::EMPTY_PACK_HASH
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect();
    assert!(t.contains(&empty), "both hashes printed:\n{t}");
    assert!(!s.path("replay.hashlog").exists(), "nothing ran");
}

#[test]
fn verify_rejects_a_record_from_a_newer_schema_or_with_inputs() {
    let s = Scratch::new("schema");
    let replay = s.record("replay.json", 9, 20);
    let mut rec = json(&replay);
    rec["schema"] = serde_json::json!(7);
    write_json(&replay, &rec);
    let out = s.harness().arg("verify").arg(&replay).output().unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(2), "{t}");
    assert!(t.contains("record schema 7"), "{t}");

    let mut rec = json(&replay);
    rec["schema"] = serde_json::json!(0);
    rec["commands"] = serde_json::json!([{ "tick": 1, "team": 0, "sequence": 0 }]);
    write_json(&replay, &rec);
    let out = s.harness().arg("run").arg(&replay).output().unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(2), "{t}");
    assert!(
        t.contains("accepts no loadouts, policies or commands"),
        "{t}"
    );
}

#[test]
fn content_flag_selects_the_pack_a_record_is_checked_against() {
    let s = Scratch::new("content-dir");
    std::fs::create_dir_all(s.path("pack")).unwrap();
    std::fs::write(s.path("pack/one.txt"), b"x").unwrap();
    let replay = s.path("replay.json");
    let out = s
        .harness()
        .arg("--content")
        .arg(s.path("pack"))
        .args(["record", "--seed", "1", "--ticks", "10", "--out"])
        .arg(&replay)
        .output()
        .unwrap();
    assert!(out.status.success(), "{}", text(&out));
    let empty: String = blindside_content::EMPTY_PACK_HASH
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect();
    assert_ne!(json(&replay)["content_hash"], empty);
    // Against the default (empty) pack it is refused; against its own pack it verifies.
    let out = s.harness().arg("verify").arg(&replay).output().unwrap();
    assert_eq!(out.status.code(), Some(2), "{}", text(&out));
    let out = s
        .harness()
        .arg("verify")
        .arg(&replay)
        .arg("--content")
        .arg(s.path("pack"))
        .output()
        .unwrap();
    assert!(out.status.success(), "{}", text(&out));
}

/// A `--content` directory that is not there is a typo, not a pack. The built-in default
/// stays lenient (Phase 0 ships no `content/`, and the empty pack IS the pack), so the
/// asymmetry is what this pins: named and missing is exit 2, absent default is fine.
#[test]
fn a_named_content_directory_that_does_not_exist_is_a_usage_error() {
    let s = Scratch::new("content-missing");
    let missing = s.path("no-such-pack");
    for args in [
        vec!["run"],
        vec!["verify"],
        vec!["canary", "--record"],
        vec!["bisect", "--injected", "--record"],
    ] {
        let mut c = s.harness();
        c.args(&args).arg(fixture()).arg("--content").arg(&missing);
        let out = c.output().unwrap();
        let t = text(&out);
        assert_eq!(out.status.code(), Some(2), "{args:?}:\n{t}");
        assert!(t.contains("no such directory"), "{args:?}:\n{t}");
    }
    // The built-in default pack root is absent in Phase 0, and that is not an error.
    let out = s.harness().arg("run").arg(fixture()).output().unwrap();
    assert!(out.status.success(), "{}", text(&out));
}

// ---- canary -------------------------------------------------------------------------

#[test]
fn canary_passes_the_fixture_clean_in_under_ten_seconds() {
    let s = Scratch::new("canary");
    let out = s
        .harness()
        .args(["canary", "--record"])
        .arg(fixture())
        .output()
        .unwrap();
    let t = text(&out);
    assert!(out.status.success(), "canary failed:\n{t}");
    assert!(
        t.contains("OK: 10000 ticks, hashes identical every tick"),
        "{t}"
    );
    assert!(
        t.contains("final hash: 653b9057c4dd809407213920a217794adafd41c7ea92976e6bf344b76a5639bc"),
        "{t}"
    );
    assert!(!t.contains("DESYNC"), "{t}");
    let wall = float_after(&t, "wall-clock: ").expect(&t);
    assert!(wall < 10.0, "canary took {wall}s:\n{t}");
    // The hash log is on by default, named after the record.
    let log = s.path("phase0-empty-10k.hashlog");
    assert!(log.is_file(), "{t}");
    assert_eq!(read(&log).lines().count(), 10_001);
    assert!(!s.path("divergence.json").exists());
}

#[test]
fn canary_injected_fails_at_the_injection_tick_and_names_the_field() {
    let s = Scratch::new("canary-injected");
    let out = s
        .harness()
        .args(["canary", "--record"])
        .arg(fixture())
        .args([
            "--injected",
            "--inject-tick",
            "4242",
            "--hash-every",
            "1000",
        ])
        .output()
        .unwrap();
    let t = text(&out);
    assert!(!out.status.success(), "injected canary must fail:\n{t}");
    assert_eq!(out.status.code(), Some(1), "{t}");
    assert_eq!(number_after(&t, "injected at tick "), Some(4242), "{t}");
    assert_eq!(number_after(&t, "DESYNC at tick "), Some(4242), "{t}");
    assert!(t.contains("hash A: "), "{t}");
    assert!(t.contains("hash B: "), "{t}");
    assert!(
        t.contains("inject_fold"),
        "diff must name the field that diverged:\n{t}"
    );
    assert!(t.contains("divergence written to divergence.json"), "{t}");
    assert!(s.path("divergence.json").is_file(), "{t}");
    // The log stops at the divergent tick, whatever the cadence.
    let log = read(&s.path("phase0-empty-10k.hashlog"));
    let ticks: Vec<&str> = log.lines().map(|l| l.split(',').next().unwrap()).collect();
    assert_eq!(ticks, ["0", "1000", "2000", "3000", "4000", "4242"]);
}

#[test]
fn canary_injected_default_tick_is_5000() {
    let s = Scratch::new("canary-injected-default");
    let out = s
        .harness()
        .args(["canary", "--record"])
        .arg(fixture())
        .arg("--injected")
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(1), "{t}");
    let injected = number_after(&t, "injected at tick ").expect(&t);
    let reported = number_after(&t, "DESYNC at tick ").expect(&t);
    assert_eq!(injected, reported, "{t}");
    assert_eq!(injected, 5000, "{t}");
}

#[test]
fn canary_inject_tick_outside_the_run_is_a_usage_error() {
    let s = Scratch::new("canary-inject-range");
    let short = s.record("short.json", 1, 100);
    let out = s
        .harness()
        .args(["canary", "--record"])
        .arg(&short)
        .arg("--injected")
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(2), "{t}");
    assert!(t.contains("--inject-tick 5000 must be in 1..=100"), "{t}");
    let out = s
        .harness()
        .args(["canary", "--record"])
        .arg(&short)
        .args(["--injected", "--inject-tick", "0"])
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(2), "{}", text(&out));
    assert!(!s.path("short.hashlog").exists(), "nothing ran");
}

// ---- bisect -------------------------------------------------------------------------

#[test]
fn bisect_locates_a_tampered_tick_in_a_dense_log_and_writes_the_dump() {
    let s = Scratch::new("bisect-dense");
    let replay = s.record("replay.json", 7, 3000);
    let log = s.path("foreign.hashlog");
    let out = s
        .harness()
        .arg("run")
        .arg(&replay)
        .arg("--hash-log")
        .arg(&log)
        .output()
        .unwrap();
    assert!(out.status.success(), "{}", text(&out));
    let pristine = read(&log);

    // Against its own log there is nothing to find.
    let out = s
        .harness()
        .args(["bisect", "--record"])
        .arg(&replay)
        .arg("--hash-log")
        .arg(&log)
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(0), "{t}");
    assert!(
        t.contains("OK: 3000 ticks, none of 3001 checkpoint(s) differs"),
        "{t}"
    );

    // Tamper tick 1234 and every later tick: the shape of a desync that started there.
    tamper_log(&log, 1234);
    let out = s
        .harness()
        .args(["bisect", "--record"])
        .arg(&replay)
        .arg("--hash-log")
        .arg(&log)
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(1), "{t}");
    assert_eq!(number_after(&t, "DIVERGENCE at tick "), Some(1234), "{t}");
    assert!(t.contains("binary search"), "{t}");
    assert!(t.contains("recorded: "), "{t}");
    assert!(t.contains("local   : "), "{t}");
    assert!(t.contains("tick 1233 matched on both sides"), "{t}");
    assert!(t.contains("local state at tick 1234"), "{t}");
    assert!(t.contains("  tick = 1234"), "{t}");
    assert!(
        t.contains("changed across tick 1233 -> 1234") && t.contains("agents["),
        "bisect must print a structural diff at the divergent tick:\n{t}"
    );
    let dump = s.path("replay.tick1234.dump");
    assert!(t.contains("written to replay.tick1234.dump"), "{t}");
    assert!(dump.is_file());
    assert!(read(&dump).contains("tick = 1234\n"));

    // A single tampered entry (the log re-converges) is still found, by the linear
    // fallback, at the same tick.
    std::fs::write(&log, &pristine).unwrap();
    let one: String = read(&log)
        .lines()
        .map(|l| {
            if l.starts_with("1234,") {
                let (tick, hash) = l.split_once(',').unwrap();
                let flipped = if hash.starts_with('0') { "1" } else { "0" };
                format!("{tick},{flipped}{}\n", &hash[1..])
            } else {
                format!("{l}\n")
            }
        })
        .collect();
    std::fs::write(&log, one).unwrap();
    let out = s
        .harness()
        .args(["bisect", "--record"])
        .arg(&replay)
        .arg("--hash-log")
        .arg(&log)
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(1), "{t}");
    assert_eq!(number_after(&t, "DIVERGENCE at tick "), Some(1234), "{t}");
    assert!(t.contains("linear scan"), "{t}");
}

#[test]
fn bisect_narrows_a_sparse_log_to_its_checkpoint_window() {
    let s = Scratch::new("bisect-sparse");
    let replay = s.record("replay.json", 7, 3000);
    let log = s.path("every100.hashlog");
    let out = s
        .harness()
        .arg("run")
        .arg(&replay)
        .arg("--hash-log")
        .arg(&log)
        .args(["--hash-every", "100"])
        .output()
        .unwrap();
    assert!(out.status.success(), "{}", text(&out));
    assert_eq!(read(&log).lines().count(), 31);
    tamper_log(&log, 1234);
    let out = s
        .harness()
        .args(["bisect", "--record"])
        .arg(&replay)
        .arg("--hash-log")
        .arg(&log)
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(1), "{t}");
    assert_eq!(
        number_after(&t, "DIVERGENCE at checkpoint tick "),
        Some(1300),
        "{t}"
    );
    assert!(t.contains("31 checkpoint(s)"), "{t}");
    assert!(t.contains("tick 1200 matched on both sides"), "{t}");
    assert!(t.contains("no entry in 1201..=1299"), "{t}");
    assert!(t.contains("--hash-every 1"), "{t}");
    assert!(s.path("replay.tick1300.dump").is_file(), "{t}");
}

#[test]
fn bisect_injected_locates_the_injection_in_one_command() {
    let s = Scratch::new("bisect-injected");
    let out = s
        .harness()
        .args(["bisect", "--record"])
        .arg(fixture())
        .arg("--injected")
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(1), "{t}");
    assert_eq!(number_after(&t, "DIVERGENCE at tick "), Some(5000), "{t}");
    assert!(
        t.contains("differing field(s) between the two instances"),
        "{t}"
    );
    assert!(t.contains("inject_fold"), "{t}");
    assert!(t.contains("tick 4999 matched on both sides"), "{t}");
    assert!(s.path("phase0-empty-10k.tick5000.dump").is_file(), "{t}");
}

#[test]
fn bisect_injected_with_checkpoints_every_100_steps_to_the_exact_tick() {
    let s = Scratch::new("bisect-injected-100");
    let out = s
        .harness()
        .args(["bisect", "--record"])
        .arg(fixture())
        .args(["--injected", "--inject-tick", "1234", "--hash-every", "100"])
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(1), "{t}");
    assert!(t.contains("foreign checkpoints every 100 tick(s)"), "{t}");
    assert_eq!(number_after(&t, "DIVERGENCE at tick "), Some(1234), "{t}");
    assert!(t.contains("over 101 checkpoint(s)"), "{t}");
    assert!(
        t.contains(
            "bracketed the desync in 1200..=1300; a lockstep walk of that window pinned tick 1234"
        ),
        "{t}"
    );
    let probes = number_after(&t, "checkpoint(s), ").expect(&t);
    assert!(probes <= 8, "{probes} re-runs for 101 checkpoints:\n{t}");
    assert!(t.contains("inject_fold"), "{t}");
    assert!(read(&s.path("phase0-empty-10k.tick1234.dump")).contains("tick = 1234\n"));
}

#[test]
fn bisect_reproduces_a_canary_divergence_file() {
    let s = Scratch::new("bisect-divergence");
    let replay = s.record("eleven.json", 11, 2000);
    let div = s.path("divergence.json");
    let out = s
        .harness()
        .args(["canary", "--record"])
        .arg(&replay)
        .args(["--injected", "--inject-tick", "777", "--divergence"])
        .arg(&div)
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(1), "{t}");
    assert!(div.is_file(), "{t}");

    let file = json(&div);
    assert_eq!(file["record"]["seed"], 11);
    assert_eq!(file["record"]["ticks"], 2000);
    assert_eq!(file["tick"], 777);
    assert_eq!(file["hash_a"].as_str().unwrap().len(), 64);
    assert_eq!(file["hash_b"].as_str().unwrap().len(), 64);
    assert_ne!(file["hash_a"], file["hash_b"]);
    assert_eq!(file["diff"][0]["path"], "inject_fold");
    assert_eq!(file["injection"]["tick"], 777);

    let out = s
        .harness()
        .args(["bisect", "--from-divergence"])
        .arg(&div)
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(1), "{t}");
    assert_eq!(
        number_after(&t, "recorded injection at tick "),
        Some(777),
        "{t}"
    );
    assert_eq!(
        number_after(&t, "REPRODUCED: divergence at tick "),
        Some(777),
        "{t}"
    );
    // Both instances carry the bug, so an un-armed instance matches neither.
    assert!(t.contains("matches A: false, matches B: false"), "{t}");
    assert!(t.contains("inject_fold"), "{t}");
}

#[test]
fn bisect_argument_shapes_and_help() {
    let s = Scratch::new("bisect-args");
    let out = s.harness().arg("bisect").output().unwrap();
    assert_eq!(out.status.code(), Some(2), "{}", text(&out));
    let out = s
        .harness()
        .args(["bisect", "--record"])
        .arg(fixture())
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(2), "{}", text(&out));
    let out = s
        .harness()
        .args(["bisect", "--record"])
        .arg(fixture())
        .args(["--hash-log", "x", "--injected"])
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(2), "two sides:\n{}", text(&out));
    let out = s
        .harness()
        .args(["bisect", "--from-divergence", "does-not-exist.json"])
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(2), "{t}");
    assert!(t.contains("cannot read"), "{t}");
    // Exit codes are documented in --help, with the git bisect run example.
    let out = s.harness().args(["bisect", "--help"]).output().unwrap();
    let t = text(&out);
    assert!(out.status.success(), "{t}");
    for needle in [
        "Exit codes:",
        "0  no divergence",
        "1  divergence located",
        "2  usage",
        "git bisect run",
    ] {
        assert!(t.contains(needle), "missing `{needle}` in:\n{t}");
    }
    let out = s.harness().arg("--help").output().unwrap();
    assert!(text(&out).contains("Exit codes:"));
}

// ---- diff-dumps -----------------------------------------------------------------------

#[test]
fn diff_dumps_prints_the_field_level_diff_of_two_dumps() {
    let s = Scratch::new("diff-dumps");
    let seven = s.record("seven.json", 7, 100);
    let eight = s.record("eight.json", 8, 100);
    for r in [&seven, &eight] {
        let out = s
            .harness()
            .arg("run")
            .arg(r)
            .args(["--dump-state-at", "42"])
            .output()
            .unwrap();
        assert!(out.status.success(), "{}", text(&out));
    }
    let a = s.path("seven.tick42.dump");
    let b = s.path("eight.tick42.dump");
    let out = s
        .harness()
        .arg("diff-dumps")
        .arg(&a)
        .arg(&b)
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(1), "{t}");
    assert!(t.contains("5 differing field(s):"), "{t}");
    assert!(t.contains("  seed\n      A: 7\n      B: 8\n"), "{t}");
    assert!(t.contains("agents[1].pos.x"), "{t}");
    assert!(!t.contains("  tick\n"), "same tick on both sides:\n{t}");

    let out = s
        .harness()
        .arg("diff-dumps")
        .arg(&a)
        .arg(&a)
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(0), "{t}");
    assert!(t.contains("OK: identical (8 field(s))"), "{t}");

    let out = s
        .harness()
        .arg("diff-dumps")
        .arg(&a)
        .arg(s.path("missing.dump"))
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(2), "{}", text(&out));
}

#[test]
fn diff_dumps_of_two_injected_bisects_names_the_mutated_field() {
    // Two processes stand in for two machines: each bisects the injected fixture and
    // dumps its (armed) local state at tick N; the dumps differ in the folded field only.
    let a = Scratch::new("diff-dumps-injected-a");
    let b = Scratch::new("diff-dumps-injected-b");
    for s in [&a, &b] {
        let out = s
            .harness()
            .args(["bisect", "--record"])
            .arg(fixture())
            .args(["--injected", "--inject-tick", "300"])
            .output()
            .unwrap();
        assert_eq!(out.status.code(), Some(1), "{}", text(&out));
    }
    let out = harness()
        .arg("diff-dumps")
        .arg(a.path("phase0-empty-10k.tick300.dump"))
        .arg(b.path("phase0-empty-10k.tick300.dump"))
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(1), "{t}");
    assert!(t.contains("1 differing field(s):\n  inject_fold\n"), "{t}");
}

// ---- batch ----------------------------------------------------------------------------

#[test]
fn batch_table_is_byte_identical_for_one_and_eight_jobs() {
    let s = Scratch::new("batch");
    let mut tables = Vec::new();
    for jobs in ["1", "8"] {
        let out_path = s.path(&format!("j{jobs}.csv"));
        let out = s
            .harness()
            .args([
                "batch", "--seeds", "0..100", "--ticks", "100", "--jobs", jobs, "--out",
            ])
            .arg(&out_path)
            .output()
            .unwrap();
        let t = text(&out);
        assert!(out.status.success(), "{t}");
        assert!(t.contains("batch: 100 seed(s) 0..=99 x 100 ticks"), "{t}");
        assert!(t.contains(&format!("{jobs} job(s)")), "{t}");
        assert!(t.contains("matches/hour: "), "{t}");
        assert!(t.contains("aggregate ticks/s: "), "{t}");
        assert!(t.contains("table: "), "{t}");
        tables.push(std::fs::read(&out_path).unwrap());
    }
    assert_eq!(tables[0], tables[1], "the table depends on J");
    let table = String::from_utf8(tables[0].clone()).unwrap();
    let lines: Vec<&str> = table.lines().collect();
    assert_eq!(lines.len(), 100);
    assert!(lines[0].starts_with("0,"));
    assert!(lines[99].starts_with("99,"));
    assert_eq!(lines[7].len(), 2 + 64);
    assert!(!table.contains('\r'));
    // Each row is what `record` produces for that seed.
    let seven = s.record("seven.json", 7, 100);
    assert_eq!(
        lines[7],
        format!("7,{}", json(&seven)["final_hash"].as_str().unwrap())
    );
    // Inclusive range and empty range.
    let out = s
        .harness()
        .args([
            "batch", "--seeds", "5..=6", "--ticks", "10", "--out", "inc.csv",
        ])
        .output()
        .unwrap();
    assert!(out.status.success(), "{}", text(&out));
    assert_eq!(read(&s.path("inc.csv")).lines().count(), 2);
    let out = s
        .harness()
        .args([
            "batch",
            "--seeds",
            "5..5",
            "--ticks",
            "10",
            "--out",
            "empty.csv",
        ])
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(2), "{}", text(&out));
}

// ---- golden ---------------------------------------------------------------------------

#[test]
fn golden_prints_the_checked_in_tables() {
    // The checked-in golden_tables.rs must be what `golden` generates today, modulo
    // rustfmt: compare with whitespace collapsed.
    let out = harness().arg("golden").output().unwrap();
    assert!(out.status.success(), "{}", text(&out));
    let generated = String::from_utf8(out.stdout).unwrap();
    let checked_in = std::fs::read_to_string(
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../crates/blindside-sim/src/golden_tables.rs"),
    )
    .unwrap();
    // rustfmt splits long rows across lines and adds a trailing comma inside the tuple.
    let squash = |s: &str| {
        s.chars()
            .filter(|c| !c.is_whitespace())
            .collect::<String>()
            .replace(",)", ")")
    };
    assert_eq!(
        squash(&generated),
        squash(&checked_in),
        "regenerate with: cargo run -p blindside-harness -- golden > \
         crates/blindside-sim/src/golden_tables.rs && cargo fmt --all"
    );
}
