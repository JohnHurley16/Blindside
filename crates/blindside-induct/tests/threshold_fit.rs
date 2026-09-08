//! How well the fitted threshold recovers the one that generated the demonstrations.
//!
//! The threshold is the only number the induction invents, and it is invented from a handful
//! of stops, so it needs measuring rather than asserting. This is a sweep: a known tree at
//! many true thresholds, demonstrations walked from it in the corridor `phase2/tuning.py`
//! describes, and for each run two numbers -- how far the fitted threshold landed from the
//! true one, and how often the induced tree and the generating tree agree on stops the
//! induction never saw.
//!
//! A run only says anything about the fit when its demonstrations bracket the true threshold
//! from both sides; the tables count those separately and average the error over them.
//!
//! Run it with `cargo test --test threshold_fit -- --nocapture` to see the tables.

mod common;

use blindside_induct::blocks::{BlockSet, Predicate};
use blindside_induct::induce::induce;
use blindside_induct::step_input::StepInput;
use blindside_induct::tree::DecisionTree;

/// True thresholds across the range Phase 2 produces. `phase2/tuning.py` fixes the reference
/// tree's theta at 64 cells of position sigma and sweeps 24 to 220: below about 48 the agent
/// runs out of budget, above about 100 it gets lost, and a player's fitted theta is expected
/// to sit near the lower, forgiving edge. Sigma itself runs from 0.5 just after a shaft fix
/// to about 100 at 380 cells out, so these are the thresholds a demonstration can teach.
///
/// None of them is a round number, on purpose. The fit reports the roundest number its band
/// allows, so a sweep over round thresholds (the first version of this one used 16, 24, 32,
/// ...) measures that preference rather than the fit: whenever the band held the true value
/// the error was exactly zero.
const THETAS: [f64; 10] = [16.7, 23.3, 31.4, 40.9, 47.1, 55.6, 63.8, 79.3, 101.7, 119.2];
/// Demonstrations per run. Phase 2 records three.
const DEMOS: [usize; 3] = [2, 3, 5];
/// Stops per demonstration.
const STOPS: [usize; 3] = [12, 20, 32];
const SEEDS: [u64; 3] = [1, 2, 3];
/// Unseen stops each run is scored on.
const UNSEEN: usize = 200;

struct Run {
    theta: f64,
    demos: usize,
    stops: usize,
    /// Did the demonstrations bracket the true threshold from both sides?
    informative: bool,
    /// |fitted - true|, when the induced tree tests the parametric predicate at all.
    error: Option<f64>,
    /// How wide a bracket the demonstrations left the threshold.
    bracket: Option<f64>,
    /// Where in that bracket the fitted threshold landed: 0 its bottom edge, 1 its top.
    position: Option<f64>,
    /// Unseen stops where the induced tree and the generating tree disagree.
    wrong: usize,
    /// The same over the unseen stops the threshold is responsible for: the ones the other
    /// blocks do not already decide.
    wrong_on_threshold: usize,
    on_threshold: usize,
    /// What the same tree would have got wrong with the threshold put at the exact middle of
    /// the bracket: the best any rule that reads only the demonstrations can do.
    wrong_at_ceiling: usize,
    wrong_on_threshold_at_ceiling: usize,
}

fn one(
    blocks: &BlockSet,
    base: &DecisionTree,
    parametric: &Predicate,
    theta: f64,
    demos: usize,
    stops: usize,
    seed: u64,
) -> Run {
    let reference = common::tree_with_theta(blocks, base, theta);
    let traces = common::corridor_traces(blocks, &reference, demos, stops, seed * 1_000_003);
    let induced = induce(blocks, &traces)
        .expect("valid input")
        .tree
        .expect("a demonstration of one tree cannot contradict itself");

    let name = parametric.param.as_deref().expect("a parametric predicate");
    let (lo, hi) = common::constraining_bracket(blocks, &reference, &traces, &parametric.id);
    let informative = lo.is_finite() && hi.is_finite();
    let fitted = induced
        .predicates_used()
        .contains(&parametric.id)
        .then(|| induced.params.get(&parametric.id, name))
        .flatten();
    let error = fitted.map(|value| (value - theta).abs());
    let position = match (fitted, informative) {
        (Some(value), true) => Some((value - lo) / (hi - lo)),
        _ => None,
    };

    let unseen = common::corridor_stops(blocks, &reference, UNSEEN, seed.wrapping_add(90_001));
    let wrong = unseen
        .iter()
        .filter(|(input, action)| induced.decide(input, blocks) != action)
        .count();
    let responsible: Vec<&(StepInput, String)> = unseen
        .iter()
        .filter(|(input, _)| common::decides(blocks, &reference, input, &parametric.id))
        .collect();

    let mut ceiling = induced.clone();
    if informative {
        ceiling
            .params
            .set(&parametric.id, name, lo / 2.0 + hi / 2.0);
    }
    Run {
        theta,
        demos,
        stops,
        informative,
        error,
        bracket: informative.then_some(hi - lo),
        position,
        wrong,
        wrong_on_threshold: responsible
            .iter()
            .filter(|(input, action)| induced.decide(input, blocks) != action)
            .count(),
        on_threshold: responsible.len(),
        wrong_at_ceiling: unseen
            .iter()
            .filter(|(input, action)| ceiling.decide(input, blocks) != action)
            .count(),
        wrong_on_threshold_at_ceiling: responsible
            .iter()
            .filter(|(input, action)| ceiling.decide(input, blocks) != action)
            .count(),
    }
}

