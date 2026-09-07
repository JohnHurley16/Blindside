//! `MatchRecord`: the replay. Seed, schema, content pack hash, loadouts, policies and the
//! command log -- the only live input (ARCHITECTURE.md "recording") -- plus the two
//! fields Phase 0 needs to verify a replay.
//!
//! The in-memory type lives here because blindside-sim may depend on nothing but vm and
//! content (ARCHITECTURE.md), and the sim is what a record is an input to. The on-disk
//! encoding is the harness's business (`blindside-harness/src/record.rs`, JSON via serde);
//! this crate has no serialiser, only the rules a record must satisfy, so that every
//! loader -- harness, server, client -- validates the same way.
//!
//! DEFAULT (awaiting designer), both from BLD-20's recommendations: the record carries
//! `ticks` and `final_hash` (the acceptance criteria need a length to run "to completion"
//! and a recorded hash to verify against; ARCHITECTURE's struct has neither); and the
//! on-disk format is JSON.

use crate::{TeamId, Tick};

/// Version of the record layout. Checked on load; a record from another schema is
/// migrated through [`MatchRecord::migrate`] or refused, never guessed at.
///
/// Rule (BLD-30, for the PR template): any change to a serialised field bumps this in the
/// same PR, and the old schema gains a `migrate` arm.
pub const MATCH_RECORD_SCHEMA: u16 = 0;

/// What a team brings to a match. Empty stub in Phase 0; typed in Phase 3.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Loadout;

/// A reference to a policy (behaviour) a team fields. Empty stub in Phase 0.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct PolicyRef;

/// A live input from a team during the match. Empty stub in Phase 0.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Command;

/// One command in the log, with the coordinates that order it.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CommandEntry {
    /// The tick the command applies in.
    pub tick: Tick,
    pub team: TeamId,
    /// Orders a team's commands within one tick. Assigned by the team's client in the
    /// order it issued them; never reused within a (tick, team).
    pub sequence: u32,
    pub command: Command,
}

impl CommandEntry {
    /// The total order of the command log: (tick, team, sequence).
    pub fn key(&self) -> (Tick, TeamId, u32) {
        (self.tick, self.team, self.sequence)
    }
}

/// A replay. See the module docs for what is decided and what is defaulted.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MatchRecord {
    pub schema: u16,
    pub seed: u64,
    /// `blindside_content::content_hash` of the pack the match was played against.
    /// Replays break silently without this.
    pub content_hash: [u8; 32],
    pub loadouts: Vec<Loadout>,
    pub policies: Vec<PolicyRef>,
    /// The only live input. Stored sorted by [`CommandEntry::key`], strictly ascending;
    /// [`MatchRecord::validate`] refuses anything else.
    pub commands: Vec<CommandEntry>,
    /// Number of ticks the match ran for. The sim runs `ticks` steps from tick 0.
    pub ticks: u64,
    /// `Sim::state_hash()` at tick `ticks`.
    pub final_hash: [u8; 32],
}

/// Why a record is not usable. Typed, so a loader can tell "wrong version" from "corrupt".
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum RecordError {
    /// A schema this build cannot read: newer than [`MATCH_RECORD_SCHEMA`], or one with no
    /// migration arm.
    UnknownSchema { found: u16, supported: u16 },
    /// `commands[index]` sorts before or equal to `commands[index - 1]`.
    UnsortedCommands { index: usize },
}

impl std::fmt::Display for RecordError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            RecordError::UnknownSchema { found, supported } => write!(
                f,
                "record schema {found} but this build reads schema {supported} (and migrates older ones)"
            ),
            RecordError::UnsortedCommands { index } => write!(
                f,
                "commands are not sorted by (tick, team, sequence): entry {index} does not follow entry {}",
                index - 1
            ),
        }
    }
}

impl std::error::Error for RecordError {}

