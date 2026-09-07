//! One flipped choice: no separator, the conflict names it, and the query is in labels.
//! And when several stops conflict, the query asks about the pair whose resolution removes
//! the most conflicts.

mod common;

use std::collections::BTreeMap;

use blindside_induct::induce::induce;
use blindside_induct::named_trace::NamedTrace;
use blindside_induct::params::Params;
use blindside_induct::step_input::StepInput;
use blindside_induct::step_ref::StepRef;
use blindside_induct::trace::{Step, Trace};

fn action_of<'a>(traces: &'a [NamedTrace], step: &StepRef) -> &'a str {
    let named = traces
        .iter()
        .find(|t| t.name == step.trace)
        .expect("known trace");
    &named.trace.steps[step.index].action
}

#[test]
fn one_flipped_choice_yields_no_separator_and_a_query_in_labels() {
    let blocks = common::blocks();
    let reference = common::example_tree();
    let mut traces = common::synthetic_traces(&blocks, &reference, 3, 20, 7, 1.5);

    // Flip a stop in the second trace whose choice the reference tree makes without looking
    // at any parametric reading, so the flip contradicts the others under every threshold.
    let flipped_trace = 1;
    let flipped_index = traces[flipped_trace]
        .trace
        .steps
        .iter()
        .position(|step| {
            let mut low = StepInput::from(step);
            let mut high = StepInput::from(step);
            for value in low.raw.values_mut() {
                *value = f64::MIN;
            }
            for value in high.raw.values_mut() {
                *value = f64::MAX;
            }
            reference.decide(&low, &blocks) == step.action
                && reference.decide(&high, &blocks) == step.action
        })
        .expect("some stop is decided without the parametric predicate");
    let original = traces[flipped_trace].trace.steps[flipped_index]
        .action
        .clone();
    let other = blocks
        .actions
        .iter()
        .map(|a| a.id.clone())
        .find(|id| *id != original)
        .expect("two actions");
    traces[flipped_trace].trace.steps[flipped_index].action = other;

    let result = induce(&blocks, &traces).expect("valid input");
    assert!(!result.consistent);
    assert!(result.tree.is_none());

    let flipped = StepRef {
        trace: traces[flipped_trace].name.clone(),
        index: flipped_index,
    };
    assert!(
        result.conflicts.iter().any(|pair| pair.contains(&flipped)),
        "conflicts must name the flipped stop: {:?}",
        result.conflicts
    );
    for pair in &result.conflicts {
        assert_ne!(action_of(&traces, &pair[0]), action_of(&traces, &pair[1]));
    }

    let query = result.query.expect("an inconsistent set carries a query");
    assert!(
        query.pair.contains(&flipped),
        "the query should ask about the flipped stop: {:?}",
        query.pair
    );
    for predicate in &blocks.predicates {
        assert!(
            query.text.contains(&predicate.label),
            "label {:?} missing from:\n{}",
            predicate.label,
            query.text
        );
    }
    for action in &blocks.actions {
        assert!(
            query.text.contains(&action.label),
            "label {:?} missing from:\n{}",
            action.label,
            query.text
        );
    }
    let ids = blocks
        .predicates
        .iter()
        .map(|p| p.id.as_str())
        .chain(blocks.actions.iter().map(|a| a.id.as_str()));
    for id in ids {
        assert!(
            !query.text.contains(id),
            "id {id:?} leaked into:\n{}",
            query.text
        );
    }
}

/// One trace, two vector classes that both conflict. The first class (earliest stops) is an
/// even one-against-one; the second is three-against-one. Resolving a pair in the second
/// removes three conflicts; in the first, one. The query must ask about the second.
#[test]
fn the_query_asks_about_the_pair_whose_resolution_removes_the_most_conflicts() {
    let blocks = common::blocks();
    let plain: Vec<String> = blocks
        .predicates
        .iter()
        .filter(|p| p.param.is_none())
        .map(|p| p.id.clone())
        .collect();
    assert!(
        plain.len() >= 2,
        "two non-parametric predicates make two classes"
    );
    let first = blocks.actions[0].id.clone();
    let second = blocks.actions[1].id.clone();

    // (which class, action). The parametric predicate is absent from every stop.
    let plan = [
        (0, &first),
        (0, &second),
        (1, &first),
        (1, &first),
        (1, &first),
        (1, &second),
    ];
    let steps = plan
        .iter()
        .enumerate()
        .map(|(i, (class, action))| Step {
            tick: 10 * (i as u64 + 1),
            junction: i as u64,
            predicates: BTreeMap::from([
                (plain[0].clone(), *class == 1),
                (plain[1].clone(), *class == 0),
            ]),
            raw: BTreeMap::new(),
            action: (*action).clone(),
        })
        .collect();
    let traces = vec![NamedTrace {
        name: "two-classes.json".to_string(),
        trace: Trace {
            seed: 1,
            enabled_predicates: plain.clone(),
            enabled_actions: vec![first.clone(), second.clone()],
            params: Params::new(),
            steps,
            outcome: None,
        },
    }];

    let result = induce(&blocks, &traces).expect("valid input");
    assert!(!result.consistent);
    assert_eq!(result.conflicts.len(), 4);
    let query = result.query.expect("a query");
    let at = |index: usize| StepRef {
        trace: "two-classes.json".to_string(),
        index,
    };
    assert_eq!(
        query.pair,
        [at(2), at(5)],
        "not the earliest pair, the most useful one"
    );
}
