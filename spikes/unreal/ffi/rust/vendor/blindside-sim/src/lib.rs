//! blindside-sim: the deterministic core.
//!
//! Phase 0: an EMPTY but real simulation. It exists so the harness, canary, replay and
//! bisect tooling can be built and proven against something whose state hash changes
//! every tick. There is no cave, no sensors, no policies yet; just a handful of agents
//! whose ground-truth positions advance by RNG-drawn amounts.
//!
//! Hard rules (docs/DETERMINISM.md) apply to every line of this crate:
//! see docs/DETERMINISM.md rules 1-8. In short: fixed-point only, ordered maps only,
//! no wall clock, stateless RNG, no threads inside a tick, iteration by stable ID,
//! and no I/O of any kind (`std::fs`, `std::io`, `std::net`, `std::env`). The lint in
//! tools/determinism-lint rejects the spellings; `#![deny(unsafe_code)]` below makes any
//! `unsafe` an explicit, `// SAFETY:`-justified exception (rule 8, BLD-34).
//!
//! The one invariant (CLAUDE.md): `World` is `pub(crate)`. Nothing outside this crate can
//! observe ground truth. The production API is the tick, the seed and a hash. The one
//! window for tooling is the `diagnostics` module -- strings only, behind the
//! `diagnostics` feature, which `blindside-harness` enables and no client crate may.

#![deny(unsafe_code)]

mod hash;
mod ids;
mod record;
mod rng;
mod world;

pub mod fxmath;

#[cfg(feature = "diagnostics")]
pub mod diagnostics;

#[cfg(any(test, feature = "diagnostics"))]
pub mod testing;

#[cfg(test)]
mod golden;
#[cfg(test)]
mod golden_tables;

pub use ids::{ActionId, AgentId, AncientKindId, ModuleId, PredicateId, SensorId, TeamId, Tick};
pub use record::{
    Command, CommandEntry, Loadout, MatchRecord, PolicyRef, RecordError, MATCH_RECORD_SCHEMA,
};
pub use rng::{DeterministicRng, Purpose};

/// Fixed-point scalar used everywhere in the sim. No floating point, ever. Defined here
/// exactly once; `fixed` is pinned in the workspace root with no features.
pub type Fx = fixed::types::I32F32;

use world::World;

/// The build lacks the `inject-desync` feature, so `Sim::set_inject_tick` has nothing to
/// arm. Only the canary-injection CI job and the harness's own tests enable it.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct InjectDesyncUnavailable;

impl std::fmt::Display for InjectDesyncUnavailable {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(
            "this build of blindside-sim has no inject-desync fixture (build with \
             --features inject-desync)",
        )
    }
}

impl std::error::Error for InjectDesyncUnavailable {}

/// One simulation instance.
///
/// Constructed from a [`MatchRecord`] and stepped one tick at a time. Two `Sim`s built
/// from the same record and stepped the same number of times must report identical
/// `state_hash()`es on every platform. That is the property the Phase 0 canary exists to
/// check, and it checks it through this constructor and no other: the replay path is the
/// only path (BLD-23), so what the canary proves is what the runner, the server and the
/// client will run.
#[derive(Clone)]
pub struct Sim {
    seed: u64,
    rng: DeterministicRng,
    world: World,
    /// The tick whose `step` runs the BLD-35 injection, if armed.
    #[cfg(feature = "inject-desync")]
    inject_tick: Option<Tick>,
}

impl Sim {
    /// Build a sim from a record. Everything else is derived deterministically.
    ///
    /// Phase 0 consumes the seed and nothing else: the record's loadouts, policies and
    /// commands are empty stubs that Phase 3 types and applies here (loadouts and
    /// policies at construction, commands per tick in `step`). The record is not
    /// validated here -- a loader does that with [`MatchRecord::migrate`] and
    /// [`MatchRecord::validate`] before it has a record to hand over -- and `ticks` and
    /// `final_hash` are the caller's business: the sim does not know how long a match is,
    /// it only steps.
    pub fn new(record: &MatchRecord) -> Sim {
        let seed = record.seed;
        Sim {
            seed,
            rng: DeterministicRng::new(seed),
            world: World::new(),
            #[cfg(feature = "inject-desync")]
            inject_tick: None,
        }
    }

    /// Advance the simulation by exactly one tick.
    pub fn step(&mut self) {
        self.world.step(&self.rng);
        self.maybe_inject();
    }

    #[cfg(feature = "inject-desync")]
    fn maybe_inject(&mut self) {
        if self.inject_tick == Some(self.world.tick) {
            self.world.inject_desync();
        }
    }

    #[cfg(not(feature = "inject-desync"))]
    fn maybe_inject(&mut self) {}

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
    /// The coverage table is on `World`.
    pub fn state_hash(&self) -> [u8; 32] {
        let mut bytes = Vec::with_capacity(64);
        hash::write_canonical(self, &mut bytes);
        *blake3::hash(&bytes).as_bytes()
    }

    /// Whether this build carries the BLD-35 `inject-desync` fixture. Present in every
    /// build so tooling can compile against one API and report the difference at runtime.
    pub const fn inject_desync_available() -> bool {
        cfg!(feature = "inject-desync")
    }

