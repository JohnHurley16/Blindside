//! blindside-harness — headless runner, desync canary, replay record/verify, batch
//! throughput, and bisect. The `harness` binary is a thin CLI over this crate.
//!
//! This crate is tooling and is NOT subject to the DETERMINISM.md hard rules, but it
//! sees a `Sim` only through `tick()`, `state_hash()`, `state_debug()` and the documented
//! test hook. It never reaches into `World`.

pub mod bisect;
pub mod canary;
pub mod record;
pub mod runner;
