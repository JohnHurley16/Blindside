// BLD-32, positive half: everything `blindside_sim::diagnostics` returns is a String or
// an Option<String>, exhaustively. The struct patterns list every field without `..`, so
// a new non-string field on either type -- the "just for debugging" accessor -- breaks
// this program and the test with it.
use blindside_sim::diagnostics::{diff, dump, DiffEntry, DiffReport};
use blindside_sim::{MatchRecord, Sim, MATCH_RECORD_SCHEMA};

fn is_string(_: String) {}

fn only_strings(e: &DiffEntry) -> (&String, &Option<String>, &Option<String>) {
    let DiffEntry { path, a, b } = e;
    (path, a, b)
}

fn record() -> MatchRecord {
    MatchRecord {
        schema: MATCH_RECORD_SCHEMA,
        seed: 1,
        content_hash: [0; 32],
        loadouts: Vec::new(),
        policies: Vec::new(),
        commands: Vec::new(),
        ticks: 1,
        final_hash: [0; 32],
    }
}

fn main() {
    let a = Sim::new(&record());
    let mut b = Sim::new(&record());
    b.step();
    is_string(dump(&a));
    let report = diff(&a, &b);
    let DiffReport { entries } = &report;
    for e in entries {
        let _ = only_strings(e);
    }
}
