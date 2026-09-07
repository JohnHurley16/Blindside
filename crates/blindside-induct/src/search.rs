//! The minimal separator over boolean vectors.
//!
//! Smallest by internal-node count; ties -> fewest distinct predicates -> the
//! lexicographically smallest preorder sequence of predicate ids. Exact and exhaustive.
//! The size search is a memoised recursion over the subset of vectors a node sees (a path
//! constrains each predicate one of three ways, so at most 3^p subsets). It is repeated for
//! each subset of predicates the tree may use (2^p) to settle the distinct-predicate tie
//! exactly, since that tie does not decompose over subtrees. Comfortable to about six
//! predicates, which is what this is written for.

use std::collections::BTreeMap;

/// One distinct predicate vector and the action it must map to.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Sample {
    pub vector: Vec<bool>,
    pub action: usize,
}

/// A tree over vector columns and action indices, before ids are put back.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SearchTree {
    Leaf(usize),
    Split {
        column: usize,
        yes: Box<SearchTree>,
        no: Box<SearchTree>,
    },
}

/// What "smaller" means, in order: internal nodes, distinct predicates, then the preorder
/// sequence of predicate ranks (a column's position in id order).
pub type TreeKey = (usize, usize, Vec<usize>);

impl SearchTree {
    pub fn internal_nodes(&self) -> usize {
        match self {
            SearchTree::Leaf(_) => 0,
            SearchTree::Split { yes, no, .. } => 1 + yes.internal_nodes() + no.internal_nodes(),
        }
    }

    pub fn key(&self, rank_of_column: &[usize]) -> TreeKey {
        let mut preorder = Vec::new();
        self.preorder(rank_of_column, &mut preorder);
        let mut distinct = preorder.clone();
        distinct.sort_unstable();
        distinct.dedup();
        (preorder.len(), distinct.len(), preorder)
    }

    fn preorder(&self, rank_of_column: &[usize], out: &mut Vec<usize>) {
        if let SearchTree::Split { column, yes, no } = self {
            out.push(rank_of_column[*column]);
            yes.preorder(rank_of_column, out);
            no.preorder(rank_of_column, out);
        }
    }
}

/// `columns_by_id` lists every column the tree may test, in id order. Returns `None` only
/// when two samples with different actions share a vector, which callers rule out first.
pub fn minimal_tree(samples: &[Sample], columns_by_id: &[usize]) -> Option<SearchTree> {
    if samples.is_empty() {
        return None;
    }
    assert!(
        columns_by_id.len() < 64,
        "columns are masked in a u64; induce() caps the count far below this"
    );
    let all: Vec<usize> = (0..samples.len()).collect();
    let global = Search::new(samples, columns_by_id.to_vec()).min_size(&all)?;
    let width = columns_by_id.iter().copied().max().map_or(0, |m| m + 1);
    let mut rank_of_column = vec![0; width];
    for (rank, &column) in columns_by_id.iter().enumerate() {
        rank_of_column[column] = rank;
    }
    let p = columns_by_id.len();
    for distinct in 0..=p {
        let mut best: Option<(TreeKey, SearchTree)> = None;
        for mask in 0u64..(1u64 << p) {
            if mask.count_ones() as usize != distinct {
                continue;
            }
            let allowed: Vec<usize> = columns_by_id
                .iter()
                .enumerate()
                .filter(|(i, _)| mask & (1u64 << i) != 0)
                .map(|(_, &column)| column)
                .collect();
            let mut search = Search::new(samples, allowed);
            if search.min_size(&all) != Some(global) {
                continue;
            }
            let Some(tree) = search.lexmin(&all) else {
                continue;
            };
            let key = tree.key(&rank_of_column);
            if best.as_ref().is_none_or(|(k, _)| key < *k) {
                best = Some((key, tree));
            }
        }
        if let Some((_, tree)) = best {
            return Some(tree);
        }
    }
    None
}

struct Search<'a> {
    samples: &'a [Sample],
    /// The columns this search may test, in id order.
    columns: Vec<usize>,
    memo: BTreeMap<Vec<usize>, Option<usize>>,
}

