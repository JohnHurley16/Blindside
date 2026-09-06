//! On-disk replay formats (harness only; serde is fine here).
//!
//! `MatchRecord` mirrors the struct in `docs/ARCHITECTURE.md`. In Phase 0 the sim takes
//! no loadouts, policies or commands, so those fields are carried as opaque JSON values
//! and must be empty; Phase 3 replaces them with typed structs and bumps
//! `MATCH_RECORD_SCHEMA`.
//!
//! `HashLog` is the per-tick sidecar written by `harness record` and checked by
//! `harness verify`: `hashes[t]` is the state hash at tick `t`, for `t` in `0..=ticks`,
//! so `hashes[0]` is the freshly constructed state and `hashes[ticks]` is the final one.

use std::fmt;
use std::path::Path;

use serde::{Deserialize, Serialize};

/// Version of the `MatchRecord` JSON layout. Bump on any incompatible change.
pub const MATCH_RECORD_SCHEMA: u16 = 0;

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

/// Hash of the content pack a replay was recorded against (DETERMINISM.md: "Replays carry
/// a content pack hash").
///
/// Phase 0 has no content pack, so this is BLAKE3 over a fixed placeholder tag plus the
/// content schema version. It is a real field with real checking so that the day a
/// content pack exists, nothing about the replay format changes except this function.
pub fn content_hash() -> HexHash {
    let mut h = blake3::Hasher::new();
    h.update(b"blindside-content placeholder pack v0");
    h.update(&blindside_content::CONTENT_SCHEMA.to_le_bytes());
    HexHash(*h.finalize().as_bytes())
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
    /// Phase 0: must be empty. `(Tick, TeamId, Command)` in Phase 3.
    pub commands: Vec<serde_json::Value>,
    /// Number of ticks the match ran for.
    pub ticks: u64,
    /// State hash at tick `ticks`.
    pub final_hash: HexHash,
}

impl MatchRecord {
    /// Load and validate. Rejects a record from another schema, another content pack,
    /// or carrying inputs the Phase 0 sim cannot consume.
    pub fn load(path: &Path) -> Result<MatchRecord, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        let rec: MatchRecord = serde_json::from_str(&text)
            .map_err(|e| format!("{} is not a MatchRecord: {e}", path.display()))?;
        rec.validate()?;
        Ok(rec)
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.schema != MATCH_RECORD_SCHEMA {
            return Err(format!(
                "record schema {} but this harness reads schema {}",
                self.schema, MATCH_RECORD_SCHEMA
            ));
        }
        let want = content_hash();
        if self.content_hash != want {
            return Err(format!(
                "content hash mismatch: record {} but current content pack {want}",
                self.content_hash
            ));
        }
        if !self.loadouts.is_empty() || !self.policies.is_empty() || !self.commands.is_empty() {
            return Err(
                "Phase 0 sim accepts no loadouts, policies or commands; record has some".into(),
            );
        }
        Ok(())
    }

    pub fn save(&self, path: &Path) -> Result<(), String> {
        let text = serde_json::to_string_pretty(self).map_err(|e| e.to_string())?;
        std::fs::write(path, text).map_err(|e| format!("cannot write {}: {e}", path.display()))
    }
}

/// Per-tick hash sidecar. See the module docs for indexing.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct HashLog {
    pub seed: u64,
    pub ticks: u64,
    pub hashes: Vec<HexHash>,
}

impl HashLog {
    pub fn load(path: &Path) -> Result<HashLog, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        serde_json::from_str(&text).map_err(|e| format!("{} is not a HashLog: {e}", path.display()))
    }

    pub fn save(&self, path: &Path) -> Result<(), String> {
        let text = serde_json::to_string_pretty(self).map_err(|e| e.to_string())?;
        std::fs::write(path, text).map_err(|e| format!("cannot write {}: {e}", path.display()))
    }
}
