//! `harness golden`: generate `crates/blindside-sim/src/golden_tables.rs` (BLD-25).
//!
//! The sim may not use floats, so any reference value that needs one is produced here.
//! As it turns out none does yet: every input is an integer or an explicit bit pattern
//! and every output is `Fx::to_bits()`, so the tables pin the sim's own arithmetic and
//! RNG as they are today. That is what a golden table is for -- a bit that moves under a
//! `fixed` upgrade, a toolchain bump or a new platform moves every replay with it, and
//! this is where it shows first. When `fxmath` gains sqrt/sin/cos/atan2 (Phase 3), their
//! float references are computed here and emitted the same way.
//!
//! Output is Rust source on stdout, ready for `cargo fmt`.

use std::fmt::Write;

use blindside_sim::{DeterministicRng, Fx, Purpose, Tick};

/// (seed, tick, entity, purpose) rows: corners and ordinary values of every input, and
/// every `Purpose` variant. 40 rows; BLD-24 asks for at least 32.
fn rng_inputs() -> Vec<(u64, u64, u32, Purpose)> {
    let seeds = [0u64, 1, 0xDEAD_BEEF, 0x9E37_79B9_7F4A_7C15, u64::MAX];
    let probes = [
        (0u64, 0u32, Purpose::MoveX),
        (0, 0, Purpose::MoveY),
        (1, 1, Purpose::MoveX),
        (1, 2, Purpose::MoveY),
        (1000, 2, Purpose::MoveY),
        (9_600, 7, Purpose::MoveX),
        (10_000, 1, Purpose::TestShuffle),
        (u64::MAX, u32::MAX, Purpose::MoveY),
    ];
    let mut rows = Vec::new();
    for seed in seeds {
        for (tick, entity, purpose) in probes {
            rows.push((seed, tick, entity, purpose));
        }
    }
    rows
}

/// Operand pairs for the arithmetic table, as `Fx` values built without floats.
fn fx_pairs() -> Vec<(Fx, Fx)> {
    let one_and_a_half = Fx::from_bits(0x1_8000_0000);
    let third_ish = Fx::from_bits(0x5555_5555);
    vec![
        (Fx::from_num(1), Fx::from_num(2)),
        (Fx::from_num(3), Fx::from_num(2)),
        (Fx::from_num(-1), Fx::from_num(3)),
        (Fx::from_num(7), Fx::from_num(3)),
        (Fx::from_num(-7), Fx::from_num(3)),
        (one_and_a_half, one_and_a_half),
        (Fx::from_bits(1), Fx::from_bits(1)),
        (Fx::from_num(12_345), Fx::from_bits(0x1234_5678)),
        (third_ish, Fx::from_num(3)),
        (Fx::MAX, Fx::from_num(1)),
        (Fx::MAX, Fx::MAX),
        (Fx::MIN, Fx::from_num(-1)),
    ]
}

const OPS: [&str; 4] = ["Add", "Sub", "Mul", "Div"];

fn apply(op: &str, a: Fx, b: Fx) -> Fx {
    match op {
        "Add" => a.wrapping_add(b),
        "Sub" => a.wrapping_sub(b),
        "Mul" => a.wrapping_mul(b),
        "Div" => a.wrapping_div(b),
        _ => unreachable!("op {op}"),
    }
}

/// The complete `golden_tables.rs` source.
pub fn render() -> String {
    let mut out = String::new();
    out.push_str(
        "//! Golden tables for blindside-sim, checked in as raw bits (BLD-24, BLD-25).\n\
         //!\n\
         //! GENERATED -- do not edit. Regenerate, from the workspace root, with:\n\
         //!\n\
         //!     cargo run -p blindside-harness -- golden > crates/blindside-sim/src/golden_tables.rs\n\
         //!     cargo fmt --all\n\
         //!\n\
         //! A regenerated file that differs from the checked-in one means the RNG mix, the\n\
         //! `fixed` crate, the toolchain or the platform changed the bits, and with them every\n\
         //! replay ever recorded: that is a deliberate, versioned change or a bug, never a\n\
         //! routine refresh. `golden.rs` asserts every row; CI runs it on three OSes.\n\
         //!\n\
         //! Generator: crates/blindside-harness/src/golden.rs (floats are permitted there; none\n\
         //! were needed -- every input is an integer or a bit pattern, every output is\n\
         //! `Fx::to_bits()` as `u64`). The trailing comment on each row is the value in decimal.\n\
         \n\
         use crate::golden::FxOp;\n\
         use crate::Purpose;\n\
         \n\
         /// `DeterministicRng::new(seed).draw(Tick(tick), entity, purpose).to_bits()`.\n\
         /// Columns: seed, tick, entity, purpose, bits.\n\
         pub const RNG_DRAWS: &[(u64, u64, u32, Purpose, u64)] = &[\n",
    );
    for (seed, tick, entity, purpose) in rng_inputs() {
        let v = DeterministicRng::new(seed).draw(Tick(tick), entity, purpose);
        writeln!(
            out,
            "    ({seed:#018x}, {tick}, {entity}, Purpose::{purpose:?}, {:#018x}), // {v}",
            v.to_bits() as u64
        )
        .unwrap();
    }
    out.push_str(
        "];\n\
         \n\
         /// `apply(op, Fx::from_bits(a), Fx::from_bits(b)).to_bits()` (wrapping forms).\n\
         /// Columns: op, a bits, b bits, result bits.\n\
         pub const FX_ARITHMETIC: &[(FxOp, u64, u64, u64)] = &[\n",
    );
    for (a, b) in fx_pairs() {
        for op in OPS {
            let r = apply(op, a, b);
            writeln!(
                out,
                "    (FxOp::{op}, {:#018x}, {:#018x}, {:#018x}), // {a} {op} {b} = {r}",
                a.to_bits() as u64,
                b.to_bits() as u64,
                r.to_bits() as u64
            )
            .unwrap();
        }
    }
    out.push_str("];\n");
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn render_has_enough_rows_and_no_float_literals() {
        let text = render();
        let rng_rows = text.lines().filter(|l| l.contains("Purpose::")).count();
        assert!(rng_rows >= 32, "{rng_rows}");
        assert!(text.lines().filter(|l| l.contains("FxOp::")).count() >= 40);
        // Every literal in the code (not the comments) is a hex or plain integer.
        for line in text.lines().filter(|l| l.trim_start().starts_with('(')) {
            let code = line.split("//").next().unwrap();
            assert!(
                !code.contains(".0") && !code.contains(".5"),
                "float-looking token in {line}"
            );
        }
    }

    #[test]
    fn render_is_deterministic() {
        assert_eq!(render(), render());
    }
}
