//! blindside-sim: the deterministic core.
//!
//! Phase 0: an EMPTY but real simulation. It exists so the harness, canary, replay and
//! bisect tooling can be built and proven against something whose state hash changes
//! every tick. There is no cave, no sensors, no policies yet; just a handful of agents
//! whose ground-truth positions advance by RNG-drawn amounts.
//!
//! Hard rules (docs/DETERMINISM.md) apply to every line of this crate:
//! see docs/DETERMINISM.md rules 1-8. In short: fixed-point only, ordered maps only,
//! no wall clock, stateless RNG, no threads inside a tick, iteration by stable ID.
//!
//! The one invariant (CLAUDE.md): `World` is `pub(crate)`. Nothing outside this crate can
//! observe ground truth. The production API is the tick, the seed and a hash. The two
//! ground-truth hooks the harness needs (`state_debug` for canary diffs, `perturb_for_test`
//! for the injected-divergence test) exist only behind the `test-hooks` cargo feature,
//! which `blindside-harness` enables and no client crate may.

mod hash;
mod ids;
mod rng;
mod world;

pub use ids::{ActionId, AgentId, AncientKindId, ModuleId, PredicateId, SensorId, Tick};
pub use rng::DeterministicRng;

/// Fixed-point scalar used everywhere in the sim. No floating point, ever.
pub type Fx = fixed::types::I32F32;

use world::World;

/// One simulation instance.
///
/// Constructed from a seed, stepped one tick at a time. Two `Sim`s built from the same
/// seed and stepped the same number of times must report identical `state_hash()`es on
/// every platform. That is the property the Phase 0 canary exists to check.
pub struct Sim {
    seed: u64,
    rng: DeterministicRng,
    world: World,
}

impl Sim {
    /// Build a sim from a seed. Everything else is derived deterministically.
    pub fn new(seed: u64) -> Sim {
        Sim {
            seed,
            rng: DeterministicRng::new(seed),
            world: World::new(),
        }
    }

    /// Advance the simulation by exactly one tick.
    pub fn step(&mut self) {
        self.world.step(&self.rng);
    }

    /// The current tick. Tick 0 is the freshly-constructed state.
    pub fn tick(&self) -> Tick {
        self.world.tick
    }

    /// The seed this sim was constructed from.
    pub fn seed(&self) -> u64 {
        self.seed
    }

    /// Platform-independent hash of everything that can affect future ticks.
    ///
    /// BLAKE3 over the canonical little-endian serialisation in `hash.rs`. Never the
    /// standard library's default hasher (randomly keyed, not stable across versions).
    pub fn state_hash(&self) -> [u8; 32] {
        let mut bytes = Vec::with_capacity(64);
        hash::write_canonical(self, &mut bytes);
        *blake3::hash(&bytes).as_bytes()
    }

    /// Structured, diff-friendly dump of the hashed state: `(field path, value)` pairs in
    /// a fixed order. The canary diffs two of these when hashes diverge.
    ///
    /// Covers exactly the same fields as `state_hash()`, in the same order. If you add a
    /// field to one, add it to the other.
    ///
    /// HARNESS HOOK: exposes ground truth, so it exists only with the `test-hooks`
    /// feature. Never enable that feature from a client, policy or renderer crate.
    #[cfg(feature = "test-hooks")]
    pub fn state_debug(&self) -> Vec<(String, String)> {
        hash::debug_fields(self)
    }

