//! Bisect: locate the first tick at which a local re-run disagrees with hashes produced
//! elsewhere (another run, another OS, another build), then dump the local state there
//! (BLD-36).
//!
//! DEFAULT (awaiting designer): bisect semantics are "a replay plus a foreign hash log",
//! the BLD-20 minimum recommendation, and a desync is assumed never to heal, so the
//! mismatch is monotone in tick and the log's entries can be binary-searched with a fresh
//! re-run per probe (about log2(entries) re-runs). A log whose final entry agrees cannot
//! be a desync under that assumption -- it is an edited or corrupt log -- and falls back
//! to one linear pass, which says so.
//!
//! The foreign side is one of two things:
//!
//! - `Foreign::Log`: a plain `tick,hash` log (`record.rs`), possibly recorded every N
//!   ticks. The search narrows to the first differing checkpoint and the last agreeing
//!   one. With a dense log those are adjacent and the tick is exact; with a sparse log the
//!   desync began somewhere in the window between them, and the report says so: the
//!   recorded side contributed hashes only, and there are none in the window to compare.
//!   The local state is dumped at the first differing checkpoint either way.
//! - `Foreign::Injected`: the canary in bisect mode. A third armed instance plays the
//!   foreign side and records its checkpoint log every N ticks (default every tick); the
//!   local instance is armed too, as every instance of a sim with a real HashMap bug
//!   would be. The search narrows to the checkpoint window as above, and then -- because
//!   this foreign side can be re-run -- two fresh armed instances walk the window in
//!   lockstep, comparing every tick, to the exact tick. That walk is what proves the
//!   checkpoint-then-linear machinery end to end (the N=100 test).
//!
//! DEFAULT (awaiting designer): BLD-36 asks that "with a log recorded every N ticks,
//! bisect narrows to the checkpoint then steps linearly to the exact tick". Only
//! `Foreign::Injected` can do that literally: stepping linearly means comparing per tick,
//! and a foreign log recorded every N ticks has no hashes to compare against inside the
//! window -- the exact tick is not recoverable from what the other machine sent. So
//! `Foreign::Log` narrows and then says which window it narrowed to, and tells the reader
//! to re-record the other side with `--hash-every 1`; the checkpoint-then-linear walk (and
//! the N = 100 test the story asks for) lives in injected mode, where the foreign side is
//! a process this binary can re-run. Reporting a false exact tick would be worse than
//! reporting the window.
//!
//! The recorded side contributes hashes only, never state, so the diff printed at the
//! divergence tick is the LOCAL instance's state change across that tick (`t-1` -> `t`):
//! the fields that moved during the tick that first disagreed. In injected mode both
//! sides are in-process and the A-vs-B field diff is printed as well.
//!
//! When the divergence came from the canary (`divergence.json`), the file carries the
//! record and both sides' field-level diff; `reproduce` re-runs it.

use std::fmt;

use blindside_sim::{diagnostics, Sim, Tick};

use crate::canary::{
    self, entries, write_diff, CanaryError, CanaryRun, DiffEntry, Divergence, Inject,
};
use crate::record::{Cadence, HashLog, HexHash, MatchRecord, SimRecord};

/// What the local re-run is compared against.
#[derive(Clone, Copy, Debug)]
pub enum Foreign<'a> {
    Log(&'a HashLog),
    /// Both sides armed for `tick`; the foreign checkpoint log is recorded every `every`.
    Injected {
        tick: u64,
        every: u64,
    },
}

/// How the divergent checkpoint was found.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SearchMode {
    /// The final checkpoint differed, so the log was bisected under the assumption that
    /// a desync never heals.
    Binary,
    /// The final checkpoint matched, so the mismatch is transient (the log re-converges
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

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Search {
    pub mode: SearchMode,
    /// Fresh re-runs performed to find the checkpoint.
    pub probes: u64,
    /// Entries in the checkpoint log.
    pub checkpoints: usize,
}

