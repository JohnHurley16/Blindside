//! The induction: fit every parameter and find the minimal separator, or say why none
//! exists. `FORMAT.md` states the guarantees this module implements.

use serde::Serialize;

use crate::blocks::{BlockSet, Predicate};
use crate::conflicts::{self, Conflicts};
use crate::dataset::Dataset;
use crate::error::{Error, Result};
use crate::named_trace::NamedTrace;
use crate::params::Params;
use crate::query::{self, Query};
use crate::search::{self, SearchTree, TreeKey};
use crate::step_ref::StepRef;
use crate::thresholds::{self, Candidate};
use crate::tree::{DecisionTree, Node};
use crate::tuning;

/// What `induct induce` prints.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Induction {
    pub consistent: bool,
    pub tree: Option<DecisionTree>,
    pub conflicts: Vec<[StepRef; 2]>,
    pub query: Option<Query>,
}

/// Predicate columns in id order, and each column's rank in that order.
struct Ranking {
    columns_by_id: Vec<usize>,
    rank_of_column: Vec<usize>,
}

impl Ranking {
    fn new(blocks: &BlockSet) -> Self {
        let columns_by_id = blocks.predicate_columns_by_id();
        let mut rank_of_column = vec![0; blocks.predicates.len()];
        for (rank, &column) in columns_by_id.iter().enumerate() {
            rank_of_column[column] = rank;
        }
        Ranking {
            columns_by_id,
            rank_of_column,
        }
    }
}

/// A parametric predicate with recorded raw values, and the thresholds worth trying.
struct Fitted<'a> {
    predicate: &'a Predicate,
    name: &'a str,
    candidates: Vec<Candidate>,
}

/// One parameter assignment tried, with everything the ranking needs.
struct Fit {
    params: Params,
    thetas: Vec<f64>,
    margin: f64,
    dataset: Dataset,
    conflicts: Conflicts,
    tree: Option<(TreeKey, SearchTree)>,
}

pub fn induce(blocks: &BlockSet, traces: &[NamedTrace]) -> Result<Induction> {
    blocks.validate()?;
    for named in traces {
        named.trace.validate(blocks, &named.name)?;
    }
    if traces.iter().all(|t| t.trace.steps.is_empty()) {
        return Err(Error::input("no stops to induce from"));
    }
    if blocks.predicates.len() > tuning::MAX_PREDICATES {
        return Err(Error::input(format!(
            "blocks: {} predicates; the exact search is written for at most {}",
            blocks.predicates.len(),
            tuning::MAX_PREDICATES
        )));
    }

    let ranking = Ranking::new(blocks);
    let (base, fitted) = parametric_candidates(blocks, traces, &ranking);
    let mut best: Option<Fit> = None;
    let mut odometer = vec![0usize; fitted.len()];
    loop {
        let mut params = base.clone();
        let mut thetas = Vec::with_capacity(fitted.len());
        let mut margin = f64::INFINITY;
        for (slot, f) in fitted.iter().enumerate() {
            let candidate = f.candidates[odometer[slot]];
            params.set(&f.predicate.id, f.name, candidate.value);
            thetas.push(candidate.value);
            margin = margin.min(candidate.margin);
        }
        if fitted.is_empty() {
            margin = 0.0;
        }
        let fit = evaluate_fit(blocks, traces, params, thetas, margin, &ranking);
        if best.as_ref().is_none_or(|current| better(&fit, current)) {
            best = Some(fit);
        }
        if !advance(&mut odometer, &fitted) {
            break;
        }
    }
    let best = best.expect("the loop always evaluates at least one assignment");
    Ok(report(blocks, traces, best))
}

