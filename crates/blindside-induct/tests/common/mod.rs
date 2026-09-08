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

/// A copy of `tree` whose one parametric predicate is set to `theta`.
pub fn tree_with_theta(blocks: &BlockSet, tree: &DecisionTree, theta: f64) -> DecisionTree {
    let mut out = tree.clone();
    for predicate in blocks.predicates.iter().filter(|p| p.param.is_some()) {
        let name = predicate.param.as_deref().expect("filtered on param");
        out.params.set(&predicate.id, name, theta);
    }
    out
}

/// Stops the way the Phase 2 corridor produces them, so a fitted threshold is measured
/// against the raw readings the sim actually records rather than a uniform cloud.
///
/// `phase2/tuning.py` gives position sigma against distance walked since the last shaft fix
/// (9 cells at 100, 18 at 150, 30 at 200, 45 at 250, 63 at 300, 99 at 380); `0.03 d +
/// 0.0006 d^2` reproduces that table exactly. Passages are 14 to 36 cells and the corridor is
/// eight junctions deep.
///
/// The agent stops at every junction it reaches, on the way out and on the way home alike --
/// `examples/demo-2.json` is the shape: sigma keeps climbing all the way home and only
/// collapses when the shaft is reached. That matters here because the stops made on the way
/// home are mostly decided by the other blocks, so they say nothing about the threshold while
/// still sitting either side of it. Choices come from `tree`, so a trace is a perfect
/// demonstration of it.
///
/// Two things it assumes about the block list, since a generator has to mean something by a
/// column: the first action is the one that goes further in, and of the non-parametric
/// predicates the first is "somewhere new to go from here" and the second is sticky until the
/// agent gets home. Nothing is named.
pub struct Corridor<'a> {
    blocks: &'a BlockSet,
    tree: &'a DecisionTree,
    rng: Lcg,
    /// Cells walked since the last shaft fix.
    distance: f64,
    /// Junctions between the agent and the shaft.
    depth: u64,
    sticky: bool,
    index: u64,
}

/// Distance since a fix, in cells, to the position sigma the estimator reports.
fn sigma_of(distance: f64) -> f64 {
    (0.03 * distance + 0.0006 * distance * distance).max(0.5)
}

/// Junctions in the corridor: `phase2/tuning.py`'s JUNCTIONS. At the deepest one there is
/// nowhere new to go.
const DEPTH: u64 = 8;
/// How often the first non-parametric block holds at a junction that is not the deepest. A
/// frontier junction with two or three passages almost always has somewhere new to go, and
/// `phase2/tuning.py` needs that: the reference tree's excursions are ended by the threshold,
/// not by running out of corridor.
const FIRST_PLAIN_CHANCE: f64 = 0.9;
/// How often the second non-parametric block turns on at a stop below half depth, after which
/// it stays on until the agent gets home. One deposit per corridor, and it is deep.
const SECOND_PLAIN_CHANCE: f64 = 0.08;

impl<'a> Corridor<'a> {
    pub fn new(blocks: &'a BlockSet, tree: &'a DecisionTree, seed: u64) -> Self {
        Corridor {
            blocks,
            tree,
            rng: Lcg(seed),
            distance: 0.0,
            depth: 0,
            sticky: false,
            index: 0,
        }
    }

    /// One stop: walk a passage, read the blocks, take the tree's choice, and move the way it
    /// chose -- deeper, or one junction nearer the shaft, where a fix collapses sigma.
    pub fn stop(&mut self) -> Step {
        self.distance += 14.0 + 22.0 * self.rng.unit();
        let mut predicates = BTreeMap::new();
        let mut raw = BTreeMap::new();
        let mut plain = 0;
        for p in &self.blocks.predicates {
            match &p.param {
                Some(name) => {
                    let reading = sigma_of(self.distance);
                    let theta = self
                        .tree
                        .params
                        .get(&p.id, name)
                        .expect("the reference tree carries every parameter");
                    raw.insert(p.id.clone(), reading);
                    predicates.insert(p.id.clone(), reading > theta);
                }
                None => {
                    let value = if plain == 0 {
                        self.depth < DEPTH && self.rng.chance(FIRST_PLAIN_CHANCE)
                    } else {
                        let deep = self.depth * 2 >= DEPTH;
                        self.sticky = self.sticky || (deep && self.rng.chance(SECOND_PLAIN_CHANCE));
                        self.sticky
                    };
                    predicates.insert(p.id.clone(), value);
                    plain += 1;
                }
            }
        }
        let input = StepInput {
            predicates: predicates.clone(),
            raw: raw.clone(),
        };
        let action = self.tree.decide(&input, self.blocks).to_string();
        let step = Step {
            tick: 10 * (self.index + 1),
            junction: self.depth,
            predicates,
            raw,
            action,
        };
        self.index += 1;
        if step.action == self.blocks.actions[0].id {
            self.depth += 1;
        } else {
            self.depth = self.depth.saturating_sub(1);
            if self.depth == 0 {
                // Home: the shaft fixes the pose and the cargo is delivered.
                self.distance = 0.0;
                self.sticky = false;
            }
        }
        step
    }
}

