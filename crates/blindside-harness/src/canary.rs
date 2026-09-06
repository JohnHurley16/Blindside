//! Desync canary: two `Sim`s from identical inputs, stepped in lockstep, hashes compared
//! every tick. On the first divergence, report the tick, both hashes, and a structural
//! diff of `state_debug()`.
//!
//! `--inject` deliberately corrupts instance B on one tick using an ordering obtained by
//! iterating a `std::collections::HashMap` (the classic rule-2 violation), and the
//! acceptance criterion is that the reported divergence tick equals the injection tick.

use std::collections::{HashMap, HashSet};
use std::fmt;
use std::path::Path;

use blindside_sim::{Fx, Sim};
use serde::{Deserialize, Serialize};

use crate::record::HexHash;

/// One line of a structural state diff.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind")]
pub enum DiffEntry {
    Changed { path: String, a: String, b: String },
    OnlyA { path: String, a: String },
    OnlyB { path: String, b: String },
}

/// Field-by-field diff of two `state_debug()` dumps, in A's field order, with fields
/// only B has appended.
pub fn diff_debug(a: &[(String, String)], b: &[(String, String)]) -> Vec<DiffEntry> {
    let b_by_path: HashMap<&str, &str> = b.iter().map(|(k, v)| (k.as_str(), v.as_str())).collect();
    let a_paths: HashSet<&str> = a.iter().map(|(k, _)| k.as_str()).collect();
    let mut out = Vec::new();
    for (path, va) in a {
        match b_by_path.get(path.as_str()) {
            Some(vb) if *vb == va => {}
            Some(vb) => out.push(DiffEntry::Changed {
                path: path.clone(),
                a: va.clone(),
                b: (*vb).to_string(),
            }),
            None => out.push(DiffEntry::OnlyA {
                path: path.clone(),
                a: va.clone(),
            }),
        }
    }
    for (path, vb) in b {
        if !a_paths.contains(path.as_str()) {
            out.push(DiffEntry::OnlyB {
                path: path.clone(),
                b: vb.clone(),
            });
        }
    }
    out
}

/// The perturbation that was applied to instance B, recorded so a divergence can be
/// re-run exactly (`harness bisect --from-divergence`).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Injection {
    pub tick: u64,
    /// Entity ordering applied; this is what the HashMap iteration produced.
    pub order: Vec<u32>,
}

/// What `harness canary` writes to `divergence.json` on failure.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Divergence {
    pub seed: u64,
    /// Tick count the canary was asked for.
    pub ticks: u64,
    pub tick: u64,
    pub hash_a: HexHash,
    pub hash_b: HexHash,
    pub diff: Vec<DiffEntry>,
    #[serde(default)]
    pub injection: Option<Injection>,
}

impl Divergence {
    pub fn load(path: &Path) -> Result<Divergence, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        serde_json::from_str(&text)
            .map_err(|e| format!("{} is not a divergence file: {e}", path.display()))
    }

    pub fn save(&self, path: &Path) -> Result<(), String> {
        let text = serde_json::to_string_pretty(self).map_err(|e| e.to_string())?;
        std::fs::write(path, text).map_err(|e| format!("cannot write {}: {e}", path.display()))
    }
}

impl fmt::Display for Divergence {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        writeln!(f, "DESYNC at tick {}", self.tick)?;
        writeln!(f, "  hash A: {}", self.hash_a)?;
        writeln!(f, "  hash B: {}", self.hash_b)?;
        if self.diff.is_empty() {
            writeln!(
                f,
                "  state_debug() is identical: the hash covers something the debug dump \
                 does not (fix hash.rs; they must cover the same fields)"
            )?;
        } else {
            writeln!(f, "  {} differing field(s):", self.diff.len())?;
            for d in &self.diff {
                match d {
                    DiffEntry::Changed { path, a, b } => {
                        writeln!(f, "  {path}")?;
                        writeln!(f, "      A: {a}")?;
                        writeln!(f, "      B: {b}")?;
                    }
                    DiffEntry::OnlyA { path, a } => {
                        writeln!(f, "  {path}  (only in A)")?;
                        writeln!(f, "      A: {a}")?;
                    }
                    DiffEntry::OnlyB { path, b } => {
                        writeln!(f, "  {path}  (only in B)")?;
                        writeln!(f, "      B: {b}")?;
                    }
                }
            }
        }
        Ok(())
    }
}

impl std::error::Error for Divergence {}

#[derive(Clone, Debug)]
pub struct CanaryOk {
    pub ticks: u64,
    pub final_hash: HexHash,
}

/// Entity IDs the perturbation can target, read off the public debug dump (the harness
/// has no other view of the sim, and must not). Paths look like `agents[7].pos.x`.
fn entity_ids_from_debug(debug: &[(String, String)]) -> Vec<u32> {
    let mut ids = Vec::new();
    for (path, _) in debug {
        if let Some(rest) = path.strip_prefix("agents[") {
            if let Some(end) = rest.find(']') {
                if let Ok(id) = rest[..end].parse::<u32>() {
                    if !ids.contains(&id) {
                        ids.push(id);
                    }
                }
            }
        }
    }
    ids
}

