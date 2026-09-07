//! Desync canary: two `Sim`s from one `MatchRecord`, both through `Sim::new` and nothing
//! else, stepped in lockstep, hashes compared every tick (BLD-33). On the first
//! divergence, report the tick, both hashes, and the structural diff from
//! `blindside_sim::diagnostics`.
//!
//! Both instances live in ONE process on purpose: std's `RandomState` is randomised per
//! `HashMap`, so a HashMap-iteration bug shows up as two instances disagreeing, which is
//! what the BLD-35 fixture reproduces. `--injected` arms `Sim::set_inject_tick` in BOTH
//! instances for one tick. On that tick each instance, inside its own `step`, builds a
//! fresh `std::collections::HashMap` and folds its iteration order into a hashed field --
//! the rule-2 violation from DETERMINISM.md, done the way a real bug would do it: in every
//! instance, independently, with whatever order that instance's hasher key produced. The
//! acceptance criterion is that the reported divergence tick equals the injection tick.
//! The fixture exists only in builds with the sim's `inject-desync` feature; without it
//! arming is an error (exit 2), never a silent pass.

use std::fmt;
use std::path::Path;
use std::time::{Duration, Instant};

use blindside_sim::diagnostics::{self, DiffReport};
use blindside_sim::{InjectDesyncUnavailable, Sim, Tick};
use serde::{Deserialize, Serialize};

use crate::record::{Cadence, HashLog, HexHash, MatchRecord};

/// One line of a structural state diff: the serde-able twin of
/// `blindside_sim::diagnostics::DiffEntry`. `a`/`b` is `None` when only the other
/// instance has the field.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct DiffEntry {
    pub path: String,
    pub a: Option<String>,
    pub b: Option<String>,
}

impl From<&diagnostics::DiffEntry> for DiffEntry {
    fn from(e: &diagnostics::DiffEntry) -> DiffEntry {
        DiffEntry {
            path: e.path.clone(),
            a: e.a.clone(),
            b: e.b.clone(),
        }
    }
}

/// A sim diff report as harness entries, in the report's (hash-layout) order.
pub fn entries(report: &DiffReport) -> Vec<DiffEntry> {
    report.entries.iter().map(DiffEntry::from).collect()
}

/// The injection that was armed, recorded so a divergence can be re-run
/// (`harness bisect --from-divergence`). The iteration orders themselves are not
/// observable from outside the sim -- and are different on every run, which is the point.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Injection {
    pub tick: u64,
}

/// What `harness canary` writes to `divergence.json` on failure. Carries the record it
/// ran, so the file alone is enough to re-run it.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Divergence {
    pub record: MatchRecord,
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

/// Render a diff with `a`/`b` as the side labels, two spaces in.
pub fn write_diff(f: &mut fmt::Formatter<'_>, diff: &[DiffEntry], a: &str, b: &str) -> fmt::Result {
    for d in diff {
        match (&d.a, &d.b) {
            (Some(va), Some(vb)) => {
                writeln!(f, "  {}", d.path)?;
                writeln!(f, "      {a}: {va}")?;
                writeln!(f, "      {b}: {vb}")?;
            }
            (Some(va), None) => {
                writeln!(f, "  {}  (only in {})", d.path, a.trim())?;
                writeln!(f, "      {a}: {va}")?;
            }
            (None, Some(vb)) => {
                writeln!(f, "  {}  (only in {})", d.path, b.trim())?;
                writeln!(f, "      {b}: {vb}")?;
            }
            (None, None) => writeln!(f, "  {}  (absent on both sides)", d.path)?,
        }
    }
    Ok(())
}

/// A diff as printable text with the given side labels (what `write_diff` renders).
pub struct DiffText<'a>(pub &'a [DiffEntry], pub &'a str, pub &'a str);

impl fmt::Display for DiffText<'_> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write_diff(f, self.0, self.1, self.2)
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
                "  diagnostics::diff is empty: the hash covers something the dump does not \
                 (fix hash.rs; they must cover the same fields)"
            )?;
        } else {
            writeln!(f, "  {} differing field(s):", self.diff.len())?;
            write_diff(f, &self.diff, "A", "B")?;
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

/// Request to arm the BLD-35 fixture in both instances for `tick`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Inject {
    pub tick: u64,
}

