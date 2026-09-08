//! Synthetic round trip: traces played from the theta-aware tree induce it back.
//!
//! This is `docs/PHASE-2-JUNCTION-TEST.md`'s third acceptance criterion, asserted exactly as
//! that file now states it: the tree comes back, and theta comes back inside the constraining
//! bracket. The bracket is the most the demonstrations say about theta; the second assertion
//! on theta says how well the fit uses it, since a threshold one ulp above the bracket's floor
//! is inside it too.

mod common;

use std::collections::BTreeMap;

use blindside_induct::induce::induce;
use blindside_induct::named_trace::NamedTrace;
use blindside_induct::params::Params;
use blindside_induct::step_input::StepInput;
use blindside_induct::trace::{Step, Trace};

/// Seeds enough that the assertions below are properties rather than one lucky draw.
const SEEDS: std::ops::RangeInclusive<u64> = 1..=100;

/// The known trees: the contract's example, whose theta is 2.9, and two whose theta is not a
/// round number. The fit reports the roundest number its band allows, so a round true theta
/// flatters it: whenever its band holds 2.9 the error is exactly zero. The bound below is set
/// on all three together and is not met by the round one alone.
const OTHER_THETAS: [f64; 2] = [2.87, 3.13];

/// The most a fit may miss the true threshold by, as a fraction of the bracket the
/// demonstrations left it, averaged over every seed and tree.
///
/// Measured over the 300 runs: the fit scores 0.304 (0.279 on the contract's tree, 0.305 and
/// 0.328 on the non-round ones; 0.928 on the worst single run). A fit that hugs an edge of the
/// bracket -- which the bracket assertion alone lets through -- scores 0.527 at the floor and
/// 0.473 at the ceiling on the same runs, because the true threshold sits anywhere in the
/// bracket with nothing to prefer one end; the exact middle of the bracket, the best any rule
/// that reads only the demonstrations can do, scores 0.219. The bound sits between the fit and
/// the nearer edge: 0.10 above the fit, 0.07 below the edge. The test prints all four.
const MEAN_RELATIVE_ERROR_BOUND: f64 = 0.40;

#[test]
fn synthetic_demonstrations_induce_the_generating_tree_back_on_every_seed() {
    let blocks = common::blocks();
    let contract = common::example_tree();
    let mut references = vec![contract.clone()];
    references.extend(
        OTHER_THETAS
            .iter()
            .map(|&theta| common::tree_with_theta(&blocks, &contract, theta)),
    );

    let mut relative_errors: Vec<f64> = Vec::new();
    // What a fit at the exact middle of the bracket, and one at its floor, would have scored.
    let (mut at_middle, mut at_floor, mut at_ceiling): (Vec<f64>, Vec<f64>, Vec<f64>) =
        (Vec::new(), Vec::new(), Vec::new());
    for reference in &references {
        let mut this_tree: Vec<f64> = Vec::new();
        for seed in SEEDS {
            let traces = common::synthetic_traces(&blocks, reference, 3, 20, seed, 1.5);
            let result = induce(&blocks, &traces).expect("valid input");
            assert!(result.consistent, "seed {seed}: {:?}", result.conflicts);
            let tree = result.tree.expect("a consistent set has a tree");

            for named in &traces {
                for step in &named.trace.steps {
                    assert_eq!(
                        tree.decide(&StepInput::from(step), &blocks),
                        step.action,
                        "seed {seed}, {} tick {}",
                        named.name,
                        step.tick
                    );
                }
            }
            assert_eq!(tree.root, reference.root, "seed {seed}: a different rule");

            for predicate in blocks.predicates.iter().filter(|p| p.param.is_some()) {
                let name = predicate.param.as_deref().expect("filtered on param");
                let truth = reference
                    .params
                    .get(&predicate.id, name)
                    .expect("the reference carries its theta");
                let fitted = tree
                    .params
                    .get(&predicate.id, name)
                    .unwrap_or_else(|| panic!("seed {seed}: theta is fitted"));

                // What the demonstrations actually said about the threshold, and all they
                // said: above the largest reading among the stops the threshold sent the low
                // way, below the smallest among those it sent the high way, counting only the
                // stops the other predicates do not already decide. A stop the tree sends the
                // same way whatever the reading is carries no information about where the
                // threshold goes, however close its reading sits.
                let (lo, hi) = common::constraining_bracket(&blocks, &tree, &traces, &predicate.id);
                assert!(
                    lo.is_finite() && hi.is_finite(),
                    "seed {seed}: the synthetic data must constrain the threshold from both sides"
                );
                assert!(
                    lo < fitted && fitted < hi,
                    "seed {seed}: theta {fitted} must lie strictly inside ({lo}, {hi})"
                );
                this_tree.push((fitted - truth).abs() / (hi - lo));
                at_middle.push((lo / 2.0 + hi / 2.0 - truth).abs() / (hi - lo));
                at_floor.push((lo - truth).abs() / (hi - lo));
                at_ceiling.push((hi - truth).abs() / (hi - lo));
            }
        }
        let mean = this_tree.iter().sum::<f64>() / this_tree.len() as f64;
        let worst = this_tree.iter().copied().fold(0.0, f64::max);
        println!(
            "theta {}: |fit - true| is {mean:.3} of the bracket on average, {worst:.3} at worst",
            reference
                .params
                .get("uncertainty_exceeds", "theta")
                .map_or_else(|| "?".to_string(), |t| t.to_string())
        );
        relative_errors.extend(this_tree);
    }

    let average = |errors: &[f64]| errors.iter().sum::<f64>() / errors.len() as f64;
    let mean = average(&relative_errors);
    println!(
        "all: |fit - true| is {mean:.3} of the bracket on average over {} runs; the middle of          the bracket would score {:.3}, its floor {:.3}, its ceiling {:.3}",
        relative_errors.len(),
        average(&at_middle),
        average(&at_floor),
        average(&at_ceiling)
    );
    assert!(
        mean < MEAN_RELATIVE_ERROR_BOUND,
        "the fitted threshold misses the true one by {mean:.3} of the bracket on average; a fit \
         hugging an edge of the bracket scores 0.5"
    );
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
