//! Generate `include/blindside_sim.h` from `src/lib.rs` with cbindgen.
//!
//! The header is a build artefact, never hand-written and never edited. A hand-written
//! header that drifts from the Rust does not fail to compile; it produces a call with the
//! wrong argument sizes, which is a memory-safety bug that shows up as a crash three
//! months later somewhere else entirely.
//!
//! It is written into the crate's source tree (`crates/blindside-ffi/include/`) rather
//! than `OUT_DIR` on purpose: Unreal Build Tool needs a stable include path that does not
//! contain a Cargo hash, and it must exist before UBT runs. It is checked in so a reader
//! can see the whole boundary in one file without building anything, and
//! `tests/header_surface.rs` asserts the checked-in copy is the one this build produces.

use std::path::PathBuf;

fn main() {
    let crate_dir = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
    let out = crate_dir.join("include").join("blindside_sim.h");
    std::fs::create_dir_all(out.parent().unwrap()).unwrap();

    println!("cargo:rerun-if-changed=src/lib.rs");
    println!("cargo:rerun-if-changed=cbindgen.toml");
    println!("cargo:rerun-if-changed=build.rs");

    match cbindgen::generate(&crate_dir) {
        Ok(bindings) => {
            // `write_to_file` only rewrites when the contents change, so an unchanged
            // header does not touch its mtime and does not make UBT rebuild the world.
            bindings.write_to_file(&out);
        }
        Err(e) => {
            // A cbindgen failure must fail the build. Silently keeping a stale header is
            // precisely the drift this file exists to prevent.
            panic!("cbindgen failed: {e}");
        }
    }
}
