//! Bisect: locate the first tick at which a local re-run disagrees with a hash log
//! recorded elsewhere (another run, another OS), then re-run to that tick on a fresh
//! instance and dump the state there.
//!
//! The recorded side contributes hashes only, never state, so the diff printed at the
//! divergence tick is the LOCAL instance's state change across that tick (`t-1` -> `t`):
//! the fields that moved during the tick that first disagreed. That is the list of
//! suspects the tick number alone does not give you.
//!
//! When the divergence came from the canary (`divergence.json`), both sides' states were
//! in one process and the file carries their field-level diff; `reproduce` re-runs it.

use std::fmt;

use blindside_sim::Sim;

use crate::canary::{self, diff_debug, CanaryOk, DiffEntry, Divergence, Inject};
use crate::record::{HashLog, HexHash, MatchRecord};
use crate::runner::{check_log, sim_from_record};

/// How the divergent tick was found.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SearchMode {
    /// The final hash differed, so the log was bisected under the assumption that a
    /// desync never heals: `tick - 1` matches and `tick` differs.
    Binary,
    /// The final hash matched, so the mismatch is transient (the log re-converges
    /// later). Found by a single linear pass; it is the globally first mismatch.
    Linear,
}

impl fmt::Display for SearchMode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            SearchMode::Binary => "binary search",
            SearchMode::Linear => "linear scan (transient mismatch: final hash matches)",
        })
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Located {
    Clean {
        ticks: u64,
    },
    Divergent {
        tick: u64,
        recorded: HexHash,
        local: HexHash,
        mode: SearchMode,
        /// Number of fresh re-runs performed to locate the tick.
        probes: u64,
    },
}

fn hash_at(rec: &MatchRecord, tick: u64) -> HexHash {
    let mut sim = sim_from_record(rec);
    for _ in 0..tick {
        sim.step();
    }
    HexHash(sim.state_hash())
}

struct Prober<'a> {
    rec: &'a MatchRecord,
    log: &'a HashLog,
    probes: u64,
}

impl Prober<'_> {
    /// Fresh instance to `tick`; if its hash differs from the log, return it.
    fn differs(&mut self, tick: u64) -> Option<HexHash> {
        self.probes += 1;
        let local = hash_at(self.rec, tick);
        (local != self.log.hashes[tick as usize]).then_some(local)
    }
}

/// Find the first tick whose local hash differs from `log`. `Err` is structural (the log
/// does not belong to the record).
pub fn locate(rec: &MatchRecord, log: &HashLog) -> Result<Located, String> {
    check_log(rec, log)?;
    let n = rec.ticks;
    let mut p = Prober {
        rec,
        log,
        probes: 0,
    };

    if let Some(local) = p.differs(n) {
        // A real desync stays desynced, so the mismatch predicate is monotone in tick and
        // a binary search finds the boundary.
        if let Some(local0) = p.differs(0) {
            return Ok(Located::Divergent {
                tick: 0,
                recorded: log.hashes[0],
                local: local0,
                mode: SearchMode::Binary,
                probes: p.probes,
            });
        }
        let (mut lo, mut hi, mut hi_local) = (0u64, n, local);
        while hi - lo > 1 {
            let mid = lo + (hi - lo) / 2;
            match p.differs(mid) {
                Some(l) => {
                    hi = mid;
                    hi_local = l;
                }
                None => lo = mid,
            }
        }
        return Ok(Located::Divergent {
            tick: hi,
            recorded: log.hashes[hi as usize],
            local: hi_local,
            mode: SearchMode::Binary,
            probes: p.probes,
        });
    }

    // Final hash agrees. Either the log is clean or a mismatch is transient, which is
    // not the shape of a desync (it is the shape of a corrupt or edited log), so the
    // monotone assumption is off and one linear pass is the honest answer.
    let mut sim = sim_from_record(rec);
    for t in 0..=n {
        if t > 0 {
            sim.step();
        }
        let local = HexHash(sim.state_hash());
        if local != log.hashes[t as usize] {
            return Ok(Located::Divergent {
                tick: t,
                recorded: log.hashes[t as usize],
                local,
                mode: SearchMode::Linear,
                probes: p.probes + 1,
            });
        }
    }
    Ok(Located::Clean { ticks: n })
}

/// The local instance at one tick, plus what changed across the tick that reached it.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StateAtTick {
    pub tick: u64,
    pub hash: HexHash,
    /// `state_debug()` at `tick`.
    pub state: Vec<(String, String)>,
    /// Diff of `state_debug()` from `tick - 1` (A) to `tick` (B). Empty at tick 0.
    pub step_diff: Vec<DiffEntry>,
}

/// Fresh instance from `rec`, run to `tick`.
pub fn replay_to(rec: &MatchRecord, tick: u64) -> StateAtTick {
    replay_sim_to(sim_from_record(rec), tick)
}

fn replay_sim_to(mut sim: Sim, tick: u64) -> StateAtTick {
    let mut before = None;
    for t in 1..=tick {
        if t == tick {
            before = Some(sim.state_debug());
        }
        sim.step();
    }
    let state = sim.state_debug();
    let step_diff = match &before {
        Some(b) => diff_debug(b, &state),
        None => Vec::new(),
    };
    StateAtTick {
        tick,
        hash: HexHash(sim.state_hash()),
        state,
        step_diff,
    }
}

