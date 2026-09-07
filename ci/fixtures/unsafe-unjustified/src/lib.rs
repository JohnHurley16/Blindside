//! BLD-34 fixture, FAIL half: the same code as `../unsafe-justified` with the
//! justifications removed. `determinism-lint` must report exactly four findings here and
//! exit 1 — if it ever exits 0, the rule-8 check has rotted and every `unsafe` merged
//! since is unreviewed.
//!
//! The four, in source order:
//!   1. `#![allow(unsafe_code)]`  — a crate-wide allow, which is never a justification
//!   2. `#[allow(unsafe_code)]`   — an item allow whose comment block says nothing about safety
//!   3. `unsafe fn read`          — the item that allow covers
//!   4. `unsafe { read(&y) }`     — a block whose marker is not directly above it
//!
//! Never built or run. Nothing here is sound and nothing here claims to be.

#![allow(unsafe_code)]

// Not a justification: it explains what the function does, not why the dereference is
// valid, and it does not carry the marker the rule requires.
#[allow(unsafe_code)]
pub unsafe fn read(p: &u8) -> u8 {
    *p
}

pub fn call() -> u8 {
    let x = 7;
    // The marker below is real, but it is not directly above the unsafe block: a
    // statement intervenes, so it justifies the `let y`, not the dereference.
    // SAFETY: nothing here is being justified.
    let y = x;
    let v = unsafe { read(&y) };
    v
}