/// The local instance at one tick, plus what changed across the tick that reached it.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StateAtTick {
    pub tick: u64,
    pub hash: HexHash,
    /// `diagnostics::dump` at `tick`: one `path = value` line per hashed field.
    pub dump: String,
    /// `diagnostics::diff` from `tick - 1` (A) to `tick` (B). Empty at tick 0.
    pub step_diff: Vec<DiffEntry>,
}

/// A located divergence.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Divergent {
    /// The exact divergent tick, or -- when `exact` is false -- the first differing
    /// checkpoint.
    pub tick: u64,
    pub exact: bool,
    /// The last tick both sides are known to agree on, if any.
    pub agreed: Option<u64>,
    /// Foreign and local hashes at `tick`.
    pub foreign: HexHash,
    pub local: HexHash,
    pub search: Search,
    /// Injected mode: the checkpoint window walked in lockstep to find the exact tick.
    pub walked: Option<(u64, u64)>,
    /// Injected mode: the A-vs-B field diff at `tick`.
    pub pair_diff: Option<Vec<DiffEntry>>,
    /// The local instance at `tick`.
    pub state: StateAtTick,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Located {
    Clean { ticks: u64, checkpoints: usize },
    Divergent(Box<Divergent>),
}

fn local_sim(rec: &SimRecord, inject: Option<u64>) -> Result<Sim, String> {
    let mut sim = Sim::new(rec);
    if let Some(t) = inject {
        sim.set_inject_tick(Some(Tick(t)))
            .map_err(|e| format!("--injected: {e}"))?;
    }
    Ok(sim)
}

fn step_to(sim: &mut Sim, tick: u64) {
    while sim.tick().0 < tick {
        sim.step();
    }
}

/// Fresh local instance to `tick`; its hash.
fn hash_at(rec: &SimRecord, inject: Option<u64>, tick: u64) -> Result<HexHash, String> {
    let mut sim = local_sim(rec, inject)?;
    step_to(&mut sim, tick);
    Ok(HexHash(sim.state_hash()))
}

/// The foreign checkpoint log: the given one, checked against the record, or a fresh
/// armed instance's on the requested cadence.
fn checkpoint_log(rec: &SimRecord, foreign: Foreign) -> Result<HashLog, String> {
    match foreign {
        Foreign::Log(log) => {
            if log.is_empty() {
                return Err("hash log is empty".into());
            }
            let (last, _) = log.last().unwrap();
            if last > rec.ticks {
                return Err(format!(
                    "hash log runs to tick {last} but the record has {} ticks",
                    rec.ticks
                ));
            }
            Ok(log.clone())
        }
        Foreign::Injected { tick, every } => {
            if tick == 0 || tick > rec.ticks {
                return Err(format!(
                    "--inject-tick {tick} must be in 1..={} (tick 0 is the constructed state; nothing steps into it)",
                    rec.ticks
                ));
            }
            let cadence = Cadence::new(every, rec.ticks);
            let mut sim = local_sim(rec, Some(tick))?;
            let mut log = HashLog::default();
            for t in 0..=rec.ticks {
                if t > 0 {
                    sim.step();
                }
                if cadence.keeps(t) {
                    log.push(t, HexHash(sim.state_hash()));
                }
            }
            Ok(log)
        }
    }
}

struct Prober<'a> {
    rec: &'a SimRecord,
    inject: Option<u64>,
    log: &'a HashLog,
    probes: u64,
}

impl Prober<'_> {
    /// Fresh instance to the tick of entry `idx`; if its hash differs, return it.
    fn differs(&mut self, idx: usize) -> Result<Option<HexHash>, String> {
        self.probes += 1;
        let (tick, foreign) = self.log.entries[idx];
        let local = hash_at(self.rec, self.inject, tick)?;
        Ok((local != foreign).then_some(local))
    }
}

