//! The block list: the predicates and actions a tree may be built from.
//!
//! `blocks.json` is the only place the day-one items are enumerated. Nothing in this crate
//! names a block by id or label; everything reads this list.

use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::error::{Error, Result};

/// A boolean test over belief. Parametric when `param` is set: its boolean is then a
/// function of a raw number and that one parameter (`raw > value`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Predicate {
    pub id: String,
    pub label: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub param: Option<String>,
}

/// Something an agent can be told to do at a stop.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Action {
    pub id: String,
    pub label: String,
}

/// The whole list, in file order. A predicate's position in `predicates` is the column it
/// occupies in every predicate vector.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BlockSet {
    pub predicates: Vec<Predicate>,
    pub actions: Vec<Action>,
}

impl BlockSet {
    pub fn load(path: &Path) -> Result<Self> {
        let text = fs::read_to_string(path).map_err(|e| Error::io(path, e))?;
        let blocks: BlockSet =
            serde_json::from_str(&text).map_err(|e| Error::json(&path.display().to_string(), e))?;
        blocks.validate()?;
        Ok(blocks)
    }

    pub fn from_json(text: &str) -> Result<Self> {
        let blocks: BlockSet = serde_json::from_str(text).map_err(|e| Error::json("blocks", e))?;
        blocks.validate()?;
        Ok(blocks)
    }

    /// Ids must be unique among predicates and among actions.
    pub fn validate(&self) -> Result<()> {
        let mut seen = BTreeSet::new();
        for predicate in &self.predicates {
            if !seen.insert(predicate.id.as_str()) {
                return Err(Error::input(format!(
                    "blocks: predicate id {:?} appears twice",
                    predicate.id
                )));
            }
        }
        let mut seen = BTreeSet::new();
        for action in &self.actions {
            if !seen.insert(action.id.as_str()) {
                return Err(Error::input(format!(
                    "blocks: action id {:?} appears twice",
                    action.id
                )));
            }
        }
        Ok(())
    }

    pub fn predicate(&self, id: &str) -> Option<&Predicate> {
        self.predicates.iter().find(|p| p.id == id)
    }

    pub fn action(&self, id: &str) -> Option<&Action> {
        self.actions.iter().find(|a| a.id == id)
    }

    /// The column a predicate occupies in a vector.
    pub fn predicate_index(&self, id: &str) -> Option<usize> {
        self.predicates.iter().position(|p| p.id == id)
    }

    pub fn action_index(&self, id: &str) -> Option<usize> {
        self.actions.iter().position(|a| a.id == id)
    }

    /// A predicate's label, or the id itself when it is not in the list. Callers validate
    /// first; the fallback only keeps rendering total.
    pub fn predicate_label<'a>(&'a self, id: &'a str) -> &'a str {
        self.predicate(id).map_or(id, |p| p.label.as_str())
    }

    pub fn action_label<'a>(&'a self, id: &'a str) -> &'a str {
        self.action(id).map_or(id, |a| a.label.as_str())
    }

    /// Every predicate column, ordered by id. This is the lexical order the induction
    /// breaks its last tie in.
    pub fn predicate_columns_by_id(&self) -> Vec<usize> {
        let mut columns: Vec<usize> = (0..self.predicates.len()).collect();
        columns.sort_by(|&a, &b| self.predicates[a].id.cmp(&self.predicates[b].id));
        columns
    }
}
