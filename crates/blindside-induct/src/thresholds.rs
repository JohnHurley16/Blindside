//! Candidate thresholds for one parametric predicate.
//!
//! Given every raw value recorded for the predicate across all traces, the candidates are
//! the midpoints between consecutive distinct sorted values, plus one below the minimum and
//! one above the maximum. Each candidate carries its margin: the distance to the nearest
//! recorded value.

use crate::tuning;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Candidate {
    pub value: f64,
    pub margin: f64,
}

pub fn candidates(raws: &[f64]) -> Vec<Candidate> {
    let mut sorted: Vec<f64> = raws.iter().copied().filter(|r| r.is_finite()).collect();
    sorted.sort_by(f64::total_cmp);
    sorted.dedup();
    let (Some(&min), Some(&max)) = (sorted.first(), sorted.last()) else {
        return Vec::new();
    };
    let smallest_gap = sorted
        .windows(2)
        .map(|w| w[1] - w[0])
        .fold(f64::INFINITY, f64::min);
    let outer = if sorted.len() >= 2 {
        smallest_gap * tuning::OUTER_CANDIDATE_GAP_FRACTION
    } else {
        tuning::LONE_RAW_MARGIN
    };
    let mut out = vec![Candidate {
        value: min - outer,
        margin: outer,
    }];
    for w in sorted.windows(2) {
        let half = (w[1] - w[0]) / 2.0;
        out.push(Candidate {
            value: w[0] + half,
            margin: half,
        });
    }
    out.push(Candidate {
        value: max + outer,
        margin: outer,
    });
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn midpoints_and_two_outer_candidates() {
        let c = candidates(&[2.0, 1.0, 4.0, 2.0]);
        let values: Vec<f64> = c.iter().map(|c| c.value).collect();
        assert_eq!(values, vec![0.5, 1.5, 3.0, 4.5]);
        let margins: Vec<f64> = c.iter().map(|c| c.margin).collect();
        assert_eq!(margins, vec![0.5, 0.5, 1.0, 0.5]);
    }

    #[test]
    fn a_single_value_gives_only_the_outer_pair() {
        let values: Vec<f64> = candidates(&[3.0]).iter().map(|c| c.value).collect();
        assert_eq!(values, vec![2.0, 4.0]);
    }

    #[test]
    fn nothing_recorded_gives_nothing() {
        assert!(candidates(&[]).is_empty());
    }
}
