//! On-disk replay formats (harness only; serde is fine here).
//!
//! `MatchRecord` here is the JSON encoding of `blindside_sim::MatchRecord` (the type from
//! `docs/ARCHITECTURE.md`, which lives in the sim because the sim is what a record is an
//! input to). `to_sim` converts and applies the sim's rules -- schema through
//! `migrate()`, and commands REJECTED unless already sorted by (tick, team, sequence);
//! it never re-sorts, because a caller that handed over an unsorted log does not know
//! what order it meant. This module adds the one rule only a loader can apply: the
//! record's `content_hash` must be the loaded pack's. `save` runs the same rules before
//! writing, so an unsorted log is refused rather than written (BLD-30).
//!
//! In Phase 0 the sim takes no loadouts, policies or commands, so those fields are
//! carried as opaque JSON values and must be empty; Phase 3 types them and bumps
//! `MATCH_RECORD_SCHEMA` in the sim.
//!
//! `HashLog` is the per-tick hash log `run`, `verify`, `canary` and `record --hash-log`
//! write and `bisect --hash-log` reads (BLD-31): plain text, one `tick,hash` line per
//! logged tick, LF-terminated, no header, so `diff`, `cmp` and `sha256sum` work on it
//! directly and two machines' logs can be compared without this binary. Tick 0 is the
//! constructed state. With `--hash-every N` the log keeps ticks `0, N, 2N, ...` and always
//! the final tick, so the last line is the final hash whatever the cadence. Carrying no
//! seed or tick count is the price of the plain format: a log from another record is
//! reported as a divergence at tick 0, not as a usage error.

use std::fmt;
use std::path::{Path, PathBuf};

use blindside_content::ContentPack;
use serde::{Deserialize, Serialize};

pub use blindside_sim::MATCH_RECORD_SCHEMA;

/// The sim's own record type: what `Sim::new` takes.
pub type SimRecord = blindside_sim::MatchRecord;

/// A 32-byte hash serialised as 64 lowercase hex characters.
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct HexHash(pub [u8; 32]);

impl HexHash {
    pub fn to_hex(self) -> String {
        self.0.iter().map(|b| format!("{b:02x}")).collect()
    }

    pub fn from_hex(s: &str) -> Result<HexHash, String> {
        if s.len() != 64 {
            return Err(format!("expected 64 hex chars, got {}", s.len()));
        }
        let mut out = [0u8; 32];
        for (i, byte) in out.iter_mut().enumerate() {
            *byte = u8::from_str_radix(&s[2 * i..2 * i + 2], 16)
                .map_err(|e| format!("bad hex at byte {i}: {e}"))?;
        }
        Ok(HexHash(out))
    }
}

impl fmt::Display for HexHash {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.to_hex())
    }
}

impl fmt::Debug for HexHash {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "HexHash({})", self.to_hex())
    }
}

impl From<[u8; 32]> for HexHash {
    fn from(b: [u8; 32]) -> HexHash {
        HexHash(b)
    }
}

impl Serialize for HexHash {
    fn serialize<S: serde::Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_str(&self.to_hex())
    }
}

impl<'de> Deserialize<'de> for HexHash {
    fn deserialize<D: serde::Deserializer<'de>>(d: D) -> Result<HexHash, D::Error> {
        let s = String::deserialize(d)?;
        HexHash::from_hex(&s).map_err(serde::de::Error::custom)
    }
}

/// Where the content pack is unless `--content` says otherwise: `content/` at the
/// workspace root, resolved at compile time. The harness is a development tool that runs
/// from its workspace. A missing directory is the empty pack (Phase 0).
pub fn default_content_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("content")
}

