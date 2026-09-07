// BLD-32: the diagnostics API is the one sanctioned window onto ground truth, and it is
// strings only. None of these routes from its return types to `World` may compile.
use blindside_sim::diagnostics::{diff, dump};
use blindside_sim::{MatchRecord, Sim, MATCH_RECORD_SCHEMA};

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
    let b = Sim::new(&record());
    let report = diff(&a, &b);
    // No accessor on the report yields the world.
    let _w = report.world();
    // The report cannot be read as a world by type.
    let _w: &blindside_sim::World = &report;
    // The dump is a String; it has no field named after ground truth.
    let _t = dump(&a).tick;
}
