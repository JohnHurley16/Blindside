//! The induced tree is the smallest consistent one, checked by brute force over every
//! tree up to its size and every candidate threshold.

mod common;

use blindside_induct::blocks::BlockSet;
use blindside_induct::induce::induce;
use blindside_induct::named_trace::NamedTrace;
use blindside_induct::params::Params;
use blindside_induct::step_input::StepInput;
use blindside_induct::thresholds::candidates;
use blindside_induct::tree::{DecisionTree, Node};

/// Every tree with exactly `size` internal nodes over the given predicates and actions.
fn all_trees(predicates: &[String], actions: &[String], size: usize) -> Vec<Node> {
    if size == 0 {
        return actions.iter().map(|a| Node::action(a)).collect();
    }
    let mut out = Vec::new();
    for predicate in predicates {
        for yes_size in 0..size {
            let no_size = size - 1 - yes_size;
            for yes in all_trees(predicates, actions, yes_size) {
                for no in all_trees(predicates, actions, no_size) {
                    out.push(Node::branch(predicate, yes.clone(), no));
                }
            }
        }
    }
    out
}

/// Every parameter assignment the induction could have chosen: the cartesian product of
/// each parametric predicate's candidate thresholds over the recorded raws.
fn param_grid(blocks: &BlockSet, traces: &[NamedTrace]) -> Vec<Params> {
    let mut grid = vec![Params::new()];
    for predicate in &blocks.predicates {
        let Some(name) = predicate.param.as_deref() else {
            continue;
        };
        let raws = common::raws_for(traces, &predicate.id);
        let values: Vec<f64> = candidates(&raws).iter().map(|c| c.value).collect();
        if values.is_empty() {
            continue;
        }
        grid = grid
            .iter()
            .flat_map(|base| {
                values.iter().map(move |&value| {
                    let mut params = base.clone();
                    params.set(&predicate.id, name, value);
                    params
                })
            })
            .collect();
    }
    grid
}

fn consistent(
    root: &Node,
    params: &Params,
    blocks: &BlockSet,
    stops: &[(StepInput, String)],
) -> bool {
    let tree = DecisionTree {
        params: params.clone(),
        root: root.clone(),
    };
    stops
        .iter()
        .all(|(input, action)| tree.decide(input, blocks) == action)
}

#[test]
fn the_induced_tree_is_the_smallest_consistent_one_by_brute_force() {
    let blocks = common::blocks();
    let reference = common::example_tree();
    let traces = common::synthetic_traces(&blocks, &reference, 3, 20, 7, 1.5);
    let induced = induce(&blocks, &traces)
        .expect("valid input")
        .tree
        .expect("consistent");
    // The generating rule needs every block predicate, so the data exercises all of them.
    assert_eq!(induced.predicates_used().len(), blocks.predicates.len());

    let stops: Vec<(StepInput, String)> = traces
        .iter()
        .flat_map(|t| &t.trace.steps)
        .map(|s| (StepInput::from(s), s.action.clone()))
        .collect();
    let predicates: Vec<String> = blocks.predicates.iter().map(|p| p.id.clone()).collect();
    let actions: Vec<String> = blocks.actions.iter().map(|a| a.id.clone()).collect();
    let grid = param_grid(&blocks, &traces);
    assert!(
        grid.len() > 1,
        "the parametric predicate must have candidates"
    );

    // No tree with fewer nodes is consistent under any candidate threshold.
    let smallest = (0..=induced.node_count()).find(|&size| {
        all_trees(&predicates, &actions, size).iter().any(|root| {
            grid.iter()
                .any(|params| consistent(root, params, &blocks, &stops))
        })
    });
    assert_eq!(smallest, Some(induced.node_count()));
    assert_eq!(induced.node_count(), 3);
}
