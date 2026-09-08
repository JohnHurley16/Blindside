//! One flipped choice: no separator, the conflict names it, and the query is in labels.
//! And when several stops conflict, the query asks about the pair whose resolution removes
//! the most conflicts.
//!
//! The second half is about which conflicts are reported at all. When the demonstrations
//! contradict each other, several bands of the threshold usually leave the same number of
//! stops to disown, and they do not report the same pairs; the band reported from is the one
//! whose pairs are between the closest readings. Each case below states the pairs a player
//! would name and checks that those, and only those, come back.

mod common;

use std::collections::BTreeMap;

use blindside_induct::blocks::BlockSet;
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

// --- Which conflicts are reported ----------------------------------------------------------

/// A stop that kept going (`ON`) or turned back (`BACK`).
const ON: bool = true;
const BACK: bool = false;

/// One demonstration whose stops all read alike on the plain predicates and differ only in
/// the parametric reading -- `None` where the block did not exist at that stop -- and in the
/// choice. So the parametric predicate is the only thing that can tell two stops apart, and
/// which stops are reported as contradicting each other is entirely down to where its
/// threshold is put.
fn one_run(blocks: &BlockSet, stops: &[(Option<f64>, bool)]) -> Vec<NamedTrace> {
    let parametric = blocks
        .predicates
        .iter()
        .find(|p| p.param.is_some())
        .expect("a parametric predicate");
    let plain: Vec<String> = blocks
        .predicates
        .iter()
        .filter(|p| p.param.is_none())
        .map(|p| p.id.clone())
        .collect();
    let (going_on, turning_back) = (blocks.actions[0].id.clone(), blocks.actions[1].id.clone());
    let steps = stops
        .iter()
        .enumerate()
        .map(|(i, &(reading, on))| Step {
            tick: 10 * (i as u64 + 1),
            junction: i as u64,
            predicates: plain
                .iter()
                .map(|id| (id.clone(), id == &plain[0]))
                .collect(),
            raw: reading
                .map(|r| BTreeMap::from([(parametric.id.clone(), r)]))
                .unwrap_or_default(),
            action: if on {
                going_on.clone()
            } else {
                turning_back.clone()
            },
        })
        .collect();
    vec![NamedTrace {
        name: "one-run.json".to_string(),
        trace: Trace {
            seed: 1,
            enabled_predicates: blocks.predicates.iter().map(|p| p.id.clone()).collect(),
            enabled_actions: vec![going_on, turning_back],
            params: Params::new(),
            steps,
            outcome: None,
        },
    }]
}

/// The conflicts `induce` reports for one run, as pairs of stop indices, and the pair its
/// query asks about.
fn reported(
    blocks: &BlockSet,
    stops: &[(Option<f64>, bool)],
) -> (Vec<(usize, usize)>, (usize, usize)) {
    let traces = one_run(blocks, stops);
    let result = induce(blocks, &traces).expect("valid input");
    assert!(!result.consistent, "these stops contradict each other");
    assert!(result.tree.is_none());
    let pairs = result
        .conflicts
        .iter()
        .map(|[a, b]| (a.index, b.index))
        .collect();
    let query = result.query.expect("an inconsistent set carries a query");
    (pairs, (query.pair[0].index, query.pair[1].index))
}

/// The degenerate set: one demonstration, one flipped choice, and readings so evenly spaced
/// that every band of the threshold leaves exactly one stop to be disowned. Nothing about the
/// threshold is decided by the contradiction, so the whole grid ties -- and what the player is
/// shown depends entirely on which of the tied bands is reported from.
///
/// The bands are all the same width too, so the search's own tie-break (the widest band, then
/// the lowest) lands on the outer band below every reading, where every stop reads alike and
/// the flipped stop is reported as contradicting all five of the others -- including the ones
/// whose readings sit the other side of it, which is not a pair anyone can act on. Reported
/// from the band whose pairs are between the closest readings, the contradiction is the one a
/// player would name: it turned back at this reading and kept going at a higher one.
#[test]
fn a_flipped_choice_among_evenly_spaced_readings_names_the_stops_either_side_of_it() {
    let blocks = common::blocks();
    let flipped = 3;
    let stops: Vec<(Option<f64>, bool)> = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        .iter()
        .enumerate()
        .map(|(i, &reading)| (Some(reading), i != flipped))
        .collect();
    let (pairs, query) = reported(&blocks, &stops);

    // Only the stops that kept going at a higher reading contradict the one that turned back.
    assert_eq!(
        pairs,
        vec![(3, 4), (3, 5)],
        "a threshold below every reading would report all five other stops"
    );
    assert!(
        pairs.iter().all(|&(a, b)| a == flipped || b == flipped),
        "every pair names the flipped stop"
    );
    assert!(query.0 == flipped || query.1 == flipped);
}

