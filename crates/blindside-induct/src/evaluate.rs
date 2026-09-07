//! The one rule for turning a stop's readings into a predicate's boolean.
//!
//! A parametric predicate with a raw value and a parameter is `raw > value`. Anything else
//! falls back to the recorded boolean. A predicate absent from both maps is `None` -- the
//! block did not exist at that stop -- and every caller treats `None` as false.

use crate::blocks::Predicate;
use crate::params::Params;
use crate::step_input::StepInput;

pub fn predicate_value(predicate: &Predicate, input: &StepInput, params: &Params) -> Option<bool> {
    if let Some(name) = &predicate.param {
        if let (Some(raw), Some(threshold)) = (
            input.raw.get(&predicate.id),
            params.get(&predicate.id, name),
        ) {
            return Some(*raw > threshold);
        }
    }
    input.predicates.get(&predicate.id).copied()
}