impl<'a> Search<'a> {
    fn new(samples: &'a [Sample], columns: Vec<usize>) -> Self {
        Search {
            samples,
            columns,
            memo: BTreeMap::new(),
        }
    }

    /// The one action every sample in the subset maps to, if there is one.
    fn uniform(&self, subset: &[usize]) -> Option<usize> {
        let first = self.samples[subset[0]].action;
        subset
            .iter()
            .all(|&i| self.samples[i].action == first)
            .then_some(first)
    }

    fn split(&self, subset: &[usize], column: usize) -> (Vec<usize>, Vec<usize>) {
        subset
            .iter()
            .copied()
            .partition(|&i| self.samples[i].vector[column])
    }

    /// Fewest internal nodes that separate the subset using only `columns`.
    fn min_size(&mut self, subset: &[usize]) -> Option<usize> {
        if self.uniform(subset).is_some() {
            return Some(0);
        }
        if let Some(&known) = self.memo.get(subset) {
            return known;
        }
        let mut best: Option<usize> = None;
        let columns = self.columns.clone();
        for column in columns {
            let (yes, no) = self.split(subset, column);
            if yes.is_empty() || no.is_empty() {
                continue;
            }
            if let (Some(a), Some(b)) = (self.min_size(&yes), self.min_size(&no)) {
                let size = 1 + a + b;
                if best.is_none_or(|current| size < current) {
                    best = Some(size);
                }
            }
        }
        self.memo.insert(subset.to_vec(), best);
        best
    }

    /// The minimal tree with the lexicographically smallest preorder: the smallest column
    /// (in id order) that heads some minimal tree, then the same choice in each subtree.
    /// Subtree sizes are fixed by the split, so the greedy choice is exact.
    fn lexmin(&mut self, subset: &[usize]) -> Option<SearchTree> {
        if let Some(action) = self.uniform(subset) {
            return Some(SearchTree::Leaf(action));
        }
        let target = self.min_size(subset)?;
        let columns = self.columns.clone();
        for column in columns {
            let (yes, no) = self.split(subset, column);
            if yes.is_empty() || no.is_empty() {
                continue;
            }
            let (Some(a), Some(b)) = (self.min_size(&yes), self.min_size(&no)) else {
                continue;
            };
            if 1 + a + b != target {
                continue;
            }
            let yes_tree = self.lexmin(&yes)?;
            let no_tree = self.lexmin(&no)?;
            return Some(SearchTree::Split {
                column,
                yes: Box::new(yes_tree),
                no: Box::new(no_tree),
            });
        }
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample(bits: &[bool], action: usize) -> Sample {
        Sample {
            vector: bits.to_vec(),
            action,
        }
    }

    #[test]
    fn an_and_of_two_columns_needs_two_nodes_and_roots_at_the_first_by_id() {
        // action 1 iff column 0 and column 2; column 1 is noise.
        let mut samples = Vec::new();
        for bits in 0..8u8 {
            let v = [bits & 1 != 0, bits & 2 != 0, bits & 4 != 0];
            samples.push(sample(&v, usize::from(v[0] && v[2])));
        }
        // id order puts column 2 before column 0.
        let tree = minimal_tree(&samples, &[2, 1, 0]).unwrap();
        assert_eq!(tree.internal_nodes(), 2);
        match tree {
            SearchTree::Split { column, .. } => assert_eq!(column, 2),
            SearchTree::Leaf(_) => panic!("root must split"),
        }
    }

    #[test]
    fn a_uniform_set_is_one_leaf_and_a_conflict_is_none() {
        let uniform = vec![sample(&[true], 1), sample(&[false], 1)];
        assert_eq!(minimal_tree(&uniform, &[0]), Some(SearchTree::Leaf(1)));
        let conflict = vec![sample(&[true], 0), sample(&[true], 1)];
        assert_eq!(minimal_tree(&conflict, &[0]), None);
    }
}