fn sweep() -> Vec<Run> {
    let blocks = common::blocks();
    let base = common::example_tree();
    let parametric = blocks
        .predicates
        .iter()
        .find(|p| p.param.is_some())
        .expect("the block list has a parametric predicate")
        .clone();
    let mut runs = Vec::new();
    for theta in THETAS {
        for demos in DEMOS {
            for stops in STOPS {
                for seed in SEEDS {
                    runs.push(one(&blocks, &base, &parametric, theta, demos, stops, seed));
                }
            }
        }
    }
    runs
}

struct Summary {
    runs: usize,
    informative: usize,
    mean_abs: f64,
    mean_rel: f64,
    accuracy: f64,
    wrong: usize,
    /// Accuracy over only the unseen stops the threshold is responsible for.
    threshold_accuracy: f64,
    wrong_on_threshold: usize,
    on_threshold: usize,
    mean_bracket: f64,
    /// Mean distance from the middle of the bracket, as a fraction of its width.
    off_centre: f64,
    ceiling_accuracy: f64,
    ceiling_threshold_accuracy: f64,
}

/// Error is averaged over the runs that actually taught a threshold; accuracy over all of
/// them, since a run that taught nothing still has to decide.
fn summarise(runs: &[&Run]) -> Summary {
    let fitted: Vec<&&Run> = runs
        .iter()
        .filter(|r| r.informative && r.error.is_some())
        .collect();
    let n = fitted.len().max(1) as f64;
    let wrong: usize = runs.iter().map(|r| r.wrong).sum();
    let placed: Vec<&&Run> = runs.iter().filter(|r| r.position.is_some()).collect();
    let m = placed.len().max(1) as f64;
    let wrong_on_threshold: usize = runs.iter().map(|r| r.wrong_on_threshold).sum();
    let on_threshold: usize = runs.iter().map(|r| r.on_threshold).sum();
    Summary {
        runs: runs.len(),
        informative: runs.iter().filter(|r| r.informative).count(),
        mean_abs: fitted.iter().map(|r| r.error.unwrap()).sum::<f64>() / n,
        mean_rel: fitted
            .iter()
            .map(|r| r.error.unwrap() / r.theta)
            .sum::<f64>()
            / n,
        accuracy: 1.0 - wrong as f64 / (runs.len() * UNSEEN) as f64,
        wrong,
        threshold_accuracy: 1.0 - wrong_on_threshold as f64 / on_threshold.max(1) as f64,
        wrong_on_threshold,
        on_threshold,
        mean_bracket: placed.iter().filter_map(|r| r.bracket).sum::<f64>() / m,
        off_centre: placed
            .iter()
            .filter_map(|r| r.position)
            .map(|p| (p - 0.5).abs())
            .sum::<f64>()
            / m,
        ceiling_accuracy: 1.0
            - runs.iter().map(|r| r.wrong_at_ceiling).sum::<usize>() as f64
                / (runs.len() * UNSEEN) as f64,
        ceiling_threshold_accuracy: 1.0
            - runs
                .iter()
                .map(|r| r.wrong_on_threshold_at_ceiling)
                .sum::<usize>() as f64
                / on_threshold.max(1) as f64,
    }
}

