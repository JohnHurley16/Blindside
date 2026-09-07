//! One demonstration, as the Python side records it. Field names are the contract's.

use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::blocks::BlockSet;
use crate::error::{Error, Result};
use crate::params::Params;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Trace {
    pub seed: u64,
    /// Which blocks existed in this run. Informational here: the induction reads what each
    /// stop actually recorded, since disabled predicates are absent from both of its maps.
    #[serde(default)]
    pub enabled_predicates: Vec<String>,
    #[serde(default)]
    pub enabled_actions: Vec<String>,
    /// The parameters the demonstration evaluated its booleans with.
    #[serde(default)]
    pub params: Params,
    pub steps: Vec<Step>,
    #[serde(default)]
    pub outcome: Option<Outcome>,
}

/// One stop: the booleans as the demonstration evaluated them, the raw number behind every
/// parametric predicate, and the choice made. Disabled predicates are absent from both maps.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Step {
    pub tick: u64,
    pub junction: u64,
    #[serde(default)]
    pub predicates: BTreeMap<String, bool>,
    #[serde(default)]
    pub raw: BTreeMap<String, f64>,
    pub action: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Outcome {
    pub success: bool,
    pub ticks: u64,
    pub lost: bool,
}

impl Trace {
    pub fn load(path: &Path) -> Result<Self> {
        let text = fs::read_to_string(path).map_err(|e| Error::io(path, e))?;
        serde_json::from_str(&text).map_err(|e| Error::json(&path.display().to_string(), e))
    }

    pub fn from_json(text: &str, name: &str) -> Result<Self> {
        serde_json::from_str(text).map_err(|e| Error::json(name, e))
    }

    /// Every predicate and action id in the trace must be in the block list. `name` is for
    /// the message only.
    pub fn validate(&self, blocks: &BlockSet, name: &str) -> Result<()> {
        for id in &self.enabled_predicates {
            if blocks.predicate(id).is_none() {
                return Err(Error::input(format!(
                    "{name}: enabled predicate {id:?} is not in the block list"
                )));
            }
        }
        for id in &self.enabled_actions {
            if blocks.action(id).is_none() {
                return Err(Error::input(format!(
                    "{name}: enabled action {id:?} is not in the block list"
                )));
            }
        }
        for (index, step) in self.steps.iter().enumerate() {
            for id in step.predicates.keys().chain(step.raw.keys()) {
                if blocks.predicate(id).is_none() {
                    return Err(Error::input(format!(
                        "{name}: stop {index} records predicate {id:?}, which is not in the block list"
                    )));
                }
            }
            if blocks.action(&step.action).is_none() {
                return Err(Error::input(format!(
                    "{name}: stop {index} chose {:?}, which is not in the block list",
                    step.action
                )));
            }
        }
        Ok(())
    }
}
