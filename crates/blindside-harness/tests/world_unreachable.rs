//! BLD-32: the compile-time proof that nothing outside blindside-sim can reach `World`.
//!
//! ARCHITECTURE.md: "Write a compile-time test asserting `Policy::evaluate` cannot reach
//! `World`. It exists to catch the 'just for debugging' accessor someone adds in year
//! two." Policies do not exist yet, but the harness is the first code that wants ground
//! truth (to hash and diff), so the scaffold lands here with the variant that matters
//! today: from outside the crate -- from this crate, which enables the `diagnostics`
//! feature -- `World` cannot be named, its module cannot be opened, and nothing that
//! `diagnostics::diff` or `diagnostics::dump` returns is or contains it.
//!
//! The mechanism is module privacy (`pub(crate) struct World` in a private `mod world`)
//! checked by the compiler through trybuild, not a source lint: the expected diagnostics
//! are checked in as `tests/ui/*.stderr`, so a new accessor that makes one of these
//! programs compile fails the test on every CI OS.
//!
//! PHASE 3 FOLLOW-UP: when `Policy`, `Predicate` and `Belief` exist, add the cases the
//! architecture actually names -- a `Policy::evaluate` and a `Predicate::eval` that try
//! to take `&World` (or anything but `&Belief`) must fail to compile -- and a sensor-layer
//! case proving `Sensor::sample` is the only trait method that sees both. Until then this
//! file is the placeholder those cases are added to; do not let it be forgotten.

#[test]
fn world_cannot_be_named_or_reached_from_outside_blindside_sim() {
    let t = trybuild::TestCases::new();
    // `blindside_sim::World` is not a name.
    t.compile_fail("tests/ui/name_world.rs");
    // `blindside_sim::world` is not a module anyone can open.
    t.compile_fail("tests/ui/world_module.rs");
    // The diagnostics API returns strings; no path from its return types leads to a type
    // from world.rs.
    t.compile_fail("tests/ui/through_diagnostics.rs");
    // And the positive half: everything `diagnostics` hands out is a String, exhaustively.
    t.pass("tests/ui/diagnostics_is_strings.rs");
}