/// Corrupt `b` the way a HashMap-iterating sim would: derive an entity ordering from a
/// `HashMap` and apply it to the state. Returns the ordering used and the number of agents
/// touched. With `order = Some(..)` the given ordering is applied instead, which is how a
/// recorded divergence is replayed exactly.
fn inject_b(b: &mut Sim, order: Option<Vec<u32>>) -> (Vec<u32>, usize) {
    let order = order.unwrap_or_else(|| {
        let mut by_id: HashMap<u32, Fx> = HashMap::new();
        for id in entity_ids_from_debug(&b.state_debug()) {
            by_id.insert(id, Fx::from_num(id));
        }
        // The values are irrelevant; the bug being modelled is that the ORDER below is
        // whatever the hasher's random key produced in this process.
        by_id.keys().copied().collect()
    });
    let touched = b.perturb_for_test(&order);
    (order, touched)
}

/// Request to perturb instance B on `tick`. `order = None` derives the ordering from a
/// HashMap (the real test); `Some` replays a recorded ordering.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Inject {
    pub tick: u64,
    pub order: Option<Vec<u32>>,
}

/// Run the canary for `ticks` ticks. With `inject = Some(..)`, instance B is perturbed
/// immediately after both instances reach the injection tick (before that tick's
/// comparison).
///
/// `on_inject` is called with (tick, ordering, agents touched) when the injection
/// happens so the CLI can report it.
pub fn run(
    seed: u64,
    ticks: u64,
    inject: Option<Inject>,
    mut on_inject: impl FnMut(u64, &[u32], usize),
) -> Result<CanaryOk, Box<Divergence>> {
    let mut a = Sim::new(seed);
    let mut b = Sim::new(seed);
    let mut injection = None;
    for t in 0..=ticks {
        if t > 0 {
            a.step();
            b.step();
        }
        debug_assert_eq!(a.tick().0, t);
        debug_assert_eq!(b.tick().0, t);
        if let Some(inj) = inject.as_ref().filter(|i| i.tick == t) {
            let (order, touched) = inject_b(&mut b, inj.order.clone());
            on_inject(t, &order, touched);
            injection = Some(Injection { tick: t, order });
        }
        let ha = a.state_hash();
        let hb = b.state_hash();
        if ha != hb {
            return Err(Box::new(Divergence {
                seed,
                ticks,
                tick: t,
                hash_a: HexHash(ha),
                hash_b: HexHash(hb),
                diff: diff_debug(&a.state_debug(), &b.state_debug()),
                injection,
            }));
        }
    }
    Ok(CanaryOk {
        ticks,
        final_hash: HexHash(a.state_hash()),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn kv(pairs: &[(&str, &str)]) -> Vec<(String, String)> {
        pairs
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect()
    }

    #[test]
    fn diff_reports_changed_and_one_sided_fields() {
        let a = kv(&[("tick", "1"), ("x", "same"), ("y", "1"), ("only_a", "z")]);
        let b = kv(&[("tick", "1"), ("x", "same"), ("y", "2"), ("only_b", "w")]);
        let d = diff_debug(&a, &b);
        assert_eq!(
            d,
            vec![
                DiffEntry::Changed {
                    path: "y".into(),
                    a: "1".into(),
                    b: "2".into()
                },
                DiffEntry::OnlyA {
                    path: "only_a".into(),
                    a: "z".into()
                },
                DiffEntry::OnlyB {
                    path: "only_b".into(),
                    b: "w".into()
                },
            ]
        );
    }

    #[test]
    fn entity_ids_are_parsed_from_debug_paths() {
        let s = Sim::new(1);
        let ids = entity_ids_from_debug(&s.state_debug());
        assert_eq!(ids, vec![1, 2]);
    }

    #[test]
    fn injection_is_caught_in_the_same_tick() {
        for inject_at in [0u64, 1, 250, 1000] {
            let mut seen = None;
            let r = run(
                5,
                1000,
                Some(Inject {
                    tick: inject_at,
                    order: None,
                }),
                |t, _, touched| {
                    assert!(touched > 0);
                    seen = Some(t);
                },
            );
            let d = r.expect_err("injected canary must diverge");
            assert_eq!(seen, Some(inject_at));
            assert_eq!(d.tick, inject_at);
            assert!(!d.diff.is_empty());
            assert_eq!(d.injection.as_ref().map(|i| i.tick), Some(inject_at));
        }
    }

    #[test]
    fn divergence_round_trips_through_json() {
        let d = run(
            5,
            100,
            Some(Inject {
                tick: 40,
                order: Some(vec![2, 1]),
            }),
            |_, _, _| {},
        )
        .unwrap_err();
        assert_eq!(d.injection.as_ref().unwrap().order, vec![2, 1]);
        let text = serde_json::to_string(&d).unwrap();
        let back: Divergence = serde_json::from_str(&text).unwrap();
        assert_eq!(back, *d);
    }

    #[test]
    fn clean_run_passes() {
        let ok = run(5, 2000, None, |_, _, _| panic!("no injection expected")).unwrap();
        assert_eq!(ok.ticks, 2000);
    }
}
