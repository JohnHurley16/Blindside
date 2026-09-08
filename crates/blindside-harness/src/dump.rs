//! State dumps as files, and the diff of two of them (BLD-36 `diff-dumps`).
//!
//! A dump is `blindside_sim::diagnostics::dump` written to disk: one `path = value` line
//! per hashed field, in hash-layout order. It is the only form in which a state crosses
//! a machine boundary -- strings, produced inside the sim behind the `diagnostics`
//! feature -- so two machines that disagree at a tick each write theirs and this module
//! diffs them without either machine's `Sim`. The diff has the same shape as the canary's
//! (`DiffEntry`): A's fields in A's order, then fields only B has.

use std::path::Path;

use crate::canary::DiffEntry;

/// A parsed dump: `(path, value)` in file order.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Dump {
    pub fields: Vec<(String, String)>,
}

impl Dump {
    /// Parse `path = value` lines. Blank lines are ignored; a `\r` before the newline is
    /// tolerated. The first ` = ` splits path from value, so a value may contain one.
    pub fn parse(text: &str) -> Result<Dump, String> {
        let mut fields = Vec::new();
        for (i, raw) in text.lines().enumerate() {
            let line = raw.trim_end_matches('\r');
            if line.is_empty() {
                continue;
            }
            let (path, value) = line
                .split_once(" = ")
                .ok_or_else(|| format!("line {}: expected `path = value`, got `{line}`", i + 1))?;
            fields.push((path.to_string(), value.to_string()));
        }
        Ok(Dump { fields })
    }

    pub fn load(path: &Path) -> Result<Dump, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        Dump::parse(&text).map_err(|e| format!("{}: {e}", path.display()))
    }
}

/// Field-level diff of two dumps, in `a`'s order then `b`-only fields in `b`'s order.
/// Identical dumps yield an empty list.
pub fn diff(a: &Dump, b: &Dump) -> Vec<DiffEntry> {
    let mut entries = Vec::new();
    for (path, va) in &a.fields {
        match b.fields.iter().find(|(p, _)| p == path) {
            Some((_, vb)) if vb == va => {}
            Some((_, vb)) => entries.push(DiffEntry {
                path: path.clone(),
                a: Some(va.clone()),
                b: Some(vb.clone()),
            }),
            None => entries.push(DiffEntry {
                path: path.clone(),
                a: Some(va.clone()),
                b: None,
            }),
        }
    }
    for (path, vb) in &b.fields {
        if !a.fields.iter().any(|(p, _)| p == path) {
            entries.push(DiffEntry {
                path: path.clone(),
                a: None,
                b: Some(vb.clone()),
            });
        }
    }
    entries
}

#[cfg(test)]
mod tests {
    use super::*;
    use blindside_sim::diagnostics;
    use blindside_sim::Sim;

    use crate::record::{HexHash, MatchRecord};

    fn sim(seed: u64, ticks: u64) -> Sim {
        let rec = MatchRecord::empty(seed, ticks, HexHash([0; 32]))
            .to_sim()
            .unwrap();
        let mut s = Sim::new(&rec);
        for _ in 0..ticks {
            s.step();
        }
        s
    }

    #[test]
    fn a_dump_parses_to_the_fields_the_sim_rendered() {
        let s = sim(3, 5);
        let text = diagnostics::dump(&s);
        let d = Dump::parse(&text).unwrap();
        assert_eq!(d.fields.len(), 8);
        assert_eq!(d.fields[0], ("seed".to_string(), "3".to_string()));
        assert_eq!(d.fields[1], ("tick".to_string(), "5".to_string()));
        assert!(d.fields[4].1.contains("(0x"), "{:?}", d.fields[4]);
        // CRLF on the way in is fine.
        assert_eq!(Dump::parse(&text.replace('\n', "\r\n")).unwrap(), d);
        assert!(Dump::parse("tick 5\n").is_err());
    }

    #[test]
    fn diff_of_two_dumps_matches_the_in_process_diff() {
        let a = sim(7, 42);
        let b = sim(8, 42);
        let da = Dump::parse(&diagnostics::dump(&a)).unwrap();
        let db = Dump::parse(&diagnostics::dump(&b)).unwrap();
        let from_files = diff(&da, &db);
        let in_process = crate::canary::entries(&diagnostics::diff(&a, &b));
        assert_eq!(from_files, in_process);
        assert_eq!(from_files[0].path, "seed");
        assert!(from_files.iter().all(|e| e.path != "tick"));
        assert!(diff(&da, &da).is_empty());
    }

    #[test]
    fn a_field_on_one_side_only_is_reported() {
        let a = Dump::parse("seed = 1\ntick = 2\n").unwrap();
        let b = Dump::parse("seed = 1\nextra = 9\n").unwrap();
        let d = diff(&a, &b);
        assert_eq!(d.len(), 2);
        assert_eq!((d[0].path.as_str(), d[0].b.as_deref()), ("tick", None));
        assert_eq!((d[1].path.as_str(), d[1].a.as_deref()), ("extra", None));
    }
}
