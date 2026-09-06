//! Headless run / record / verify / batch over `Sim`.

use std::time::{Duration, Instant};

use blindside_sim::Sim;

use crate::record::{content_hash, HashLog, HexHash, MatchRecord, MATCH_RECORD_SCHEMA};

/// Construct a sim from a record.
///
/// Phase 0: the only input in a record the sim consumes is the seed. Once the sim takes
/// loadouts/policies/commands, they are applied here and nowhere else.
pub fn sim_from_record(rec: &MatchRecord) -> Sim {
    Sim::new(rec.seed)
}

#[derive(Clone, Debug)]
pub struct RunOutcome {
    pub ticks: u64,
    pub final_hash: HexHash,
    pub elapsed: Duration,
}

impl RunOutcome {
    pub fn ticks_per_second(&self) -> f64 {
        let secs = self.elapsed.as_secs_f64();
        if secs > 0.0 {
            self.ticks as f64 / secs
        } else {
            f64::INFINITY
        }
    }
}

/// Run a loaded record to its tick count. Does not compare against the recorded hash;
/// the caller does, so it can report both.
pub fn run(rec: &MatchRecord) -> RunOutcome {
    let mut sim = sim_from_record(rec);
    let start = Instant::now();
    for _ in 0..rec.ticks {
        sim.step();
    }
    let elapsed = start.elapsed();
    RunOutcome {
        ticks: rec.ticks,
        final_hash: HexHash(sim.state_hash()),
        elapsed,
    }
}