impl MatchRecord {
    /// Test-only: the empty Phase 0 record for a seed -- no inputs, a zero content hash,
    /// zero ticks, zero final hash. Exists so the crate's own tests build a `Sim` through
    /// the one constructor without inventing a second one (BLD-23: no ad-hoc constructor).
    /// Tooling outside the crate builds records with its content hash filled in.
    #[cfg(test)]
    pub(crate) fn seed_only(seed: u64) -> MatchRecord {
        MatchRecord {
            schema: MATCH_RECORD_SCHEMA,
            seed,
            content_hash: [0; 32],
            loadouts: Vec::new(),
            policies: Vec::new(),
            commands: Vec::new(),
            ticks: 0,
            final_hash: [0; 32],
        }
    }

    /// Bring a record of any known schema up to [`MATCH_RECORD_SCHEMA`]. The chain is
    /// identity for schema 0 today; each future schema adds an arm that rewrites the
    /// previous one, so a Phase 0 replay stays loadable a year on (DETERMINISM.md: a
    /// schema version with a migration path). Migration does not validate; call
    /// [`MatchRecord::validate`] after.
    pub fn migrate(self) -> Result<MatchRecord, RecordError> {
        match self.schema {
            MATCH_RECORD_SCHEMA => Ok(self),
            found => Err(RecordError::UnknownSchema {
                found,
                supported: MATCH_RECORD_SCHEMA,
            }),
        }
    }

    /// The rules every loader applies: current schema, commands strictly sorted by
    /// (tick, team, sequence). Content hash agreement is checked by the loader that knows
    /// which pack is loaded.
    pub fn validate(&self) -> Result<(), RecordError> {
        if self.schema != MATCH_RECORD_SCHEMA {
            return Err(RecordError::UnknownSchema {
                found: self.schema,
                supported: MATCH_RECORD_SCHEMA,
            });
        }
        for (i, w) in self.commands.windows(2).enumerate() {
            if w[0].key() >= w[1].key() {
                return Err(RecordError::UnsortedCommands { index: i + 1 });
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn record(commands: Vec<CommandEntry>) -> MatchRecord {
        MatchRecord {
            schema: MATCH_RECORD_SCHEMA,
            seed: 7,
            content_hash: [0; 32],
            loadouts: Vec::new(),
            policies: Vec::new(),
            commands,
            ticks: 10,
            final_hash: [0; 32],
        }
    }

    fn cmd(tick: u64, team: u16, sequence: u32) -> CommandEntry {
        CommandEntry {
            tick: Tick(tick),
            team: TeamId(team),
            sequence,
            command: Command,
        }
    }

    #[test]
    fn migrate_is_identity_for_the_current_schema() {
        let r = record(Vec::new());
        assert_eq!(r.clone().migrate(), Ok(r));
    }

    #[test]
    fn unknown_schema_is_a_typed_error_from_migrate_and_validate() {
        let mut r = record(Vec::new());
        r.schema = MATCH_RECORD_SCHEMA + 1;
        let want = RecordError::UnknownSchema {
            found: MATCH_RECORD_SCHEMA + 1,
            supported: MATCH_RECORD_SCHEMA,
        };
        assert_eq!(r.validate(), Err(want.clone()));
        assert_eq!(r.migrate(), Err(want));
    }

    #[test]
    fn sorted_commands_validate() {
        let r = record(vec![
            cmd(1, 0, 0),
            cmd(1, 0, 1),
            cmd(1, 1, 0),
            cmd(2, 0, 0),
            cmd(2, 0, 5),
        ]);
        assert_eq!(r.validate(), Ok(()));
        assert_eq!(record(Vec::new()).validate(), Ok(()));
        assert_eq!(record(vec![cmd(3, 3, 3)]).validate(), Ok(()));
    }

    #[test]
    fn unsorted_commands_are_a_typed_error_naming_the_entry() {
        // Out of order on each coordinate, and a duplicate key.
        let cases = [
            (vec![cmd(2, 0, 0), cmd(1, 0, 0)], 1),
            (vec![cmd(1, 1, 0), cmd(1, 0, 0)], 1),
            (vec![cmd(1, 0, 1), cmd(1, 0, 0)], 1),
            (vec![cmd(1, 0, 0), cmd(1, 0, 1), cmd(1, 0, 1)], 2),
        ];
        for (commands, index) in cases {
            assert_eq!(
                record(commands).validate(),
                Err(RecordError::UnsortedCommands { index })
            );
        }
    }
}
