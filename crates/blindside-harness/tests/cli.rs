//! End-to-end tests of the `harness` binary, driven through its CLI exactly the way CI
//! will drive it.

use std::path::PathBuf;
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
}

impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

#[test]
fn canary_passes_10000_ticks_clean() {
    let out = harness()
        .args(["canary", "--ticks", "10000"])
        .output()
        .unwrap();
    let t = text(&out);
    assert!(out.status.success(), "canary failed:\n{t}");
    assert!(t.contains("OK: 10000 ticks"), "{t}");
    assert!(!t.contains("DESYNC"), "{t}");
}

#[test]
fn canary_inject_fails_and_reports_the_injection_tick() {
    let s = Scratch::new("canary-inject");
    let out = harness()
        .current_dir(&s.0)
        .args([
            "canary",
            "--ticks",
            "10000",
            "--inject",
            "--inject-tick",
            "4242",
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
        t.contains("agents["),
        "diff must name the field that diverged:\n{t}"
    );
    assert!(
        s.path("divergence.json").is_file(),
        "canary must write divergence.json in the cwd by default:\n{t}"
    );
}

#[test]
fn canary_inject_default_tick_is_reported_consistently() {
    let s = Scratch::new("canary-inject-default");
    let out = harness()
        .current_dir(&s.0)
        .args(["canary", "--ticks", "1000", "--inject"])
        .output()
        .unwrap();
    let t = text(&out);
    assert!(!out.status.success(), "{t}");
    let injected = number_after(&t, "injected at tick ").expect(&t);
    let reported = number_after(&t, "DESYNC at tick ").expect(&t);
    assert_eq!(injected, reported, "{t}");
    assert_eq!(injected, 500, "{t}");
}

#[test]
fn record_then_verify_is_ok() {
    let s = Scratch::new("record-verify");
    let replay = s.path("replay.json");
    let hashes = s.path("hashes.json");
    let out = harness()
        .args(["record", "--seed", "7", "--ticks", "500", "--out"])
        .arg(&replay)
        .arg("--hashes")
        .arg(&hashes)
        .output()
        .unwrap();
    assert!(out.status.success(), "{}", text(&out));
    assert!(replay.is_file());
    assert!(hashes.is_file());

    let out = harness()
        .arg("verify")
        .arg(&replay)
        .arg(&hashes)
        .output()
        .unwrap();
    let t = text(&out);
    assert!(out.status.success(), "{t}");
    assert!(t.contains("OK: 500 ticks"), "{t}");

    let out = harness().arg("run").arg(&replay).output().unwrap();
    let t = text(&out);
    assert!(out.status.success(), "{t}");
    assert!(t.contains("final hash: "), "{t}");
    assert!(t.contains("ticks/s: "), "{t}");
    assert!(t.contains("OK: final hash matches record"), "{t}");
}

#[test]
fn record_default_sidecar_name_and_shape() {
    let s = Scratch::new("record-default");
    let replay = s.path("replay.json");
    let out = harness()
        .args(["record", "--seed", "3735928559", "--ticks", "1000", "--out"])
        .arg(&replay)
        .output()
        .unwrap();
    assert!(out.status.success(), "{}", text(&out));
    let hashes = s.path("replay.hashes.json");
    assert!(hashes.is_file(), "default sidecar not written");

    let rec: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&replay).unwrap()).unwrap();
    assert_eq!(rec["seed"], 3735928559u64);
    assert_eq!(rec["ticks"], 1000);
    assert_eq!(rec["schema"], 0);
    assert_eq!(rec["loadouts"], serde_json::json!([]));
    assert_eq!(rec["policies"], serde_json::json!([]));
    assert_eq!(rec["commands"], serde_json::json!([]));
    assert_eq!(rec["content_hash"].as_str().unwrap().len(), 64);
    // Cross-platform pin shared with blindside-sim.
    assert_eq!(
        rec["final_hash"],
        "5a6930a5dab0a7627913befbc590c79453415c483200c8d4eb55eb8a3faaf17a"
    );

    let log: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&hashes).unwrap()).unwrap();
    let list = log["hashes"].as_array().unwrap();
    assert_eq!(list.len(), 1001, "one hash per tick 0..=1000");
    assert_eq!(list[1000], rec["final_hash"]);
}

#[test]
fn verify_against_tampered_hashes_reports_the_tick() {
    let s = Scratch::new("tampered");
    let replay = s.path("replay.json");
    let hashes = s.path("hashes.json");
    let out = harness()
        .args(["record", "--seed", "9", "--ticks", "200", "--out"])
        .arg(&replay)
        .arg("--hashes")
        .arg(&hashes)
        .output()
        .unwrap();
    assert!(out.status.success(), "{}", text(&out));

    let mut log: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&hashes).unwrap()).unwrap();
    let orig = log["hashes"][37].as_str().unwrap().to_string();
    let flipped = if orig.starts_with('0') { "1" } else { "0" };
    log["hashes"][37] = serde_json::Value::String(format!("{flipped}{}", &orig[1..]));
    std::fs::write(&hashes, serde_json::to_string_pretty(&log).unwrap()).unwrap();

    let out = harness()
        .arg("verify")
        .arg(&replay)
        .arg(&hashes)
        .output()
        .unwrap();
    let t = text(&out);
    assert!(!out.status.success(), "{t}");
    assert_eq!(out.status.code(), Some(1), "{t}");
    assert_eq!(number_after(&t, "MISMATCH at tick "), Some(37), "{t}");
}