/// First differing entry of the checkpoint log: `(index, local hash, search)`.
fn bracket(
    rec: &SimRecord,
    inject: Option<u64>,
    log: &HashLog,
) -> Result<Option<(usize, HexHash, Search)>, String> {
    let last = log.len() - 1;
    let mut p = Prober {
        rec,
        inject,
        log,
        probes: 0,
    };
    let search = |mode, probes| Search {
        mode,
        probes,
        checkpoints: log.len(),
    };
    if let Some(local_last) = p.differs(last)? {
        // A real desync stays desynced, so the mismatch predicate is monotone over the
        // entries and a binary search finds the boundary.
        if let Some(local0) = p.differs(0)? {
            return Ok(Some((0, local0, search(SearchMode::Binary, p.probes))));
        }
        let (mut lo, mut hi, mut hi_local) = (0usize, last, local_last);
        while hi - lo > 1 {
            let mid = lo + (hi - lo) / 2;
            match p.differs(mid)? {
                Some(l) => {
                    hi = mid;
                    hi_local = l;
                }
                None => lo = mid,
            }
        }
        return Ok(Some((hi, hi_local, search(SearchMode::Binary, p.probes))));
    }
    // Final checkpoint agrees. Either the log is clean or a mismatch is transient, which
    // is not the shape of a desync (it is the shape of a corrupt or edited log), so the
    // monotone assumption is off and one linear pass is the honest answer.
    let mut sim = local_sim(rec, inject)?;
    for (i, &(tick, foreign)) in log.entries.iter().enumerate() {
        step_to(&mut sim, tick);
        let local = HexHash(sim.state_hash());
        if local != foreign {
            return Ok(Some((i, local, search(SearchMode::Linear, p.probes + 1))));
        }
    }
    Ok(None)
}

/// Two fresh armed instances from `start` (where they agree) to `end`, one tick at a
/// time: at the first tick they differ on, B's hash, their field diff, and A's state
/// (the dump and step diff come from the same instance whose hash is reported -- a
/// third armed instance would fold its own order and hash differently).
fn walk_injected(
    rec: &SimRecord,
    inject: u64,
    start: u64,
    end: u64,
) -> Result<(HexHash, Vec<DiffEntry>, StateAtTick), String> {
    let mut a = local_sim(rec, Some(inject))?;
    let mut b = local_sim(rec, Some(inject))?;
    step_to(&mut a, start);
    step_to(&mut b, start);
    let mut before: Option<Sim> = None;
    loop {
        let ha = a.state_hash();
        let hb = b.state_hash();
        if ha != hb {
            let step_diff = before
                .map(|p| entries(&diagnostics::diff(&p, &a)))
                .unwrap_or_default();
            let state = StateAtTick {
                tick: a.tick().0,
                hash: HexHash(ha),
                dump: diagnostics::dump(&a),
                step_diff,
            };
            return Ok((HexHash(hb), entries(&diagnostics::diff(&a, &b)), state));
        }
        if a.tick().0 >= end {
            return Err(format!(
                "the checkpoint at tick {end} differed but a lockstep walk from {start} found \
                 no differing tick: the injection did not fire (widen INJECT_ENTRIES and \
                 record why)"
            ));
        }
        before = Some(a.clone());
        a.step();
        b.step();
    }
}

/// Find the first tick whose local hash differs from the foreign side. `Err` is
/// structural (the log does not fit the record, the fixture is absent).
pub fn locate(rec: &MatchRecord, foreign: Foreign) -> Result<Located, String> {
    let sim_rec = rec.to_sim()?;
    let inject = match foreign {
        Foreign::Injected { tick, .. } => Some(tick),
        Foreign::Log(_) => None,
    };
    let log = checkpoint_log(&sim_rec, foreign)?;
    let Some((idx, local_at_idx, search)) = bracket(&sim_rec, inject, &log)? else {
        return Ok(Located::Clean {
            ticks: sim_rec.ticks,
            checkpoints: log.len(),
        });
    };
    let (hi, foreign_at_hi) = log.entries[idx];
    let agreed = (idx > 0).then(|| log.entries[idx - 1].0);
    let found = match foreign {
        Foreign::Log(_) => {
            let exact = match agreed {
                Some(a) => hi - a == 1,
                None => hi == 0,
            };
            let state = replay_to(&sim_rec, None, hi)?;
            debug_assert_eq!(state.hash, local_at_idx);
            Divergent {
                tick: hi,
                exact,
                agreed,
                foreign: foreign_at_hi,
                local: local_at_idx,
                search,
                walked: None,
                pair_diff: None,
                state,
            }
        }
        Foreign::Injected { tick, .. } => {
            let start = agreed.unwrap_or(0);
            let (hb, diff, state) = walk_injected(&sim_rec, tick, start, hi)?;
            Divergent {
                tick: state.tick,
                exact: true,
                agreed: (state.tick > 0).then(|| state.tick - 1),
                foreign: hb,
                local: state.hash,
                search,
                walked: Some((start, hi)),
                pair_diff: Some(diff),
                state,
            }
        }
    };
    Ok(Located::Divergent(Box::new(found)))
}