/// Run a fresh match and capture the record plus the per-tick hash log.
pub fn record(seed: u64, ticks: u64) -> (MatchRecord, HashLog) {
    let mut sim = Sim::new(seed);
    let mut hashes = Vec::with_capacity(ticks as usize + 1);
    hashes.push(HexHash(sim.state_hash()));
    for _ in 0..ticks {
        sim.step();
        hashes.push(HexHash(sim.state_hash()));
    }
    let final_hash = *hashes.last().expect("at least tick 0");
    let rec = MatchRecord {
        schema: MATCH_RECORD_SCHEMA,
        seed,
        content_hash: content_hash(),
        loadouts: Vec::new(),
        policies: Vec::new(),
        commands: Vec::new(),
        ticks,
        final_hash,
    };
    let log = HashLog {
        seed,
        ticks,
        hashes,
    };
    (rec, log)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum VerifyOutcome {
    Ok {
        ticks: u64,
        final_hash: HexHash,
    },
    Mismatch {
        tick: u64,
        expected: HexHash,
        actual: HexHash,
    },
}

/// Structural check that `log` is the sidecar of `rec`: same seed, same tick count, one
/// hash per tick `0..=ticks`.
pub fn check_log(rec: &MatchRecord, log: &HashLog) -> Result<(), String> {
    if log.seed != rec.seed {
        return Err(format!(
            "hash log seed {} does not match record seed {}",
            log.seed, rec.seed
        ));
    }
    if log.ticks != rec.ticks {
        return Err(format!(
            "hash log covers {} ticks but record has {}",
            log.ticks, rec.ticks
        ));
    }
    let want_len = rec.ticks as usize + 1;
    if log.hashes.len() != want_len {
        return Err(format!(
            "hash log has {} entries; expected {} (one per tick 0..={})",
            log.hashes.len(),
            want_len,
            rec.ticks
        ));
    }
    Ok(())
}

/// Re-run the record and check every per-tick hash against the log, then the record's
/// final hash. `Err` is a structural problem (the log does not belong to the record);
/// `Ok(Mismatch)` is a real divergence.
pub fn verify(rec: &MatchRecord, log: &HashLog) -> Result<VerifyOutcome, String> {
    check_log(rec, log)?;
    let mut sim = sim_from_record(rec);
    for t in 0..=rec.ticks {
        if t > 0 {
            sim.step();
        }
        let actual = HexHash(sim.state_hash());
        let expected = log.hashes[t as usize];
        if actual != expected {
            return Ok(VerifyOutcome::Mismatch {
                tick: t,
                expected,
                actual,
            });
        }
    }
    let actual = HexHash(sim.state_hash());
    if actual != rec.final_hash {
        return Ok(VerifyOutcome::Mismatch {
            tick: rec.ticks,
            expected: rec.final_hash,
            actual,
        });
    }
    Ok(VerifyOutcome::Ok {
        ticks: rec.ticks,
        final_hash: actual,
    })
}

#[derive(Clone, Debug)]
pub struct BatchOutcome {
    pub matches: u64,
    pub ticks_per_match: u64,
    pub elapsed: Duration,
    /// XOR of every match's final hash: cheap, order-independent, and enough to compare
    /// two batch runs (and to stop the optimiser discarding the work).
    pub digest: HexHash,
}

impl BatchOutcome {
    pub fn matches_per_hour(&self) -> f64 {
        let secs = self.elapsed.as_secs_f64();
        if secs > 0.0 {
            self.matches as f64 * 3600.0 / secs
        } else {
            f64::INFINITY
        }
    }

    pub fn ticks_per_second(&self) -> f64 {
        let secs = self.elapsed.as_secs_f64();
        if secs > 0.0 {
            (self.matches * self.ticks_per_match) as f64 / secs
        } else {
            f64::INFINITY
        }
    }
}

/// Run `matches` sequential matches of `ticks` ticks with seeds `base_seed, base_seed+1,
/// ...` on one thread, and time them. Single-threaded on purpose: the number reported is
/// per core, which is what the "thousands per hour on a laptop" target is about.
pub fn batch(base_seed: u64, matches: u64, ticks: u64) -> BatchOutcome {
    let mut digest = [0u8; 32];
    let start = Instant::now();
    for i in 0..matches {
        let mut sim = Sim::new(base_seed.wrapping_add(i));
        for _ in 0..ticks {
            sim.step();
        }
        for (d, h) in digest.iter_mut().zip(sim.state_hash()) {
            *d ^= h;
        }
    }
    BatchOutcome {
        matches,
        ticks_per_match: ticks,
        elapsed: start.elapsed(),
        digest: HexHash(digest),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn record_then_verify_is_ok() {
        let (rec, log) = record(11, 300);
        assert_eq!(log.hashes.len(), 301);
        assert_eq!(rec.final_hash, log.hashes[300]);
        assert_eq!(
            verify(&rec, &log).unwrap(),
            VerifyOutcome::Ok {
                ticks: 300,
                final_hash: rec.final_hash
            }
        );
    }

    #[test]
    fn tampered_log_reports_the_tampered_tick() {
        let (rec, mut log) = record(11, 300);
        let mut bytes = log.hashes[123].0;
        bytes[0] ^= 0x01;
        log.hashes[123] = HexHash(bytes);
        match verify(&rec, &log).unwrap() {
            VerifyOutcome::Mismatch { tick, .. } => assert_eq!(tick, 123),
            other => panic!("expected mismatch, got {other:?}"),
        }
    }

    #[test]
    fn tampered_final_hash_reports_last_tick() {
        let (mut rec, log) = record(11, 300);
        let mut bytes = rec.final_hash.0;
        bytes[31] ^= 0x80;
        rec.final_hash = HexHash(bytes);
        match verify(&rec, &log).unwrap() {
            VerifyOutcome::Mismatch { tick, .. } => assert_eq!(tick, 300),
            other => panic!("expected mismatch, got {other:?}"),
        }
    }

    #[test]
    fn log_from_another_record_is_rejected() {
        let (rec, _) = record(1, 10);
        let (_, log) = record(2, 10);
        assert!(verify(&rec, &log).is_err());
    }

    #[test]
    fn run_agrees_with_record_and_the_cross_platform_pin() {
        let (rec, _) = record(0xDEAD_BEEF, 1000);
        assert_eq!(run(&rec).final_hash, rec.final_hash);
        // Same pin as blindside-sim's known_hash_at_tick_1000.
        assert_eq!(
            rec.final_hash.to_hex(),
            "5a6930a5dab0a7627913befbc590c79453415c483200c8d4eb55eb8a3faaf17a"
        );
    }
}
