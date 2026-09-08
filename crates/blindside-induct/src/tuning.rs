//! Every number in the crate, in one place, with the reason next to it.

/// How far past the smallest and largest recorded raw reading the two outer bands are taken
/// to reach, as a fraction of the smallest gap between distinct readings. Those two bands are
/// unbounded in truth -- nothing was ever seen out there -- so the threshold reported from
/// one of them has to stop somewhere, and half a gap is the closest thing the data has to a
/// scale of its own.
pub const OUTER_BAND_GAP_FRACTION: f64 = 0.5;

/// The same reach when only one distinct reading was ever recorded: there is no gap to take a
/// fraction of, so use one unit of the reading's own scale.
pub const LONE_RAW_BAND: f64 = 1.0;

/// Decimals kept when a number is shown to the player (raw readings in the query, thresholds
/// in the tree render). Position sigma is in cells; a thousandth of a cell is below anything
/// the player can act on. Trailing zeros are trimmed.
pub const NUMBER_DECIMALS: usize = 3;

/// How far the search for a round threshold will go before it gives up and reports the exact
/// middle of the interval. It stops at the first decimal place that has a number inside, so
/// this only binds when two recorded readings are within 1e-15 of each other; past that the
/// difference between the two answers is below what a f64 can carry anyway.
pub const MAX_THRESHOLD_DECIMALS: usize = 15;

/// The most predicates a block list may carry before `induce` refuses it. The exact
/// search sweeps 2^p predicate subsets, each over a memo of at most 3^p vector subsets;
/// at eight that is 256 sweeps over 6561 entries and finishes in well under a second,
/// and the design's vocabulary is three growing to about six. Past this the search needs
/// a different algorithm, not more patience.
pub const MAX_PREDICATES: usize = 8;
