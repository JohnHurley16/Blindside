//! Identical vectors with different actions.

use std::collections::BTreeMap;

use crate::dataset::Dataset;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Conflicts {
    /// Dataset positions `(a, b)` with `a < b`, sorted.
    pub pairs: Vec<(usize, usize)>,
    /// The fewest stops whose choice would have to change for no conflict to remain: within
    /// each vector class, every stop outside the majority action. This is the minimum vertex
    /// cover of the conflict graph, which is a disjoint union of complete multipartite
    /// graphs and so has this closed form.
    pub disowned: usize,
}

pub fn find(dataset: &Dataset) -> Conflicts {
    let mut classes: BTreeMap<&[bool], Vec<usize>> = BTreeMap::new();
    for (position, step) in dataset.steps.iter().enumerate() {
        classes
            .entry(step.vector.as_slice())
            .or_default()
            .push(position);
    }
    let mut pairs = Vec::new();
    let mut disowned = 0;
    for members in classes.values() {
        let mut counts: BTreeMap<usize, usize> = BTreeMap::new();
        for &position in members {
            *counts.entry(dataset.steps[position].action).or_default() += 1;
        }
        let majority = counts.values().copied().max().unwrap_or(0);
        disowned += members.len() - majority;
        for (k, &a) in members.iter().enumerate() {
            for &b in &members[k + 1..] {
                if dataset.steps[a].action != dataset.steps[b].action {
                    pairs.push((a, b));
                }
            }
        }
    }
    pairs.sort_unstable();
    Conflicts { pairs, disowned }
}
