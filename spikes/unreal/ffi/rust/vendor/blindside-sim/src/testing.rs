//! Test helpers built on the stateless RNG (BLD-25).
//!
//! Tests that need a "random" order or index -- the shuffled-draw property test, later
//! the VM's random programs and the fixed-point differential tests -- get it from
//! `DeterministicRng::draw`, so no rand-family crate is needed even as a dev-dependency
//! and every such test is reproducible bit-for-bit on every platform (DETERMINISM.md
//! rule 4 is applied to dev-dependencies too: the lint's dependency check fails on one).
//!
//! Compiled for this crate's own tests and, for tooling, under the `diagnostics` feature.
//! Nothing here is sim logic and nothing in the sim calls it.

use crate::{DeterministicRng, Purpose, Tick};

/// A draw reduced to an index in `0..bound`. `bound` must be non-zero.
///
/// The draw's 32 fractional bits are scaled by `bound` and the integer part taken, which
/// is uniform over `0..bound` up to a bias of `bound / 2^32` (nil for any test-sized
/// `bound`). The purpose is always `Purpose::TestShuffle`; vary `tick` and `entity`.
pub fn bounded_index(rng: &DeterministicRng, tick: Tick, entity: u32, bound: usize) -> usize {
    assert!(bound > 0, "bounded_index: bound must be non-zero");
    let bits = rng.draw(tick, entity, Purpose::TestShuffle).to_bits() as u64;
    debug_assert!(bits < (1u64 << 32), "draw is in [0, 1): 32 fractional bits");
    ((bits as u128 * bound as u128) >> 32) as usize
}

/// A permutation of `0..n`, by Fisher-Yates over draws at `tick`. The same `(rng, tick,
/// n)` always yields the same permutation; different ticks yield different ones.
pub fn permutation(rng: &DeterministicRng, tick: Tick, n: usize) -> Vec<usize> {
    let mut order: Vec<usize> = (0..n).collect();
    shuffle(rng, tick, &mut order);
    order
}

/// Shuffle `items` in place, Fisher-Yates, entity `i` drawing the swap partner for
/// position `i`.
pub fn shuffle<T>(rng: &DeterministicRng, tick: Tick, items: &mut [T]) {
    for i in (1..items.len()).rev() {
        let j = bounded_index(rng, tick, i as u32, i + 1);
        items.swap(i, j);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bounded_index_stays_in_bounds_and_covers_the_range() {
        let rng = DeterministicRng::new(3);
        let mut seen = [false; 7];
        for e in 0..500u32 {
            let i = bounded_index(&rng, Tick(1), e, 7);
            assert!(i < 7);
            seen[i] = true;
        }
        assert!(seen.iter().all(|&s| s), "{seen:?}");
        assert_eq!(bounded_index(&rng, Tick(1), 9, 1), 0);
    }

    #[test]
    fn permutation_is_a_permutation_and_is_repeatable() {
        let rng = DeterministicRng::new(11);
        let p = permutation(&rng, Tick(5), 100);
        let mut sorted = p.clone();
        sorted.sort_unstable();
        assert_eq!(sorted, (0..100).collect::<Vec<_>>());
        assert_eq!(p, permutation(&rng, Tick(5), 100));
        assert_ne!(p, permutation(&rng, Tick(6), 100));
        assert_ne!(p, permutation(&DeterministicRng::new(12), Tick(5), 100));
        assert!(p.iter().enumerate().any(|(i, &j)| i != j));
        assert!(permutation(&rng, Tick(1), 0).is_empty());
        assert_eq!(permutation(&rng, Tick(1), 1), vec![0]);
    }
}
