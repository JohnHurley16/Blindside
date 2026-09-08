//! The induction: fit every parameter and find the minimal separator, or say why none
//! exists. `FORMAT.md` states the guarantees this module implements.

use std::cmp::Ordering;

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
use crate::thresholds::Grid;
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

/// A parametric predicate with recorded raw readings, and the bands its threshold may sit in.
struct Fitted<'a> {
    predicate: &'a Predicate,
    name: &'a str,
    grid: Grid,
    candidates: Vec<f64>,
}

/// One parameter assignment tried, with everything the ranking needs.
struct Fit {
    params: Params,
    thetas: Vec<f64>,
    /// The narrowest margin across the bands the thresholds came from: how far the tightest
    /// of them sits from the nearest recorded reading. Infinite when nothing is fitted, which
    /// compares equal with itself.
    margin: f64,
    dataset: Dataset,
    conflicts: Conflicts,
    tree: Option<(TreeKey, SearchTree)>,
}

/// Everything one induction is searched over: the block list, the demonstrations, the
/// parameters that are not being fitted, and the bands the ones that are may sit in.
struct Problem<'a> {
    blocks: &'a BlockSet,
    traces: &'a [NamedTrace],
    base: Params,
    fitted: Vec<Fitted<'a>>,
    ranking: Ranking,
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

    let problem = Problem::new(blocks, traces);
    let (best, bands) = problem.best();
    let settled = problem.settle(best, &bands);
    Ok(report(blocks, traces, settled))
}

