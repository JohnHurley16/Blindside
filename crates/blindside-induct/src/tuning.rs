//! Every number in the crate, in one place, with the reason next to it.

/// How far past the smallest and largest recorded raw value the two outer threshold
/// candidates sit, as a fraction of the smallest gap between distinct raws. Half a gap
/// gives them the same margin as the tightest midpoint, so they never beat a midpoint on
/// margin unless every gap is that tight.
pub const OUTER_CANDIDATE_GAP_FRACTION: f64 = 0.5;

/// Margin for the outer candidates when only one distinct raw value was ever recorded:
/// there is no gap to take a fraction of, so use one unit of the raw's own scale.
pub const LONE_RAW_MARGIN: f64 = 1.0;

/// Decimals kept when a number is shown to the player (raw readings in the query,
/// thresholds in the tree render). Position sigma is in cells; a thousandth of a cell is
/// below anything the player can act on. Trailing zeros are trimmed.
pub const NUMBER_DECIMALS: usize = 3;

/// The most predicates a block list may carry before `induce` refuses it. The exact
/// search sweeps 2^p predicate subsets, each over a memo of at most 3^p vector subsets;
/// at eight that is 256 sweeps over 6561 entries and finishes in well under a second,
/// and the design's vocabulary is three growing to about six. Past this the search needs
/// a different algorithm, not more patience.
pub const MAX_PREDICATES: usize = 8;
