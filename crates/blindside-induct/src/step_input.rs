//! What `decide` reads: the predicate booleans and raw numbers of one stop. This is the
//! `"predicates"` + `"raw"` part of a trace step; anything else in the object is ignored.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::blocks::BlockSet;
use crate::error::{Error, Result};
use crate::trace::Step;

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StepInput {
    #[serde(default)]
    pub predicates: BTreeMap<String, bool>,
    #[serde(default)]
    pub raw: BTreeMap<String, f64>,
}

impl StepInput {
    /// Every predicate the stop reads must be one the block list has, exactly as a trace's
    /// stops are checked before an induction. `name` is for the message only.
    pub fn validate(&self, blocks: &BlockSet, name: &str) -> Result<()> {
        for id in self.predicates.keys().chain(self.raw.keys()) {
            if blocks.predicate(id).is_none() {
                return Err(Error::input(format!(
                    "{name}: reads predicate {id:?}, which is not in the block list"
                )));
            }
        }
        Ok(())
    }
}

impl From<&Step> for StepInput {
    fn from(step: &Step) -> Self {
        StepInput {
            predicates: step.predicates.clone(),
            raw: step.raw.clone(),
        }
    }
}
