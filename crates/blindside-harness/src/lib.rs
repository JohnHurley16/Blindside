//! blindside-harness — headless runner, desync canary, replay record/verify, batch
//! executor, bisect, dump diffing, and the golden-table generator. The `harness` binary
//! is a thin CLI over this crate.
//!
//! This crate is tooling and is NOT subject to the DETERMINISM.md hard rules, but it
//! sees a `Sim` only through `Sim::new(&MatchRecord)`, `step()`, `tick()`,
//! `state_hash()`, the feature-gated, string-only `blindside_sim::diagnostics` module,
//! and `set_inject_tick`. It never reaches into `World`; `tests/world_unreachable.rs`
//! proves it cannot.

pub mod bisect;
pub mod canary;
pub mod dump;
pub mod golden;
pub mod record;
pub mod runner;

/// The cross-platform anchor: the empty sim on seed `0xDEAD_BEEF` after 1000 ticks. The
/// same value is pinned in blindside-sim (`GOLDEN_SEED_DEADBEEF_TICK_1000`) and is what
/// CI's `cross-platform` job checks from the other direction.
pub const PIN_SEED_DEADBEEF_TICK_1000: &str =
    "f1f69639853665744a704bae5e7d5e1a15986d4748e95d1870ccab665c7dbb9f";
