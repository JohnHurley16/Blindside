//! Two minimal trees fit equally well; the same one is chosen every run.

mod common;

use std::collections::{BTreeMap, BTreeSet};

use blindside_induct::induce::induce;
use blindside_induct::named_trace::NamedTrace;
use blindside_induct::params::Params;
use blindside_induct::trace::{Step, Trace};
use blindside_induct::tree::Node;

/// A rule two different minimal trees fit equally well: the first action when both
/// non-parametric predicates hold, else the second. Either predicate can be the root; both
/// trees have two nodes over the same two predicates, so only the lexical tie-break decides.
fn ambiguous_traces() -> (Vec<NamedTrace>, Vec<String>) {
    let blocks = common::blocks();
    let plain: Vec<String> = blocks
        .predicates
        .iter()
        .filter(|p| p.param.is_none())
        .map(|p| p.id.clone())
        .collect();
    assert_eq!(plain.len(), 2);
    let ids: Vec<String> = blocks.predicates.iter().map(|p| p.id.clone()).collect();
    let steps = (0..8u64)
        .map(|bits| {
            let predicates: BTreeMap<String, bool> = ids
                .iter()
                .enumerate()
                .map(|(k, id)| (id.clone(), bits & (1 << k) != 0))
                .collect();
            let both = predicates[&plain[0]] && predicates[&plain[1]];
            let action = blocks.actions[usize::from(!both)].id.clone();
            Step {
                tick: 10 * (bits + 1),
                junction: bits,
                predicates,
                raw: BTreeMap::new(),
                action,
            }
        })
        .collect();
    let trace = Trace {
        seed: 1,
        enabled_predicates: ids,
        enabled_actions: blocks.actions.iter().map(|a| a.id.clone()).collect(),
        params: Params::new(),
        steps,
        outcome: None,
    };
    let named = NamedTrace {
        name: "ambiguous.json".to_string(),
        trace,
    };
    (vec![named], plain)
}

#[test]
fn a_tie_between_two_minimal_trees_is_broken_the_same_way_every_run() {
    let blocks = common::blocks();
    let (traces, plain) = ambiguous_traces();
    let expected_root = plain.iter().min().unwrap().clone();
    let mut outputs = BTreeSet::new();
    for _ in 0..100 {
        let tree = induce(&blocks, &traces)
            .expect("valid input")
            .tree
            .expect("consistent");
        assert_eq!(tree.node_count(), 2);
        assert_eq!(tree.predicates_used().len(), 2);
        match &tree.root {
            Node::Branch { predicate, .. } => assert_eq!(*predicate, expected_root),
            Node::Action { .. } => panic!("the root must be a branch"),
        }
        outputs.insert(serde_json::to_string(&tree).unwrap());
    }
    assert_eq!(outputs.len(), 1);
}