/// Why the canary could not run (exit 2). A divergence is not an error; it is the
/// result, in [`CanaryRun::outcome`].
#[derive(Debug)]
pub enum CanaryError {
    /// `--injected` on a build whose sim has no fixture.
    InjectUnavailable(InjectDesyncUnavailable),
    /// Tick 0 is the constructed state and cannot be produced by a step; a tick past the
    /// run would never fire.
    InjectTickOutOfRange { tick: u64, ticks: u64 },
    /// The record failed the sim's rules.
    InvalidRecord(String),
}

impl fmt::Display for CanaryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CanaryError::InjectUnavailable(e) => write!(f, "--injected: {e}"),
            CanaryError::InjectTickOutOfRange { tick, ticks } => write!(
                f,
                "--inject-tick {tick} must be in 1..={ticks} (tick 0 is the constructed state; nothing steps into it)"
            ),
            CanaryError::InvalidRecord(e) => write!(f, "record: {e}"),
        }
    }
}

impl std::error::Error for CanaryError {}

/// A completed canary run: instance A's hash log on the requested cadence (up to and
/// including the divergent tick, if any), the wall-clock, and the verdict.
#[derive(Debug)]
pub struct CanaryRun {
    pub log: HashLog,
    pub elapsed: Duration,
    pub outcome: Result<CanaryOk, Box<Divergence>>,
}

