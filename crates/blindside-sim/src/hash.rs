//! Canonical serialisation of everything that affects future ticks.
//!
//! Hand-written, little-endian, fields in a fixed order, maps in key order. No serde, no
//! derived hashing. The byte layout is the contract, and it must be identical on every
//! platform and stable across compiler versions.
//!
//! DEFAULT (awaiting designer): the hasher is BLAKE3, 256 bits, over this layout -- the
//! BLD-20 recommendation (matches the width of `content_hash`; fixed-key; never std's
//! `DefaultHasher`, which is randomly keyed per process and unstable across versions).
//!
//! `StateHash for World` and `debug_fields` MUST cover the same fields in the same order.
//! The canary diffs `debug_fields` output (through `diagnostics`) when hashes disagree, so
//! a field present in one but not the other produces either an undiagnosable divergence
//! or a diff that lies. The coverage table lives on `World`.

use std::collections::BTreeMap;

use crate::world::{AgentTruth, Vec2Fx, World};
use crate::{AgentId, Fx, Sim, Tick};

/// Layout version. Bump when the byte layout below changes so old recorded hashes are
/// not compared against new ones by accident.
///
/// History: 1 -- seed, tick, agents. 2 -- `inject_fold` inserted after `tick` (BLD-35).
pub(crate) const LAYOUT_VERSION: u16 = 2;

/// Serialise a hashed field. One impl per World field type, so the coverage list on
/// `World` is also the list of impls that feed the hash.
pub(crate) trait StateHash {
    fn write_state(&self, out: &mut Vec<u8>);
}

impl StateHash for u16 {
    fn write_state(&self, out: &mut Vec<u8>) {
        out.extend_from_slice(&self.to_le_bytes());
    }
}

impl StateHash for u32 {
    fn write_state(&self, out: &mut Vec<u8>) {
        out.extend_from_slice(&self.to_le_bytes());
    }
}

impl StateHash for u64 {
    fn write_state(&self, out: &mut Vec<u8>) {
        out.extend_from_slice(&self.to_le_bytes());
    }
}

impl StateHash for Fx {
    /// Raw bits, never a decimal rendering: a one-ulp difference must change the hash.
    fn write_state(&self, out: &mut Vec<u8>) {
        out.extend_from_slice(&self.to_bits().to_le_bytes());
    }
}

impl StateHash for Tick {
    fn write_state(&self, out: &mut Vec<u8>) {
        self.0.write_state(out);
    }
}

impl StateHash for AgentId {
    fn write_state(&self, out: &mut Vec<u8>) {
        self.0.write_state(out);
    }
}

impl StateHash for Vec2Fx {
    fn write_state(&self, out: &mut Vec<u8>) {
        self.x.write_state(out);
        self.y.write_state(out);
    }
}

impl StateHash for AgentTruth {
    fn write_state(&self, out: &mut Vec<u8>) {
        self.pos.write_state(out);
    }
}

/// Count, then every (key, value) in key order (DETERMINISM.md rule 6): the same entries
/// inserted in any order serialise identically, and the key is part of the bytes so an
/// entry that moved to another key is a different state.
impl<K: StateHash, V: StateHash> StateHash for BTreeMap<K, V> {
    fn write_state(&self, out: &mut Vec<u8>) {
        (self.len() as u32).write_state(out);
        for (k, v) in self {
            k.write_state(out);
            v.write_state(out);
        }
    }
}

/// The coverage table on `World` is the spec for this impl. `moved_last_step` is
/// deliberately absent.
impl StateHash for World {
    fn write_state(&self, out: &mut Vec<u8>) {
        self.tick.write_state(out);
        self.inject_fold.write_state(out);
        self.agents.write_state(out);
    }
}

pub(crate) fn write_canonical(sim: &Sim, out: &mut Vec<u8>) {
    LAYOUT_VERSION.write_state(out);
    sim.seed.write_state(out);
    sim.world.write_state(out);
}