/// Every parametric predicate in id order. One with recorded raw values gets candidate
/// thresholds; one with none keeps the first value any trace's params give it, or nothing.
fn parametric_candidates<'a>(
    blocks: &'a BlockSet,
    traces: &[NamedTrace],
    ranking: &Ranking,
) -> (Params, Vec<Fitted<'a>>) {
    let mut base = Params::new();
    let mut fitted = Vec::new();
    for &column in &ranking.columns_by_id {
        let predicate = &blocks.predicates[column];
        let Some(name) = predicate.param.as_deref() else {
            continue;
        };
        let raws: Vec<f64> = traces
            .iter()
            .flat_map(|t| &t.trace.steps)
            .filter_map(|s| s.raw.get(&predicate.id).copied())
            .collect();
        let candidates = thresholds::candidates(&raws);
        if candidates.is_empty() {
            let recorded = traces
                .iter()
                .find_map(|t| t.trace.params.get(&predicate.id, name));
            if let Some(value) = recorded {
                base.set(&predicate.id, name, value);
            }
        } else {
            fitted.push(Fitted {
                predicate,
                name,
                candidates,
            });
        }
    }
    (base, fitted)
}

/// Steps the odometer to the next assignment; false once every one has been tried.
fn advance(odometer: &mut [usize], fitted: &[Fitted<'_>]) -> bool {
    for (slot, digit) in odometer.iter_mut().enumerate().rev() {
        *digit += 1;
        if *digit < fitted[slot].candidates.len() {
            return true;
        }
        *digit = 0;
    }
    false
}

fn evaluate_fit(
    blocks: &BlockSet,
    traces: &[NamedTrace],
    params: Params,
    thetas: Vec<f64>,
    margin: f64,
    ranking: &Ranking,
) -> Fit {
    let dataset = Dataset::build(blocks, traces, &params);
    let conflicts = conflicts::find(&dataset);
    let tree = if conflicts.pairs.is_empty() {
        search::minimal_tree(&dataset.samples(), &ranking.columns_by_id)
            .map(|tree| (tree.key(&ranking.rank_of_column), tree))
    } else {
        None
    };
    Fit {
        params,
        thetas,
        margin,
        dataset,
        conflicts,
        tree,
    }
}

/// Is `a` a better fit than `b`? Consistent beats inconsistent. Among consistent fits: the
/// smaller tree key, then the wider margin, then the smaller thresholds. Among inconsistent
/// fits: fewer disowned stops, then the same two tie-breaks.
fn better(a: &Fit, b: &Fit) -> bool {
    use std::cmp::Ordering::{Equal, Greater, Less};
    let primary = match (&a.tree, &b.tree) {
        (Some(_), None) => Less,
        (None, Some(_)) => Greater,
        (Some((ka, _)), Some((kb, _))) => ka.cmp(kb),
        (None, None) => a.conflicts.disowned.cmp(&b.conflicts.disowned),
    };
    match primary {
        Less => return true,
        Greater => return false,
        Equal => {}
    }
    match b.margin.total_cmp(&a.margin) {
        Less => return true,
        Greater => return false,
        Equal => {}
    }
    let thetas = a
        .thetas
        .iter()
        .zip(&b.thetas)
        .map(|(x, y)| x.total_cmp(y))
        .find(|order| *order != Equal)
        .unwrap_or(Equal);
    thetas == Less
}

fn report(blocks: &BlockSet, traces: &[NamedTrace], fit: Fit) -> Induction {
    let conflicts: Vec<[StepRef; 2]> = fit
        .conflicts
        .pairs
        .iter()
        .map(|&(a, b)| {
            [
                fit.dataset.step_ref(a, traces),
                fit.dataset.step_ref(b, traces),
            ]
        })
        .collect();
    match fit.tree {
        Some((_, tree)) => Induction {
            consistent: true,
            tree: Some(DecisionTree {
                params: fit.params,
                root: to_node(&tree, blocks),
            }),
            conflicts,
            query: None,
        },
        None => {
            let query = query::build(blocks, traces, &fit.dataset, &fit.conflicts);
            Induction {
                consistent: false,
                tree: None,
                conflicts,
                query,
            }
        }
    }
}

fn to_node(tree: &SearchTree, blocks: &BlockSet) -> Node {
    match tree {
        SearchTree::Leaf(action) => Node::action(&blocks.actions[*action].id),
        SearchTree::Split { column, yes, no } => Node::branch(
            &blocks.predicates[*column].id,
            to_node(yes, blocks),
            to_node(no, blocks),
        ),
    }
}