#[test]
fn verify_rejects_a_record_with_a_foreign_content_hash() {
    let s = Scratch::new("content-hash");
    let replay = s.path("replay.json");
    let hashes = s.path("hashes.json");
    let out = harness()
        .args(["record", "--seed", "9", "--ticks", "20", "--out"])
        .arg(&replay)
        .arg("--hashes")
        .arg(&hashes)
        .output()
        .unwrap();
    assert!(out.status.success(), "{}", text(&out));

    let mut rec: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&replay).unwrap()).unwrap();
    rec["content_hash"] = serde_json::Value::String("00".repeat(32));
    std::fs::write(&replay, serde_json::to_string_pretty(&rec).unwrap()).unwrap();

    let out = harness()
        .arg("verify")
        .arg(&replay)
        .arg(&hashes)
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(2), "{t}");
    assert!(t.contains("content hash mismatch"), "{t}");
}

#[test]
fn batch_reports_matches_per_hour() {
    let out = harness()
        .args(["batch", "--matches", "20", "--ticks", "100"])
        .output()
        .unwrap();
    let t = text(&out);
    assert!(out.status.success(), "{t}");
    assert!(t.contains("matches/hour: "), "{t}");
    assert!(t.contains("digest: "), "{t}");
}

#[test]
fn bisect_locates_a_tampered_tick_and_prints_a_diff() {
    let s = Scratch::new("bisect");
    let replay = s.path("replay.json");
    let hashes = s.path("hashes.json");
    let out = harness()
        .args(["record", "--seed", "7", "--ticks", "3000", "--out"])
        .arg(&replay)
        .arg("--hashes")
        .arg(&hashes)
        .output()
        .unwrap();
    assert!(out.status.success(), "{}", text(&out));

    let pristine = std::fs::read_to_string(&hashes).unwrap();

    // Tamper tick 1234 and every later tick: the shape of a desync that started there.
    let mut log: serde_json::Value = serde_json::from_str(&pristine).unwrap();
    for i in 1234..=3000 {
        let orig = log["hashes"][i].as_str().unwrap().to_string();
        let flipped = if orig.starts_with('0') { "1" } else { "0" };
        log["hashes"][i] = serde_json::Value::String(format!("{flipped}{}", &orig[1..]));
    }
    std::fs::write(&hashes, serde_json::to_string_pretty(&log).unwrap()).unwrap();

    let out = harness()
        .arg("bisect")
        .arg(&replay)
        .arg(&hashes)
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
    assert!(
        t.contains("changed across tick 1233 -> 1234") && t.contains("agents["),
        "bisect must print a structural diff at the divergent tick:\n{t}"
    );

    // A single tampered entry (the log re-converges) is still found, by the linear
    // fallback, at the same tick.
    let mut log: serde_json::Value = serde_json::from_str(&pristine).unwrap();
    let orig = log["hashes"][1234].as_str().unwrap().to_string();
    let flipped = if orig.starts_with('0') { "1" } else { "0" };
    log["hashes"][1234] = serde_json::Value::String(format!("{flipped}{}", &orig[1..]));
    std::fs::write(&hashes, serde_json::to_string_pretty(&log).unwrap()).unwrap();
    let out = harness()
        .arg("bisect")
        .arg(&replay)
        .arg(&hashes)
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(1), "{t}");
    assert_eq!(number_after(&t, "DIVERGENCE at tick "), Some(1234), "{t}");
    assert!(t.contains("linear scan"), "{t}");
    assert!(t.contains("local state at tick 1234"), "{t}");
}

#[test]
fn bisect_reproduces_a_canary_divergence_file() {
    let s = Scratch::new("bisect-divergence");
    let div = s.path("divergence.json");
    let out = harness()
        .args([
            "canary",
            "--ticks",
            "2000",
            "--seed",
            "11",
            "--inject",
            "--inject-tick",
            "777",
            "--divergence",
        ])
        .arg(&div)
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(1), "{t}");
    assert!(t.contains("divergence written to "), "{t}");
    assert!(div.is_file(), "{t}");

    let file: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&div).unwrap()).unwrap();
    assert_eq!(file["seed"], 11);
    assert_eq!(file["ticks"], 2000);
    assert_eq!(file["tick"], 777);
    assert_eq!(file["hash_a"].as_str().unwrap().len(), 64);
    assert_eq!(file["hash_b"].as_str().unwrap().len(), 64);
    assert_ne!(file["hash_a"], file["hash_b"]);
    assert!(!file["diff"].as_array().unwrap().is_empty());
    assert_eq!(file["injection"]["tick"], 777);

    let out = harness()
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
    assert!(t.contains("diff identical to the recorded one"), "{t}");
    assert!(t.contains("matches A: true, matches B: false"), "{t}");
    assert!(t.contains("agents["), "{t}");
}

#[test]
fn bisect_argument_shapes() {
    let out = harness().arg("bisect").output().unwrap();
    assert_eq!(out.status.code(), Some(2), "{}", text(&out));
    let out = harness()
        .args(["bisect", "--from-divergence", "does-not-exist.json"])
        .output()
        .unwrap();
    let t = text(&out);
    assert_eq!(out.status.code(), Some(2), "{t}");
    assert!(t.contains("cannot read"), "{t}");
}