/// Two clusters of readings, and a flip in the lower one. The bands that leave one stop to
/// disown are not next to each other: between 1 and 2, where the stop that kept going at 3
/// is the odd one out among everything above 1; and between 3 and 100, where the stop that
/// turned back at 2 is the odd one out among the three low readings. The first names four
/// pairs, three of them blaming a reading of 3 against readings of 100 to 102. The second
/// names the two pairs a player would: turned back at 2, kept going at 1 and at 3.
#[test]
fn a_flip_in_the_lower_cluster_is_reported_against_its_own_cluster() {
    let blocks = common::blocks();
    let stops = [
        (Some(1.0), ON),
        (Some(2.0), BACK),
        (Some(3.0), ON),
        (Some(100.0), BACK),
        (Some(101.0), BACK),
        (Some(102.0), BACK),
    ];
    let (pairs, query) = reported(&blocks, &stops);
    assert_eq!(pairs, vec![(0, 1), (1, 2)]);
    assert!(query == (0, 1) || query == (1, 2));
}

/// The same shape with the flip in the upper cluster. The tying bands are between 3 and 100
/// and between 101 and 102, again not adjacent; the second would blame the stop that turned
/// back at 100 against the three that kept going at 1, 2 and 3.
#[test]
fn a_flip_in_the_upper_cluster_is_reported_against_its_own_cluster() {
    let blocks = common::blocks();
    let stops = [
        (Some(1.0), ON),
        (Some(2.0), ON),
        (Some(3.0), ON),
        (Some(100.0), BACK),
        (Some(101.0), ON),
        (Some(102.0), BACK),
    ];
    let (pairs, query) = reported(&blocks, &stops);
    assert_eq!(pairs, vec![(3, 4), (4, 5)]);
    assert!(query == (3, 4) || query == (4, 5));
}

/// The widest tying band is the wrong one. Between 101 and 150 there is room for a threshold
/// anywhere in 49 cells, and the search's tie-break would take it; but from there the stop
/// that turned back at 100 is reported against the ones that kept going at 1, 50 and 99. The
/// band between 99 and 100 is one cell wide and names the pairs a player would recognise.
#[test]
fn the_closest_pairs_beat_the_widest_band() {
    let blocks = common::blocks();
    let stops = [
        (Some(1.0), ON),
        (Some(50.0), ON),
        (Some(99.0), ON),
        (Some(100.0), BACK),
        (Some(101.0), ON),
        (Some(150.0), BACK),
    ];
    let (pairs, _) = reported(&blocks, &stops);
    assert_eq!(pairs, vec![(3, 4), (4, 5)]);
}

/// Two tying bands of equal width, so the search's tie-break takes the lower: between 1 and
/// 2, from which the stop that kept going at 3 is reported against four stops, one of them
/// three cells away. Between 3 and 4, the stop that turned back at 2 is reported against its
/// two neighbours, one cell either side.
#[test]
fn the_closest_pairs_beat_the_lowest_band() {
    let blocks = common::blocks();
    let stops = [
        (Some(1.0), ON),
        (Some(2.0), BACK),
        (Some(3.0), ON),
        (Some(4.0), BACK),
        (Some(5.0), BACK),
        (Some(6.0), BACK),
    ];
    let (pairs, _) = reported(&blocks, &stops);
    assert_eq!(pairs, vec![(0, 1), (1, 2)]);
}

/// Two flipped choices among evenly spaced readings, at 3 and at 6. Every band leaves two
/// stops to disown, so all nine tie. Reported from the band between them -- 4 to 5 -- each
/// flipped stop is set against its own neighbours and nothing further than two cells away.
/// From the band below every reading, the two are set against every other stop, five cells
/// apart at worst.
#[test]
fn two_flips_are_each_reported_against_their_own_neighbours() {
    let blocks = common::blocks();
    let stops = [
        (Some(1.0), ON),
        (Some(2.0), ON),
        (Some(3.0), BACK),
        (Some(4.0), ON),
        (Some(5.0), ON),
        (Some(6.0), BACK),
        (Some(7.0), ON),
        (Some(8.0), ON),
    ];
    let (pairs, _) = reported(&blocks, &stops);
    assert_eq!(pairs, vec![(0, 2), (1, 2), (2, 3), (4, 5), (5, 6), (5, 7)]);
}

/// A stop where the parametric block did not exist reads as not exceeding any threshold, so
/// it sits with the low readings whatever the threshold. It kept going; the stop that turned
/// back at 2 contradicts it under every threshold above 2, and that pair is at no distance in
/// readings because no reading entered into it. Every band ties on one stop to disown; the
/// one reported from, between 2 and 3, names that pair and nothing else -- the next band up
/// would add the stop that kept going at 3.
#[test]
fn a_stop_without_a_reading_is_at_no_distance() {
    let blocks = common::blocks();
    let stops = [
        (None, ON),
        (Some(2.0), BACK),
        (Some(3.0), ON),
        (Some(4.0), ON),
    ];
    let (pairs, query) = reported(&blocks, &stops);
    assert_eq!(pairs, vec![(0, 1)]);
    assert_eq!(query, (0, 1));
}
