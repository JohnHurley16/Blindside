//! Where a parametric predicate's threshold may sit, and the one number reported for it.
//!
//! Given every raw reading recorded for the predicate across all traces, the distinct sorted
//! readings cut the line into `n + 1` bands. Every threshold inside one band reads the
//! recorded stops identically, so one candidate per band is all the search has to try. Each
//! band has a margin -- half its width, the distance from its middle to the nearest reading --
//! which is what breaks ties between bands that fit equally well. What the induction finally
//! reports for the chosen band is not its candidate but the roundest number strictly inside
//! it, nearest its middle. `FORMAT.md` states the guarantee.

use crate::tuning;

/// The distinct readings recorded for one parametric predicate, ascending, and how far past
/// the ends the two outer bands reach.
#[derive(Debug, Clone, PartialEq)]
pub struct Grid {
    sorted: Vec<f64>,
    outer: f64,
}

impl Grid {
    /// `None` when nothing finite was recorded, which is the case where there is nothing to
    /// fit and the trace's own parameter is kept instead.
    pub fn new(raws: &[f64]) -> Option<Grid> {
        let mut sorted: Vec<f64> = raws.iter().copied().filter(|r| r.is_finite()).collect();
        sorted.sort_by(f64::total_cmp);
        sorted.dedup();
        if sorted.is_empty() {
            return None;
        }
        let outer = if sorted.len() >= 2 {
            let smallest_gap = sorted
                .windows(2)
                .map(|w| w[1] - w[0])
                .fold(f64::INFINITY, f64::min);
            smallest_gap * tuning::OUTER_BAND_GAP_FRACTION
        } else {
            tuning::LONE_RAW_BAND
        };
        Some(Grid { sorted, outer })
    }

    /// One band below every reading, one between each consecutive pair, one above every
    /// reading. Band `i` is every threshold that reads the first `i` readings as not
    /// exceeding it and the rest as exceeding it.
    pub fn bands(&self) -> usize {
        self.sorted.len() + 1
    }

    /// One threshold from each band, ascending: what the search tries.
    pub fn candidates(&self) -> Vec<f64> {
        (0..self.bands()).map(|band| self.middle(band)).collect()
    }

    /// The open interval of thresholds a band stands for. The outer bands are unbounded in
    /// truth; they are taken to reach a full smallest gap past the end reading -- the candidate sits half a gap past it and the margin is the other half -- which is
    /// as far as the recorded data can justify, so their margin never beats an interior
    /// band's unless every gap is the smallest.
    pub fn interval(&self, band: usize) -> (f64, f64) {
        let n = self.sorted.len();
        let lo = if band == 0 {
            self.sorted[0] - 2.0 * self.outer
        } else {
            self.sorted[band - 1]
        };
        let hi = if band >= n {
            self.sorted[n - 1] + 2.0 * self.outer
        } else {
            self.sorted[band]
        };
        (lo, hi)
    }

    /// Half the band's width: how far its middle sits from the nearest recorded reading.
    pub fn margin(&self, band: usize) -> f64 {
        let (lo, hi) = self.interval(band);
        (hi - lo) / 2.0
    }

    /// The threshold reported for a band: the roundest number strictly inside it, nearest
    /// its middle.
    pub fn value(&self, band: usize) -> f64 {
        let (lo, hi) = self.interval(band);
        round_within(lo, hi)
    }

    fn middle(&self, band: usize) -> f64 {
        let (lo, hi) = self.interval(band);
        lo / 2.0 + hi / 2.0
    }
}