/// The hashed fields as `(path, value)` strings, in hash order: declaration order, then
/// stable-ID order inside collections. `diagnostics::dump` and `diagnostics::diff` are
/// built on this. Compiled only where something reads it, so the plain hash-producing
/// build (`cargo build -p blindside-sim`) is warning-free.
#[cfg(any(test, feature = "diagnostics"))]
pub(crate) fn debug_fields(sim: &Sim) -> Vec<(String, String)> {
    let mut f: Vec<(String, String)> = Vec::new();
    f.push(("seed".into(), sim.seed.to_string()));
    f.push(("tick".into(), sim.world.tick.0.to_string()));
    f.push((
        "inject_fold".into(),
        format!("{:#018x}", sim.world.inject_fold),
    ));
    f.push(("agents.len".into(), sim.world.agents.len().to_string()));
    for (id, agent) in &sim.world.agents {
        let k = format!("agents[{}]", id.0);
        f.push((format!("{k}.pos.x"), fx_debug(agent.pos.x)));
        f.push((format!("{k}.pos.y"), fx_debug(agent.pos.y)));
    }
    f
}

/// Exact decimal rendering plus the raw bits, so a one-ulp divergence is visible.
#[cfg(any(test, feature = "diagnostics"))]
fn fx_debug(v: Fx) -> String {
    format!("{v} (0x{:016x})", v.to_bits())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::DeterministicRng;

    /// The empty Phase 0 record for a seed, through the one constructor.
    fn sim(seed: u64) -> Sim {
        Sim::new(&crate::MatchRecord::seed_only(seed))
    }

    fn sim_after(seed: u64, steps: u64) -> Sim {
        let mut s = sim(seed);
        for _ in 0..steps {
            s.step();
        }
        s
    }

    fn hex(h: [u8; 32]) -> String {
        h.iter().map(|b| format!("{b:02x}")).collect()
    }

    /// One named mutation of a hashed field.
    type Mutation = (&'static str, Box<dyn Fn(&mut Sim)>);

    /// BLD-27: for each hashed field, mutating it changes the hash (and the debug dump,
    /// which must move with it).
    #[test]
    fn mutating_each_hashed_field_changes_the_hash() {
        let base = sim_after(5, 10);
        let base_hash = base.state_hash();
        let base_debug = debug_fields(&base);
        let mutations: Vec<Mutation> = vec![
            ("seed", Box::new(|s| s.seed ^= 1)),
            (
                "tick",
                Box::new(|s| s.world.tick = Tick(s.world.tick.0 + 1)),
            ),
            ("inject_fold", Box::new(|s| s.world.inject_fold ^= 1)),
            (
                "agents.len",
                Box::new(|s| {
                    s.world.agents.remove(&AgentId(2));
                }),
            ),
            (
                "agents[id] (re-key)",
                Box::new(|s| {
                    let a = s.world.agents.remove(&AgentId(2)).unwrap();
                    s.world.agents.insert(AgentId(3), a);
                }),
            ),
            (
                "agents[1].pos.x",
                Box::new(|s| {
                    let a = s.world.agents.get_mut(&AgentId(1)).unwrap();
                    a.pos.x = a.pos.x.wrapping_add(Fx::from_bits(1));
                }),
            ),
            (
                "agents[2].pos.y",
                Box::new(|s| {
                    let a = s.world.agents.get_mut(&AgentId(2)).unwrap();
                    a.pos.y = a.pos.y.wrapping_add(Fx::from_bits(1));
                }),
            ),
        ];
        for (name, mutate) in mutations {
            let mut s = base.clone();
            mutate(&mut s);
            assert_ne!(s.state_hash(), base_hash, "hash ignored {name}");
            assert_ne!(debug_fields(&s), base_debug, "debug dump ignored {name}");
        }
    }

    /// BLD-27: the deliberately excluded cache field does not change the hash.
    #[test]
    fn mutating_the_excluded_cache_field_does_not_change_the_hash() {
        let base = sim_after(5, 10);
        let mut s = base.clone();
        s.world.moved_last_step = 999;
        assert_ne!(s.world, base.world, "the mutation happened");
        assert_eq!(s.state_hash(), base.state_hash());
        assert_eq!(debug_fields(&s), debug_fields(&base));
    }

    /// BLD-27: a keyed collection hashes in stable-ID order, whatever order it was built in.
    #[test]
    fn insertion_order_does_not_change_the_hash() {
        let forward = sim_after(9, 3);
        let mut reversed = sim(9);
        let mut agents: Vec<(AgentId, AgentTruth)> = forward
            .world
            .agents
            .iter()
            .map(|(k, v)| (*k, v.clone()))
            .collect();
        agents.reverse();
        reversed.world = World {
            tick: forward.world.tick,
            agents: agents.into_iter().collect(),
            inject_fold: forward.world.inject_fold,
            moved_last_step: forward.world.moved_last_step,
        };
        assert_eq!(forward.state_hash(), reversed.state_hash());
        assert_eq!(debug_fields(&forward), debug_fields(&reversed));
    }

    #[test]
    fn debug_fields_follow_the_hash_layout_order() {
        let s = sim(3);
        let keys: Vec<String> = debug_fields(&s).into_iter().map(|(k, _)| k).collect();
        assert_eq!(
            keys,
            [
                "seed",
                "tick",
                "inject_fold",
                "agents.len",
                "agents[1].pos.x",
                "agents[1].pos.y",
                "agents[2].pos.x",
                "agents[2].pos.y",
            ]
        );
        assert_eq!(s.state_hash().len(), 32, "256-bit hash");
        assert_eq!(DeterministicRng::new(3), s.rng);
    }

    /// BLD-27 golden hashes: the empty sim on the canary's default seed at ticks 0, 1 and
    /// 10,000, plus the tick-1000 pin the harness shares. CI on Linux, macOS and Windows
    /// must all agree with these. A change here means the sim, the RNG or the layout
    /// changed, and needs a LAYOUT_VERSION bump and a deliberate re-pin.
    #[test]
    fn golden_hashes_for_the_empty_sim() {
        let mut s = sim(0xDEAD_BEEF);
        assert_eq!(hex(s.state_hash()), GOLDEN_SEED_DEADBEEF_TICK_0, "tick 0");
        s.step();
        assert_eq!(hex(s.state_hash()), GOLDEN_SEED_DEADBEEF_TICK_1, "tick 1");
        for _ in 1..1000 {
            s.step();
        }
        assert_eq!(
            hex(s.state_hash()),
            GOLDEN_SEED_DEADBEEF_TICK_1000,
            "tick 1000"
        );
        for _ in 1000..10_000 {
            s.step();
        }
        assert_eq!(s.tick(), Tick(10_000));
        assert_eq!(
            hex(s.state_hash()),
            GOLDEN_SEED_DEADBEEF_TICK_10000,
            "tick 10000"
        );
    }

    pub(crate) const GOLDEN_SEED_DEADBEEF_TICK_0: &str =
        "84cc366439a1a277a5a0296d72fe9068a11beb098f952be099b475f670e26385";
    pub(crate) const GOLDEN_SEED_DEADBEEF_TICK_1: &str =
        "033a0ee09a6f9f7379be75cf385d2ace0d32c707899f56d694f1d42f50c80fe2";
    pub(crate) const GOLDEN_SEED_DEADBEEF_TICK_1000: &str =
        "f1f69639853665744a704bae5e7d5e1a15986d4748e95d1870ccab665c7dbb9f";
    pub(crate) const GOLDEN_SEED_DEADBEEF_TICK_10000: &str =
        "653b9057c4dd809407213920a217794adafd41c7ea92976e6bf344b76a5639bc";
}