/// Fresh local instance from `rec` (armed if `inject`), run to `tick`.
pub fn replay_to(rec: &SimRecord, inject: Option<u64>, tick: u64) -> Result<StateAtTick, String> {
    Ok(replay_sim_to(local_sim(rec, inject)?, tick))
}

fn replay_sim_to(mut sim: Sim, tick: u64) -> StateAtTick {
    let mut before = None;
    for t in 1..=tick {
        if t == tick {
            before = Some(sim.clone());
        }
        sim.step();
    }
    let step_diff = match &before {
        Some(b) => entries(&diagnostics::diff(b, &sim)),
        None => Vec::new(),
    };
    StateAtTick {
        tick,
        hash: HexHash(sim.state_hash()),
        dump: diagnostics::dump(&sim),
        step_diff,
    }
}

impl fmt::Display for StateAtTick {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        writeln!(f, "local state at tick {} (hash {}):", self.tick, self.hash)?;
        for line in self.dump.lines() {
            writeln!(f, "  {line}")?;
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
            write_diff(f, &self.step_diff, "before", "after ")?;
        }
        Ok(())
    }
}

impl fmt::Display for Divergent {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let Search {
            mode,
            probes,
            checkpoints,
        } = self.search;
        if self.exact {
            writeln!(
                f,
                "DIVERGENCE at tick {}  (found by {mode} over {checkpoints} checkpoint(s), {probes} re-run(s))",
                self.tick
            )?;
        } else {
            writeln!(
                f,
                "DIVERGENCE at checkpoint tick {}  (found by {mode} over {checkpoints} checkpoint(s), {probes} re-run(s))",
                self.tick
            )?;
        }
        if let Some((start, end)) = self.walked {
            writeln!(
                f,
                "  checkpoints bracketed the desync in {start}..={end}; a lockstep walk of that window pinned tick {}",
                self.tick
            )?;
        }
        writeln!(f, "  recorded: {}", self.foreign)?;
        writeln!(f, "  local   : {}", self.local)?;
        match self.agreed {
            Some(a) if self.exact => writeln!(f, "  tick {a} matched on both sides")?,
            Some(a) => writeln!(
                f,
                "  tick {a} matched on both sides; the log has no entry in {}..={}, so the desync began somewhere in that window -- record the other side with --hash-every 1 to pin the tick",
                a + 1,
                self.tick - 1
            )?,
            None if self.exact => {}
            None => writeln!(
                f,
                "  the log has no entry before tick {}, so nothing is known to agree",
                self.tick
            )?,
        }
        if let Some(diff) = &self.pair_diff {
            writeln!(
                f,
                "  {} differing field(s) between the two instances:",
                diff.len()
            )?;
            write_diff(f, diff, "A", "B")?;
        }
        write!(f, "{}", self.state)?;
        if self.pair_diff.is_none() {
            writeln!(
                f,
                "the recorded side supplied hashes only; the diff above is the local instance's change across the divergent tick"
            )?;
        }
        Ok(())
    }
}

/// Result of re-running a canary divergence from `divergence.json`.
#[derive(Debug)]
pub struct Reproduction {
    /// Fresh single instance, never armed, run to the divergence tick.
    pub local: StateAtTick,
    pub matches_a: bool,
    pub matches_b: bool,
    /// Present when the divergence file records an injection: the canary re-run with the
    /// fixture armed for the same tick. Its two instances fold fresh `HashMap` orders,
    /// so the hashes are new; what must repeat is the tick.
    pub rerun: Option<Result<CanaryRun, CanaryError>>,
}

