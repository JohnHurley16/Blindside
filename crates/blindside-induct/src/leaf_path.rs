//! One root-to-leaf path of a tree: the predicates tested along it, which way each went,
//! and the action at the end. The sentence render is built from these.

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LeafPath {
    /// `(predicate id, branch taken)` from the root down; `true` is the yes branch.
    pub literals: Vec<(String, bool)>,
    pub action: String,
}
