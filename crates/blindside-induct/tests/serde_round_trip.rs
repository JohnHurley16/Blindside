//! tree.json parses and re-serialises equal.

mod common;

use blindside_induct::tree::{DecisionTree, Node};
use serde_json::Value;

#[test]
fn the_example_tree_parses_and_reserialises_equal() {
    let tree = DecisionTree::from_json(common::TREE_JSON).unwrap();
    let again = serde_json::to_string(&tree).unwrap();
    let original: Value = serde_json::from_str(common::TREE_JSON).unwrap();
    let reserialised: Value = serde_json::from_str(&again).unwrap();
    assert_eq!(original, reserialised);
    assert_eq!(DecisionTree::from_json(&again).unwrap(), tree);
}

#[test]
fn a_leaf_root_without_params_parses_and_writes_empty_params() {
    let tree = DecisionTree::from_json(r#"{"root": {"action": "return_to_beacon"}}"#).unwrap();
    assert_eq!(tree.root, Node::action("return_to_beacon"));
    assert!(tree.params.is_empty());
    assert_eq!(
        serde_json::to_string(&tree).unwrap(),
        r#"{"params":{},"root":{"action":"return_to_beacon"}}"#
    );
}