/// `count` demonstrations of `stops` stops each, walked by `tree`.
pub fn corridor_traces(
    blocks: &BlockSet,
    tree: &DecisionTree,
    count: usize,
    stops: usize,
    seed: u64,
) -> Vec<NamedTrace> {
    (0..count)
        .map(|k| {
            let mut corridor = Corridor::new(blocks, tree, seed.wrapping_add(k as u64 * 7919));
            let steps: Vec<Step> = (0..stops).map(|_| corridor.stop()).collect();
            NamedTrace {
                name: format!("corridor-{k}.json"),
                trace: Trace {
                    seed: k as u64,
                    enabled_predicates: blocks.predicates.iter().map(|p| p.id.clone()).collect(),
                    enabled_actions: blocks.actions.iter().map(|a| a.id.clone()).collect(),
                    params: tree.params.clone(),
                    steps,
                    outcome: None,
                },
            }
        })
        .collect()
}

/// `count` stops from the same corridor, as (what a policy reads, what `tree` would do).
pub fn corridor_stops(
    blocks: &BlockSet,
    tree: &DecisionTree,
    count: usize,
    seed: u64,
) -> Vec<(StepInput, String)> {
    let mut corridor = Corridor::new(blocks, tree, seed);
    (0..count)
        .map(|_| {
            let step = corridor.stop();
            (StepInput::from(&step), step.action.clone())
        })
        .collect()
}

/// The open interval the recorded stops leave for one parametric predicate's threshold.
///
/// A stop only says something about the threshold when the other predicates do not already
/// decide it: that is exactly a stop whose action changes when the reading is forced below
/// every threshold and then above every one. Such a stop whose recorded action is the
/// forced-low one requires the threshold above its reading; the forced-high one requires it
/// below. Everything else carries no information about the threshold at all.
///
/// Returns `(lo, hi)`, infinite on a side nothing constrains.
pub fn constraining_bracket(
    blocks: &BlockSet,
    tree: &DecisionTree,
    traces: &[NamedTrace],
    predicate: &str,
) -> (f64, f64) {
    let (mut lo, mut hi) = (f64::NEG_INFINITY, f64::INFINITY);
    for step in traces.iter().flat_map(|t| &t.trace.steps) {
        let Some(&reading) = step.raw.get(predicate) else {
            continue;
        };
        let forced = |value: f64| {
            let mut input = StepInput::from(step);
            input.raw.insert(predicate.to_string(), value);
            tree.decide(&input, blocks).to_string()
        };
        let (low, high) = (forced(f64::NEG_INFINITY), forced(f64::INFINITY));
        if low == high {
            continue;
        }
        if step.action == low {
            lo = lo.max(reading);
        } else if step.action == high {
            hi = hi.min(reading);
        }
    }
    (lo, hi)
}

/// Does one predicate decide this stop, or do the others settle it without asking? True when
/// forcing the reading below every threshold and then above every one changes what `tree`
/// does.
pub fn decides(blocks: &BlockSet, tree: &DecisionTree, input: &StepInput, predicate: &str) -> bool {
    if !input.raw.contains_key(predicate) {
        return false;
    }
    let forced = |value: f64| {
        let mut forced = input.clone();
        forced.raw.insert(predicate.to_string(), value);
        tree.decide(&forced, blocks).to_string()
    };
    forced(f64::NEG_INFINITY) != forced(f64::INFINITY)
}
