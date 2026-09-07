//! Fixed-point transcendental math: the ONLY permitted home for `sqrt`, `sin`, `cos` and
//! `atan2` in the constrained crates (DETERMINISM.md, "Practical notes": trig and sqrt
//! are the usual culprits; use fixed-point implementations from a single module, never
//! platform math libraries).
//!
//! Phase 0 (BLD-24): this module deliberately contains NO implementations. It exists so
//! that the rule has an address before anyone needs the functions. Phase 3 adds them here
//! and nowhere else, each as explicit integer arithmetic over `Fx` bits, each pinned by a
//! golden table generated with `cargo run -p blindside-harness -- golden` (the harness may
//! use floats to produce a reference; this crate may not).
//!
//! What must never appear here or anywhere else in the sim: `f32`/`f64`, `libm`, the
//! `fixed` crate's float conversions, or any `std`/`core` float method. The determinism
//! lint rejects the spellings; this header records the intent.
//!
//! Anything that computes a root or an angle by any other route -- a lookup table in
//! another module, an "approximate" helper next to the code that needs it -- is a second
//! implementation, and two implementations of `sqrt` in one sim is how two machines
//! disagree by one ulp in month nine.