impl Reproduction {
    /// Did the local re-run confirm the recorded divergence? Without an injection the
    /// other process cannot be re-run, so the recorded diff stands as is. With one, the
    /// re-run must diverge on the recorded tick.
    pub fn reproduced(&self, original: &Divergence) -> bool {
        match &self.rerun {
            None => true,
            Some(Ok(CanaryRun {
                outcome: Err(d), ..
            })) => d.tick == original.tick,
            Some(_) => false,
        }
    }
}

pub fn reproduce(div: &Divergence) -> Result<Reproduction, String> {
    let sim_rec = div.record.to_sim()?;
    let local = replay_to(&sim_rec, None, div.tick)?;
    let rerun = div
        .injection
        .as_ref()
        .map(|inj| canary::run(&div.record, Some(Inject { tick: inj.tick }), 1, |_| {}));
    Ok(Reproduction {
        matches_a: local.hash == div.hash_a,
        matches_b: local.hash == div.hash_b,
        local,
        rerun,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::record::{content_hash_of, default_content_dir};
    use crate::runner::record;

    fn content() -> HexHash {
        content_hash_of(&default_content_dir()).unwrap()
    }

    fn flip(h: &mut HexHash) {
        h.0[0] ^= 0x01;
    }

    fn divergent(l: Located) -> Box<Divergent> {
        match l {
            Located::Divergent(d) => d,
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn clean_log_is_clean() {
        let (rec, log) = record(7, 400, 1, content());
        assert_eq!(
            locate(&rec, Foreign::Log(&log)).unwrap(),
            Located::Clean {
                ticks: 400,
                checkpoints: 401
            }
        );
        let (rec, sparse) = record(7, 400, 50, content());
        assert_eq!(
            locate(&rec, Foreign::Log(&sparse)).unwrap(),
            Located::Clean {
                ticks: 400,
                checkpoints: 9
            }
        );
    }

    #[test]
    fn persistent_divergence_is_bisected_to_the_exact_tick() {
        // Corrupt every hash from tick 1234 on: the shape of a real desync.
        let (rec, mut log) = record(7, 3000, 1, content());
        for (t, h) in log.entries.iter_mut() {
            if *t >= 1234 {
                flip(h);
            }
        }
        let d = divergent(locate(&rec, Foreign::Log(&log)).unwrap());
        assert_eq!(d.tick, 1234);
        assert!(d.exact);
        assert_eq!(d.agreed, Some(1233));
        assert_eq!(d.search.mode, SearchMode::Binary);
        assert!(d.search.probes <= 16, "probes {}", d.search.probes);
        assert_eq!(d.state.tick, 1234);
        assert_eq!(d.state.step_diff[0].path, "tick");
        assert!(d.pair_diff.is_none());
        assert!(d.to_string().contains("DIVERGENCE at tick 1234"), "{d}");
    }

    #[test]
    fn sparse_log_narrows_to_the_checkpoint_window() {
        // Every 100 ticks, corrupted from the first checkpoint after 1234 onward.
        let (rec, mut log) = record(7, 3000, 100, content());
        for (t, h) in log.entries.iter_mut() {
            if *t >= 1234 {
                flip(h);
            }
        }
        let d = divergent(locate(&rec, Foreign::Log(&log)).unwrap());
        assert_eq!(d.tick, 1300);
        assert!(!d.exact);
        assert_eq!(d.agreed, Some(1200));
        assert_eq!(d.search.checkpoints, 31);
        assert!(d.search.probes <= 7, "probes {}", d.search.probes);
        let text = d.to_string();
        assert!(
            text.contains("DIVERGENCE at checkpoint tick 1300"),
            "{text}"
        );
        assert!(text.contains("no entry in 1201..=1299"), "{text}");
    }

    #[test]
    fn divergence_at_tick_zero_and_last_tick() {
        let (rec, mut log) = record(7, 50, 1, content());
        for (_, h) in log.entries.iter_mut() {
            flip(h);
        }
        let d = divergent(locate(&rec, Foreign::Log(&log)).unwrap());
        assert_eq!((d.tick, d.exact, d.agreed), (0, true, None));
        let (rec, mut log) = record(7, 50, 1, content());
        flip(&mut log.entries[50].1);
        let d = divergent(locate(&rec, Foreign::Log(&log)).unwrap());
        assert_eq!((d.tick, d.exact), (50, true));
    }

    #[test]
    fn transient_mismatch_falls_back_to_linear() {
        let (rec, mut log) = record(7, 3000, 1, content());
        flip(&mut log.entries[1234].1);
        let d = divergent(locate(&rec, Foreign::Log(&log)).unwrap());
        assert_eq!(d.tick, 1234);
        assert_eq!(d.search.mode, SearchMode::Linear);
    }

    #[test]
    fn a_log_past_the_record_or_empty_is_structural() {
        let (rec, log) = record(7, 50, 1, content());
        assert!(locate(&rec, Foreign::Log(&HashLog::default())).is_err());
        let mut long = log.clone();
        long.push(51, HexHash([0; 32]));
        assert!(locate(&rec, Foreign::Log(&long))
            .unwrap_err()
            .contains("runs to tick 51"));
    }

    #[test]
    fn injected_mode_finds_the_exact_tick_through_dense_and_sparse_checkpoints() {
        let rec = MatchRecord::empty(5, 3000, content());
        for every in [1u64, 100, 1000] {
            let d = divergent(locate(&rec, Foreign::Injected { tick: 1234, every }).unwrap());
            assert_eq!(d.tick, 1234, "every {every}");
            assert!(d.exact);
            assert_eq!(d.agreed, Some(1233));
            let diff = d.pair_diff.as_ref().unwrap();
            assert_eq!(diff.len(), 1);
            assert_eq!(diff[0].path, "inject_fold");
            assert_ne!(d.foreign, d.local);
            if every == 1 {
                assert_eq!(d.walked, Some((1233, 1234)));
            } else if every == 100 {
                // Narrowed to the 1200..=1300 window, then walked.
                assert_eq!(d.walked, Some((1200, 1300)));
                assert_eq!(d.search.checkpoints, 31);
                assert!(d.search.probes <= 7, "probes {}", d.search.probes);
            } else {
                assert_eq!(d.walked, Some((1000, 2000)));
            }
            assert!(d.state.dump.contains("tick = 1234\n"));
            assert!(d.to_string().contains("inject_fold"), "{d}");
        }
    }

    #[test]
    fn replay_to_reports_the_step_diff_and_dump() {
        let (rec, log) = record(7, 100, 1, content());
        let sim_rec = rec.to_sim().unwrap();
        let s = replay_to(&sim_rec, None, 42).unwrap();
        assert_eq!(s.tick, 42);
        assert_eq!(s.hash, log.hash_at(42).unwrap());
        assert!(!s.step_diff.is_empty());
        assert_eq!(s.step_diff[0].path, "tick");
        assert!(s.dump.contains("tick = 42\n"), "{}", s.dump);
        let s0 = replay_to(&sim_rec, None, 0).unwrap();
        assert!(s0.step_diff.is_empty());
        assert_eq!(s0.hash, log.hash_at(0).unwrap());
    }

    #[test]
    fn injected_divergence_is_reproduced_at_the_same_tick() {
        let rec = MatchRecord::empty(5, 800, content());
        let div = canary::run(&rec, Some(Inject { tick: 333 }), 1, |_| {})
            .unwrap()
            .outcome
            .unwrap_err();
        let r = reproduce(&div).unwrap();
        // Both instances folded an order into `inject_fold`, so neither matches a run
        // that never armed the fixture -- the bug is in both, like a real one would be.
        assert!(!r.matches_a);
        assert!(!r.matches_b);
        assert!(r.reproduced(&div));
        match r.rerun.unwrap().unwrap().outcome {
            Err(again) => {
                assert_eq!(again.tick, 333);
                assert_eq!(again.diff[0].path, "inject_fold");
            }
            other => panic!("{other:?}"),
        }
    }
}
