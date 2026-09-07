//! BLD-34 fixture, PASS half: every `unsafe` in a constrained crate carries a
//! `// SAFETY:` line directly above it, so `determinism-lint` exits 0 here.
//!
//! DETERMINISM.md rule 8 is "any `unsafe` in these crates requires written justification".
//! The lint checks that the justification exists; whether it is TRUE is a review item and
//! nothing here should be read as a claim that this code is sound — it is never compiled.
//!
//! The fail half lives next door in `../unsafe-unjustified`. Both are needed: a check that
//! only ever sees passing input is a check that has never been shown to go red.

#![deny(unsafe_code)]

// SAFETY: the caller hands over a live reference, so the pointer read below is valid for
// the lifetime of the call.
#[allow(unsafe_code)]
pub unsafe fn read(p: &u8) -> u8 {
    *p
}

pub fn call() -> u8 {
    let x = 7;
    // A justification may span several lines; the lint wants one of them to start with
    // the marker, and attribute lines between it and the item are skipped.
    // SAFETY: `read` only dereferences the reference it is given.
    #[allow(unsafe_code)]
    let v = unsafe { read(&x) };
    v
}
