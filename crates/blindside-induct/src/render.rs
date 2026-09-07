//! Two renders of a tree: as indented lines, and as one plain sentence. Both use labels
//! from the block list and never an id.

use serde::Serialize;

use crate::blocks::BlockSet;
use crate::tree::{DecisionTree, Node};
use crate::tuning;

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Rendered {
    pub lines: Vec<String>,
    pub sentence: String,
}

pub fn render(tree: &DecisionTree, blocks: &BlockSet) -> Rendered {
    Rendered {
        lines: to_lines(tree, blocks),
        sentence: to_sentence(tree, blocks),
    }
}

/// One line per node. A branch is `label?` (with `(param = value)` when the tree carries a
/// value for it); its children follow indented by two, prefixed `yes: ` and `no: `.
pub fn to_lines(tree: &DecisionTree, blocks: &BlockSet) -> Vec<String> {
    let mut out = Vec::new();
    write_node(&tree.root, "", 0, tree, blocks, &mut out);
    out
}

fn write_node(
    node: &Node,
    prefix: &str,
    indent: usize,
    tree: &DecisionTree,
    blocks: &BlockSet,
    out: &mut Vec<String>,
) {
    let pad = " ".repeat(indent);
    match node {
        Node::Action { action } => {
            out.push(format!("{pad}{prefix}{}", blocks.action_label(action)))
        }
        Node::Branch { predicate, yes, no } => {
            out.push(format!(
                "{pad}{prefix}{}",
                question(predicate, tree, blocks)
            ));
            write_node(yes, "yes: ", indent + 2, tree, blocks, out);
            write_node(no, "no: ", indent + 2, tree, blocks, out);
        }
    }
}

fn question(id: &str, tree: &DecisionTree, blocks: &BlockSet) -> String {
    let label = blocks.predicate_label(id);
    let threshold = blocks
        .predicate(id)
        .and_then(|p| p.param.as_deref())
        .and_then(|name| tree.params.get(id, name).map(|value| (name, value)));
    match threshold {
        Some((name, value)) => format!("{label} ({name} = {})?", display_number(value)),
        None => format!("{label}?"),
    }
}

/// The tree flattened into an ordered list of clauses, one per leaf, yes branch first.
/// Because every leaf under a node's yes branch is listed before anything under its no
/// branch, each clause only has to state the predicates that were true on its path;
/// "otherwise" carries the rest. So a chain reads "If A, x. Otherwise if B, y. Otherwise
/// z." and a nested yes branch reads "If A and B, x. Otherwise if A, y. ...". A tree that
/// is one leaf reads "Always x."
pub fn to_sentence(tree: &DecisionTree, blocks: &BlockSet) -> String {
    let clauses: Vec<String> = tree
        .root
        .paths()
        .iter()
        .enumerate()
        .map(|(i, path)| {
            let positives: Vec<&str> = path
                .literals
                .iter()
                .filter(|(_, taken)| *taken)
                .map(|(id, _)| blocks.predicate_label(id))
                .collect();
            let action = blocks.action_label(&path.action);
            match (i == 0, positives.is_empty()) {
                (true, true) => format!("Always {action}."),
                (false, true) => format!("Otherwise {action}."),
                (true, false) => format!("If {}, {action}.", positives.join(" and ")),
                (false, false) => format!("Otherwise if {}, {action}.", positives.join(" and ")),
            }
        })
        .collect();
    clauses.join(" ")
}

/// A number as the player sees it: fixed decimals, trailing zeros trimmed.
pub fn display_number(value: f64) -> String {
    let text = format!("{value:.prec$}", prec = tuning::NUMBER_DECIMALS);
    if text.contains('.') {
        text.trim_end_matches('0').trim_end_matches('.').to_string()
    } else {
        text
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn numbers_are_trimmed() {
        assert_eq!(display_number(2.9), "2.9");
        assert_eq!(display_number(3.0), "3");
        assert_eq!(display_number(2.31), "2.31");
        assert_eq!(display_number(2.6049999), "2.605");
    }
}
