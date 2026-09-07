//! Golden tables for blindside-sim, checked in as raw bits (BLD-24, BLD-25).
//!
//! GENERATED -- do not edit. Regenerate, from the workspace root, with:
//!
//!     cargo run -p blindside-harness -- golden > crates/blindside-sim/src/golden_tables.rs
//!     cargo fmt --all
//!
//! A regenerated file that differs from the checked-in one means the RNG mix, the
//! `fixed` crate, the toolchain or the platform changed the bits, and with them every
//! replay ever recorded: that is a deliberate, versioned change or a bug, never a
//! routine refresh. `golden.rs` asserts every row; CI runs it on three OSes.
//!
//! Generator: crates/blindside-harness/src/golden.rs (floats are permitted there; none
//! were needed -- every input is an integer or a bit pattern, every output is
//! `Fx::to_bits()` as `u64`). The trailing comment on each row is the value in decimal.

use crate::golden::FxOp;
use crate::Purpose;

/// `DeterministicRng::new(seed).draw(Tick(tick), entity, purpose).to_bits()`.
/// Columns: seed, tick, entity, purpose, bits.
pub const RNG_DRAWS: &[(u64, u64, u32, Purpose, u64)] = &[
    (0x0000000000000000, 0, 0, Purpose::MoveX, 0x0000000016ad76c1), // 0.0885843488
    (0x0000000000000000, 0, 0, Purpose::MoveY, 0x00000000002798f0), // 0.0006042086
    (0x0000000000000000, 1, 1, Purpose::MoveX, 0x00000000bc3db306), // 0.7353164568
    (0x0000000000000000, 1, 2, Purpose::MoveY, 0x00000000ec7f17ff), // 0.9238142965
    (
        0x0000000000000000,
        1000,
        2,
        Purpose::MoveY,
        0x00000000b33fc35c,
    ), // 0.700191698
    (
        0x0000000000000000,
        9600,
        7,
        Purpose::MoveX,
        0x0000000077eff2b2,
    ), // 0.4685050664
    (
        0x0000000000000000,
        10000,
        1,
        Purpose::TestShuffle,
        0x00000000b1e26782,
    ), // 0.6948609059
    (
        0x0000000000000000,
        18446744073709551615,
        4294967295,
        Purpose::MoveY,
        0x000000001780a5cb,
    ), // 0.091806757
    (0x0000000000000001, 0, 0, Purpose::MoveX, 0x0000000071b63fca), // 0.4441871517
    (0x0000000000000001, 0, 0, Purpose::MoveY, 0x00000000fdb09cff), // 0.9909761546
    (0x0000000000000001, 1, 1, Purpose::MoveX, 0x00000000f918eb9d), // 0.9730365046
    (0x0000000000000001, 1, 2, Purpose::MoveY, 0x0000000038f8eb1c), // 0.2225481933
    (
        0x0000000000000001,
        1000,
        2,
        Purpose::MoveY,
        0x000000008fb914c2,
    ), // 0.5614178632
    (
        0x0000000000000001,
        9600,
        7,
        Purpose::MoveX,
        0x00000000586517bc,
    ), // 0.3452925524
    (
        0x0000000000000001,
        10000,
        1,
        Purpose::TestShuffle,
        0x00000000c34c7e67,
    ), // 0.7628859521
    (
        0x0000000000000001,
        18446744073709551615,
        4294967295,
        Purpose::MoveY,
        0x000000008cfc40ca,
    ), // 0.5507240766
    (0x00000000deadbeef, 0, 0, Purpose::MoveX, 0x000000003c9173b7), // 0.2365944216
    (0x00000000deadbeef, 0, 0, Purpose::MoveY, 0x000000008e554b95), // 0.555989002
    (0x00000000deadbeef, 1, 1, Purpose::MoveX, 0x00000000355cb3f0), // 0.2084457837
    (0x00000000deadbeef, 1, 2, Purpose::MoveY, 0x000000000077cdbb), // 0.0018280584
    (
        0x00000000deadbeef,
        1000,
        2,
        Purpose::MoveY,
        0x0000000079a66485,
    ), // 0.4751952004
    (
        0x00000000deadbeef,
        9600,
        7,
        Purpose::MoveX,
        0x00000000a96357af,
    ), // 0.6616720965
    (
        0x00000000deadbeef,
        10000,
        1,
        Purpose::TestShuffle,
        0x00000000f491f034,
    ), // 0.9553518416
    (
        0x00000000deadbeef,
        18446744073709551615,
        4294967295,
        Purpose::MoveY,
        0x0000000065af7300,
    ), // 0.3972083926
    (0x9e3779b97f4a7c15, 0, 0, Purpose::MoveX, 0x0000000048218226), // 0.2817612975
    (0x9e3779b97f4a7c15, 0, 0, Purpose::MoveY, 0x00000000cd73fe3d), // 0.8025511645
    (0x9e3779b97f4a7c15, 1, 1, Purpose::MoveX, 0x000000007fa70ea0), // 0.4986428395
    (0x9e3779b97f4a7c15, 1, 2, Purpose::MoveY, 0x000000007cf273f6), // 0.4880745388
    (
        0x9e3779b97f4a7c15,
        1000,
        2,
        Purpose::MoveY,
        0x000000006eedb3fa,
    ), // 0.4333145604
    (
        0x9e3779b97f4a7c15,
        9600,
        7,
        Purpose::MoveX,
        0x00000000e3d106d4,
    ), // 0.889908244
    (
        0x9e3779b97f4a7c15,
        10000,
        1,
        Purpose::TestShuffle,
        0x00000000dfe688cf,
    ), // 0.874611426
    (
        0x9e3779b97f4a7c15,
        18446744073709551615,
        4294967295,
        Purpose::MoveY,
        0x00000000e6c2d37a,
    ), // 0.90141031
    (0xffffffffffffffff, 0, 0, Purpose::MoveX, 0x00000000526f9ea7), // 0.322015682
    (0xffffffffffffffff, 0, 0, Purpose::MoveY, 0x0000000009d3054d), // 0.0383761704
    (0xffffffffffffffff, 1, 1, Purpose::MoveX, 0x000000005a892b80), // 0.353655547
    (0xffffffffffffffff, 1, 2, Purpose::MoveY, 0x00000000691f0e8f), // 0.4106301402
    (
        0xffffffffffffffff,
        1000,
        2,
        Purpose::MoveY,
        0x00000000a9205dc6,
    ), // 0.6606501206
    (
        0xffffffffffffffff,
        9600,
        7,
        Purpose::MoveX,
        0x00000000b59a5c1d,
    ), // 0.709386594
    (
        0xffffffffffffffff,
        10000,
        1,
        Purpose::TestShuffle,
        0x00000000d5535f77,
    ), // 0.8333034196
    (
        0xffffffffffffffff,
        18446744073709551615,
        4294967295,
        Purpose::MoveY,
        0x00000000155dd373,
    ), // 0.0834629207
];