/// Hash of the content pack under `dir` (DETERMINISM.md: "Replays carry a content pack
/// hash"). Computed by blindside-content over the files there; in Phase 0 that is the
/// empty pack and `blindside_content::EMPTY_PACK_HASH`.
pub fn content_hash_of(dir: &Path) -> Result<HexHash, String> {
    let pack = ContentPack::read_dir(dir)
        .map_err(|e| format!("content pack at {}: {e}", dir.display()))?;
    Ok(HexHash(blindside_content::content_hash(&pack)))
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct MatchRecord {
    pub schema: u16,
    pub seed: u64,
    pub content_hash: HexHash,
    /// Phase 0: must be empty. Typed in Phase 3.
    pub loadouts: Vec<serde_json::Value>,
    /// Phase 0: must be empty. Typed in Phase 3.
    pub policies: Vec<serde_json::Value>,
    /// Phase 0: must be empty. `{tick, team, sequence, command}` entries in Phase 3,
    /// stored sorted by that key (the sim refuses any other order).
    pub commands: Vec<serde_json::Value>,
    /// Number of ticks the match ran for.
    pub ticks: u64,
    /// State hash at tick `ticks`.
    pub final_hash: HexHash,
}

impl MatchRecord {
    /// The empty Phase 0 record for a seed: no loadouts, policies or commands, against
    /// the pack whose hash is given, with `final_hash` still zero. `record` and `batch`
    /// start from this and fill the hash in by running it.
    pub fn empty(seed: u64, ticks: u64, content_hash: HexHash) -> MatchRecord {
        MatchRecord {
            schema: MATCH_RECORD_SCHEMA,
            seed,
            content_hash,
            loadouts: Vec::new(),
            policies: Vec::new(),
            commands: Vec::new(),
            ticks,
            final_hash: HexHash([0; 32]),
        }
    }

    /// Load and validate against the pack under `content`. Rejects a record from another
    /// schema, another content pack, or carrying inputs the Phase 0 sim cannot consume.
    pub fn load(path: &Path, content: &Path) -> Result<MatchRecord, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        let rec: MatchRecord = serde_json::from_str(&text)
            .map_err(|e| format!("{} is not a MatchRecord: {e}", path.display()))?;
        rec.validate(content)?;
        Ok(rec)
    }

    /// The sim's rules (through `to_sim`), then the loader's: the content hash must be the
    /// loaded pack's. A mismatch is a hard error carrying both hashes, never a warning.
    pub fn validate(&self, content: &Path) -> Result<(), String> {
        self.to_sim()?;
        let want = content_hash_of(content)?;
        if self.content_hash != want {
            return Err(format!(
                "content hash mismatch: record {} but current content pack {want}",
                self.content_hash
            ));
        }
        Ok(())
    }

    /// Convert to the sim's `MatchRecord`, migrating the schema and validating the
    /// command order on the way. Phase 0 refuses any loadout, policy or command.
    pub fn to_sim(&self) -> Result<SimRecord, String> {
        if !self.loadouts.is_empty() || !self.policies.is_empty() || !self.commands.is_empty() {
            return Err(
                "Phase 0 sim accepts no loadouts, policies or commands; record has some".into(),
            );
        }
        let rec = SimRecord {
            schema: self.schema,
            seed: self.seed,
            content_hash: self.content_hash.0,
            loadouts: Vec::new(),
            policies: Vec::new(),
            commands: Vec::new(),
            ticks: self.ticks,
            final_hash: self.final_hash.0,
        };
        let rec = rec.migrate().map_err(|e| e.to_string())?;
        rec.validate().map_err(|e| e.to_string())?;
        Ok(rec)
    }

    /// The canonical text: pretty JSON, LF line endings, no trailing newline. `save`
    /// writes exactly this, so a loaded record re-serialises byte-identically.
    pub fn to_json(&self) -> Result<String, String> {
        serde_json::to_string_pretty(self).map_err(|e| e.to_string())
    }

    /// Validate through the sim's rules, then write. An unsorted command log is refused
    /// here rather than sorted on the way out, so a record that reaches disk is one a
    /// loader will accept.
    pub fn save(&self, path: &Path) -> Result<(), String> {
        self.to_sim()?;
        let text = self.to_json()?;
        std::fs::write(path, text).map_err(|e| format!("cannot write {}: {e}", path.display()))
    }
}

