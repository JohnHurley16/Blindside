//! Headless run / record / batch over `Sim` (BLD-31, BLD-38).
//!
//! Timing lives here and nowhere in the sim: `std::time` is banned in blindside-sim, so
//! the harness is where "10,000 step() calls under 10 ms" is measured (`step_cost`). The
//! runner touches a `Sim` only through `Sim::new(&MatchRecord)`, `step`, `tick` and
//! `state_hash`; it never names `World`.
//!
//! `run_measured` steps a record twice. The first pass is `step_cost`: steps only, no
//! hashing, no allocation, timed as a whole -- the number the Phase 3 budget is about
//! (~0.6 s/match for 1,000 matches in 10 minutes), extrapolated to matches/hour at 9,600
//! ticks/match (Phase 1: 20 Hz x 480 s). The second pass (`run`) hashes on the cadence
//! asked for, keeps the log and the optional state dump, and is timed as a whole too; the
//! hash cost per tick is the difference between the two passes divided by the hashes
//! computed, so no timer sits inside the loop to distort a 15 ns step.

use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use blindside_sim::Sim;

use crate::record::{Cadence, HashLog, HexHash, MatchRecord, SimRecord};

/// Ticks per match the throughput line extrapolates to.
///
/// DEFAULT (awaiting designer): 20 Hz x 480 s = 9,600 ticks per match -- Phase 1 ran at
/// 20 Hz and its worst tick was 33 ms, which rules out 60 Hz; no Phase 0 document states
/// a rate. Nothing in the sim depends on it. It is the divisor in the "matches/hour"
/// line and nowhere else, so a different answer re-prints a report and moves no hash --
/// which is why it was defaulted rather than blocked on. BLD-20 question 14; the
/// question and this default are `docs/HARNESS.md` section 1.
pub const TICKS_PER_MATCH: u64 = 9_600;

/// Fresh instance from the record, stepped `ticks` times with nothing else in the loop.
/// Returns the final hash (so the optimiser cannot drop the work) and the wall-clock.
pub fn step_cost(rec: &SimRecord, ticks: u64) -> (HexHash, Duration) {
    let mut sim = Sim::new(rec);
    let start = Instant::now();
    for _ in 0..ticks {
        sim.step();
    }
    let elapsed = start.elapsed();
    (HexHash(sim.state_hash()), elapsed)
}

#[derive(Clone, Debug)]
pub struct RunOutcome {
    pub ticks: u64,
    pub final_hash: HexHash,
    /// Wall-clock of the step-only pass, when `run_measured` took one.
    pub step_time: Option<Duration>,
    /// Wall-clock of the hashing pass (steps, hashes on the cadence, log, dump).
    pub hashed_time: Duration,
    /// Number of `state_hash` calls in the hashing pass.
    pub hashes: u64,
    /// Cadence the hashing pass used.
    pub cadence: Cadence,
    pub log: HashLog,
    /// `diagnostics::dump` at the requested tick, if one was requested.
    pub dump: Option<(u64, String)>,
}

impl RunOutcome {
    /// Steps per second: from the step-only pass when there was one, else from the
    /// hashing pass (which then includes the hashes).
    pub fn ticks_per_second(&self) -> f64 {
        per_second(self.ticks, self.step_time.unwrap_or(self.hashed_time))
    }

    /// Matches per hour at [`TICKS_PER_MATCH`].
    pub fn matches_per_hour(&self) -> f64 {
        self.ticks_per_second() * 3600.0 / TICKS_PER_MATCH as f64
    }

    /// Cost of one `state_hash`: the hashing pass minus the step-only pass, per hash.
    /// `None` without a step-only pass; zero when noise makes the hashing pass the
    /// faster one.
    pub fn hash_cost(&self) -> Option<Duration> {
        let step_time = self.step_time?;
        if self.hashes == 0 {
            return Some(Duration::ZERO);
        }
        Some(
            self.hashed_time
                .saturating_sub(step_time)
                .checked_div(self.hashes as u32)
                .unwrap_or(Duration::ZERO),
        )
    }
}

fn per_second(count: u64, elapsed: Duration) -> f64 {
    let secs = elapsed.as_secs_f64();
    if secs > 0.0 {
        count as f64 / secs
    } else {
        f64::INFINITY
    }
}