impl<'a> Problem<'a> {
    /// Every parametric predicate in id order. One with recorded raw readings gets a grid of
    /// bands; one with none keeps the first value any trace's params give it, or nothing.
    fn new(blocks: &'a BlockSet, traces: &'a [NamedTrace]) -> Problem<'a> {
        let ranking = Ranking::new(blocks);
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
            match Grid::new(&raws) {
                Some(grid) => {
                    let candidates = grid.candidates();
                    fitted.push(Fitted {
                        predicate,
                        name,
                        grid,
                        candidates,
                    });
                }
                None => {
                    let recorded = traces
                        .iter()
                        .find_map(|t| t.trace.params.get(&predicate.id, name));
                    if let Some(value) = recorded {
                        base.set(&predicate.id, name, value);
                    }
                }
            }
        }
        Problem {
            blocks,
            traces,
            base,
            fitted,
            ranking,
        }
    }

    /// Tries one threshold from every band of every parametric predicate and keeps the best.
    /// Returns the fit and the band each predicate's threshold came from.
    fn best(&self) -> (Fit, Vec<usize>) {
        let mut best: Option<(Fit, Vec<usize>)> = None;
        let mut odometer = vec![0usize; self.fitted.len()];
        loop {
            let fit = self.fit(&odometer);
            if best
                .as_ref()
                .is_none_or(|(current, _)| better(&fit, current))
            {
                best = Some((fit, odometer.clone()));
            }
            if !self.advance(&mut odometer) {
                break;
            }
        }
        best.expect("the loop always evaluates at least one assignment")
    }

    /// The fit that is reported, from the bands the search chose.
    ///
    /// When the demonstrations are consistent the bands stand: each threshold is reported as
    /// the roundest number strictly inside its band, which reads every recorded stop exactly
    /// as the candidate did. When they are not, the band is chosen again from every band
    /// that ties on the count of stops to disown -- the whole tie set, which need not be
    /// contiguous -- by what the player will be shown: the one whose conflict pairs are
    /// between the closest readings. Should the reported thresholds somehow not tie with
    /// what the search found, the search's own fit is kept.
    fn settle(&self, best: Fit, bands: &[usize]) -> Fit {
        if self.fitted.is_empty() {
            return best;
        }
        let mut bands = bands.to_vec();
        if best.tree.is_none() {
            for slot in 0..self.fitted.len() {
                bands[slot] = self.closest_conflicts(&bands, slot, &best);
            }
        }
        let settled = self.reported(&bands);
        if primary(&settled, &best) == Ordering::Equal {
            settled
        } else {
            best
        }
    }

    /// Of every band of `slot` that fits exactly as well as `best` (the other predicates held
    /// where they are), the one whose conflict pairs are between the closest readings; of
    /// those, the widest; of those, the lowest.
    fn closest_conflicts(&self, bands: &[usize], slot: usize, best: &Fit) -> usize {
        let grid = &self.fitted[slot].grid;
        let mut chosen: Option<(usize, Vec<f64>)> = None;
        for band in 0..grid.bands() {
            let mut moved = bands.to_vec();
            moved[slot] = band;
            let fit = self.fit(&moved);
            if primary(&fit, best) != Ordering::Equal {
                continue;
            }
            let gaps = self.gaps(&fit, slot);
            let closer = chosen.as_ref().is_none_or(|(current, current_gaps)| {
                match widest_first(&gaps, current_gaps) {
                    Ordering::Less => true,
                    Ordering::Greater => false,
                    Ordering::Equal => grid.margin(band) > grid.margin(*current),
                }
            });
            if closer {
                chosen = Some((band, gaps));
            }
        }
        chosen
            .map(|(band, _)| band)
            .expect("the band the search chose ties with itself")
    }

    /// How far apart, in `slot`'s readings, the two stops of every conflict pair under `fit`
    /// are, widest first. A stop with no reading for the predicate is at no distance from
    /// anything: its reading did not enter into the pair.
    fn gaps(&self, fit: &Fit, slot: usize) -> Vec<f64> {
        let id = &self.fitted[slot].predicate.id;
        let reading = |position: usize| {
            let step = &fit.dataset.steps[position];
            self.traces[step.trace_pos].trace.steps[step.index]
                .raw
                .get(id)
                .copied()
        };
        let mut gaps: Vec<f64> = fit
            .conflicts
            .pairs
            .iter()
            .map(|&(a, b)| match (reading(a), reading(b)) {
                (Some(x), Some(y)) => (x - y).abs(),
                _ => 0.0,
            })
            .collect();
        gaps.sort_by(|a, b| b.total_cmp(a));
        gaps
    }

    /// The fit at one threshold from each chosen band: what the search compares.
    fn fit(&self, bands: &[usize]) -> Fit {
        let thetas = self
            .fitted
            .iter()
            .zip(bands)
            .map(|(f, &band)| f.candidates[band])
            .collect();
        self.fit_at(thetas, self.margin(bands))
    }

    /// The fit at the threshold reported for each chosen band: the roundest number strictly
    /// inside it.
    fn reported(&self, bands: &[usize]) -> Fit {
        let thetas = self
            .fitted
            .iter()
            .zip(bands)
            .map(|(f, &band)| f.grid.value(band))
            .collect();
        self.fit_at(thetas, self.margin(bands))
    }

    /// The narrowest margin across the chosen bands.
    fn margin(&self, bands: &[usize]) -> f64 {
        self.fitted
            .iter()
            .zip(bands)
            .map(|(f, &band)| f.grid.margin(band))
            .fold(f64::INFINITY, f64::min)
    }

    /// Steps the odometer to the next assignment; false once every one has been tried.
    fn advance(&self, odometer: &mut [usize]) -> bool {
        for (slot, digit) in odometer.iter_mut().enumerate().rev() {
            *digit += 1;
            if *digit < self.fitted[slot].candidates.len() {
                return true;
            }
            *digit = 0;
        }
        false
    }

    fn fit_at(&self, thetas: Vec<f64>, margin: f64) -> Fit {
        let mut params = self.base.clone();
        for (f, &theta) in self.fitted.iter().zip(&thetas) {
            params.set(&f.predicate.id, f.name, theta);
        }
        let dataset = Dataset::build(self.blocks, self.traces, &params);
        let conflicts = conflicts::find(&dataset);
        let tree = if conflicts.pairs.is_empty() {
            search::minimal_tree(&dataset.samples(), &self.ranking.columns_by_id)
                .map(|tree| (tree.key(&self.ranking.rank_of_column), tree))
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
}

/// How well two fits separate the demonstrations, before any tie-break: a consistent fit
/// beats an inconsistent one, a smaller tree beats a larger one, and among inconsistent fits
/// the one needing fewer stops disowned wins.
fn primary(a: &Fit, b: &Fit) -> Ordering {
    match (&a.tree, &b.tree) {
        (Some(_), None) => Ordering::Less,
        (None, Some(_)) => Ordering::Greater,
        (Some((ka, _)), Some((kb, _))) => ka.cmp(kb),
        (None, None) => a.conflicts.disowned.cmp(&b.conflicts.disowned),
    }
}

/// Is `a` a better fit than `b`? By `primary`; then the wider margin, so of two bands that
/// fit equally well the wider wins; then the smaller thresholds.
fn better(a: &Fit, b: &Fit) -> bool {
    match primary(a, b) {
        Ordering::Less => return true,
        Ordering::Greater => return false,
        Ordering::Equal => {}
    }
    match b.margin.total_cmp(&a.margin) {
        Ordering::Less => return true,
        Ordering::Greater => return false,
        Ordering::Equal => {}
    }
    a.thetas
        .iter()
        .zip(&b.thetas)
        .map(|(x, y)| x.total_cmp(y))
        .find(|order| *order != Ordering::Equal)
        .unwrap_or(Ordering::Equal)
        == Ordering::Less
}

/// Which of two gap lists, each widest first, is between the closer readings: the one whose
/// widest gap is narrower, then whose next is, and so on; a list that runs out first is the
/// closer, since it has fewer pairs and every pair it has compared equal.
fn widest_first(a: &[f64], b: &[f64]) -> Ordering {
    a.iter()
        .zip(b)
        .map(|(x, y)| x.total_cmp(y))
        .find(|order| *order != Ordering::Equal)
        .unwrap_or(a.len().cmp(&b.len()))
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
