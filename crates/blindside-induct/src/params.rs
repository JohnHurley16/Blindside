//! Parameter values for parametric predicates: predicate id -> parameter name -> value.
//! A `BTreeMap` at both levels so the JSON is always written in one order.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(transparent)]
pub struct Params(pub BTreeMap<String, BTreeMap<String, f64>>);

impl Params {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn get(&self, predicate: &str, param: &str) -> Option<f64> {
        self.0.get(predicate).and_then(|m| m.get(param)).copied()
    }

    pub fn set(&mut self, predicate: &str, param: &str, value: f64) {
        self.0
            .entry(predicate.to_string())
            .or_default()
            .insert(param.to_string(), value);
    }

    pub fn is_empty(&self) -> bool {
        self.0.is_empty()
    }
}
