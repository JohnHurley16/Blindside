//! `fixtures/phase0-empty-10k.record` (BLD-30): the checked-in Phase 0 replay -- the
//! empty sim, seed `0xDEAD_BEEF` (3735928559), 10,000 ticks, against the empty content
//! pack -- loaded through the schema migration chain and re-run.
//!
//! The file is schema 0. It is the fixture the canary and the cross-OS CI compare run on,
//! and the one a future schema's `migrate` arm must still load.
//!
//! Recorded with, from the workspace root:
//!
//! ```text
//! cargo run -p blindside-harness --release -- record --seed 3735928559 --ticks 10000 \
//!     --out fixtures/phase0-empty-10k.record
//! ```
//!
//! (the 10,001-line hash log is not checked in; `verify` regenerates it). Any change to
//! the sim, the RNG, the hash layout or the record schema changes `final_hash` and must
//! be re-recorded deliberately, with the schema or layout bump in the same commit.

use std::path::PathBuf;

use blindside_harness::record::{default_content_dir, MatchRecord, MATCH_RECORD_SCHEMA};
use blindside_harness::runner;

/// Byte size of the checked-in fixture. Pretty JSON, LF line endings, no trailing
/// newline: 281 bytes, well under the 1 KB the story budgets.
const FIXTURE_BYTES: u64 = 281;
const _: () = assert!(FIXTURE_BYTES < 1024, "the fixture must stay under 1 KB");

/// `Sim::state_hash()` at tick 10,000 on seed 0xDEAD_BEEF -- the same value blindside-sim
/// pins as `GOLDEN_SEED_DEADBEEF_TICK_10000`.
const FIXTURE_FINAL_HASH: &str = "653b9057c4dd809407213920a217794adafd41c7ea92976e6bf344b76a5639bc";

fn fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("fixtures")
        .join("phase0-empty-10k.record")
}

fn load() -> MatchRecord {
    MatchRecord::load(&fixture_path(), &default_content_dir()).expect("fixture loads")
}

#[test]
fn fixture_loads_through_migrate_and_validates() {
    let rec = load();
    assert_eq!(rec.schema, 0, "the fixture is the v0 record");
    assert_eq!(rec.schema, MATCH_RECORD_SCHEMA);
    assert_eq!(rec.seed, 0xDEAD_BEEF);
    assert_eq!(rec.ticks, 10_000);
    assert_eq!(rec.content_hash.0, blindside_content::EMPTY_PACK_HASH);
    let sim_rec = rec.to_sim().expect("migrates and validates");
    assert_eq!(sim_rec.schema, blindside_sim::MATCH_RECORD_SCHEMA);
    assert!(sim_rec.commands.is_empty());
    assert_eq!(rec.final_hash.to_hex(), FIXTURE_FINAL_HASH);
}

#[test]
fn fixture_has_the_documented_size_and_lf_endings() {
    let bytes = std::fs::read(fixture_path()).unwrap();
    assert!(!bytes.contains(&b'\r'), "CRLF crept into the fixture");
    assert_eq!(bytes.len() as u64, FIXTURE_BYTES);
}

#[test]
fn fixture_re_serialises_byte_identically() {
    let on_disk = std::fs::read_to_string(fixture_path()).unwrap();
    assert_eq!(load().to_json().unwrap(), on_disk);
}

#[test]
fn fixture_final_hash_is_reproduced_by_a_re_run() {
    let rec = load();
    let out = runner::run(&rec.to_sim().unwrap(), 1, None);
    assert_eq!(out.ticks, 10_000);
    assert_eq!(out.final_hash, rec.final_hash);
    assert_eq!(out.final_hash.to_hex(), FIXTURE_FINAL_HASH);
    assert_eq!(out.log.len(), 10_001);
}