/// Run a record to its tick count, hashing on `every` and dumping the state at
/// `dump_at` if asked. Does not compare against the recorded hash; the caller does, so
/// it can report both.
pub fn run(rec: &SimRecord, every: u64, dump_at: Option<u64>) -> RunOutcome {
    let ticks = rec.ticks;
    let cadence = Cadence::new(every, ticks);
    let mut sim = Sim::new(rec);
    let mut log = HashLog::default();
    let mut dump = None;
    let mut hashes = 0u64;
    let start = Instant::now();
    for t in 0..=ticks {
        if t > 0 {
            sim.step();
        }
        if cadence.keeps(t) {
            hashes += 1;
            log.push(t, HexHash(sim.state_hash()));
        }
        if dump_at == Some(t) {
            dump = Some((t, blindside_sim::diagnostics::dump(&sim)));
        }
    }
    let hashed_time = start.elapsed();
    let final_hash = log
        .last()
        .map(|(_, h)| h)
        .expect("the final tick is always kept");
    RunOutcome {
        ticks,
        final_hash,
        step_time: None,
        hashed_time,
        hashes,
        cadence,
        log,
        dump,
    }
}

/// `step_cost` then `run`: the throughput numbers `harness run` prints.
pub fn run_measured(rec: &SimRecord, every: u64, dump_at: Option<u64>) -> RunOutcome {
    let (step_hash, step_time) = step_cost(rec, rec.ticks);
    let mut out = run(rec, every, dump_at);
    debug_assert_eq!(out.final_hash, step_hash, "the two passes disagree");
    out.step_time = Some(step_time);
    out
}

/// Run a fresh empty match and return the record with `final_hash` filled in, plus the
/// hash log on `every`.
pub fn record(seed: u64, ticks: u64, every: u64, content_hash: HexHash) -> (MatchRecord, HashLog) {
    let mut rec = MatchRecord::empty(seed, ticks, content_hash);
    let sim_rec = rec.to_sim().expect("an empty record is valid");
    let out = run(&sim_rec, every, None);
    rec.final_hash = out.final_hash;
    (rec, out.log)
}

#[derive(Clone, Debug)]
pub struct BatchOutcome {
    /// `(seed, final_hash)` sorted by seed, whatever order the jobs finished in.
    pub rows: Vec<(u64, HexHash)>,
    pub ticks_per_match: u64,
    pub jobs: usize,
    pub elapsed: Duration,
}

impl BatchOutcome {
    pub fn matches_per_hour(&self) -> f64 {
        per_second(self.rows.len() as u64, self.elapsed) * 3600.0
    }

    /// Aggregate steps per second across all jobs.
    pub fn ticks_per_second(&self) -> f64 {
        per_second(self.rows.len() as u64 * self.ticks_per_match, self.elapsed)
    }

    /// The `seed,final_hash` table: one line per seed, ascending, no header, LF.
    pub fn table(&self) -> String {
        let mut out = String::with_capacity(self.rows.len() * 90);
        for (seed, hash) in &self.rows {
            out.push_str(&seed.to_string());
            out.push(',');
            out.push_str(&hash.to_hex());
            out.push('\n');
        }
        out
    }
}

