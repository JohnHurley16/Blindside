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
