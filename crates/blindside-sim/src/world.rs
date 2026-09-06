//! Ground truth. `pub(crate)` ONLY. See the invariant in CLAUDE.md.
//!
//! Phase 0: a placeholder world with a fixed set of agents whose positions random-walk
//! each tick. Enough for the state hash to change every tick and for an injected
//! non-determinism to have somewhere to hide.

use std::collections::BTreeMap;

use crate::rng::DeterministicRng;
use crate::{AgentId, Fx, Tick};

/// RNG purpose IDs used by the world step. Stable; never renumber.
pub(crate) mod purpose {
    pub const MOVE_X: u16 = 1;
    pub const MOVE_Y: u16 = 2;
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Vec2Fx {
    pub x: Fx,
    pub y: Fx,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct AgentTruth {
    pub pos: Vec2Fx,
}

pub(crate) struct World {
    pub tick: Tick,
    /// Keyed by stable ID; `BTreeMap` iterates in key order (DETERMINISM.md rule 6).
    pub agents: BTreeMap<AgentId, AgentTruth>,
}

/// Phase 0 placeholder roster. Agent IDs are explicit, not derived from position in
/// this list (rule 7). Later phases replace this with match setup from a `MatchRecord`.
const INITIAL_AGENTS: &[(AgentId, i32, i32)] = &[(AgentId(1), 0, 0), (AgentId(2), 10, -10)];

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
        }
    }

    pub fn step(&mut self, rng: &DeterministicRng) {
        self.tick = Tick(self.tick.0 + 1);
        let tick = self.tick;
        // Each agent moves by a draw in [-0.5, 0.5) on each axis.
        let half = Fx::from_num(1) / 2;
        // Iteration order is by AgentId (BTreeMap key order). The RNG is stateless, so
        // even if this order changed the drawn values would not.
        for (id, agent) in self.agents.iter_mut() {
            let dx = rng.draw(tick, id.0, purpose::MOVE_X) - half;
            let dy = rng.draw(tick, id.0, purpose::MOVE_Y) - half;
            agent.pos.x = agent.pos.x.wrapping_add(dx);
            agent.pos.y = agent.pos.y.wrapping_add(dy);
        }
    }
}
