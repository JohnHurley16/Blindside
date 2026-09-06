//! Canonical serialisation of everything that affects future ticks.
//!
//! Hand-written, little-endian, fields in a fixed order, maps in key order. No serde, no
//! derived hashing. The byte layout is the contract, and it must be identical on every
//! platform and stable across compiler versions.
//!
//! `write_canonical` and `debug_fields` MUST cover the same fields in the same order.
//! The canary diffs `debug_fields` output when `write_canonical` hashes disagree, so a
//! field present in one but not the other produces either an undiagnosable divergence or
//! a diff that lies.

use crate::{Fx, Sim};

/// Layout version. Bump when the byte layout below changes so old recorded hashes are
/// not compared against new ones by accident.
const LAYOUT_VERSION: u16 = 1;

fn put_u16(out: &mut Vec<u8>, v: u16) {
    out.extend_from_slice(&v.to_le_bytes());
}
fn put_u32(out: &mut Vec<u8>, v: u32) {
    out.extend_from_slice(&v.to_le_bytes());
}
fn put_u64(out: &mut Vec<u8>, v: u64) {
    out.extend_from_slice(&v.to_le_bytes());
}
fn put_fx(out: &mut Vec<u8>, v: Fx) {
    out.extend_from_slice(&v.to_bits().to_le_bytes());
}

pub(crate) fn write_canonical(sim: &Sim, out: &mut Vec<u8>) {
    put_u16(out, LAYOUT_VERSION);
    put_u64(out, sim.seed);
    put_u64(out, sim.world.tick.0);
    put_u32(out, sim.world.agents.len() as u32);
    for (id, agent) in &sim.world.agents {
        put_u32(out, id.0);
        put_fx(out, agent.pos.x);
        put_fx(out, agent.pos.y);
    }
}

pub(crate) fn debug_fields(sim: &Sim) -> Vec<(String, String)> {
    let mut f: Vec<(String, String)> = Vec::new();
    f.push(("seed".into(), sim.seed.to_string()));
    f.push(("tick".into(), sim.world.tick.0.to_string()));
    f.push(("agents.len".into(), sim.world.agents.len().to_string()));
    for (id, agent) in &sim.world.agents {
        let k = format!("agents[{}]", id.0);
        f.push((format!("{k}.pos.x"), fx_debug(agent.pos.x)));
        f.push((format!("{k}.pos.y"), fx_debug(agent.pos.y)));
    }
    f
}

/// Exact decimal rendering plus the raw bits, so a one-ulp divergence is visible.
fn fx_debug(v: Fx) -> String {
    format!("{v} (0x{:016x})", v.to_bits())
}
