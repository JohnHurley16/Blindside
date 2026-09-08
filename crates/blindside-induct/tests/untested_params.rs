//! A tree carries values only for the predicates it tests. Every parametric predicate with
//! readings is fitted during the search, since the search has to know what tree each
//! threshold admits; but a value for a predicate the chosen tree never asks about was not
//! fitted to anything, and does not reach the file. The tree that comes back must still
//! render, decide and round-trip without it.

mod common;

use std::collections::BTreeMap;

use blindside_induct::blocks::BlockSet;
use blindside_induct::induce::induce;
use blindside_induct::named_trace::NamedTrace;
use blindside_induct::params::Params;
use blindside_induct::render::to_lines;
use blindside_induct::step_input::StepInput;
use blindside_induct::trace::{Step, Trace};
use blindside_induct::tree::DecisionTree;

/// Two parametric predicates, so that one can be tested while the other is only read.
const BLOCKS: &str = r#"{ "predicates": [ {"id": "carrying_cargo", "label": "carrying"},
                  {"id": "uncertainty_exceeds",  "label": "lost", "param": "theta", "provisional": 3.0},
                  {"id": "time_elapsed_exceeds", "label": "late", "param": "seconds", "provisional": 100.0} ],
  "actions":    [ {"id": "take_branch",      "label": "take a branch"},
                  {"id": "return_to_beacon", "label": "go back"} ] }"#;

const THETA: f64 = 3.0;
const SECONDS: f64 = 100.0;

fn blocks() -> BlockSet {
    BlockSet::from_json(BLOCKS).expect("the block list parses")
}

/// One stop, its booleans read at the provisional values and both raw readings recorded.
fn stop(carrying: bool, sigma: f64, seconds: f64) -> StepInput {
    let mut predicates = BTreeMap::new();
    predicates.insert("carrying_cargo".to_string(), carrying);
    predicates.insert("uncertainty_exceeds".to_string(), sigma > THETA);
    predicates.insert("time_elapsed_exceeds".to_string(), seconds > SECONDS);
    let mut raw = BTreeMap::new();
    raw.insert("uncertainty_exceeds".to_string(), sigma);
    raw.insert("time_elapsed_exceeds".to_string(), seconds);
    StepInput { predicates, raw }
}

fn demonstration(stops: &[(StepInput, &str)]) -> NamedTrace {
    let mut params = Params::new();
    params.set("uncertainty_exceeds", "theta", THETA);
    params.set("time_elapsed_exceeds", "seconds", SECONDS);
    let steps = stops
        .iter()
        .enumerate()
        .map(|(i, (input, action))| Step {
            tick: 10 * (i as u64 + 1),
            junction: i as u64,
            predicates: input.predicates.clone(),
            raw: input.raw.clone(),
            action: action.to_string(),
        })
        .collect();
    NamedTrace {
        name: "demo.json".to_string(),
        trace: Trace {
            seed: 1,
            enabled_predicates: blocks().predicates.iter().map(|p| p.id.clone()).collect(),
            enabled_actions: blocks().actions.iter().map(|a| a.id.clone()).collect(),
            params,
            steps,
            outcome: None,
        },
    }
}

/// Every predicate the params name is one the tree tests.
fn params_are_a_subset_of_the_tests(tree: &DecisionTree) {
    let used = tree.predicates_used();
    for id in tree.params.0.keys() {
        assert!(
            used.contains(id),
            "params carry {id:?}, which the tree never tests"
        );
    }
}

#[test]
fn a_fitted_value_is_written_only_for_a_predicate_the_tree_tests() {
    let blocks = blocks();
    // Go back when carrying or when lost; the clock readings vary and decide nothing.
    let stops = [
        (stop(false, 1.0, 50.0), "take_branch"),
        (stop(false, 2.0, 150.0), "take_branch"),
        (stop(false, 4.0, 60.0), "return_to_beacon"),
        (stop(false, 5.0, 200.0), "return_to_beacon"),
        (stop(true, 1.5, 120.0), "return_to_beacon"),
        (stop(true, 4.5, 30.0), "return_to_beacon"),
    ];
    let traces = vec![demonstration(&stops)];
    let induction = induce(&blocks, &traces).expect("a well-formed trace");
    let tree = induction.tree.expect("the stops are consistent");

    let used = tree.predicates_used();
    assert!(used.contains("uncertainty_exceeds"), "{used:?}");
    assert!(!used.contains("time_elapsed_exceeds"), "{used:?}");
    assert!(
        tree.params.get("uncertainty_exceeds", "theta").is_some(),
        "the threshold the tree tests is fitted and written"
    );
    assert!(
        !tree.params.0.contains_key("time_elapsed_exceeds"),
        "a value nobody fitted is not a fit: {:?}",
        tree.params
    );
    params_are_a_subset_of_the_tests(&tree);

    // The tree it wrote still renders, decides, and reads back, without that entry.
    let lines = to_lines(&tree, &blocks);
    assert!(lines.iter().any(|l| l.contains("theta = ")), "{lines:?}");
    assert!(!lines.iter().any(|l| l.contains("seconds")), "{lines:?}");
    for (input, action) in &stops {
        assert_eq!(tree.decide(input, &blocks), *action);
    }
    let late = stop(false, 1.0, 999.0);
    assert_eq!(tree.decide(&late, &blocks), "take_branch");

    let text = serde_json::to_string(&tree).unwrap();
    assert!(!text.contains("time_elapsed_exceeds"), "{text}");
    let again = DecisionTree::from_json(&text).unwrap();
    again.validate(&blocks).unwrap();
    assert_eq!(again, tree);
    assert_eq!(again.decide(&late, &blocks), "take_branch");
}

#[test]
fn a_tree_that_tests_nothing_parametric_writes_no_params_at_all() {
    let blocks = blocks();
    // Every stop goes back, whatever was read: one leaf, and readings for both predicates.
    let stops = [
        (stop(false, 1.0, 50.0), "return_to_beacon"),
        (stop(true, 4.0, 150.0), "return_to_beacon"),
        (stop(false, 6.0, 250.0), "return_to_beacon"),
    ];
    let traces = vec![demonstration(&stops)];
    let tree = induce(&blocks, &traces)
        .expect("a well-formed trace")
        .tree
        .expect("one action is consistent with itself");
    assert_eq!(tree.node_count(), 0);
    assert!(tree.params.is_empty(), "{:?}", tree.params);
    assert_eq!(
        serde_json::to_string(&tree).unwrap(),
        r#"{"params":{},"root":{"action":"return_to_beacon"}}"#
    );
    assert_eq!(to_lines(&tree, &blocks), vec!["go back"]);
    assert_eq!(
        tree.decide(&stop(false, 9.0, 9.0), &blocks),
        "return_to_beacon"
    );
}

#[test]
fn the_contracts_example_still_carries_the_value_it_tests() {
    // The positive control: synthetic demonstrations of the contract's tree, which does
    // test its one parametric predicate, come back with a value for it.
    let blocks = common::blocks();
    let reference = common::example_tree();
    let traces = common::synthetic_traces(&blocks, &reference, 3, 40, 11, 1.0);
    let tree = induce(&blocks, &traces)
        .expect("synthetic traces are well formed")
        .tree
        .expect("demonstrations of one tree are consistent");
    params_are_a_subset_of_the_tests(&tree);
    if tree.predicates_used().contains("uncertainty_exceeds") {
        assert!(tree.params.get("uncertainty_exceeds", "theta").is_some());
    }
}
