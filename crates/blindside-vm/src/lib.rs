//! blindside-vm — bytecode interpreter with an instruction budget.
//!
//! Phase 0 stub. This crate is subject to the docs/DETERMINISM.md hard rules 1-8
//! (fixed-point only, ordered maps only, no wall clock, stateless RNG). Any `unsafe` is
//! an explicit, `// SAFETY:`-justified exception to the deny below (rule 8, BLD-34).

#![deny(unsafe_code)]

/// Per-tick instruction budget for a policy. Also a balance lever (see ARCHITECTURE.md).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct VmBudget {
    pub ops_per_tick: u32,
}