    /// Arm (or, with `None`, disarm) the BLD-35 fixture: the `step` that produces `tick`
    /// folds a fresh `HashMap`'s iteration order into the hashed `World::inject_fold`.
    /// Tick 0 is the constructed state and no step produces it, so arming it does nothing.
    ///
    /// Without the `inject-desync` feature this is a stub that touches nothing and
    /// reports `Err(InjectDesyncUnavailable)`; the sim then contains no `HashMap` at all.
    #[cfg(feature = "inject-desync")]
    pub fn set_inject_tick(&mut self, tick: Option<Tick>) -> Result<(), InjectDesyncUnavailable> {
        self.inject_tick = tick;
        Ok(())
    }

    /// See the `inject-desync` version. This build has no fixture.
    #[cfg(not(feature = "inject-desync"))]
    pub fn set_inject_tick(&mut self, _tick: Option<Tick>) -> Result<(), InjectDesyncUnavailable> {
        Err(InjectDesyncUnavailable)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The empty Phase 0 record for a seed, through the one constructor.
    fn sim(seed: u64) -> Sim {
        Sim::new(&MatchRecord::seed_only(seed))
    }

    #[test]
    fn same_seed_hashes_identically_for_1000_ticks() {
        let mut a = sim(0xDEAD_BEEF);
        let mut b = sim(0xDEAD_BEEF);
        for t in 0..=1000u64 {
            assert_eq!(a.tick(), Tick(t));
            assert_eq!(a.tick(), b.tick());
            assert_eq!(a.state_hash(), b.state_hash(), "hash diverged at tick {t}");
            assert_eq!(
                hash::debug_fields(&a),
                hash::debug_fields(&b),
                "debug diverged at tick {t}"
            );
            a.step();
            b.step();
        }
    }

    #[test]
    fn hash_changes_every_tick() {
        let mut s = sim(7);
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
        let mut a = sim(1);
        let mut b = sim(2);
        // Tick 0 already differs because the seed is part of the hashed state.
        assert_ne!(a.state_hash(), b.state_hash());
        for _ in 0..100 {
            a.step();
            b.step();
        }
        assert_ne!(a.state_hash(), b.state_hash());
        assert_ne!(hash::debug_fields(&a), hash::debug_fields(&b));
    }

    #[test]
    fn debug_and_hash_are_consistent() {
        // Equal debug dumps imply equal hashes and vice versa.
        let mut a = sim(99);
        let mut b = sim(99);
        for _ in 0..50 {
            a.step();
            b.step();
        }
        assert_eq!(hash::debug_fields(&a), hash::debug_fields(&b));
        assert_eq!(a.state_hash(), b.state_hash());
        b.step();
        assert_ne!(hash::debug_fields(&a), hash::debug_fields(&b));
        assert_ne!(a.state_hash(), b.state_hash());
    }

    #[test]
    fn the_cache_field_is_rewritten_every_step() {
        let mut s = sim(4);
        assert_eq!(s.world.moved_last_step, 0);
        s.step();
        assert_eq!(s.world.moved_last_step, 2);
    }

    #[cfg(not(feature = "inject-desync"))]
    #[test]
    fn without_the_feature_injection_is_reported_unavailable_and_never_fires() {
        assert!(!Sim::inject_desync_available());
        let mut a = sim(5);
        let mut b = sim(5);
        assert_eq!(
            a.set_inject_tick(Some(Tick(3))),
            Err(InjectDesyncUnavailable)
        );
        for _ in 0..10 {
            a.step();
            b.step();
            assert_eq!(a.state_hash(), b.state_hash());
            assert_eq!(a.world.inject_fold, 0);
        }
    }

    /// BLD-35, sim side: two instances armed for the same tick agree until it and disagree
    /// from it on, because each folds its own `HashMap`'s order. Run 20 times, as the
    /// story asks, so a fixture that only usually fires is caught here and not in CI.
    #[cfg(feature = "inject-desync")]
    #[test]
    fn with_the_feature_two_instances_diverge_at_exactly_the_injection_tick() {
        assert!(Sim::inject_desync_available());
        for round in 0..20u64 {
            let inject_at = 5 + round;
            let mut a = sim(5);
            let mut b = sim(5);
            a.set_inject_tick(Some(Tick(inject_at))).unwrap();
            b.set_inject_tick(Some(Tick(inject_at))).unwrap();
            for t in 1..=inject_at + 5 {
                a.step();
                b.step();
                assert_eq!(a.tick(), Tick(t));
                if t < inject_at {
                    assert_eq!(
                        a.state_hash(),
                        b.state_hash(),
                        "round {round}: early divergence at tick {t}"
                    );
                    assert_eq!(a.world.inject_fold, 0);
                } else {
                    assert_ne!(a.state_hash(), b.state_hash(), "round {round}: instances agree at tick {t}; the fixture did not fire (widen INJECT_ENTRIES and record why)");
                    assert_ne!(a.world.inject_fold, 0);
                    assert_ne!(a.world.inject_fold, b.world.inject_fold);
                }
            }
            // And an unarmed pair stays clean, feature or no feature.
            let mut c = sim(5);
            let mut d = sim(5);
            c.set_inject_tick(None).unwrap();
            for _ in 0..inject_at + 5 {
                c.step();
                d.step();
            }
            assert_eq!(c.state_hash(), d.state_hash());
        }
    }
}