/// One empty match per seed, `ticks` ticks each, at most `jobs` running at once
/// (DETERMINISM.md rule 5: parallelism between matches only, never inside a tick). Each
/// match is its own `Sim` from its own record; a worker takes the next seed from a shared
/// counter, so the schedule depends on timing but the table does not: rows are sorted by
/// seed before they are returned, and the hash of a seed is a function of nothing else.
pub fn batch(seeds: &[u64], ticks: u64, jobs: usize, content_hash: HexHash) -> BatchOutcome {
    let jobs = jobs.max(1).min(seeds.len().max(1));
    let next = AtomicU64::new(0);
    let rows: Mutex<Vec<(u64, HexHash)>> = Mutex::new(Vec::with_capacity(seeds.len()));
    let start = Instant::now();
    std::thread::scope(|scope| {
        for _ in 0..jobs {
            scope.spawn(|| {
                let mut mine = Vec::new();
                loop {
                    let i = next.fetch_add(1, Ordering::Relaxed) as usize;
                    if i >= seeds.len() {
                        break;
                    }
                    let seed = seeds[i];
                    let rec = MatchRecord::empty(seed, ticks, content_hash)
                        .to_sim()
                        .expect("an empty record is valid");
                    let (hash, _) = step_cost(&rec, ticks);
                    mine.push((seed, hash));
                }
                rows.lock().unwrap().extend(mine);
            });
        }
    });
    let elapsed = start.elapsed();
    let mut rows = rows.into_inner().unwrap();
    rows.sort_by_key(|&(seed, _)| seed);
    BatchOutcome {
        rows,
        ticks_per_match: ticks,
        jobs,
        elapsed,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::record::{content_hash_of, default_content_dir};

    fn content() -> HexHash {
        content_hash_of(&default_content_dir()).unwrap()
    }

    #[test]
    fn record_then_run_reproduces_the_final_hash_and_the_log() {
        let (rec, log) = record(11, 300, 1, content());
        assert_eq!(log.len(), 301);
        assert_eq!(log.last().unwrap(), (300, rec.final_hash));
        let out = run_measured(&rec.to_sim().unwrap(), 1, Some(42));
        assert_eq!(out.final_hash, rec.final_hash);
        assert_eq!(out.log, log);
        assert_eq!(out.hashes, 301);
        assert!(out.step_time.is_some());
        assert!(out.hash_cost().is_some());
        let (tick, dump) = out.dump.unwrap();
        assert_eq!(tick, 42);
        assert!(dump.contains("tick = 42\n"), "{dump}");
        assert!(run(&rec.to_sim().unwrap(), 1, None).hash_cost().is_none());
    }

    #[test]
    fn hash_every_n_keeps_multiples_and_the_final_tick() {
        let (rec, dense) = record(11, 250, 1, content());
        let out = run(&rec.to_sim().unwrap(), 100, None);
        let ticks: Vec<u64> = out.log.entries.iter().map(|&(t, _)| t).collect();
        assert_eq!(ticks, [0, 100, 200, 250]);
        assert_eq!(out.hashes, 4);
        for (t, h) in &out.log.entries {
            assert_eq!(dense.hash_at(*t), Some(*h), "tick {t}");
        }
        assert_eq!(out.final_hash, rec.final_hash);
    }

    /// BLD-31: 10,000 `step()` calls on the empty sim in under 10 ms, measured here with
    /// `std::time` because the sim may not. Best of three so a page fault or a scheduler
    /// hiccup on the first pass does not fail the build; the bound is on the sim, not on
    /// the operating system.
    #[test]
    fn ten_thousand_steps_take_under_ten_milliseconds() {
        let rec = MatchRecord::empty(0xDEAD_BEEF, 10_000, content())
            .to_sim()
            .unwrap();
        let best = (0..3).map(|_| step_cost(&rec, 10_000).1).min().unwrap();
        assert!(
            best < Duration::from_millis(10),
            "10,000 steps took {best:?} (best of 3)"
        );
    }

    #[test]
    fn run_agrees_with_the_cross_platform_pin() {
        let (rec, _) = record(0xDEAD_BEEF, 1000, 1, content());
        // Same pin as blindside-sim's GOLDEN_SEED_DEADBEEF_TICK_1000.
        assert_eq!(rec.final_hash.to_hex(), crate::PIN_SEED_DEADBEEF_TICK_1000);
    }

    #[test]
    fn batch_table_is_identical_for_one_and_eight_jobs() {
        let seeds: Vec<u64> = (100..140).collect();
        let one = batch(&seeds, 200, 1, content());
        let eight = batch(&seeds, 200, 8, content());
        assert_eq!(one.jobs, 1);
        assert_eq!(eight.jobs, 8);
        assert_eq!(one.table(), eight.table());
        assert_eq!(one.rows.len(), 40);
        assert!(one.table().starts_with("100,"));
        // Every row is the same hash `record` would produce for that seed.
        let (rec, _) = record(123, 200, 1, content());
        assert_eq!(one.rows[23], (123, rec.final_hash));
    }
}
