//! The block list: the predicates and actions a tree may be built from.
//!
//! `blocks.json` is the only place the day-one items are enumerated. Nothing in this crate
//! names a block by id or label; everything reads this list.

use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::error::{Error, Result};
use crate::strict;

/// A boolean test over belief. Parametric when `param` is set: its boolean is then a
/// function of a raw number and that one parameter (`raw > value`).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Predicate {
    pub id: String,
    pub label: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub param: Option<String>,
    /// Which tutorial run this block appears in. One of the contract's two Python-side
    /// fields: the induction never reads it, and carries it only so that a block list
    /// holding it is not rejected as malformed.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub stage: Option<i64>,
    /// The value of `param` a demonstration reads this predicate's boolean with before the
    /// induction has fitted the real one. The other Python-side field: a fitted threshold
    /// comes from the raw readings and never from here, so the induction ignores it. Only a
    /// parametric predicate may carry one (`validate`); on any other it is a mistake, and
    /// is refused rather than ignored.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub provisional: Option<f64>,
}

/// Something an agent can be told to do at a stop.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Action {
    pub id: String,
    pub label: String,
    /// As `Predicate::stage`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub stage: Option<i64>,
}

/// The whole list, in file order. A predicate's position in `predicates` is the column it
/// occupies in every predicate vector.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BlockSet {
    #[serde(deserialize_with = "strict::objects")]
    pub predicates: Vec<Predicate>,
    #[serde(deserialize_with = "strict::objects")]
    pub actions: Vec<Action>,
}

impl BlockSet {
    pub fn load(path: &Path) -> Result<Self> {
        let text = fs::read_to_string(path).map_err(|e| Error::io(path, e))?;
        let blocks: BlockSet = strict::from_str(&text, &path.display().to_string())?;
        blocks.validate()?;
        Ok(blocks)
    }

    pub fn from_json(text: &str) -> Result<Self> {
        let blocks: BlockSet = strict::from_str(text, "blocks")?;
        blocks.validate()?;
        Ok(blocks)
    }

    /// Ids must be unique among predicates and among actions, and only a parametric
    /// predicate may carry a provisional value.
    pub fn validate(&self) -> Result<()> {
        let mut seen = BTreeSet::new();
        for predicate in &self.predicates {
            if !seen.insert(predicate.id.as_str()) {
                return Err(Error::input(format!(
                    "blocks: predicate id {:?} appears twice",
                    predicate.id
                )));
            }
            if predicate.provisional.is_some() && predicate.param.is_none() {
                return Err(Error::input(format!(
                    "blocks: predicate {:?} has a provisional value but no param for it to be a value of",
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_provisional_value_on_a_parametric_predicate_parses_and_is_carried() {
        let blocks = BlockSet::from_json(
            r#"{"predicates": [{"id": "p", "label": "p", "param": "k", "provisional": 2.5}],
                "actions": [{"id": "a", "label": "a"}]}"#,
        )
        .expect("a provisional value on a parametric predicate is in the contract");
        assert_eq!(blocks.predicates[0].provisional, Some(2.5));
        let again = serde_json::to_string(&blocks).unwrap();
        assert_eq!(BlockSet::from_json(&again).unwrap(), blocks);
    }

    #[test]
    fn a_provisional_value_without_a_param_is_refused() {
        let err = BlockSet::from_json(
            r#"{"predicates": [{"id": "p", "label": "p", "provisional": 2.5}],
                "actions": [{"id": "a", "label": "a"}]}"#,
        )
        .expect_err("a value with nothing to be a value of");
        assert!(err.to_string().contains("provisional"), "{err}");
    }

    #[test]
    fn a_predicate_without_a_provisional_value_writes_none() {
        let blocks = BlockSet::from_json(
            r#"{"predicates": [{"id": "p", "label": "p", "param": "k"}],
                "actions": [{"id": "a", "label": "a"}]}"#,
        )
        .unwrap();
        assert_eq!(blocks.predicates[0].provisional, None);
        assert!(!serde_json::to_string(&blocks)
            .unwrap()
            .contains("provisional"));
    }
}
