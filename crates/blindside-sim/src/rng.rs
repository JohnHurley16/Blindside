//! Counter-based, stateless RNG (DETERMINISM.md rule 4).
//!
//! `draw(tick, entity, purpose)` is a pure function of the seed and its three arguments.
//! There is no internal state, so the order in which callers draw cannot affect any
//! result. That removes the most common desync source in a sim with many actors.
//!
//! DEFAULT (awaiting designer): the mix function is the SplitMix64 finaliser, applied one
//! full round per input -- the BLD-20 recommendation. It is explicit integer arithmetic
//! (shifts, xors, wrapping multiplies) with no `std::hash::Hasher`, no `RandomState` and
//! no interior mutability, so the bits are identical on every platform. The golden table
//! in `golden_tables.rs` pins it: change `mix` or `draw_u64` and every recorded replay
//! stops verifying, so that change has to be deliberate.

use crate::{Fx, Tick};

/// What a draw is for. The fourth RNG input, so that two different uses at the same
/// (tick, entity) never share a value.
///
/// Explicit, stable discriminants (DETERMINISM.md rule 7 applied to RNG purposes): a
/// variant is never renumbered and a retired variant's number is never reused, because
/// every replay ever recorded depends on them. Phase 3 appends variants; it does not
/// reorder them. 0 is never assigned, so a zeroed purpose is never a valid one.
#[repr(u16)]
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Purpose {
    /// Phase 0 placeholder world: an agent's x-axis step in its random walk.
    MoveX = 1,
    /// Phase 0 placeholder world: an agent's y-axis step in its random walk.
    MoveY = 2,
    /// Reserved for the `testing` helpers (shuffles, bounded indices). Sim logic never
    /// draws with it; a high number keeps it clear of the purposes Phase 3 will add.
    TestShuffle = 0xFF00,
}

/// Stateless RNG. Cheap to copy; hold one per `Sim`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct DeterministicRng {
    seed: u64,
}

/// SplitMix64 finaliser. Fixed constants, wrapping integer arithmetic only, so the
/// result is bit-identical on every platform.
#[inline]
fn mix(mut z: u64) -> u64 {
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    z ^ (z >> 31)
}

const GOLDEN: u64 = 0x9E37_79B9_7F4A_7C15;

impl DeterministicRng {
    pub fn new(seed: u64) -> DeterministicRng {
        DeterministicRng { seed }
    }

    pub fn seed(&self) -> u64 {
        self.seed
    }

    /// Draw a value uniformly distributed in `[0, 1)` for the given
    /// (tick, entity, purpose) triple.
    ///
    /// Range: `[0, 1)` in `Fx`. The integer part is always zero and the 32 fractional
    /// bits are the raw hash, so every representable value in `[0, 1)` is reachable and
    /// equally likely (`mean_of_draws_is_one_half` checks the distribution is not skewed).
    ///
    /// Counter-based and stateless: calling this twice with the same arguments, in any
    /// order relative to other calls, returns the same value.
    pub fn draw(&self, tick: Tick, entity: u32, purpose: Purpose) -> Fx {
        Fx::from_bits(self.draw_u64(tick, entity, purpose as u16) as i64)
    }