/// `apply(op, Fx::from_bits(a), Fx::from_bits(b)).to_bits()` (wrapping forms).
/// Columns: op, a bits, b bits, result bits.
pub const FX_ARITHMETIC: &[(FxOp, u64, u64, u64)] = &[
    (
        FxOp::Add,
        0x0000000100000000,
        0x0000000200000000,
        0x0000000300000000,
    ), // 1 Add 2 = 3
    (
        FxOp::Sub,
        0x0000000100000000,
        0x0000000200000000,
        0xffffffff00000000,
    ), // 1 Sub 2 = -1
    (
        FxOp::Mul,
        0x0000000100000000,
        0x0000000200000000,
        0x0000000200000000,
    ), // 1 Mul 2 = 2
    (
        FxOp::Div,
        0x0000000100000000,
        0x0000000200000000,
        0x0000000080000000,
    ), // 1 Div 2 = 0.5
    (
        FxOp::Add,
        0x0000000300000000,
        0x0000000200000000,
        0x0000000500000000,
    ), // 3 Add 2 = 5
    (
        FxOp::Sub,
        0x0000000300000000,
        0x0000000200000000,
        0x0000000100000000,
    ), // 3 Sub 2 = 1
    (
        FxOp::Mul,
        0x0000000300000000,
        0x0000000200000000,
        0x0000000600000000,
    ), // 3 Mul 2 = 6
    (
        FxOp::Div,
        0x0000000300000000,
        0x0000000200000000,
        0x0000000180000000,
    ), // 3 Div 2 = 1.5
    (
        FxOp::Add,
        0xffffffff00000000,
        0x0000000300000000,
        0x0000000200000000,
    ), // -1 Add 3 = 2
    (
        FxOp::Sub,
        0xffffffff00000000,
        0x0000000300000000,
        0xfffffffc00000000,
    ), // -1 Sub 3 = -4
    (
        FxOp::Mul,
        0xffffffff00000000,
        0x0000000300000000,
        0xfffffffd00000000,
    ), // -1 Mul 3 = -3
    (
        FxOp::Div,
        0xffffffff00000000,
        0x0000000300000000,
        0xffffffffaaaaaaab,
    ), // -1 Div 3 = -0.3333333333
    (
        FxOp::Add,
        0x0000000700000000,
        0x0000000300000000,
        0x0000000a00000000,
    ), // 7 Add 3 = 10
    (
        FxOp::Sub,
        0x0000000700000000,
        0x0000000300000000,
        0x0000000400000000,
    ), // 7 Sub 3 = 4
    (
        FxOp::Mul,
        0x0000000700000000,
        0x0000000300000000,
        0x0000001500000000,
    ), // 7 Mul 3 = 21
    (
        FxOp::Div,
        0x0000000700000000,
        0x0000000300000000,
        0x0000000255555555,
    ), // 7 Div 3 = 2.3333333333
    (
        FxOp::Add,
        0xfffffff900000000,
        0x0000000300000000,
        0xfffffffc00000000,
    ), // -7 Add 3 = -4
    (
        FxOp::Sub,
        0xfffffff900000000,
        0x0000000300000000,
        0xfffffff600000000,
    ), // -7 Sub 3 = -10
    (
        FxOp::Mul,
        0xfffffff900000000,
        0x0000000300000000,
        0xffffffeb00000000,
    ), // -7 Mul 3 = -21
    (
        FxOp::Div,
        0xfffffff900000000,
        0x0000000300000000,
        0xfffffffdaaaaaaab,
    ), // -7 Div 3 = -2.3333333333
    (
        FxOp::Add,
        0x0000000180000000,
        0x0000000180000000,
        0x0000000300000000,
    ), // 1.5 Add 1.5 = 3
    (
        FxOp::Sub,
        0x0000000180000000,
        0x0000000180000000,
        0x0000000000000000,
    ), // 1.5 Sub 1.5 = 0
    (
        FxOp::Mul,
        0x0000000180000000,
        0x0000000180000000,
        0x0000000240000000,
    ), // 1.5 Mul 1.5 = 2.25
    (
        FxOp::Div,
        0x0000000180000000,
        0x0000000180000000,
        0x0000000100000000,
    ), // 1.5 Div 1.5 = 1
    (
        FxOp::Add,
        0x0000000000000001,
        0x0000000000000001,
        0x0000000000000002,
    ), // 0.0000000002 Add 0.0000000002 = 0.0000000005
    (
        FxOp::Sub,
        0x0000000000000001,
        0x0000000000000001,
        0x0000000000000000,
    ), // 0.0000000002 Sub 0.0000000002 = 0
    (
        FxOp::Mul,
        0x0000000000000001,
        0x0000000000000001,
        0x0000000000000000,
    ), // 0.0000000002 Mul 0.0000000002 = 0
    (
        FxOp::Div,
        0x0000000000000001,
        0x0000000000000001,
        0x0000000100000000,
    ), // 0.0000000002 Div 0.0000000002 = 1
    (
        FxOp::Add,
        0x0000303900000000,
        0x0000000012345678,
        0x0000303912345678,
    ), // 12345 Add 0.071111111 = 12345.071111111
    (
        FxOp::Sub,
        0x0000303900000000,
        0x0000000012345678,
        0x00003038edcba988,
    ), // 12345 Sub 0.071111111 = 12344.928888889
    (
        FxOp::Mul,
        0x0000303900000000,
        0x0000000012345678,
        0x0000036dddddc0b8,
    ), // 12345 Mul 0.071111111 = 877.8666649293
    (
        FxOp::Div,
        0x0000303900000000,
        0x0000000012345678,
        0x0002a6219016841d,
    ), // 12345 Div 0.071111111 = 173601.562843568
    (
        FxOp::Add,
        0x0000000055555555,
        0x0000000300000000,
        0x0000000355555555,
    ), // 0.3333333333 Add 3 = 3.3333333333
    (
        FxOp::Sub,
        0x0000000055555555,
        0x0000000300000000,
        0xfffffffd55555555,
    ), // 0.3333333333 Sub 3 = -2.6666666667
    (
        FxOp::Mul,
        0x0000000055555555,
        0x0000000300000000,
        0x00000000ffffffff,
    ), // 0.3333333333 Mul 3 = 0.9999999998
    (
        FxOp::Div,
        0x0000000055555555,
        0x0000000300000000,
        0x000000001c71c71c,
    ), // 0.3333333333 Div 3 = 0.111111111
    (
        FxOp::Add,
        0x7fffffffffffffff,
        0x0000000100000000,
        0x80000000ffffffff,
    ), // 2147483647.9999999998 Add 1 = -2147483647.0000000002
    (
        FxOp::Sub,
        0x7fffffffffffffff,
        0x0000000100000000,
        0x7ffffffeffffffff,
    ), // 2147483647.9999999998 Sub 1 = 2147483646.9999999998
    (
        FxOp::Mul,
        0x7fffffffffffffff,
        0x0000000100000000,
        0x7fffffffffffffff,
    ), // 2147483647.9999999998 Mul 1 = 2147483647.9999999998
    (
        FxOp::Div,
        0x7fffffffffffffff,
        0x0000000100000000,
        0x7fffffffffffffff,
    ), // 2147483647.9999999998 Div 1 = 2147483647.9999999998
    (
        FxOp::Add,
        0x7fffffffffffffff,
        0x7fffffffffffffff,
        0xfffffffffffffffe,
    ), // 2147483647.9999999998 Add 2147483647.9999999998 = -0.0000000005
    (
        FxOp::Sub,
        0x7fffffffffffffff,
        0x7fffffffffffffff,
        0x0000000000000000,
    ), // 2147483647.9999999998 Sub 2147483647.9999999998 = 0
    (
        FxOp::Mul,
        0x7fffffffffffffff,
        0x7fffffffffffffff,
        0xffffffff00000000,
    ), // 2147483647.9999999998 Mul 2147483647.9999999998 = -1
    (
        FxOp::Div,
        0x7fffffffffffffff,
        0x7fffffffffffffff,
        0x0000000100000000,
    ), // 2147483647.9999999998 Div 2147483647.9999999998 = 1
    (
        FxOp::Add,
        0x8000000000000000,
        0xffffffff00000000,
        0x7fffffff00000000,
    ), // -2147483648 Add -1 = 2147483647
    (
        FxOp::Sub,
        0x8000000000000000,
        0xffffffff00000000,
        0x8000000100000000,
    ), // -2147483648 Sub -1 = -2147483647
    (
        FxOp::Mul,
        0x8000000000000000,
        0xffffffff00000000,
        0x8000000000000000,
    ), // -2147483648 Mul -1 = -2147483648
    (
        FxOp::Div,
        0x8000000000000000,
        0xffffffff00000000,
        0x8000000000000000,
    ), // -2147483648 Div -1 = -2147483648
];
