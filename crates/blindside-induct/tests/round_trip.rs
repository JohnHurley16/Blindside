//! Synthetic round trip: traces played from the theta-aware tree induce it back.

mod common;

use std::collections::BTreeMap;

use blindside_induct::induce::induce;
use blindside_induct::named_trace::NamedTrace;
use blindside_induct::params::Params;
use blindside_induct::step_input::StepInput;
use blindside_induct::trace::{Step, Trace};

#[test]
fn three_synthetic_demonstrations_induce_the_generating_tree_back() {
    let blocks = common::blocks();
    let reference = common::example_tree();
    let traces = common::synthetic_traces(&blocks, &reference, 3, 20, 7, 1.5);

    let result = induce(&blocks, &traces).expect("valid input");
    assert!(result.consistent, "conflicts: {:?}", result.conflicts);
    let tree = result.tree.expect("a consistent set has a tree");

    for named in &traces {
        for step in &named.trace.steps {
            assert_eq!(
                tree.decide(&StepInput::from(step), &blocks),
                step.action,
                "{} tick {}",
                named.name,
                step.tick
            );
        }
    }
    assert_eq!(tree.node_count(), reference.node_count());

    for predicate in blocks.predicates.iter().filter(|p| p.param.is_some()) {
        let name = predicate.param.as_deref().unwrap();
        let theta_star = reference.params.get(&predicate.id, name).unwrap();
        let raws = common::raws_for(&traces, &predicate.id);
        let below = raws
            .iter()
            .copied()
            .filter(|r| *r < theta_star)
            .fold(f64::NEG_INFINITY, f64::max);
        let above = raws
            .iter()
            .copied()
            .filter(|r| *r > theta_star)
            .fold(f64::INFINITY, f64::min);
        assert!(
            below.is_finite() && above.is_finite(),
            "the synthetic data must straddle theta"
        );
        let fitted = tree
            .params
            .get(&predicate.id, name)
            .expect("theta is fitted");
        assert!(
            below < fitted && fitted < above,
            "theta {fitted} must lie strictly inside ({below}, {above})"
        );
    }
}

#[test]
fn a_tutorial_run_with_fewer_blocks_is_evidence_not_a_contradiction() {
    let blocks = common::blocks();
    let reference = common::example_tree();
    let mut traces = common::synthetic_traces(&blocks, &reference, 2, 20, 11, 1.5);

    // Run one of the tutorial: no drift, and only "an unexplored branch here" and "take a
    // branch" exist. The player takes a branch at every stop.
    let steps = (0..4u64)
        .map(|i| Step {
            tick: 10 * (i + 1),
            junction: i,
            predicates: BTreeMap::from([("unexplored_branch_exists".to_string(), true)]),
            raw: BTreeMap::new(),
            action: "take_branch".to_string(),
        })
        .collect();
    traces.insert(
        0,
        NamedTrace {
            name: "tutorial-1.json".to_string(),
            trace: Trace {
                seed: 1,
                enabled_predicates: vec!["unexplored_branch_exists".to_string()],
                enabled_actions: vec!["take_branch".to_string()],
                params: Params::new(),
                steps,
                outcome: None,
            },
        },
    );

    let result = induce(&blocks, &traces).expect("valid input");
    assert!(result.consistent, "conflicts: {:?}", result.conflicts);
    let tree = result.tree.expect("consistent");
    for named in &traces {
        for step in &named.trace.steps {
            assert_eq!(tree.decide(&StepInput::from(step), &blocks), step.action);
        }
    }
}
