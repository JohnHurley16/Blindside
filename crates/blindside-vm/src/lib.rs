//! blindside-vm — bytecode interpreter with an instruction budget.
//!
//! Phase 0 stub. This crate is subject to the docs/DETERMINISM.md hard rules 1-8
//! (fixed-point only, ordered maps only, no wall clock, stateless RNG).

/// Per-tick instruction budget for a policy. Also a balance lever (see ARCHITECTURE.md).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct VmBudget {
    pub ops_per_tick: u32,
}
