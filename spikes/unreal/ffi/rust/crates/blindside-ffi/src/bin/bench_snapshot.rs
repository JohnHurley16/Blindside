//! What the boundary costs per frame.
//!
//! The question this answers is the only one that recurs forever: a client copies a belief
//! snapshot out of the sim every tick for the whole life of the project, so if that copy
//! is expensive the architecture is wrong and it is cheaper to know now.
//!
//! It times four things separately, because they have different fixes if any of them is
//! too slow:
//!
//! - `step`      — advancing the sim one tick. Not the boundary's cost; the sim's.
//! - `fill`      — staging the belief inside the library. In Phase 3 this is reading a
//!                 real `Belief`; here it is the stand-in derivation, which is if anything
//!                 more work per point than a read would be.
//! - `copy`      — `bs_sim_belief_snapshot` into a caller buffer. THIS is the boundary.
//! - `hash`      — `Sim::state_hash()`, because the on-screen readout calls it every frame
//!                 and BLAKE3 over a growing state is the thing most likely to surprise.
//!
//! Run: `cargo run -p blindside-ffi --release --bin bench-snapshot`
//!
//! `std::time::Instant` is fine here: this crate is not in the sim's dependency tree, and
//! DETERMINISM.md rule 3 constrains the sim, not a benchmark that measures it.

use std::time::Instant;

use blindside_ffi::{
    bs_sim_belief_snapshot, bs_sim_create, bs_sim_destroy, bs_sim_state_hash, bs_sim_step,
    bs_sim_tick, BsStatus,
};

/// Time `f` over `iters` iterations and return nanoseconds per iteration.
fn per_iter_ns(iters: u32, mut f: impl FnMut()) -> f64 {
    // Warm up: first touch of a fresh buffer is page faults, not the steady state a game
    // loop sees.
    for _ in 0..(iters / 10).max(1) {
        f();
    }
    let t0 = Instant::now();
    for _ in 0..iters {
        f();
    }
    t0.elapsed().as_nanos() as f64 / f64::from(iters)
}

fn main() {
    println!("blindside FFI boundary cost");
    println!("host: {} / {}", std::env::consts::OS, std::env::consts::ARCH);
    println!(
        "profile: {}",
        if cfg!(debug_assertions) {
            "debug-assertions ON (matches the workspace release profile, which keeps them \
             on for overflow checking)"
        } else {
            "debug-assertions off"
        }
    );
    println!();

    // A sim tick and a state hash do not depend on the snapshot size, so measure them once.
    {
        let s = bs_sim_create(0xB1D5_1DE0, 1);
        assert!(!s.is_null());
        let step_ns = per_iter_ns(200_000, || {
            assert_eq!(unsafe { bs_sim_step(s, 1) }, BsStatus::Ok);
        });
        let mut h = [0u8; 32];
        let hash_ns = per_iter_ns(200_000, || {
            assert_eq!(
                unsafe { bs_sim_state_hash(s, h.as_mut_ptr()) },
                BsStatus::Ok
            );
        });
        let mut t = 0u64;
        let tick_ns = per_iter_ns(500_000, || {
            assert_eq!(unsafe { bs_sim_tick(s, &mut t) }, BsStatus::Ok);
        });
        println!("per-call, independent of snapshot size:");
        println!("  bs_sim_step(1)      {step_ns:9.1} ns  (sim tick + 1-point stage)");
        println!("  bs_sim_state_hash   {hash_ns:9.1} ns  (BLAKE3 over the Phase 0 state)");
        println!("  bs_sim_tick         {tick_ns:9.1} ns  (a trivial call: this is what the");
        println!("                                  FFI call overhead itself costs)");
        unsafe { bs_sim_destroy(s) };
        println!();
    }

    // The sizes are not round numbers by accident. They come from the project's own
    // measurements, so the answer is about this game and not about memcpy in general:
    //
    //   76      Phase 1's toy lidar, one sweep (BELIEF-CATALOGUE.md 1.2)
    //   11,500  a real scanning sensor's returns in ONE 20 Hz tick, from
    //           DESIGN-PRINCIPLES.md 8's parameters (~23,000 per 10 Hz revolution)
    //   23,000  one full revolution, "what the machine sees now"
    //           (spikes/godot/cloud/LIDAR.md 6)
    //   500,000 the accumulated map after a 40 m drive, voxel-downsampled at 30 mm
    //           (LIDAR.md 6). This is the number that decides the architecture.
    // 1,530,334 the same walk NOT downsampled -- what the Godot cloud spike actually drew
    //           in one draw call (LIDAR.md, "10_accumulated_walk")
    //
    // 8192 is in the list only because it is blindside-ffi's stand-in default.
    println!("belief snapshot, by point count:");
    println!("  sim tick budget at 20 Hz = 50 ms; render frame at 60 Hz = 16.6 ms");
    println!(
        "{:>9}  {:>11}  {:>12}  {:>12}  {:>9}  {:>9}  {:>9}",
        "points", "bytes", "step+fill ns", "copy ns", "copy GB/s", "% 50ms", "% 16.6ms"
    );

    for &n in &[
        76u32, 8192, 11_500, 23_000, 65_536, 500_000, 1_530_334, 4_194_303,
    ] {
        let s = bs_sim_create(0xB1D5_1DE0, n);
        assert!(!s.is_null(), "create failed for {n} points");
        let bytes = 72 + (n as usize) * 16;
        let mut buf = vec![0u8; bytes];

        // step+fill: one sim tick and one restage of the whole cloud.
        let iters = if n > 100_000 {
            2_000
        } else if n > 32_768 {
            20_000
        } else {
            100_000
        };
        let fill_ns = per_iter_ns(iters, || {
            assert_eq!(unsafe { bs_sim_step(s, 1) }, BsStatus::Ok);
        });

        let mut written = 0u32;
        let copy_ns = per_iter_ns(iters, || {
            let st = unsafe {
                bs_sim_belief_snapshot(s, 0, buf.as_mut_ptr(), bytes as u32, &mut written)
            };
            assert_eq!(st, BsStatus::Ok);
        });
        assert_eq!(written as usize, bytes);

        let gbs = (bytes as f64) / copy_ns; // bytes/ns == GB/s
        let pct_tick = copy_ns / 50_000_000.0 * 100.0;
        let pct_frame = copy_ns / 16_666_666.0 * 100.0;
        println!(
            "{n:>9}  {bytes:>11}  {fill_ns:>12.1}  {copy_ns:>12.1}  {gbs:>9.2}  \
             {pct_tick:>8.3}%  {pct_frame:>8.3}%"
        );
        unsafe { bs_sim_destroy(s) };
    }

    println!();
    println!("create/destroy (not on the hot path, measured so nobody has to guess):");
    for &n in &[11_500u32, 500_000] {
        let ns = per_iter_ns(2_000, || {
            let s = bs_sim_create(1, n);
            unsafe { bs_sim_destroy(s) };
        });
        println!("  {n:>7} points  {:>10.1} us", ns / 1000.0);
    }
}
