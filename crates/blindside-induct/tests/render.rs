//! Pinned renders of the contract's example tree.

mod common;

use blindside_induct::params::Params;
use blindside_induct::render::{to_lines, to_sentence};
use blindside_induct::tree::{DecisionTree, Node};

#[test]
fn the_example_tree_reads_as_one_sentence() {
    let blocks = common::blocks();
    let tree = common::example_tree();
    assert_eq!(
        to_sentence(&tree, &blocks),
        "If carrying, go back. Otherwise if lost, go back. Otherwise if an unexplored branch here, take a branch. Otherwise go back."
    );
}

#[test]
fn the_example_tree_renders_as_indented_lines() {
    let blocks = common::blocks();
    let tree = common::example_tree();
    let expected = vec![
        "carrying?",
        "  yes: go back",
        "  no: lost (theta = 2.9)?",
        "    yes: go back",
        "    no: an unexplored branch here?",
        "      yes: take a branch",
        "      no: go back",
    ];
    assert_eq!(to_lines(&tree, &blocks), expected);
}

#[test]
fn a_nested_yes_branch_and_a_lone_leaf_still_read_as_sentences() {
    let blocks = common::blocks();
    let nested = DecisionTree {
        params: Params::new(),
        root: Node::branch(
            "carrying_cargo",
            Node::branch(
                "uncertainty_exceeds",
                Node::action("return_to_beacon"),
                Node::action("take_branch"),
            ),
            Node::action("return_to_beacon"),
        ),
    };
    assert_eq!(
        to_sentence(&nested, &blocks),
        "If carrying and lost, go back. Otherwise if carrying, take a branch. Otherwise go back."
    );
    let leaf = DecisionTree {
        params: Params::new(),
        root: Node::action("return_to_beacon"),
    };
    assert_eq!(to_sentence(&leaf, &blocks), "Always go back.");
    assert_eq!(to_lines(&leaf, &blocks), vec!["go back"]);
}