/// Which ticks a hash log keeps: every `every`-th tick from 0, and always `last`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Cadence {
    pub every: u64,
    pub last: u64,
}

impl Cadence {
    /// `every` is clamped to at least 1: "every 0 ticks" means every tick.
    pub fn new(every: u64, last: u64) -> Cadence {
        Cadence {
            every: every.max(1),
            last,
        }
    }

    pub fn keeps(&self, tick: u64) -> bool {
        tick.is_multiple_of(self.every) || tick == self.last
    }

    /// How many ticks in `0..=last` the cadence keeps.
    pub fn count(&self) -> u64 {
        let multiples = self.last / self.every + 1;
        if self.last.is_multiple_of(self.every) {
            multiples
        } else {
            multiples + 1
        }
    }
}

impl fmt::Display for Cadence {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.every == 1 {
            f.write_str("every tick")
        } else {
            write!(f, "every {} ticks plus the final tick", self.every)
        }
    }
}

/// Per-tick hash log: `(tick, hash)` with strictly ascending ticks. See the module docs
/// for the file format.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct HashLog {
    pub entries: Vec<(u64, HexHash)>,
}

impl HashLog {
    /// Append an entry. Ticks must arrive in ascending order; a repeat or a step backwards
    /// is a bug in the caller, not in the data, so it panics.
    pub fn push(&mut self, tick: u64, hash: HexHash) {
        if let Some(&(last, _)) = self.entries.last() {
            assert!(tick > last, "hash log tick {tick} after {last}");
        }
        self.entries.push((tick, hash));
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    pub fn last(&self) -> Option<(u64, HexHash)> {
        self.entries.last().copied()
    }

    /// The hash logged for `tick`, if that tick was logged.
    pub fn hash_at(&self, tick: u64) -> Option<HexHash> {
        self.entries
            .binary_search_by_key(&tick, |&(t, _)| t)
            .ok()
            .map(|i| self.entries[i].1)
    }

    /// A one-line description of the cadence the entries show.
    pub fn describe(&self) -> String {
        match self.entries.as_slice() {
            [] => "empty".to_string(),
            [(t, _)] => format!("1 entry, tick {t}"),
            [(a, _), (b, _), ..] => {
                let n = self.entries.len();
                let last = self.entries[n - 1].0;
                let every = b - a;
                if every == 1 {
                    format!("{n} entries, every tick to {last}")
                } else {
                    format!("{n} entries, every {every} ticks to {last}")
                }
            }
        }
    }

    /// Parse the plain format. Blank lines are ignored; a `\r` before the newline is
    /// tolerated so a log that passed through a CRLF conversion still reads.
    pub fn parse(text: &str) -> Result<HashLog, String> {
        let mut log = HashLog::default();
        for (i, raw) in text.lines().enumerate() {
            let line = raw.trim_end_matches('\r');
            if line.is_empty() {
                continue;
            }
            let (tick, hash) = line
                .split_once(',')
                .ok_or_else(|| format!("line {}: expected `tick,hash`, got `{line}`", i + 1))?;
            let tick: u64 = tick
                .trim()
                .parse()
                .map_err(|e| format!("line {}: bad tick `{tick}`: {e}", i + 1))?;
            let hash =
                HexHash::from_hex(hash.trim()).map_err(|e| format!("line {}: {e}", i + 1))?;
            if let Some(&(last, _)) = log.entries.last() {
                if tick <= last {
                    return Err(format!(
                        "line {}: tick {tick} does not follow tick {last} (ticks must ascend)",
                        i + 1
                    ));
                }
            }
            log.entries.push((tick, hash));
        }
        Ok(log)
    }

    pub fn load(path: &Path) -> Result<HashLog, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        HashLog::parse(&text).map_err(|e| format!("{}: {e}", path.display()))
    }

