//! Ground truth. `pub(crate)` ONLY. See the invariant in CLAUDE.md.
//!
//! Phase 0: a placeholder world with a fixed set of agents whose positions random-walk
//! each tick. Enough for the state hash to change every tick and for an injected
//! non-determinism to have somewhere to hide.

use std::collections::BTreeMap;

use crate::rng::DeterministicRng;
use crate::{AgentId, Fx, Purpose, Tick};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Vec2Fx {
    pub x: Fx,
    pub y: Fx,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct AgentTruth {
    pub pos: Vec2Fx,
}

/// Ground truth for one match. Never leaves this crate as a type: tooling sees it as
/// strings through `diagnostics`, everything else sees a hash.
///
/// # State hash coverage (BLD-27)
///
/// `Sim::state_hash` covers everything that can affect a future tick and nothing that
/// cannot (PHASE-0-HARNESS.md: "Getting the hash wrong in either direction wastes
/// weeks"). `hash.rs` writes the fields in this order and `diagnostics::dump` renders
/// them in the same order; `hash.rs` has a mutation test per row.
///
/// | Field | Hashed | Why |
/// |---|---|---|
/// | `Sim::seed` | yes | every RNG draw is a function of it |
/// | `tick` | yes | the RNG's first input, and what a replay's commands are keyed on |
/// | `inject_fold` | yes | must be hashed or the BLD-35 injection would be invisible; always 0 unless the `inject-desync` fixture fires |
/// | `agents` -- count, then per agent in `AgentId` order: id, `pos.x`, `pos.y` | yes | positions are the only evolving state; the id is hashed with them so a re-keyed agent changes the hash and so does a missing one |
/// | `moved_last_step` | **no** | derived: rewritten from scratch by every `step` and read by nothing that affects a tick. Exists to prove the hash ignores a cache; `hash.rs` mutates it and expects the same hash |
/// | `DeterministicRng` | no, beyond the seed | stateless -- there is no counter to hash. Keep it that way; if one is ever added it goes in the "yes" rows |
///
/// Adding a field: pick its row, add it to `StateHash for World` AND `hash::debug_fields`
/// in the same position, bump `hash::LAYOUT_VERSION`, and re-pin the golden hashes.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct World {
    pub tick: Tick,
    /// Keyed by stable ID; `BTreeMap` iterates in key order (DETERMINISM.md rule 6).
    pub agents: BTreeMap<AgentId, AgentTruth>,
    /// Target of the BLD-35 `inject-desync` fixture. Hashed. 0 in every build until the
    /// fixture folds a `HashMap` iteration order into it; the field is unconditional so
    /// that builds with and without the feature share one hash layout and agree until the
    /// injection tick.
    pub inject_fold: u64,
    /// EXCLUDED from the hash (see the table above): how many agents the last `step`
    /// moved. Derived, recomputed every tick, read by nothing.
    pub moved_last_step: u32,
}

/// Phase 0 placeholder roster. Agent IDs are explicit, not derived from position in
/// this list (rule 7). Later phases replace this with match setup from a `MatchRecord`.
const INITIAL_AGENTS: &[(AgentId, i32, i32)] = &[(AgentId(1), 0, 0), (AgentId(2), 10, -10)];

/// Entries in the injected `HashMap`. The story asks for at least 16; 32 makes two maps
/// with different `RandomState` keys agree on iteration order with negligible
/// probability, so the fixture fires every run.
#[cfg(feature = "inject-desync")]
pub(crate) const INJECT_ENTRIES: u64 = 32;

impl World {
    pub fn new() -> World {
        let mut agents = BTreeMap::new();
        for &(id, x, y) in INITIAL_AGENTS {
            let prev = agents.insert(
                id,
                AgentTruth {
                    pos: Vec2Fx {
                        x: Fx::from_num(x),
                        y: Fx::from_num(y),
                    },
                },
            );
            debug_assert!(prev.is_none(), "duplicate AgentId in INITIAL_AGENTS");
        }
        World {
            tick: Tick(0),
            agents,
            inject_fold: 0,
            moved_last_step: 0,
        }
    }

    pub fn step(&mut self, rng: &DeterministicRng) {
        self.tick = Tick(self.tick.0 + 1);
        let tick = self.tick;
        // Each agent moves by a draw in [-0.5, 0.5) on each axis.
        let half = Fx::from_num(1) / 2;
        // Iteration order is by AgentId (BTreeMap key order). The RNG is stateless, so
        // even if this order changed the drawn values would not.
        let mut moved = 0u32;
        for (id, agent) in self.agents.iter_mut() {
            let dx = rng.draw(tick, id.0, Purpose::MoveX) - half;
            let dy = rng.draw(tick, id.0, Purpose::MoveY) - half;
            agent.pos.x = agent.pos.x.wrapping_add(dx);
            agent.pos.y = agent.pos.y.wrapping_add(dy);
            moved += 1;
        }
        self.moved_last_step = moved;
    }

    /// The BLD-35 fixture: the one sanctioned `HashMap` in a constrained crate, and the
    /// rule-2 violation the canary exists to catch. Builds a fresh `HashMap` -- fresh
    /// means a fresh `RandomState`, so two instances in one process get different keys
    /// and, with 32 entries, different iteration orders -- and folds that order into the
    /// hashed `inject_fold` with a polynomial fold, which is order-dependent and
    /// non-commutative: the same keys visited in another order give another value.
    ///
    /// Both canary instances call this on the injection tick, independently, exactly as
    /// two instances of a sim with a real HashMap bug would. The determinism lint exempts
    /// `HashMap` inside an item under `#[cfg(feature = "inject-desync")]` and nowhere
    /// else (tools/determinism-lint; the exemption never covers a module path).
    #[cfg(feature = "inject-desync")]
    pub fn inject_desync(&mut self) {
        let mut map: std::collections::HashMap<u64, u64> =
            std::collections::HashMap::with_capacity(INJECT_ENTRIES as usize);
        for k in 0..INJECT_ENTRIES {
            // Spread keys so they land in different buckets; the values are irrelevant.
            map.insert(k.wrapping_mul(0x9E37_79B9_7F4A_7C15), k);
        }
        let mut fold: u64 = 0xCBF2_9CE4_8422_2325;
        for key in map.keys() {
            fold = fold.wrapping_mul(0x0000_0100_0000_01B3) ^ *key;
        }
        self.inject_fold = fold;
    }
}