#[test]
fn the_fitted_threshold_lands_near_the_one_that_generated_the_demonstrations() {
    let runs = sweep();
    println!("\n{} runs, {UNSEEN} unseen stops each\n", runs.len());

    println!("  true theta | runs | informative | mean |fit-true| | mean rel err | unseen accuracy | threshold decisions");
    println!("  -----------+------+-------------+----------------+--------------+-----------------+--------------------");
    for theta in THETAS {
        let slice: Vec<&Run> = runs.iter().filter(|r| r.theta == theta).collect();
        let s = summarise(&slice);
        println!(
            "  {theta:>10.0} | {:>4} | {:>11} | {:>14.3} | {:>11.2}% | {:>14.2}% | {:>8.2}% ({}/{})",
            s.runs,
            s.informative,
            s.mean_abs,
            s.mean_rel * 100.0,
            s.accuracy * 100.0,
            s.threshold_accuracy * 100.0,
            s.wrong_on_threshold,
            s.on_threshold
        );
    }

    println!(
        "\n  demos | stops | runs | informative | mean |fit-true| | mean rel err | unseen accuracy"
    );
    println!(
        "  ------+-------+------+-------------+----------------+--------------+----------------"
    );
    for demos in DEMOS {
        for stops in STOPS {
            let slice: Vec<&Run> = runs
                .iter()
                .filter(|r| r.demos == demos && r.stops == stops)
                .collect();
            let s = summarise(&slice);
            println!(
                "  {demos:>5} | {stops:>5} | {:>4} | {:>11} | {:>14.3} | {:>11.2}% | {:>14.2}%",
                s.runs,
                s.informative,
                s.mean_abs,
                s.mean_rel * 100.0,
                s.accuracy * 100.0
            );
        }
    }

    println!(
        "\n  where in the bracket the fitted threshold landed (0 its bottom edge, 1 its top):"
    );
    let placed: Vec<f64> = runs.iter().filter_map(|r| r.position).collect();
    println!(
        "    outside  {:>4}  (below the bottom edge or above the top)",
        placed
            .iter()
            .filter(|&&p| !(0.0..=1.0).contains(&p))
            .count()
    );
    for k in 0..5 {
        let (lo, hi) = (k as f64 / 5.0, (k + 1) as f64 / 5.0);
        let n = placed
            .iter()
            .filter(|&&p| p >= lo && (p < hi || (k == 4 && p <= hi)))
            .count();
        println!("    {lo:.1}-{hi:.1} {n:>4}  {}", "#".repeat(n / 2));
    }

    let all: Vec<&Run> = runs.iter().collect();
    let s = summarise(&all);
    println!(
        "\n  ALL: {} runs, {} informative\n\
         \x20      mean |fit-true| {:.3}, mean rel err {:.2}%\n\
         \x20      unseen accuracy {:.2}% ({} wrong of {})\n\
         \x20      threshold-decision accuracy {:.2}% ({} wrong of {})\n\
         \x20      mean bracket {:.3} wide, fitted value {:.3} of a bracket from its middle\n\
         \x20      ceiling (threshold at the exact middle of the bracket):\n\
         \x20        unseen accuracy {:.2}%, threshold-decision accuracy {:.2}%\n",
        s.runs,
        s.informative,
        s.mean_abs,
        s.mean_rel * 100.0,
        s.accuracy * 100.0,
        s.wrong,
        s.runs * UNSEEN,
        s.threshold_accuracy * 100.0,
        s.wrong_on_threshold,
        s.on_threshold,
        s.mean_bracket,
        s.off_centre,
        s.ceiling_accuracy * 100.0,
        s.ceiling_threshold_accuracy * 100.0
    );

    assert!(runs.len() >= 200, "the sweep must be a sweep");
    assert!(
        s.informative * 2 >= s.runs,
        "most runs must actually teach a threshold, or the sweep measures nothing"
    );
    assert_eq!(
        placed
            .iter()
            .filter(|&&p| !(0.0..=1.0).contains(&p))
            .count(),
        0,
        "a fitted threshold outside the bracket its own demonstrations left it"
    );
    // The rule this pins: the search keeps the widest of the bands that fit equally well and
    // reports the roundest number inside it. On these thresholds that lands 0.158 of a bracket
    // from its middle. The guard is there for a fit that hugs an edge of the bracket, which
    // scores 0.5 here by definition (the true threshold sits anywhere in the bracket); it is
    // not there to tell this rule from one that reports the middle of the whole bracket, which
    // measures within noise of it on unseen decisions.
    assert!(
        s.off_centre < 0.20,
        "the fitted threshold sits {:.3} of a bracket from its middle",
        s.off_centre
    );
    // And what is left is the width of the bracket, not the choice of a point inside it: no
    // rule reading only these demonstrations can beat the ceiling by more than this.
    assert!(
        s.ceiling_threshold_accuracy - s.threshold_accuracy < 0.002,
        "threshold-decision accuracy {:.4} against a ceiling of {:.4}",
        s.threshold_accuracy,
        s.ceiling_threshold_accuracy
    );
}