/// Run the canary over the record's tick count. Both instances are `Sim::new(&record)`.
/// With `inject = Some(..)`, both are armed for the injection tick before the run starts;
/// each fires inside its own `step` on that tick, and the comparison after that step is
/// where the divergence must show. Hashes are compared every tick regardless of `every`,
/// which only thins the log.
///
/// `on_inject` is called with the tick once both instances have stepped through it, so
/// the CLI can report it.
pub fn run(
    rec: &MatchRecord,
    inject: Option<Inject>,
    every: u64,
    mut on_inject: impl FnMut(u64),
) -> Result<CanaryRun, CanaryError> {
    let sim_rec = rec.to_sim().map_err(CanaryError::InvalidRecord)?;
    let ticks = sim_rec.ticks;
    let cadence = Cadence::new(every, ticks);
    let mut a = Sim::new(&sim_rec);
    let mut b = Sim::new(&sim_rec);
    if let Some(inj) = &inject {
        if inj.tick == 0 || inj.tick > ticks {
            return Err(CanaryError::InjectTickOutOfRange {
                tick: inj.tick,
                ticks,
            });
        }
        a.set_inject_tick(Some(Tick(inj.tick)))
            .map_err(CanaryError::InjectUnavailable)?;
        b.set_inject_tick(Some(Tick(inj.tick)))
            .map_err(CanaryError::InjectUnavailable)?;
    }
    let mut log = HashLog::default();
    let start = Instant::now();
    for t in 0..=ticks {
        if t > 0 {
            a.step();
            b.step();
        }
        debug_assert_eq!(a.tick().0, t);
        debug_assert_eq!(b.tick().0, t);
        if inject.as_ref().is_some_and(|i| i.tick == t) {
            on_inject(t);
        }
        let ha = a.state_hash();
        let hb = b.state_hash();
        if ha != hb {
            log.push(t, HexHash(ha));
            return Ok(CanaryRun {
                log,
                elapsed: start.elapsed(),
                outcome: Err(Box::new(Divergence {
                    record: rec.clone(),
                    tick: t,
                    hash_a: HexHash(ha),
                    hash_b: HexHash(hb),
                    diff: entries(&diagnostics::diff(&a, &b)),
                    injection: inject
                        .as_ref()
                        .filter(|i| i.tick <= t)
                        .map(|i| Injection { tick: i.tick }),
                })),
            });
        }
        if cadence.keeps(t) {
            log.push(t, HexHash(ha));
        }
    }
    Ok(CanaryRun {
        log,
        elapsed: start.elapsed(),
        outcome: Ok(CanaryOk {
            ticks,
            final_hash: HexHash(a.state_hash()),
        }),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rec(seed: u64, ticks: u64) -> MatchRecord {
        MatchRecord::empty(seed, ticks, HexHash([0; 32]))
    }

    fn desync(r: Result<CanaryRun, CanaryError>) -> Box<Divergence> {
        match r {
            Ok(CanaryRun {
                outcome: Err(d), ..
            }) => d,
            other => panic!("expected a desync, got {other:?}"),
        }
    }

    #[test]
    fn the_test_build_carries_the_fixture() {
        // The dev-dependency enables the sim's `inject-desync` for this crate's tests, so
        // the injection tests below exercise the real HashMap path, not a stub.
        assert!(Sim::inject_desync_available());
    }

    #[test]
    fn injection_is_caught_in_the_same_tick_and_names_the_field() {
        for inject_at in [1u64, 250, 1000] {
            let mut seen = None;
            let r = run(&rec(5, 1000), Some(Inject { tick: inject_at }), 1, |t| {
                seen = Some(t)
            });
            let d = desync(r);
            assert_eq!(seen, Some(inject_at));
            assert_eq!(d.tick, inject_at, "caught in a later tick");
            assert_eq!(d.injection, Some(Injection { tick: inject_at }));
            assert_eq!(d.record.seed, 5);
            // The RNG is stateless and the fold touches one field, so the diff is exactly
            // that field: two instances, two HashMap orders, two folds.
            let paths: Vec<&str> = d.diff.iter().map(|e| e.path.as_str()).collect();
            assert_eq!(paths, ["inject_fold"], "{d}");
            assert_ne!(d.diff[0].a, d.diff[0].b);
        }
    }

    #[test]
    fn injection_fires_every_time_over_twenty_runs() {
        // BLD-35: "run 20x locally: the injection fires every time".
        for i in 0..20u64 {
            let d = desync(run(&rec(100 + i, 40), Some(Inject { tick: 20 }), 1, |_| {}));
            assert_eq!(d.tick, 20, "run {i}");
        }
    }

    #[test]
    fn inject_tick_zero_or_past_the_run_is_refused() {
        assert!(matches!(
            run(&rec(1, 10), Some(Inject { tick: 0 }), 1, |_| {}),
            Err(CanaryError::InjectTickOutOfRange { tick: 0, ticks: 10 })
        ));
        assert!(matches!(
            run(&rec(1, 10), Some(Inject { tick: 11 }), 1, |_| {}),
            Err(CanaryError::InjectTickOutOfRange {
                tick: 11,
                ticks: 10
            })
        ));
    }

    #[test]
    fn a_record_with_inputs_is_refused_not_run() {
        let mut r = rec(1, 10);
        r.commands.push(serde_json::json!({}));
        assert!(matches!(
            run(&r, None, 1, |_| {}),
            Err(CanaryError::InvalidRecord(_))
        ));
    }

    #[test]
    fn divergence_round_trips_through_json() {
        let d = desync(run(&rec(5, 100), Some(Inject { tick: 40 }), 1, |_| {}));
        let text = serde_json::to_string(&d).unwrap();
        let back: Divergence = serde_json::from_str(&text).unwrap();
        assert_eq!(back, *d);
        assert!(d.to_string().contains("inject_fold"), "{d}");
    }

    #[test]
    fn clean_run_passes_and_logs_on_the_cadence() {
        let r = run(&rec(5, 2000), None, 1, |_| panic!("no injection expected")).unwrap();
        let ok = r.outcome.unwrap();
        assert_eq!(ok.ticks, 2000);
        assert_eq!(r.log.len(), 2001);
        assert_eq!(r.log.last().unwrap(), (2000, ok.final_hash));
        let r = run(&rec(5, 2000), None, 500, |_| {}).unwrap();
        let ticks: Vec<u64> = r.log.entries.iter().map(|&(t, _)| t).collect();
        assert_eq!(ticks, [0, 500, 1000, 1500, 2000]);
        // A divergent run's log ends at the divergent tick, with A's hash.
        let r = run(&rec(5, 2000), Some(Inject { tick: 777 }), 500, |_| {}).unwrap();
        let d = r.outcome.unwrap_err();
        assert_eq!(r.log.last().unwrap(), (777, d.hash_a));
    }
}
