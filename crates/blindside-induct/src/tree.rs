//! A decision tree is a policy: predicates at the branches, actions at the leaves. The
//! serde shape is exactly the contract's `tree.json`.

use std::collections::BTreeSet;
use std::fmt;
use std::fs;
use std::path::Path;

use serde::de::{self, MapAccess, Visitor};
use serde::{Deserialize, Deserializer, Serialize};

use crate::blocks::BlockSet;
use crate::error::{Error, Result};
use crate::evaluate::predicate_value;
use crate::leaf_path::LeafPath;
use crate::params::Params;
use crate::step_input::StepInput;
use crate::strict;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DecisionTree {
    #[serde(default)]
    pub params: Params,
    pub root: Node,
}

/// Either `{"action": id}` or `{"predicate": id, "yes": node, "no": node}`.
///
/// Read by hand rather than as an untagged enum, which would try the variants in turn and
/// take the first that fit: a node carrying both an action and a predicate would parse as
/// the action, and the branch under it would be dropped without a word.
#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(untagged)]
pub enum Node {
    Action {
        action: String,
    },
    Branch {
        predicate: String,
        yes: Box<Node>,
        no: Box<Node>,
    },
}

impl DecisionTree {
    pub fn load(path: &Path) -> Result<Self> {
        let text = fs::read_to_string(path).map_err(|e| Error::io(path, e))?;
        strict::from_str(&text, &path.display().to_string())
    }

    pub fn from_json(text: &str) -> Result<Self> {
        strict::from_str(text, "tree")
    }

    /// Every predicate and action in the tree must be in the block list.
    pub fn validate(&self, blocks: &BlockSet) -> Result<()> {
        self.root.validate(blocks)
    }

    /// The action for one stop, evaluating parametric predicates with this tree's params.
    pub fn decide<'a>(&'a self, input: &StepInput, blocks: &BlockSet) -> &'a str {
        self.root.decide(input, &self.params, blocks)
    }

    /// Internal (predicate) nodes.
    pub fn node_count(&self) -> usize {
        self.root.node_count()
    }

    pub fn predicates_used(&self) -> BTreeSet<String> {
        let mut out = BTreeSet::new();
        self.root.collect_predicates(&mut out);
        out
    }
}

const NODE_FIELDS: &[&str] = &["action", "predicate", "yes", "no"];

impl<'de> Deserialize<'de> for Node {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> std::result::Result<Self, D::Error> {
        deserializer.deserialize_map(NodeVisitor)
    }
}

struct NodeVisitor;

impl<'de> Visitor<'de> for NodeVisitor {
    type Value = Node;

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(r#"{"action": id} or {"predicate": id, "yes": node, "no": node}"#)
    }

    fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> std::result::Result<Node, A::Error> {
        let mut action: Option<String> = None;
        let mut predicate: Option<String> = None;
        let mut yes: Option<Node> = None;
        let mut no: Option<Node> = None;
        while let Some(key) = map.next_key::<String>()? {
            let taken = match key.as_str() {
                "action" => action.replace(map.next_value()?).is_some(),
                "predicate" => predicate.replace(map.next_value()?).is_some(),
                "yes" => yes.replace(map.next_value()?).is_some(),
                "no" => no.replace(map.next_value()?).is_some(),
                other => return Err(de::Error::unknown_field(other, NODE_FIELDS)),
            };
            if taken {
                return Err(de::Error::custom(format!("duplicate key {key:?}")));
            }
        }
        match (action, predicate) {
            (Some(_), Some(_)) => Err(de::Error::custom(
                "a node is either an action or a predicate with two branches, not both",
            )),
            (Some(action), None) => match (yes, no) {
                (None, None) => Ok(Node::Action { action }),
                _ => Err(de::Error::custom(
                    r#"an action node cannot carry "yes" or "no""#,
                )),
            },
            (None, Some(predicate)) => Ok(Node::Branch {
                predicate,
                yes: Box::new(yes.ok_or_else(|| de::Error::missing_field("yes"))?),
                no: Box::new(no.ok_or_else(|| de::Error::missing_field("no"))?),
            }),
            (None, None) => Err(de::Error::custom(
                r#"a node needs either "action" or "predicate""#,
            )),
        }
    }
}

impl Node {
    pub fn action(id: &str) -> Node {
        Node::Action {
            action: id.to_string(),
        }
    }

    pub fn branch(predicate: &str, yes: Node, no: Node) -> Node {
        Node::Branch {
            predicate: predicate.to_string(),
            yes: Box::new(yes),
            no: Box::new(no),
        }
    }

    pub fn validate(&self, blocks: &BlockSet) -> Result<()> {
        match self {
            Node::Action { action } => {
                if blocks.action(action).is_none() {
                    return Err(Error::input(format!(
                        "tree: action {action:?} is not in the block list"
                    )));
                }
                Ok(())
            }
            Node::Branch { predicate, yes, no } => {
                if blocks.predicate(predicate).is_none() {
                    return Err(Error::input(format!(
                        "tree: predicate {predicate:?} is not in the block list"
                    )));
                }
                yes.validate(blocks)?;
                no.validate(blocks)
            }
        }
    }

    /// Walks the tree. A predicate with no value at this stop (absent from both maps, or
    /// not in the block list) counts as false, exactly as the induction treats it.
    pub fn decide<'a>(&'a self, input: &StepInput, params: &Params, blocks: &BlockSet) -> &'a str {
        match self {
            Node::Action { action } => action,
            Node::Branch { predicate, yes, no } => {
                let holds = match blocks.predicate(predicate) {
                    Some(p) => predicate_value(p, input, params),
                    None => input.predicates.get(predicate).copied(),
                }
                .unwrap_or(false);
                if holds {
                    yes.decide(input, params, blocks)
                } else {
                    no.decide(input, params, blocks)
                }
            }
        }
    }

    pub fn node_count(&self) -> usize {
        match self {
            Node::Action { .. } => 0,
            Node::Branch { yes, no, .. } => 1 + yes.node_count() + no.node_count(),
        }
    }

    pub fn collect_predicates(&self, out: &mut BTreeSet<String>) {
        if let Node::Branch { predicate, yes, no } = self {
            out.insert(predicate.clone());
            yes.collect_predicates(out);
            no.collect_predicates(out);
        }
    }

    /// Every root-to-leaf path, yes branch first at each node.
    pub fn paths(&self) -> Vec<LeafPath> {
        let mut out = Vec::new();
        self.walk_paths(&mut Vec::new(), &mut out);
        out
    }

    fn walk_paths(&self, prefix: &mut Vec<(String, bool)>, out: &mut Vec<LeafPath>) {
        match self {
            Node::Action { action } => out.push(LeafPath {
                literals: prefix.clone(),
                action: action.clone(),
            }),
            Node::Branch { predicate, yes, no } => {
                prefix.push((predicate.clone(), true));
                yes.walk_paths(prefix, out);
                prefix.pop();
                prefix.push((predicate.clone(), false));
                no.walk_paths(prefix, out);
                prefix.pop();
            }
        }
    }
}