impl fmt::Display for StateAtTick {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        writeln!(f, "local state at tick {} (hash {}):", self.tick, self.hash)?;
        for (path, value) in &self.state {
            writeln!(f, "  {path} = {value}")?;
        }
        if self.tick == 0 {
            writeln!(f, "tick 0 is the constructed state; nothing stepped yet")?;
        } else if self.step_diff.is_empty() {
            writeln!(
                f,
                "no field changed across tick {} -> {}",
                self.tick - 1,
                self.tick
            )?;
        } else {
            writeln!(
                f,
                "{} field(s) changed across tick {} -> {} (suspects):",
                self.step_diff.len(),
                self.tick - 1,
                self.tick
            )?;
            for d in &self.step_diff {
                match d {
                    DiffEntry::Changed { path, a, b } => {
                        writeln!(f, "  {path}")?;
                        writeln!(f, "      before: {a}")?;
                        writeln!(f, "      after : {b}")?;
                    }
                    DiffEntry::OnlyA { path, a } => {
                        writeln!(f, "  {path}  (removed)")?;
                        writeln!(f, "      before: {a}")?;
                    }
                    DiffEntry::OnlyB { path, b } => {
                        writeln!(f, "  {path}  (added)")?;
                        writeln!(f, "      after : {b}")?;
                    }
                }
            }
        }
        Ok(())
    }
}

/// Result of re-running a canary divergence from `divergence.json`.
#[derive(Clone, Debug)]
pub struct Reproduction {
    /// Fresh single instance (never perturbed) run to the divergence tick.
    pub local: StateAtTick,
    pub matches_a: bool,
    pub matches_b: bool,
    /// Present when the divergence file records an injection: the canary re-run with
    /// exactly that injection (same tick, same ordering).
    pub rerun: Option<Result<CanaryOk, Box<Divergence>>>,
}

impl Reproduction {
    /// Did the local re-run confirm the recorded divergence? Without an injection the
    /// other process cannot be re-run, so the recorded diff stands as is.
    pub fn reproduced(&self, original: &Divergence) -> bool {
        match &self.rerun {
            None => true,
            Some(Err(d)) => {
                d.tick == original.tick
                    && d.hash_a == original.hash_a
                    && d.hash_b == original.hash_b
            }
            Some(Ok(_)) => false,
        }
    }
}

pub fn reproduce(div: &Divergence) -> Reproduction {
    let local = replay_sim_to(Sim::new(div.seed), div.tick);
    let rerun = div.injection.as_ref().map(|inj| {
        canary::run(
            div.seed,
            div.ticks,
            Some(Inject {
                tick: inj.tick,
                order: Some(inj.order.clone()),
            }),
            |_, _, _| {},
        )
    });
    Reproduction {
        matches_a: local.hash == div.hash_a,
        matches_b: local.hash == div.hash_b,
        local,
        rerun,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::runner::record;

    fn flip(h: &mut HexHash) {
        h.0[0] ^= 0x01;
    }

    #[test]
    fn clean_log_is_clean() {
        let (rec, log) = record(7, 400);
        assert_eq!(locate(&rec, &log).unwrap(), Located::Clean { ticks: 400 });
    }

    #[test]
    fn persistent_divergence_is_bisected() {
        // Corrupt every hash from tick 1234 on: the shape of a real desync.
        let (rec, mut log) = record(7, 3000);
        for h in &mut log.hashes[1234..] {
            flip(h);
        }
        match locate(&rec, &log).unwrap() {
            Located::Divergent {
                tick, mode, probes, ..
            } => {
                assert_eq!(tick, 1234);
                assert_eq!(mode, SearchMode::Binary);
                assert!(probes <= 16, "probes {probes}");
            }
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn divergence_at_tick_zero_and_last_tick() {
        let (rec, mut log) = record(7, 50);
        for h in &mut log.hashes {
            flip(h);
        }
        match locate(&rec, &log).unwrap() {
            Located::Divergent { tick, .. } => assert_eq!(tick, 0),
            other => panic!("{other:?}"),
        }
        let (rec, mut log) = record(7, 50);
        flip(&mut log.hashes[50]);
        match locate(&rec, &log).unwrap() {
            Located::Divergent { tick, .. } => assert_eq!(tick, 50),
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn transient_mismatch_falls_back_to_linear() {
        let (rec, mut log) = record(7, 3000);
        flip(&mut log.hashes[1234]);
        match locate(&rec, &log).unwrap() {
            Located::Divergent { tick, mode, .. } => {
                assert_eq!(tick, 1234);
                assert_eq!(mode, SearchMode::Linear);
            }
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn replay_to_reports_the_step_diff() {
        let (rec, log) = record(7, 100);
        let s = replay_to(&rec, 42);
        assert_eq!(s.tick, 42);
        assert_eq!(s.hash, log.hashes[42]);
        assert!(!s.step_diff.is_empty());
        let s0 = replay_to(&rec, 0);
        assert!(s0.step_diff.is_empty());
        assert_eq!(s0.hash, log.hashes[0]);
    }

    #[test]
    fn injected_divergence_is_reproduced_exactly() {
        let div = canary::run(
            5,
            800,
            Some(Inject {
                tick: 333,
                order: None,
            }),
            |_, _, _| {},
        )
        .unwrap_err();
        let r = reproduce(&div);
        assert!(r.matches_a, "fresh instance is instance A");
        assert!(!r.matches_b);
        assert!(r.reproduced(&div));
        let again = r.rerun.unwrap().unwrap_err();
        assert_eq!(again.tick, 333);
        assert_eq!(again.diff, div.diff);
    }
}