    /// Raw hash of the four inputs, reduced to 32 bits. These become the fractional
    /// bits of the `Fx` returned by `draw`; the integer part is always zero.
    fn draw_u64(&self, tick: Tick, entity: u32, purpose: u16) -> u64 {
        // Feed each input through a full mixing round so that neighbouring ticks,
        // entities and purposes are decorrelated, then keep only the high 32 bits.
        let mut h = mix(self.seed ^ GOLDEN);
        h = mix(h ^ tick.0.wrapping_mul(GOLDEN));
        h = mix(h ^ (((entity as u64) << 16) | purpose as u64).wrapping_mul(GOLDEN));
        h = mix(h);
        // I32F32: value = bits / 2^32. Keeping bits in [0, 2^32) yields [0, 1).
        h >> 32
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::testing;

    #[test]
    fn draw_is_repeatable() {
        let r = DeterministicRng::new(42);
        let a = r.draw(Tick(10), 3, Purpose::MoveX);
        let b = r.draw(Tick(10), 3, Purpose::MoveX);
        assert_eq!(a, b);
    }

    #[test]
    fn draw_is_order_independent_for_1000_draws_in_a_shuffled_order() {
        // BLD-24 property test: 1,000 draws made in an order shuffled by the BLD-25
        // helper equal the same draws made in sorted order. The shuffle itself comes from
        // `draw`, so no rand-family crate is involved even as a dev-dependency.
        let r = DeterministicRng::new(42);
        let inputs: Vec<(Tick, u32, Purpose)> = (0..1000u64)
            .map(|i| {
                let purpose = if i % 2 == 0 {
                    Purpose::MoveX
                } else {
                    Purpose::MoveY
                };
                (Tick(i / 10), (i % 10) as u32 + (i / 100) as u32, purpose)
            })
            .collect();
        let sorted: Vec<Fx> = inputs.iter().map(|&(t, e, p)| r.draw(t, e, p)).collect();

        let order = testing::permutation(&DeterministicRng::new(7), Tick(1), inputs.len());
        assert!(
            order.iter().enumerate().any(|(i, &j)| i != j),
            "not shuffled"
        );
        let mut shuffled: Vec<(usize, Fx)> = Vec::with_capacity(inputs.len());
        for &j in &order {
            let (t, e, p) = inputs[j];
            // Interleave unrelated draws too; they must not disturb anything either.
            let _ = r.draw(Tick(999_999), 999, Purpose::MoveY);
            shuffled.push((j, r.draw(t, e, p)));
        }
        shuffled.sort_by_key(|&(j, _)| j);
        let shuffled: Vec<Fx> = shuffled.into_iter().map(|(_, v)| v).collect();
        assert_eq!(sorted, shuffled);
    }

    #[test]
    fn draw_is_in_unit_interval() {
        let r = DeterministicRng::new(0);
        for t in 0..2000u64 {
            let purpose = if t % 3 == 0 {
                Purpose::MoveX
            } else {
                Purpose::MoveY
            };
            let v = r.draw(Tick(t), t as u32 % 5, purpose);
            assert!(v >= Fx::ZERO, "{v} < 0");
            assert!(v < Fx::ONE, "{v} >= 1");
        }
    }

    #[test]
    fn mean_of_draws_is_one_half() {
        // BLD-24 sanity check, accumulated in Fx (no float anywhere in this crate, tests
        // included). 10,000 values in [0, 1) sum to under 10,000, well inside I32F32.
        let r = DeterministicRng::new(0xDEAD_BEEF);
        let mut sum = Fx::ZERO;
        for i in 0..10_000u64 {
            let purpose = if i % 2 == 0 {
                Purpose::MoveX
            } else {
                Purpose::MoveY
            };
            sum += r.draw(Tick(i / 4), (i % 4) as u32, purpose);
        }
        let mean = sum / 10_000;
        let half = Fx::from_num(1) / 2;
        let tolerance = Fx::from_num(2) / 100; // 0.02, without writing a float literal
        let error = if mean > half {
            mean - half
        } else {
            half - mean
        };
        assert!(
            error < tolerance,
            "mean {mean} is more than {tolerance} from {half}"
        );
    }

    #[test]
    fn inputs_matter() {
        let r = DeterministicRng::new(5);
        let base = r.draw(Tick(1), 1, Purpose::MoveX);
        assert_ne!(base, r.draw(Tick(2), 1, Purpose::MoveX));
        assert_ne!(base, r.draw(Tick(1), 2, Purpose::MoveX));
        assert_ne!(base, r.draw(Tick(1), 1, Purpose::MoveY));
        assert_ne!(
            base,
            DeterministicRng::new(6).draw(Tick(1), 1, Purpose::MoveX)
        );
    }

    #[test]
    fn purpose_discriminants_are_the_documented_numbers() {
        // Renumbering a variant changes every draw made with it. Pin the numbers.
        assert_eq!(Purpose::MoveX as u16, 1);
        assert_eq!(Purpose::MoveY as u16, 2);
        assert_eq!(Purpose::TestShuffle as u16, 0xFF00);
    }
}
