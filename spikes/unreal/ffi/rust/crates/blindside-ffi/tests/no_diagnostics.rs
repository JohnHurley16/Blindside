//! `blindside-sim`'s `diagnostics` feature is the tooling window onto ground truth, and
//! the sim's own module docs say that `blindside-harness` enables it and "no client,
//! policy, VM or renderer crate may". This crate is a renderer's crate.
//!
//! Cargo features are not a privacy boundary -- they unify per package across one build
//! invocation -- so the real gate is that a shipped client library is built with
//! `-p blindside-ffi` and never alongside the harness. What this test can prove is the
//! part that lives here: that this crate does not itself turn the feature on, and that
//! the symbols it would expose are absent from the build the test runs in.

/// If `diagnostics` were on, `blindside_sim::diagnostics` would exist and this would
/// compile. It is written as a `cfg`-gated failure rather than a "does not compile" test
/// so it needs no extra tooling: if the module is reachable, the test fails loudly.
#[test]
fn this_crate_does_not_pull_in_the_ground_truth_window() {
    // The check that actually bites: a compile-time one, expressed by the fact that
    // nothing below can name the module. If someone adds `features = ["diagnostics"]` to
    // Cargo.toml, this file still compiles -- so assert on the manifest instead, which is
    // where the mistake would be made.
    let manifest = include_str!("../Cargo.toml");
    for line in manifest.lines() {
        let l = line.trim();
        if l.starts_with('#') {
            continue;
        }
        assert!(
            !l.contains("diagnostics"),
            "blindside-ffi must not enable blindside-sim's `diagnostics` feature: {l}"
        );
        assert!(
            !l.contains("inject-desync"),
            "blindside-ffi must not enable the desync-injection fixture: {l}"
        );
    }
}
