//! Counter-based, stateless RNG (DETERMINISM.md rule 4).
//!
//! `draw(tick, entity, purpose)` is a pure function of the seed and its three arguments.
//! There is no internal state, so the order in which callers draw cannot affect any
//! result. That removes the most common desync source in a sim with many actors.

use crate::{Fx, Tick};

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
    /// Counter-based and stateless: calling this twice with the same arguments, in any
    /// order relative to other calls, returns the same value.
    pub fn draw(&self, tick: Tick, entity: u32, purpose: u16) -> Fx {
        Fx::from_bits(self.draw_u64(tick, entity, purpose) as i64)
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

    #[test]
    fn draw_is_repeatable() {
        let r = DeterministicRng::new(42);
        let a = r.draw(Tick(10), 3, 1);
        let b = r.draw(Tick(10), 3, 1);
        assert_eq!(a, b);
    }

    #[test]
    fn draw_is_order_independent() {
        let r = DeterministicRng::new(42);
        let triples = [
            (Tick(1), 1, 0),
            (Tick(1), 2, 0),
            (Tick(2), 1, 0),
            (Tick(2), 1, 7),
        ];

        let forward: Vec<Fx> = triples.iter().map(|&(t, e, p)| r.draw(t, e, p)).collect();
        let reverse: Vec<Fx> = triples
            .iter()
            .rev()
            .map(|&(t, e, p)| r.draw(t, e, p))
            .collect();
        let reverse: Vec<Fx> = reverse.into_iter().rev().collect();
        assert_eq!(forward, reverse);

        // Interleaving other draws between them changes nothing either.
        let mut interleaved = Vec::new();
        for &(t, e, p) in &triples {
            let _ = r.draw(Tick(999), 999, 999);
            interleaved.push(r.draw(t, e, p));
            let _ = r.draw(Tick(0), 0, 0);
        }
        assert_eq!(forward, interleaved);
    }

    #[test]
    fn draw_is_in_unit_interval() {
        let r = DeterministicRng::new(0);
        for t in 0..2000u64 {
            let v = r.draw(Tick(t), t as u32 % 5, (t % 3) as u16);
            assert!(v >= Fx::ZERO, "{v} < 0");
            assert!(v < Fx::ONE, "{v} >= 1");
        }
    }

    #[test]
    fn inputs_matter() {
        let r = DeterministicRng::new(5);
        let base = r.draw(Tick(1), 1, 1);
        assert_ne!(base, r.draw(Tick(2), 1, 1));
        assert_ne!(base, r.draw(Tick(1), 2, 1));
        assert_ne!(base, r.draw(Tick(1), 1, 2));
        assert_ne!(base, DeterministicRng::new(6).draw(Tick(1), 1, 1));
    }

    #[test]
    fn known_answers() {
        // Pin the mixing function so that an accidental change to it shows up here
        // before it shows up as a cross-version replay mismatch.
        let r = DeterministicRng::new(0);
        assert_eq!(r.draw_u64(Tick(0), 0, 0), KNOWN_SEED0_T0_E0_P0);
        let r = DeterministicRng::new(0xDEAD_BEEF);
        assert_eq!(r.draw_u64(Tick(1000), 2, 2), KNOWN_SEEDDB_T1000_E2_P2);
    }

    // Recorded from the first run of this test; any change to `mix`/`draw_u64` breaks
    // every existing replay and must be deliberate.
    const KNOWN_SEED0_T0_E0_P0: u64 = 425_174_880;
    const KNOWN_SEEDDB_T1000_E2_P2: u64 = 2_040_947_845;
}