    /// TEST HOOK for the harness canary (`harness canary --inject`). Not sim logic;
    /// nothing in this crate calls it.
    ///
    /// Applies an externally supplied entity ordering to ground truth: the agent at
    /// position `i` of `order` has `i + 1` added to its x coordinate. IDs that name no
    /// agent are ignored. Returns how many agents were touched.
    ///
    /// The harness derives `order` from iterating a `std::collections::HashMap`, i.e.
    /// from exactly the kind of non-determinism DETERMINISM.md rule 2 bans, and checks
    /// that the canary reports the divergence in the tick this was called.
    ///
    /// Exists only with the `test-hooks` feature; see `state_debug`.
    #[cfg(feature = "test-hooks")]
    pub fn perturb_for_test(&mut self, order: &[u32]) -> usize {
        let mut touched = 0;
        for (i, id) in order.iter().enumerate() {
            if let Some(agent) = self.world.agents.get_mut(&AgentId(*id)) {
                agent.pos.x = agent.pos.x.wrapping_add(Fx::from_num((i + 1) as i32));
                touched += 1;
            }
        }
        touched
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The tests read the debug dump through the crate-internal function so they pass
    /// with or without the `test-hooks` feature.
    fn state_debug(s: &Sim) -> Vec<(String, String)> {
        hash::debug_fields(s)
    }

    #[test]
    fn same_seed_hashes_identically_for_1000_ticks() {
        let mut a = Sim::new(0xDEAD_BEEF);
        let mut b = Sim::new(0xDEAD_BEEF);
        for t in 0..=1000u64 {
            assert_eq!(a.tick(), Tick(t));
            assert_eq!(a.tick(), b.tick());
            assert_eq!(a.state_hash(), b.state_hash(), "hash diverged at tick {t}");
            assert_eq!(
                state_debug(&a),
                state_debug(&b),
                "debug diverged at tick {t}"
            );
            a.step();
            b.step();
        }
    }

    #[test]
    fn hash_changes_every_tick() {
        let mut s = Sim::new(7);
        let mut prev = s.state_hash();
        for t in 1..=1000u64 {
            s.step();
            let h = s.state_hash();
            assert_ne!(
                h,
                prev,
                "hash did not change between tick {} and {t}",
                t - 1
            );
            prev = h;
        }
    }

    #[test]
    fn different_seeds_differ() {
        let mut a = Sim::new(1);
        let mut b = Sim::new(2);
        // Tick 0 already differs because the seed is part of the hashed state.
        assert_ne!(a.state_hash(), b.state_hash());
        for _ in 0..100 {
            a.step();
            b.step();
        }
        assert_ne!(a.state_hash(), b.state_hash());
        assert_ne!(state_debug(&a), state_debug(&b));
    }

    #[test]
    fn debug_and_hash_are_consistent() {
        // Equal debug dumps imply equal hashes and vice versa.
        let mut a = Sim::new(99);
        let mut b = Sim::new(99);
        for _ in 0..50 {
            a.step();
            b.step();
        }
        assert_eq!(state_debug(&a), state_debug(&b));
        assert_eq!(a.state_hash(), b.state_hash());
        b.step();
        assert_ne!(state_debug(&a), state_debug(&b));
        assert_ne!(a.state_hash(), b.state_hash());
    }

    #[test]
    fn debug_has_expected_shape() {
        let s = Sim::new(3);
        let d = state_debug(&s);
        let keys: Vec<&str> = d.iter().map(|(k, _)| k.as_str()).collect();
        assert_eq!(keys[0], "seed");
        assert_eq!(keys[1], "tick");
        assert!(keys.iter().any(|k| k.starts_with("agents[")));
    }

    #[test]
    fn known_hash_at_tick_1000() {
        // Cross-platform pin. CI on Linux, macOS and Windows must all agree with this.
        let mut s = Sim::new(0xDEAD_BEEF);
        for _ in 0..1000 {
            s.step();
        }
        let hex: String = s.state_hash().iter().map(|b| format!("{b:02x}")).collect();
        assert_eq!(hex, KNOWN_HASH_SEED_DEADBEEF_TICK_1000);
    }

    // Recorded from the first run; a change here means the sim or the layout changed.
    const KNOWN_HASH_SEED_DEADBEEF_TICK_1000: &str =
        "5a6930a5dab0a7627913befbc590c79453415c483200c8d4eb55eb8a3faaf17a";
}
