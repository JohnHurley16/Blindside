//! TOOLING ONLY. A window onto ground truth as strings, for the desync canary and bisect.
//!
//! Compiled only with the `diagnostics` cargo feature, which `blindside-harness` enables
//! and no client, policy, VM or renderer crate may. It is the one sanctioned way for
//! anything outside this crate to see what `World` holds, and it is designed to be
//! useless as a leak: field paths and values as `String`s, never a typed `&World`, nothing
//! a policy could branch on without parsing prose. `blindside-harness/tests/
//! world_unreachable.rs` proves at compile time that `World` cannot be reached through
//! `diff` or `dump`.
//!
//! DEFAULT (awaiting designer): this module is the "diagnostics-diff exception" BLD-20
//! puts to the designer -- the one place tooling may read ground truth. Built as
//! recommended; the designer's yes/no is recorded in docs/HARNESS.md when it comes.
//!
//! **Cargo features are not a privacy boundary.** Cargo unifies features per package
//! across one build invocation, so `cargo build --workspace` with the harness present
//! compiles this module into the `blindside-sim` that every other crate in that build
//! links. What makes the gate real is the BLD-29 CI check: every hash-producing or
//! shippable binary is built with `-p <crate>`, and `cargo tree -e features` on each such
//! crate must not show `diagnostics` or `inject-desync`.

use std::collections::BTreeMap;
use std::fmt;

use crate::hash;
use crate::Sim;

/// One field that differs between two sims. `a`/`b` is `None` when the field exists in
/// only the other sim (agent present in one instance and not the other).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DiffEntry {
    /// Field path as `dump` prints it, e.g. `tick`, `agents[2].pos.x`.
    pub path: String,
    pub a: Option<String>,
    pub b: Option<String>,
}

/// Every differing field, in hash-layout order: field declaration order, then stable-ID
/// order inside collections; fields only `b` has are appended in `b`'s order. Two runs
/// over the same pair of sims produce byte-identical reports.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct DiffReport {
    pub entries: Vec<DiffEntry>,
}

impl DiffReport {
    /// True when the two sims render identically -- which, because the dump covers
    /// exactly the hashed fields, means they hash identically too.
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
}

impl fmt::Display for DiffEntry {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match (&self.a, &self.b) {
            (Some(a), Some(b)) => write!(f, "{}: {a} vs {b}", self.path),
            (Some(a), None) => write!(f, "{}: {a} vs <absent>", self.path),
            (None, Some(b)) => write!(f, "{}: <absent> vs {b}", self.path),
            (None, None) => write!(f, "{}: <absent> vs <absent>", self.path),
        }
    }
}

impl fmt::Display for DiffReport {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        for e in &self.entries {
            writeln!(f, "{e}")?;
        }
        Ok(())
    }
}

/// Field-by-field diff of two sims. Identical sims yield an empty report.
pub fn diff(a: &Sim, b: &Sim) -> DiffReport {
    let fa = hash::debug_fields(a);
    let fb = hash::debug_fields(b);
    let b_by_path: BTreeMap<&str, &str> =
        fb.iter().map(|(k, v)| (k.as_str(), v.as_str())).collect();
    let a_paths: BTreeMap<&str, ()> = fa.iter().map(|(k, _)| (k.as_str(), ())).collect();
    let mut entries = Vec::new();
    for (path, va) in &fa {
        match b_by_path.get(path.as_str()) {
            Some(vb) if *vb == va => {}
            Some(vb) => entries.push(DiffEntry {
                path: path.clone(),
                a: Some(va.clone()),
                b: Some((*vb).to_string()),
            }),
            None => entries.push(DiffEntry {
                path: path.clone(),
                a: Some(va.clone()),
                b: None,
            }),
        }
    }
    for (path, vb) in &fb {
        if !a_paths.contains_key(path.as_str()) {
            entries.push(DiffEntry {
                path: path.clone(),
                a: None,
                b: Some(vb.clone()),
            });
        }
    }
    DiffReport { entries }
}

/// Every hashed field of one sim as `path = value` lines, in hash-layout order, so a
/// state at a tick can be saved on one machine and compared with another's.
pub fn dump(sim: &Sim) -> String {
    let mut out = String::new();
    for (path, value) in hash::debug_fields(sim) {
        out.push_str(&path);
        out.push_str(" = ");
        out.push_str(&value);
        out.push('\n');
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::AgentId;

    /// The empty Phase 0 record for a seed, through the one constructor.
    fn sim(seed: u64) -> Sim {
        Sim::new(&crate::MatchRecord::seed_only(seed))
    }

    #[test]
    fn identical_sims_diff_empty_and_dump_identically() {
        let mut a = sim(99);
        let mut b = sim(99);
        for _ in 0..50 {
            a.step();
            b.step();
        }
        let d = diff(&a, &b);
        assert!(d.is_empty(), "{d}");
        assert_eq!(d.to_string(), "");
        assert_eq!(dump(&a), dump(&b));
        assert_eq!(a.state_hash(), b.state_hash());
    }

    #[test]
    fn differing_sims_list_every_changed_field_in_layout_order() {
        let a = sim(99);
        let mut b = sim(99);
        b.step();
        let d = diff(&a, &b);
        let paths: Vec<&str> = d.entries.iter().map(|e| e.path.as_str()).collect();
        assert_eq!(
            paths,
            [
                "tick",
                "agents[1].pos.x",
                "agents[1].pos.y",
                "agents[2].pos.x",
                "agents[2].pos.y",
            ]
        );
        assert_eq!(d.entries[0].a.as_deref(), Some("0"));
        assert_eq!(d.entries[0].b.as_deref(), Some("1"));
        assert!(d.to_string().starts_with("tick: 0 vs 1\n"), "{d}");
        // The report reads the same both times.
        assert_eq!(diff(&a, &b), d);
    }

    #[test]
    fn a_field_present_on_one_side_only_is_reported_absent_on_the_other() {
        let a = sim(1);
        let mut b = sim(1);
        b.world.agents.remove(&AgentId(2));
        let d = diff(&a, &b);
        let paths: Vec<&str> = d.entries.iter().map(|e| e.path.as_str()).collect();
        assert_eq!(paths, ["agents.len", "agents[2].pos.x", "agents[2].pos.y"]);
        assert_eq!(d.entries[1].b, None);
        assert!(d
            .to_string()
            .contains("agents[2].pos.x: 10 (0x0000000a00000000) vs <absent>"));
        let back = diff(&b, &a);
        assert_eq!(back.entries[1].a, None);
        assert_eq!(back.entries[1].b, d.entries[1].a);
    }

    #[test]
    fn dump_renders_the_hashed_fields_as_lines() {
        let s = sim(3);
        let text = dump(&s);
        let lines: Vec<&str> = text.lines().collect();
        assert_eq!(lines[0], "seed = 3");
        assert_eq!(lines[1], "tick = 0");
        assert_eq!(lines[2], "inject_fold = 0x0000000000000000");
        assert_eq!(lines[3], "agents.len = 2");
        assert!(lines[4].starts_with("agents[1].pos.x = "));
        assert_eq!(lines.len(), 8);
    }
}