/// The shortest decimal strictly inside `(lo, hi)`; of two equally short, the one nearer the
/// middle, and the smaller of those. `lo < hi` is the caller's business; equal bounds give
/// the bound back.
///
/// This is what keeps the fitted number free of the arithmetic's own noise: a midpoint of two
/// readings carries fifteen digits of it, and every one of them is a claim about the player's
/// demonstration that the demonstration did not make.
pub fn round_within(lo: f64, hi: f64) -> f64 {
    let middle = lo / 2.0 + hi / 2.0;
    // A middle that is finite came from two finite bounds, so no comparison below meets a NaN.
    if !middle.is_finite() || lo >= hi {
        return middle;
    }
    for decimals in 0..=tuning::MAX_THRESHOLD_DECIMALS {
        let scale = 10f64.powi(decimals as i32);
        let nearest = (middle * scale).round();
        let mut best: Option<f64> = None;
        for step in [nearest, nearest - 1.0, nearest + 1.0] {
            let value = step / scale;
            if value <= lo || value >= hi {
                continue;
            }
            let closer = best.is_none_or(|current| {
                let (a, b) = ((value - middle).abs(), (current - middle).abs());
                a < b || (a == b && value < current)
            });
            if closer {
                best = Some(value);
            }
        }
        if let Some(value) = best {
            return value;
        }
    }
    middle
}

#[cfg(test)]
mod tests {
    use super::*;

    fn grid(raws: &[f64]) -> Grid {
        Grid::new(raws).expect("readings were recorded")
    }

    #[test]
    fn one_band_below_between_and_above_every_reading() {
        let g = grid(&[2.0, 1.0, 4.0, 2.0]);
        assert_eq!(g.bands(), 4);
        assert_eq!(g.candidates(), vec![0.5, 1.5, 3.0, 4.5]);
    }

    #[test]
    fn a_band_spans_from_the_reading_below_it_to_the_reading_above() {
        let g = grid(&[1.0, 2.0, 4.0, 8.0]);
        assert_eq!(g.interval(2), (2.0, 4.0));
        assert_eq!(g.interval(3), (4.0, 8.0));
        // The outer bands reach a full smallest gap past the end reading: the candidate sits half
        // a gap past it, and the margin is the other half.
        assert_eq!(g.interval(0), (0.0, 1.0));
        assert_eq!(g.interval(4), (8.0, 9.0));
    }

    #[test]
    fn a_margin_is_half_the_band_and_the_outer_bands_match_the_tightest() {
        let g = grid(&[1.0, 2.0, 4.0, 8.0]);
        let margins: Vec<f64> = (0..g.bands()).map(|band| g.margin(band)).collect();
        assert_eq!(margins, vec![0.5, 0.5, 1.0, 2.0, 0.5]);
    }

    #[test]
    fn a_single_reading_gives_only_the_outer_pair() {
        let g = grid(&[3.0]);
        assert_eq!(g.candidates(), vec![2.0, 4.0]);
        assert_eq!(g.margin(0), 1.0);
        assert_eq!(g.margin(1), 1.0);
    }

    #[test]
    fn nothing_recorded_gives_nothing() {
        assert!(Grid::new(&[]).is_none());
    }

    #[test]
    fn the_reported_value_is_the_roundest_number_the_readings_allow() {
        // The middle of (1.1, 1.2) is 1.15000000000000002 in binary; 1.15 is inside it.
        assert_eq!(round_within(1.1, 1.2), 1.15);
        assert_eq!(round_within(0.0, 1.0), 0.5);
        assert_eq!(round_within(60.6, 61.6), 61.0);
        // A whole number inside beats the exact middle.
        assert_eq!(round_within(0.99, 1.02), 1.0);
        // Ties on shortness and distance go to the smaller.
        assert_eq!(round_within(1.0, 1.9), 1.4);
        // Tiny intervals keep going until a decimal fits.
        let value = round_within(0.012_34, 0.012_36);
        assert!(value > 0.012_34 && value < 0.012_36, "{value}");
        assert_eq!(value, 0.01235);
    }

    #[test]
    fn the_reported_value_is_always_strictly_inside_its_band() {
        let g = grid(&[0.5, 2.31, 2.9, 3.4, 64.0, 99.75]);
        for band in 0..g.bands() {
            let (lo, hi) = g.interval(band);
            let value = g.value(band);
            assert!(lo < value && value < hi, "{value} outside ({lo}, {hi})");
            let candidate = g.candidates()[band];
            assert!(
                lo < candidate && candidate < hi,
                "{candidate} outside ({lo}, {hi})"
            );
        }
    }
}
