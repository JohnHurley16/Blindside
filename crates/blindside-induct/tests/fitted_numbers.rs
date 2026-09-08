//! The one number the induction invents has to survive being written down.
//!
//! A threshold taken as the midpoint of two readings carries the arithmetic's own noise --
//! `2.9285714285714284` -- and that noise is not free. It reaches the player through the
//! render, which shows three decimals, so the number on the panel is not the number in the
//! file and a stop between the two decides one way in the sim and the other in the tree. The
//! fix is to choose a round number at the moment of fitting rather than to round one at the
//! moment of printing, and these are the properties that says.

mod common;

use blindside_induct::blocks::BlockSet;
use blindside_induct::induce::induce;
use blindside_induct::named_trace::NamedTrace;
use blindside_induct::render::display_number;
use blindside_induct::step_input::StepInput;
use blindside_induct::tree::DecisionTree;

/// Every threshold a tree carries, with the predicate it belongs to.
fn thresholds(blocks: &BlockSet, tree: &DecisionTree) -> Vec<(String, f64)> {
    blocks
        .predicates
        .iter()
        .filter_map(|p| {
            let name = p.param.as_deref()?;
            Some((p.id.clone(), tree.params.get(&p.id, name)?))
        })
        .collect()
}

/// The next number above `value` a f64 can hold: the smallest reading that exceeds it.
fn just_above(value: f64) -> f64 {
    assert!(value.is_finite() && value > 0.0);
    f64::from_bits(value.to_bits() + 1)
}

fn check(blocks: &BlockSet, traces: &[NamedTrace], what: &str) {
    let tree = induce(blocks, traces)
        .expect("valid input")
        .tree
        .unwrap_or_else(|| panic!("{what}: a demonstration of one tree cannot contradict itself"));

    // What `--out` writes, read back: the file is the only thing the Python side ever sees.
    let written = serde_json::to_string(&tree).expect("a tree serialises");
    let reread = DecisionTree::from_json(&written).expect("and parses back");

    for (id, theta) in thresholds(blocks, &tree) {
        let shown = display_number(theta);
        assert_eq!(
            shown.parse::<f64>().expect("a number is shown"),
            theta,
            "{what}: the panel shows {shown} and the tree holds {theta:?}"
        );
        let (_, again) = thresholds(blocks, &reread)
            .into_iter()
            .find(|(other, _)| *other == id)
            .expect("the threshold survives the file");
        assert_eq!(
            again.to_bits(),
            theta.to_bits(),
            "{what}: {theta:?} came back from the file as {again:?}"
        );

        // A reading exactly on the boundary does not exceed it; the next one up does. Both
        // trees have to agree on that, or a stop the sim calls one thing the tree calls
        // another.
        for step in traces.iter().flat_map(|t| &t.trace.steps) {
            for reading in [theta, just_above(theta)] {
                let mut input = StepInput::from(step);
                input.raw.insert(id.clone(), reading);
                assert_eq!(
                    tree.decide(&input, blocks),
                    reread.decide(&input, blocks),
                    "{what}: the file disagrees at a reading of {reading:?}"
                );
            }
        }
    }
}

#[test]
fn a_fitted_threshold_is_a_round_number_and_survives_the_file_unchanged() {
    let blocks = common::blocks();
    let reference = common::example_tree();
    for seed in 1..=30u64 {
        let traces = common::synthetic_traces(&blocks, &reference, 3, 20, seed, 1.5);
        check(&blocks, &traces, &format!("seed {seed}"));
    }
}

/// The same over the corridor the Phase 2 sim produces, where the readings are sigmas rather
/// than a uniform cloud and the gaps between them are wide.
#[test]
fn the_same_holds_on_corridor_demonstrations() {
    let blocks = common::blocks();
    let base = common::example_tree();
    for theta in [16.0, 48.0, 64.0, 120.0] {
        let reference = common::tree_with_theta(&blocks, &base, theta);
        let traces = common::corridor_traces(&blocks, &reference, 3, 32, 4242);
        check(&blocks, &traces, &format!("theta {theta}"));
    }
}

/// What the noise looked like: a threshold with more decimals than the render can show is a
/// threshold the player is not being told.
#[test]
fn no_fitted_threshold_needs_more_decimals_than_the_render_shows() {
    let blocks = common::blocks();
    let base = common::example_tree();
    let mut worst = 0;
    for seed in 1..=30u64 {
        let traces = common::synthetic_traces(&blocks, &base, 3, 20, seed, 1.5);
        let tree = induce(&blocks, &traces).unwrap().tree.unwrap();
        for (_, theta) in thresholds(&blocks, &tree) {
            let text = format!("{theta:?}");
            let decimals = text.split_once('.').map_or(0, |(_, tail)| tail.len());
            worst = worst.max(decimals);
        }
    }
    assert!(
        worst <= 3,
        "a fitted threshold needed {worst} decimals; before the fit chose round numbers this \
         was 16"
    );
}