    /// One `tick,hash\n` line per entry.
    pub fn render(&self) -> String {
        let mut out = String::with_capacity(self.entries.len() * 70);
        for (tick, hash) in &self.entries {
            out.push_str(&tick.to_string());
            out.push(',');
            out.push_str(&hash.to_hex());
            out.push('\n');
        }
        out
    }

    pub fn save(&self, path: &Path) -> Result<(), String> {
        std::fs::write(path, self.render())
            .map_err(|e| format!("cannot write {}: {e}", path.display()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn phase0_content_hash_is_the_empty_pack() {
        assert_eq!(
            content_hash_of(&default_content_dir()).unwrap(),
            HexHash(blindside_content::EMPTY_PACK_HASH)
        );
    }

    #[test]
    fn schema_and_inputs_are_checked_through_the_sim_rules() {
        let content = default_content_dir();
        let rec = MatchRecord::empty(1, 3, content_hash_of(&content).unwrap());
        assert!(rec.validate(&content).is_ok());
        let mut newer = rec.clone();
        newer.schema = MATCH_RECORD_SCHEMA + 1;
        let e = newer.validate(&content).unwrap_err();
        assert!(e.contains("record schema 1"), "{e}");
        let mut with_commands = rec.clone();
        with_commands.commands.push(serde_json::json!({}));
        assert!(with_commands.validate(&content).is_err());
        let mut other_pack = rec;
        other_pack.content_hash = HexHash([1; 32]);
        let e = other_pack.validate(&content).unwrap_err();
        assert!(e.contains("content hash mismatch"), "{e}");
        assert!(e.contains(&HexHash([1; 32]).to_hex()), "{e}");
    }

    #[test]
    fn hash_log_round_trips_and_is_plain_lines() {
        let mut log = HashLog::default();
        log.push(0, HexHash([0; 32]));
        log.push(100, HexHash([1; 32]));
        log.push(150, HexHash([0xab; 32]));
        let text = log.render();
        assert_eq!(text.lines().count(), 3);
        assert!(text.starts_with(&format!("0,{}\n100,", "00".repeat(32))));
        assert!(text.ends_with('\n'));
        assert!(!text.contains('{'), "no JSON: {text}");
        assert_eq!(HashLog::parse(&text).unwrap(), log);
        // CRLF and blank lines are tolerated on the way in.
        let crlf = text.replace('\n', "\r\n") + "\r\n\r\n";
        assert_eq!(HashLog::parse(&crlf).unwrap(), log);
        assert_eq!(log.hash_at(100), Some(HexHash([1; 32])));
        assert_eq!(log.hash_at(101), None);
        assert_eq!(log.describe(), "3 entries, every 100 ticks to 150");
    }

    #[test]
    fn hash_log_rejects_malformed_and_unordered_lines() {
        assert!(HashLog::parse("0\n")
            .unwrap_err()
            .contains("expected `tick,hash`"));
        assert!(HashLog::parse("x,00\n").unwrap_err().contains("bad tick"));
        assert!(HashLog::parse("0,00\n")
            .unwrap_err()
            .contains("64 hex chars"));
        let h = "00".repeat(32);
        let e = HashLog::parse(&format!("5,{h}\n5,{h}\n")).unwrap_err();
        assert!(e.contains("does not follow"), "{e}");
        let e = HashLog::parse(&format!("5,{h}\n4,{h}\n")).unwrap_err();
        assert!(e.contains("does not follow"), "{e}");
    }

    #[test]
    fn cadence_keeps_multiples_and_the_last_tick() {
        let c = Cadence::new(100, 250);
        let kept: Vec<u64> = (0..=250).filter(|t| c.keeps(*t)).collect();
        assert_eq!(kept, [0, 100, 200, 250]);
        assert_eq!(c.count(), 4);
        let c = Cadence::new(100, 300);
        assert_eq!(c.count(), 4);
        assert_eq!(Cadence::new(1, 10).count(), 11);
        assert_eq!(Cadence::new(0, 10).every, 1);
        assert_eq!(Cadence::new(1, 10).to_string(), "every tick");
    }
}
