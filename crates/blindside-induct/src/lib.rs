//! Demonstration traces -> decision trees.
//!
//! `FORMAT.md` in the crate root is the contract with the Python side and states the
//! guarantees the induction makes. Everything here is a pure function of its input: no
//! clock, no randomness, and every map whose order reaches the output is a `BTreeMap`.

pub mod blocks;
pub mod choices;
pub mod cli;
pub mod conflicts;
pub mod dataset;
pub mod decision;
pub mod diff;
pub mod error;
pub mod evaluate;
pub mod induce;
pub mod leaf_path;
pub mod named_trace;
pub mod params;
pub mod query;
pub mod render;
pub mod search;
pub mod step_input;
pub mod step_ref;
pub mod thresholds;
pub mod trace;
pub mod tree;
pub mod tuning;
