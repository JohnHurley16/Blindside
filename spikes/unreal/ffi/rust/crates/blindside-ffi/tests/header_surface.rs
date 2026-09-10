//! The generated header IS the boundary. These tests read it and check it.
//!
//! CLAUDE.md's one invariant is that an agent's policy may never observe ground truth,
//! and ARCHITECTURE.md extends that to the client and the renderer. In a Rust-only world
//! that is enforced by `World` being `pub(crate)`. Across a C ABI the enforcement is
//! stronger *and* weaker: stronger because the header is a finite, readable list that a
//! human can audit in a minute; weaker because C has no privacy, so once a byte is across
//! it is across. Both facts point the same way — audit the list.
//!
//! So: parse `include/blindside_sim.h`, and fail if anything appears in it that could
//! carry ground truth. This is not a substitute for the Rust privacy; it is a second
//! lock, on the artefact the C++ actually sees.

use std::path::PathBuf;

fn header() -> String {
    let p = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("include")
        .join("blindside_sim.h");
    std::fs::read_to_string(&p).unwrap_or_else(|e| {
        panic!(
            "cannot read the generated header at {}: {e}. Run `cargo build -p blindside-ffi` \
             first; build.rs generates it.",
            p.display()
        )
    })
}

/// The header with every `/* ... */` and `// ...` comment removed, so the checks below
/// look at declarations and not at the prose cbindgen copies out of the doc comments.
fn code_only(h: &str) -> String {
    let mut out = String::with_capacity(h.len());
    let b = h.as_bytes();
    let mut i = 0;
    while i < b.len() {
        if b[i] == b'/' && i + 1 < b.len() && b[i + 1] == b'*' {
            // Skip to the matching `*/`; cbindgen does not nest block comments.
            i += 2;
            while i + 1 < b.len() && !(b[i] == b'*' && b[i + 1] == b'/') {
                i += 1;
            }
            i = (i + 2).min(b.len());
            out.push(' ');
        } else if b[i] == b'/' && i + 1 < b.len() && b[i + 1] == b'/' {
            while i < b.len() && b[i] != b'\n' {
                i += 1;
            }
        } else {
            out.push(b[i] as char);
            i += 1;
        }
    }
    out
}

/// Every `bs_*` function the header declares. Declarations wrap across lines, so this
/// works on the comment-stripped text and keys on the `(` that follows the name.
fn exported_symbols(h: &str) -> Vec<String> {
    let code = code_only(h);
    let mut out: Vec<String> = Vec::new();
    let mut rest = code.as_str();
    while let Some(at) = rest.find("bs_") {
        let tail = &rest[at..];
        let name: String = tail
            .chars()
            .take_while(|c| c.is_ascii_alphanumeric() || *c == '_')
            .collect();
        if tail[name.len()..].starts_with('(') && !out.contains(&name) {
            out.push(name);
        }
        rest = &rest[at + 3..];
    }
    out.sort();
    out
}

/// The complete, deliberate list of what crosses. Adding a function here is the moment to
/// ask whether it can carry ground truth; that is the entire point of the list existing.
const EXPECTED: &[&str] = &[
    "bs_abi_version",
    "bs_belief_header_size",
    "bs_belief_point_size",
    "bs_belief_schema",
    "bs_sim_agent_count",
    "bs_sim_belief_bytes",
    "bs_sim_belief_snapshot",
    "bs_sim_create",
    "bs_sim_destroy",
    "bs_sim_seed",
    // SPIKE ONLY. Delete this from lib.rs and from here together.
    "bs_sim_spike_force_panic",
    "bs_sim_state_hash",
    "bs_sim_step",
    "bs_sim_tick",
    "bs_status_message",
];

#[test]
fn the_header_exports_exactly_the_reviewed_list() {
    let got = exported_symbols(&header());
    let mut expected: Vec<String> = EXPECTED.iter().map(|s| s.to_string()).collect();
    expected.sort();
    assert_eq!(
        got, expected,
        "the C boundary changed. This is not a test to update casually: every name on \
         this list is something a renderer can ask the simulation for, forever."
    );
}

/// A word-level check for ground-truth vocabulary. Crude on purpose: the failure it is
/// guarding against is somebody adding `bs_sim_world_agent_positions` at 2am, and a crude
/// check catches that where a clever one would be argued with.
#[test]
fn the_header_never_names_ground_truth() {
    let h = code_only(&header()).to_ascii_lowercase();
    // Words from `world.rs` and from ARCHITECTURE.md's `World` struct.
    for forbidden in [
        "world",
        "ground_truth",
        "groundtruth",
        "agenttruth",
        "agent_truth",
        "truepos",
        "true_pos",
        "cave",
        "acoustic",
        "ancient",
        "deposit",
        "wreck",
        "beacontruth",
        "diagnostics",
        "dump",
        "bs_sim_diff",
    ] {
        // The header's prose is generated from doc comments, so a mention inside a
        // comment is possible and is fine (the file header says the word "world" four
        // times, explaining why there is no world here). A mention in a DECLARATION is
        // not fine, so the check runs on the comment-stripped text.
        assert!(
            !h.contains(forbidden),
            "the generated header names `{forbidden}` in a declaration, not a comment.\n\
             If the sim now has a legitimate reason to hand this to a renderer, that is a \
             designer conversation, not a test edit."
        );
    }
}

/// Nothing crossing the boundary is a float. DETERMINISM.md rule 1 bans `f32`/`f64` in
/// the sim; a `float` in the header would mean the conversion happened on the sim's side
/// of the line, which is the same violation wearing a different hat.
#[test]
fn nothing_that_crosses_is_a_float() {
    let h = code_only(&header());
    for f in ["float", "double"] {
        assert!(
            !h.contains(f),
            "the generated header carries a `{f}` in a declaration. Fixed-point values \
             cross as raw bits; the conversion happens on the renderer's side of the line."
        );
    }
}

/// The header the repository holds is the header this build produces. A checked-in
/// generated file that has drifted from its generator is worse than no checked-in file.
#[test]
fn the_checked_in_header_is_current() {
    let crate_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let generated = cbindgen::generate(&crate_dir).expect("cbindgen");
    let mut fresh = Vec::new();
    generated.write(&mut fresh);
    let fresh = String::from_utf8(fresh).unwrap();
    // Normalise line endings: git may check the header out with CRLF on Windows.
    let norm = |s: &str| s.replace("\r\n", "\n");
    assert_eq!(
        norm(&fresh),
        norm(&header()),
        "include/blindside_sim.h is stale. Run `cargo build -p blindside-ffi`."
    );
}
