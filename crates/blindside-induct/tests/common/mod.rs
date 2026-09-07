//! Shared test data. The block list and the theta-aware tree are the contract's examples,
//! hand-built; the synthetic traces are generated from that tree with a seeded LCG.

#![allow(dead_code)]

use std::collections::BTreeMap;

use blindside_induct::blocks::BlockSet;
use blindside_induct::named_trace::NamedTrace;
use blindside_induct::step_input::StepInput;
use blindside_induct::trace::{Outcome, Step, Trace};
use blindside_induct::tree::DecisionTree;

/// The contract's blocks.json, verbatim.
pub const BLOCKS_JSON: &str = r#"{ "predicates": [ {"id": "unexplored_branch_exists", "label": "an unexplored branch here"},
                  {"id": "uncertainty_exceeds",      "label": "lost", "param": "theta"},
                  {"id": "carrying_cargo",           "label": "carrying"} ],
  "actions":    [ {"id": "take_branch",       "label": "take a branch"},
                  {"id": "return_to_beacon",  "label": "go back"} ] }"#;

/// The contract's tree.json example, verbatim: the theta-aware tree.
pub const TREE_JSON: &str = r#"{ "params": {"uncertainty_exceeds": {"theta": 2.9}},
  "root": {"predicate": "carrying_cargo",
           "yes": {"action": "return_to_beacon"},
           "no":  {"predicate": "uncertainty_exceeds",
                   "yes": {"action": "return_to_beacon"},
                   "no":  {"predicate": "unexplored_branch_exists",
                           "yes": {"action": "take_branch"},
                           "no":  {"action": "return_to_beacon"}}}} }"#;

pub fn blocks() -> BlockSet {
    BlockSet::from_json(BLOCKS_JSON).expect("the contract's blocks parse")
}

pub fn example_tree() -> DecisionTree {
    DecisionTree::from_json(TREE_JSON).expect("the contract's tree parses")
}

/// A tiny linear congruential generator so synthetic traces are identical on every run
/// without a rand crate.
pub struct Lcg(pub u64);

impl Lcg {
    fn step(&mut self) {
        self.0 = self
            .0
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
    }

    /// Uniform on [0, 1) with 24 bits of resolution.
    pub fn unit(&mut self) -> f64 {
        self.step();
        (self.0 >> 40) as f64 / 16_777_216.0
    }

    pub fn chance(&mut self, p: f64) -> bool {
        self.unit() < p
    }
}

/// Traces made by playing `tree` (with its own params) at seeded random stops. Every block
/// is enabled. A parametric predicate's raw value is uniform on [theta - spread,
/// theta + spread] around its value in `tree`, and the recorded boolean is the one that
/// value gives. Non-parametric predicates are fair coins.
pub fn synthetic_traces(
    blocks: &BlockSet,
    tree: &DecisionTree,
    count: usize,
    stops: usize,
    seed: u64,
    spread: f64,
) -> Vec<NamedTrace> {
    let mut rng = Lcg(seed);
    let enabled_predicates: Vec<String> = blocks.predicates.iter().map(|p| p.id.clone()).collect();
    let enabled_actions: Vec<String> = blocks.actions.iter().map(|a| a.id.clone()).collect();
    (0..count)
        .map(|k| {
            let steps = (0..stops)
                .map(|i| {
                    let mut predicates = BTreeMap::new();
                    let mut raw = BTreeMap::new();
                    for p in &blocks.predicates {
                        match &p.param {
                            Some(name) => {
                                let theta = tree
                                    .params
                                    .get(&p.id, name)
                                    .expect("the reference tree carries every parameter");
                                let value = theta - spread + 2.0 * spread * rng.unit();
                                raw.insert(p.id.clone(), value);
                                predicates.insert(p.id.clone(), value > theta);
                            }
                            None => {
                                predicates.insert(p.id.clone(), rng.chance(0.5));
                            }
                        }
                    }
                    let input = StepInput {
                        predicates: predicates.clone(),
                        raw: raw.clone(),
                    };
                    let action = tree.decide(&input, blocks).to_string();
                    Step {
                        tick: 10 * (i as u64 + 1),
                        junction: i as u64,
                        predicates,
                        raw,
                        action,
                    }
                })
                .collect();
            NamedTrace {
                name: format!("synthetic-{k}.json"),
                trace: Trace {
                    seed: k as u64,
                    enabled_predicates: enabled_predicates.clone(),
                    enabled_actions: enabled_actions.clone(),
                    params: tree.params.clone(),
                    steps,
                    outcome: Some(Outcome {
                        success: true,
                        ticks: 10 * stops as u64,
                        lost: false,
                    }),
                },
            }
        })
        .collect()
}

/// Every raw value recorded for `predicate` across the traces.
pub fn raws_for(traces: &[NamedTrace], predicate: &str) -> Vec<f64> {
    traces
        .iter()
        .flat_map(|t| &t.trace.steps)
        .filter_map(|s| s.raw.get(predicate).copied())
        .collect()
}
