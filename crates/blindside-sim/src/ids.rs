//! Stable identifiers.
//!
//! Every ID here is assigned explicitly in content data files and never derived from a
//! name hash, registration order, or vector index (DETERMINISM.md rule 7). Retired IDs
//! are never reused.
//!
//! All ID types derive `Ord` so that collections keyed by them (`BTreeMap`) iterate in a
//! stable, platform-independent order (rule 6).

macro_rules! stable_id {
    ($(#[$meta:meta])* $name:ident($inner:ty)) => {
        $(#[$meta])*
        #[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
        pub struct $name(pub $inner);
    };
}

stable_id!(
    /// Simulation tick counter. Tick 0 is the initial state.
    ///
    /// DEFAULT (awaiting designer): `u64` -- the BLD-20 recommendation. Wide enough that no
    /// match, replay or batch can wrap it, and the hash layout writes it as 8 LE bytes.
    Tick(u64)
);
stable_id!(
    /// A sensor kind, from content data.
    SensorId(u16)
);
stable_id!(
    /// A predicate in the policy vocabulary, from content data.
    PredicateId(u16)
);
stable_id!(
    /// An action in the policy vocabulary, from content data.
    ActionId(u16)
);
stable_id!(
    /// A slotted module (sensor, beacon rack, cargo bay, ...), from content data.
    ModuleId(u16)
);
stable_id!(
    /// A kind of ancient system, from content data.
    AncientKindId(u16)
);
stable_id!(
    /// One agent instance within a match. Assigned by the match setup, never reused
    /// within a match.
    AgentId(u32)
);
stable_id!(
    /// A team within a match: the unit that issues commands. Assigned by the match setup.
    ///
    /// DEFAULT (awaiting designer): `u16` -- no document states a width; a match has a
    /// handful of teams and the record sorts commands by (tick, team, sequence), so a
    /// small, totally ordered integer is all that is needed.
    TeamId(u16)
);
