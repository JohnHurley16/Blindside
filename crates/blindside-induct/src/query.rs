//! The active-learning question: when no separator exists, the two stops whose
//! disagreement is worth asking about, rendered side by side with labels only.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::blocks::BlockSet;
use crate::conflicts::Conflicts;
use crate::dataset::Dataset;
use crate::named_trace::NamedTrace;
use crate::render::display_number;
use crate::step_ref::StepRef;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Query {
    pub pair: [StepRef; 2],
    pub text: String,
}

/// Action counts within one vector class: action index -> how many stops chose it.
type ActionCounts = BTreeMap<usize, usize>;

/// Picks the conflicting pair whose resolution removes the most conflicts and renders it.
/// Resolving a pair means one of its two stops takes the other's action; a pair's score
/// is the larger net reduction of its two resolutions. Earliest pair on a tie. `None`
/// without conflicts.
pub fn build(
    blocks: &BlockSet,
    traces: &[NamedTrace],
    dataset: &Dataset,
    conflicts: &Conflicts,
) -> Option<Query> {
    let mut classes: BTreeMap<&[bool], ActionCounts> = BTreeMap::new();
    for step in &dataset.steps {
        *classes
            .entry(step.vector.as_slice())
            .or_default()
            .entry(step.action)
            .or_default() += 1;
    }
    let mut chosen: Option<((usize, usize), isize)> = None;
    for &(a, b) in &conflicts.pairs {
        let class = &classes[dataset.steps[a].vector.as_slice()];
        let (x, y) = (dataset.steps[a].action, dataset.steps[b].action);
        let score = removed_by(class, x, y).max(removed_by(class, y, x));
        if chosen.is_none_or(|(_, best)| score > best) {
            chosen = Some(((a, b), score));
        }
    }
    let ((a, b), _) = chosen?;
    Some(Query {
        pair: [dataset.step_ref(a, traces), dataset.step_ref(b, traces)],
        text: text(blocks, traces, dataset, a, b),
    })
}

/// Net conflicts that disappear when one stop of a class moves from action `from` to
/// `to`. Before, the stop conflicted with every other stop not choosing `from`; after,
/// with every other stop not choosing `to`. The difference is `count(to) - count(from) + 1`,
/// negative when the move creates more conflicts than it removes.
fn removed_by(class: &ActionCounts, from: usize, to: usize) -> isize {
    let count = |action: usize| class.get(&action).copied().unwrap_or(0) as isize;
    count(to) - count(from) + 1
}

fn text(blocks: &BlockSet, traces: &[NamedTrace], dataset: &Dataset, a: usize, b: usize) -> String {
    let left = describe(blocks, traces, dataset, a);
    let right = describe(blocks, traces, dataset, b);
    let width = left
        .iter()
        .map(|line| line.chars().count())
        .max()
        .unwrap_or(0);
    let mut out = vec![
        "These two stops read the same, but you chose differently.".to_string(),
        String::new(),
    ];
    for (l, r) in left.iter().zip(&right) {
        out.push(format!("{l:<width$}   {r}"));
    }
    out.push(String::new());
    out.push("Which one would you do differently?".to_string());
    out.join("\n")
}

/// The stop as the player saw it: where it was; every predicate in the block list with its
/// value at that stop, the raw reading in brackets for a parametric one, or a note when the
/// block did not exist in that run; and the choice made.
fn describe(
    blocks: &BlockSet,
    traces: &[NamedTrace],
    dataset: &Dataset,
    position: usize,
) -> Vec<String> {
    let entry = &dataset.steps[position];
    let named = &traces[entry.trace_pos];
    let step = &named.trace.steps[entry.index];
    let mut lines = vec![format!(
        "stop {} of {} (junction {}, tick {})",
        entry.index, named.name, step.junction, step.tick
    )];
    for (column, predicate) in blocks.predicates.iter().enumerate() {
        let label = &predicate.label;
        let exists =
            step.predicates.contains_key(&predicate.id) || step.raw.contains_key(&predicate.id);
        let line = if exists {
            let value = if entry.vector[column] { "yes" } else { "no" };
            match step.raw.get(&predicate.id) {
                Some(raw) => format!("{label}: {value} ({})", display_number(*raw)),
                None => format!("{label}: {value}"),
            }
        } else {
            format!("{label}: not in this run")
        };
        lines.push(line);
    }
    lines.push(format!("you chose: {}", blocks.action_label(&step.action)));
    lines
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn moving_the_odd_one_out_removes_its_conflicts_and_creates_none() {
        // Three stops chose action 0, one chose action 1.
        let class: ActionCounts = BTreeMap::from([(0, 3), (1, 1)]);
        assert_eq!(removed_by(&class, 1, 0), 3);
        assert_eq!(removed_by(&class, 0, 1), -1);
    }

    #[test]
    fn an_even_split_removes_one_either_way() {
        let class: ActionCounts = BTreeMap::from([(0, 1), (1, 1)]);
        assert_eq!(removed_by(&class, 0, 1), 1);
        assert_eq!(removed_by(&class, 1, 0), 1);
    }
}
