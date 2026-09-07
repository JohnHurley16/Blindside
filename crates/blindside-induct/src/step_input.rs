//! What `decide` reads: the predicate booleans and raw numbers of one stop. This is the
//! `"predicates"` + `"raw"` part of a trace step; anything else in the object is ignored.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::trace::Step;

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct StepInput {
    #[serde(default)]
    pub predicates: BTreeMap<String, bool>,
    #[serde(default)]
    pub raw: BTreeMap<String, f64>,
}

impl From<&Step> for StepInput {
    fn from(step: &Step) -> Self {
        StepInput {
            predicates: step.predicates.clone(),
            raw: step.raw.clone(),
        }
    }
}
