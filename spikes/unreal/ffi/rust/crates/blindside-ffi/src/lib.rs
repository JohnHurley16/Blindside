//! blindside-ffi -- the C ABI over `blindside-sim`, for an engine client.
//!
//! # What this crate is for
//!
//! `blindside-sim` is the deterministic core (docs/DETERMINISM.md). A renderer is a
//! separate consumer that must be able to draw a match without ever being able to observe
//! ground truth (CLAUDE.md, the one invariant). This crate is the whole of the surface
//! between them. Everything an engine client can ever ask the sim is a function in this
//! file, and the generated header `include/blindside_sim.h` is the machine-checked
//! statement of that.
//!
//! # The invariant, at the ABI
//!
//! `blindside_sim::World` is `pub(crate)`. This crate cannot name it -- not for debugging,
//! not for a "just this once" accessor -- and so no function here can return it. That is a
//! stronger guarantee than a lint, because it is enforced by the Rust module system
//! before this crate compiles, and it is *visible*, because the generated C header is a
//! complete, readable list of what crosses. `tests/header_surface.rs` re-checks the
//! generated header mechanically, so a future function that widens the boundary fails a
//! test rather than a code review.
//!
//! Two things follow from this that are worth stating plainly:
//!
//! 1. The client gets a belief, a tick, and a hash. There is no "give me the world" call
//!    to accidentally add, because there is no type to return.
//! 2. This crate must NOT enable `blindside-sim`'s `diagnostics` feature. That feature is
//!    the tooling window onto ground truth (strings only) and the sim's own docs say no
//!    client crate may turn it on. `Cargo.toml` here takes `blindside-sim` with default
//!    features, and `tests/no_diagnostics.rs` fails if that changes.
//!
//! # Rules this file obeys
//!
//! - **No panic crosses the boundary.** Every `extern "C"` body is wrapped in
//!   `catch_unwind` and turns a panic into `BsStatus::Panic`. Since Rust 1.81 an unwind
//!   out of `extern "C"` aborts the process; aborting inside Unreal's editor loses the
//!   user's unsaved work, so it is caught here.
//! - **The caller frees nothing it cannot free.** The only owned thing handed out is the
//!   opaque `BsSim*`, freed by `bs_sim_destroy`. Snapshots are written into a
//!   caller-provided buffer. Strings returned are `'static` and must not be freed.
//! - **No allocation on the per-tick path.** The point staging buffer is allocated once,
//!   at `bs_sim_create`, and reused; `bs_sim_belief_snapshot` is a bounds check and two
//!   memcpys.
//!
//! # `unsafe` here, and why the deny is absent
//!
//! `blindside-sim`, `-vm` and `-content` carry `#![deny(unsafe_code)]` (DETERMINISM.md
//! rule 8). This crate cannot: dereferencing a caller's raw pointer is its entire job. It
//! is also not a constrained crate -- it is downstream of the sim, not in its dependency
//! tree -- so rules 1-8 do not apply to it. Every `unsafe` block below carries a
//! `// SAFETY:` note naming the contract the C caller must have met.

use std::panic::{catch_unwind, AssertUnwindSafe};

use blindside_sim::{MatchRecord, Sim, MATCH_RECORD_SCHEMA};

// ---------------------------------------------------------------------------
// Versions
// ---------------------------------------------------------------------------

/// Version of the *function* ABI: the names, signatures and calling convention. Bumped
/// when an existing function changes shape. A client that links a mismatched library
/// should refuse to run rather than call into it.
pub const BS_ABI_VERSION: u32 = 1;

/// Version of the *belief snapshot* byte layout, independent of the function ABI, since
/// the snapshot will change far more often than the calls that carry it. Written into
/// every snapshot header so a stale renderer detects it rather than misreads the bytes.
pub const BS_BELIEF_SCHEMA: u32 = 1;

/// Number of agents the stand-in belief reports.
///
/// GUESS / STAND-IN. The Phase 0 sim has two agents (`world.rs: INITIAL_AGENTS`) but
/// `World` is `pub(crate)`, so this crate genuinely cannot ask how many there are -- which
/// is the invariant working exactly as intended. Phase 3 replaces this constant with a
/// real public accessor on `Sim`. It is a constant here so that the number the renderer
/// draws is not silently wrong; it is deliberately not read from the sim.
const BS_STANDIN_AGENT_COUNT: u32 = 2;

/// Points per agent when `bs_sim_create` is passed `belief_points = 0`.
///
/// GUESS. ARCHITECTURE.md says the primary run-phase view is "a sparse 3D point cloud of
/// accumulated returns in the agent's estimated frame". No document says how many points
/// that is. 8192 is the spike's working number: at 16 bytes a point it is a 128 KiB copy,
/// large enough that if the copy were going to be a problem it would show up in the
/// measurement in NOTES.md. The designer should set the real ceiling.
const BS_DEFAULT_BELIEF_POINTS: u32 = 8192;

/// Hard ceiling on `belief_points`, so a bad number from script is a status code and not
/// a multi-gigabyte allocation.
const BS_MAX_BELIEF_POINTS: u32 = 1 << 22;

// ---------------------------------------------------------------------------
// Status
// ---------------------------------------------------------------------------

/// Every call returns one of these. 0 is success and every failure is negative, so
/// `if (status < 0)` is a correct check in C for the whole API, forever.
#[repr(i32)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum BsStatus {
    Ok = 0,
    /// A `BsSim*` argument was null.
    NullHandle = -1,
    /// An out-parameter pointer was null.
    NullOut = -2,
    /// The caller's buffer is smaller than `bs_sim_belief_bytes` reported.
    BufferTooSmall = -3,
    /// `agent_index` is not a live agent.
    BadAgent = -4,
    /// An argument was outside its documented range.
    BadArgument = -5,
    /// A panic was caught at the boundary. The sim instance should be considered
    /// poisoned: destroy it and make a new one. Reaching this is a bug in the sim, not in
    /// the caller.
    Panic = -6,
}

/// A human-readable name for a status. The returned pointer is to a `'static`
/// NUL-terminated string in the library's read-only data. **The caller must not free it**;
/// it stays valid for as long as the library is loaded.
#[no_mangle]
pub extern "C" fn bs_status_message(status: BsStatus) -> *const std::os::raw::c_char {
    let s: &'static [u8] = match status {
        BsStatus::Ok => b"ok\0",
        BsStatus::NullHandle => b"null sim handle\0",
        BsStatus::NullOut => b"null out-parameter\0",
        BsStatus::BufferTooSmall => b"buffer smaller than bs_sim_belief_bytes\0",
        BsStatus::BadAgent => b"no such agent index\0",
        BsStatus::BadArgument => b"argument out of range\0",
        BsStatus::Panic => b"panic caught at the FFI boundary; destroy this sim\0",
    };
    s.as_ptr() as *const std::os::raw::c_char
}

// ---------------------------------------------------------------------------
// The belief snapshot layout
// ---------------------------------------------------------------------------

/// Fixed-size header of a belief snapshot. The caller's buffer holds one of these
/// followed immediately by `point_count` [`BsBeliefPoint`]s, with no padding between them
/// (`BsBeliefHeader` is 8-aligned and 72 bytes, `BsBeliefPoint` is 4-aligned and 16).
///
/// Every fixed-point field is the RAW BITS of the sim's `Fx = fixed::types::I32F32`, as
/// `int64_t`. It is never converted to a float on the sim side -- DETERMINISM.md rule 1
/// forbids `f32`/`f64` anywhere in the sim, and that includes "just to hand to the
/// renderer". The renderer divides by 2^32 itself, on its own side of the line, where
/// floats are allowed and are nobody's determinism problem.
#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct BsBeliefHeader {
    /// [`BS_BELIEF_SCHEMA`] at the time the snapshot was written.
    pub schema: u32,
    pub agent_index: u32,
    /// The tick this belief is as of.
    pub tick: u64,
    /// Estimated pose. `Fx` raw bits; divide by 2^32 for metres.
    pub pose_x: i64,
    pub pose_y: i64,
    pub pose_z: i64,
    /// Estimated heading. `Fx` raw bits; radians.
    pub pose_yaw: i64,
    /// Trace of the position covariance -- how lost the agent thinks it is. `Fx` raw bits.
    /// This is what makes drift legible in the point cloud.
    pub pose_var: i64,
    /// Ticks since the last position fix. The "am I lost" readout.
    pub ticks_since_fix: u32,
    /// Number of `BsBeliefPoint`s following this header.
    pub point_count: u32,
    /// Reserved; currently always 0. Present so a flag can be added without moving fields.
    pub flags: u32,
    /// Explicit tail padding, so the struct's size is the same on every compiler and a
    /// `memcmp` of two snapshots does not read uninitialised bytes.
    pub reserved: u32,
}

/// One accumulated sensor return in the agent's *estimated* frame.
///
/// Coordinates are `Fx16.16` raw bits (`int32_t`), not the sim's full I32F32. A display
/// point does not need 32 fractional bits, and halving the width halves the per-frame
/// copy, which is the one cost that recurs forever. The sim keeps full precision; the
/// truncation happens here, on the render side of the line, and never feeds back.
#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct BsBeliefPoint {
    pub x: i32,
    pub y: i32,
    pub z: i32,
    /// Return quality, 0..=65535. Drives point brightness.
    pub quality: u16,
    /// Ticks since this return was accumulated, saturating. Drives fade-out.
    pub age: u16,
}

// ---------------------------------------------------------------------------
// The handle
// ---------------------------------------------------------------------------

/// Opaque handle to one simulation. The C side only ever holds a pointer to this; the
/// layout is deliberately absent from the header, so a client cannot reach past the API
/// by casting. cbindgen emits it as an opaque struct because it is not `#[repr(C)]`.
pub struct BsSim {
    sim: Sim,
    /// Reused every tick. Allocated once, at create.
    points: Vec<BsBeliefPoint>,
    points_per_agent: usize,
    header: BsBeliefHeader,
}

impl BsSim {
    /// Refill the stand-in belief from the sim's PUBLIC surface only.
    ///
    /// STAND-IN -- read this before believing any number that comes out of it.
    ///
    /// The Phase 0 sim has no `Belief` and no public way to reach an agent's state, so
    /// there is nothing real to snapshot yet. What this does instead is derive a point
    /// cloud deterministically from `Sim::state_hash()` and `Sim::tick()` -- both public,
    /// both genuinely functions of the simulation's state -- so that:
    ///
    /// - the bytes the renderer draws provably came from the sim and change when it does;
    /// - the snapshot has a realistic *volume*, which is the thing being measured;
    /// - the code path is the one Phase 3 keeps (fill a reused staging buffer on step,
    ///   memcpy it out on demand), with a real `Belief` replacing the derivation.
    ///
    /// It is NOT a model of what a belief looks like. Nothing should be tuned against
    /// these positions.
    fn refill(&mut self, agent_index: u32) {
        let hash = self.sim.state_hash();
        let tick = self.sim.tick().0;

        // splitmix64 over (hash-derived seed, tick, agent, index). Cheap, deterministic,
        // and self-contained: it does not touch the sim's DeterministicRng, whose Purpose
        // codes are part of the replay contract and are not this crate's to spend.
        let mut lane = u64::from_le_bytes([
            hash[0], hash[1], hash[2], hash[3], hash[4], hash[5], hash[6], hash[7],
        ]) ^ (u64::from(agent_index) << 48);

        // +-32 m in Fx16.16: raw bits within +-(32 << 16) == +-(1 << 21).
        fn coord(bits: u32) -> i32 {
            ((bits >> 11) as i32).wrapping_sub(1 << 20)
        }

        for (i, p) in self.points.iter_mut().enumerate() {
            let mut z = lane
                .wrapping_add(0x9E37_79B9_7F4A_7C15)
                .wrapping_add(i as u64);
            lane = z;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
            z ^= z >> 31;
            p.x = coord(z as u32);
            p.y = coord((z >> 16) as u32);
            p.z = coord((z >> 32) as u32) / 4; // caves are wider than they are tall
            p.quality = (z >> 48) as u16;
            p.age = ((tick.wrapping_add(i as u64)) % 600) as u16;
        }

        self.header = BsBeliefHeader {
            schema: BS_BELIEF_SCHEMA,
            agent_index,
            tick,
            // Fx raw bits, i.e. value * 2^32. Derived from the hash, same caveat as above.
            pose_x: i64::from(lane as i32) << 16,
            pose_y: i64::from((lane >> 20) as i32) << 16,
            pose_z: 0,
            pose_yaw: i64::from((lane >> 40) as u16) << 16,
            pose_var: ((tick % 4096) as i64) << 26,
            ticks_since_fix: (tick % 4096) as u32,
            point_count: self.points.len() as u32,
            flags: 0,
            reserved: 0,
        };
    }

    fn snapshot_bytes(&self) -> usize {
        std::mem::size_of::<BsBeliefHeader>()
            + self.points_per_agent * std::mem::size_of::<BsBeliefPoint>()
    }
}

// ---------------------------------------------------------------------------
// Boundary plumbing
// ---------------------------------------------------------------------------

/// Run `f`, turning any panic into [`BsStatus::Panic`] instead of an abort.
fn guard<F: FnOnce() -> BsStatus>(f: F) -> BsStatus {
    match catch_unwind(AssertUnwindSafe(f)) {
        Ok(s) => s,
        Err(_) => BsStatus::Panic,
    }
}

// ---------------------------------------------------------------------------
// The API. This list is the entire boundary.
// ---------------------------------------------------------------------------

/// [`BS_ABI_VERSION`] of the loaded library. Call this first and refuse to continue on a
/// mismatch; it is the one call whose signature is promised never to change.
#[no_mangle]
pub extern "C" fn bs_abi_version() -> u32 {
    BS_ABI_VERSION
}

/// [`BS_BELIEF_SCHEMA`] of the loaded library.
#[no_mangle]
pub extern "C" fn bs_belief_schema() -> u32 {
    BS_BELIEF_SCHEMA
}

/// Size in bytes of [`BsBeliefHeader`] as this library laid it out. A client compares it
/// with its own `sizeof` at startup; a mismatch means the header and the binary disagree
/// and every snapshot after that would be read at the wrong offsets.
#[no_mangle]
pub extern "C" fn bs_belief_header_size() -> u32 {
    std::mem::size_of::<BsBeliefHeader>() as u32
}

/// Size in bytes of [`BsBeliefPoint`]. See [`bs_belief_header_size`].
#[no_mangle]
pub extern "C" fn bs_belief_point_size() -> u32 {
    std::mem::size_of::<BsBeliefPoint>() as u32
}

/// Create a simulation for `seed`.
///
/// `belief_points` is the stand-in point-cloud size per agent; pass 0 for the default
/// (8192). It exists so the spike's benchmark can sweep sizes without a rebuild, and it
/// disappears in Phase 3, when the count comes from the agent's actual belief.
///
/// Returns null if `belief_points` exceeds the ceiling, or on allocation failure. The
/// returned pointer must be given to [`bs_sim_destroy`] exactly once.
#[no_mangle]
pub extern "C" fn bs_sim_create(seed: u64, belief_points: u32) -> *mut BsSim {
    let mut out: *mut BsSim = std::ptr::null_mut();
    let _ = guard(|| {
        let n = if belief_points == 0 {
            BS_DEFAULT_BELIEF_POINTS
        } else {
            belief_points
        };
        if n > BS_MAX_BELIEF_POINTS {
            return BsStatus::BadArgument;
        }
        // The record the sim is built from. Phase 0 consumes only the seed; the rest are
        // the empty stubs the sim's own tests use. A real client loads a record from disk
        // or from the server, and `MatchRecord::validate` gates it before this point.
        let record = MatchRecord {
            schema: MATCH_RECORD_SCHEMA,
            seed,
            content_hash: [0u8; 32],
            loadouts: Vec::new(),
            policies: Vec::new(),
            commands: Vec::new(),
            ticks: 0,
            final_hash: [0u8; 32],
        };
        let mut boxed = Box::new(BsSim {
            sim: Sim::new(&record),
            points: vec![BsBeliefPoint::default(); n as usize],
            points_per_agent: n as usize,
            header: BsBeliefHeader::default(),
        });
        boxed.refill(0);
        out = Box::into_raw(boxed);
        BsStatus::Ok
    });
    out
}

/// Destroy a simulation. Null is a no-op, so a client's teardown path needs no null
/// check. Passing the same pointer twice is undefined, as it is for `free`.
///
/// # Safety
/// `sim` must be null, or a pointer returned by [`bs_sim_create`] and not yet destroyed.
#[no_mangle]
pub unsafe extern "C" fn bs_sim_destroy(sim: *mut BsSim) {
    if sim.is_null() {
        return;
    }
    let _ = guard(|| {
        // SAFETY: caller contract above -- `sim` came from `Box::into_raw` in
        // `bs_sim_create` and has not been destroyed, so reclaiming the Box is the
        // matching free.
        drop(unsafe { Box::from_raw(sim) });
        BsStatus::Ok
    });
}

/// Advance the sim by `ticks` ticks and refresh agent 0's staged belief.
///
/// This is the whole of "run the simulation". A client with a fixed timestep calls it
/// with 1 per sim tick; a client catching up after a hitch calls it with n.
///
/// # Safety
/// `sim` must be a live pointer from [`bs_sim_create`], and no other thread may be
/// calling into the same handle concurrently.
#[no_mangle]
pub unsafe extern "C" fn bs_sim_step(sim: *mut BsSim, ticks: u32) -> BsStatus {
    if sim.is_null() {
        return BsStatus::NullHandle;
    }
    // SAFETY: caller contract; the handle is live and uniquely owned by the caller, which
    // is single-threaded with respect to this sim (stated in the header).
    let s = unsafe { &mut *sim };
    guard(move || {
        for _ in 0..ticks {
            s.sim.step();
        }
        s.refill(0);
        BsStatus::Ok
    })
}

/// Write the current tick to `out_tick`.
///
/// # Safety
/// `sim` must be live; `out_tick` must point to a writable `uint64_t`.
#[no_mangle]
pub unsafe extern "C" fn bs_sim_tick(sim: *const BsSim, out_tick: *mut u64) -> BsStatus {
    if sim.is_null() {
        return BsStatus::NullHandle;
    }
    if out_tick.is_null() {
        return BsStatus::NullOut;
    }
    // SAFETY: both pointers checked non-null; caller contract gives validity.
    let s = unsafe { &*sim };
    guard(move || {
        // SAFETY: `out_tick` checked non-null and documented writable.
        unsafe { *out_tick = s.sim.tick().0 };
        BsStatus::Ok
    })
}

/// Write the seed this sim was created with to `out_seed`.
///
/// # Safety
/// As [`bs_sim_tick`].
#[no_mangle]
pub unsafe extern "C" fn bs_sim_seed(sim: *const BsSim, out_seed: *mut u64) -> BsStatus {
    if sim.is_null() {
        return BsStatus::NullHandle;
    }
    if out_seed.is_null() {
        return BsStatus::NullOut;
    }
    // SAFETY: checked non-null; caller contract.
    let s = unsafe { &*sim };
    guard(move || {
        // SAFETY: checked non-null.
        unsafe { *out_seed = s.sim.seed() };
        BsStatus::Ok
    })
}

/// Copy the 32-byte BLAKE3 state hash into `out32`.
///
/// This is the number the desync canary compares. A client that shows it on screen is
/// showing the same value the server and the harness compute for that tick, which makes
/// "the two machines disagree" something a human can see rather than infer.
///
/// # Safety
/// `sim` must be live; `out32` must point to at least 32 writable bytes.
#[no_mangle]
pub unsafe extern "C" fn bs_sim_state_hash(sim: *const BsSim, out32: *mut u8) -> BsStatus {
    if sim.is_null() {
        return BsStatus::NullHandle;
    }
    if out32.is_null() {
        return BsStatus::NullOut;
    }
    // SAFETY: checked non-null; caller contract.
    let s = unsafe { &*sim };
    guard(move || {
        let h = s.sim.state_hash();
        // SAFETY: `out32` is documented as at least 32 writable bytes; `h` is exactly 32
        // and is a local, so the regions cannot overlap.
        unsafe { std::ptr::copy_nonoverlapping(h.as_ptr(), out32, 32) };
        BsStatus::Ok
    })
}

/// Number of agents whose belief can be snapshotted.
///
/// STAND-IN, see [`BS_STANDIN_AGENT_COUNT`]: this crate cannot ask the sim, because the
/// roster lives in `World`, which is `pub(crate)`.
///
/// # Safety
/// As [`bs_sim_tick`].
#[no_mangle]
pub unsafe extern "C" fn bs_sim_agent_count(sim: *const BsSim, out_count: *mut u32) -> BsStatus {
    if sim.is_null() {
        return BsStatus::NullHandle;
    }
    if out_count.is_null() {
        return BsStatus::NullOut;
    }
    guard(move || {
        // SAFETY: checked non-null.
        unsafe { *out_count = BS_STANDIN_AGENT_COUNT };
        BsStatus::Ok
    })
}

/// Bytes [`bs_sim_belief_snapshot`] will write for `agent_index`. Call it once at startup
/// and size the buffer; never call it on the hot path, because the size is fixed for the
/// life of the sim.
///
/// # Safety
/// `sim` must be live; `out_bytes` must point to a writable `uint32_t`.
#[no_mangle]
pub unsafe extern "C" fn bs_sim_belief_bytes(
    sim: *const BsSim,
    agent_index: u32,
    out_bytes: *mut u32,
) -> BsStatus {
    if sim.is_null() {
        return BsStatus::NullHandle;
    }
    if out_bytes.is_null() {
        return BsStatus::NullOut;
    }
    if agent_index >= BS_STANDIN_AGENT_COUNT {
        return BsStatus::BadAgent;
    }
    // SAFETY: checked non-null; caller contract.
    let s = unsafe { &*sim };
    guard(move || {
        // SAFETY: checked non-null.
        unsafe { *out_bytes = s.snapshot_bytes() as u32 };
        BsStatus::Ok
    })
}

/// Copy `agent_index`'s belief into the caller's buffer: a [`BsBeliefHeader`] followed by
/// `header.point_count` [`BsBeliefPoint`]s.
///
/// The buffer belongs to the caller from creation to destruction. Nothing is allocated
/// here, nothing is handed back to free, and the library keeps no pointer into it after
/// the call returns. This is the call that happens every frame forever, so it is a bounds
/// check and two memcpys and nothing else.
///
/// Fails with [`BsStatus::BufferTooSmall`] rather than writing a partial snapshot, so a
/// caller that sized its buffer against an older schema gets an error, not silent garbage.
///
/// # Safety
/// `sim` must be live. `buffer` must point to at least `buffer_bytes` writable bytes.
/// `out_written` may be null.
#[no_mangle]
pub unsafe extern "C" fn bs_sim_belief_snapshot(
    sim: *const BsSim,
    agent_index: u32,
    buffer: *mut u8,
    buffer_bytes: u32,
    out_written: *mut u32,
) -> BsStatus {
    if sim.is_null() {
        return BsStatus::NullHandle;
    }
    if buffer.is_null() {
        return BsStatus::NullOut;
    }
    if agent_index >= BS_STANDIN_AGENT_COUNT {
        return BsStatus::BadAgent;
    }
    // SAFETY: checked non-null; caller contract.
    let s = unsafe { &*sim };
    guard(move || {
        let need = s.snapshot_bytes();
        if (buffer_bytes as usize) < need {
            return BsStatus::BufferTooSmall;
        }
        let hdr_len = std::mem::size_of::<BsBeliefHeader>();
        let mut header = s.header;
        header.agent_index = agent_index;
        // SAFETY: `buffer` has at least `need` >= `hdr_len` writable bytes, and `header`
        // is a local `Copy` value so the regions cannot overlap. The header is written
        // byte-wise rather than through a `*mut BsBeliefHeader` because
        // `copy_nonoverlapping::<u8>` needs no alignment guarantee: a misaligned client
        // buffer is then merely slow rather than undefined behaviour.
        unsafe {
            std::ptr::copy_nonoverlapping(
                (&header as *const BsBeliefHeader) as *const u8,
                buffer,
                hdr_len,
            );
            // SAFETY: the points region is `need - hdr_len` bytes, exactly the staging
            // buffer's size, and lies inside the caller's buffer by the check above.
            std::ptr::copy_nonoverlapping(
                s.points.as_ptr() as *const u8,
                buffer.add(hdr_len),
                need - hdr_len,
            );
        }
        if !out_written.is_null() {
            // SAFETY: checked non-null.
            unsafe { *out_written = need as u32 };
        }
        BsStatus::Ok
    })
}

/// Deliberately panic inside the library, to prove the boundary catches it.
///
/// SPIKE ONLY. It exists so NOTES.md can *show* a caught panic returning
/// [`BsStatus::Panic`] with the editor still running, rather than assert that it would.
/// It must not exist in a shipped library; `tests/header_surface.rs` names it as the one
/// allowed exception, so deleting it does not mean editing the test twice.
///
/// # Safety
/// `sim` must be live.
#[no_mangle]
pub unsafe extern "C" fn bs_sim_spike_force_panic(sim: *const BsSim) -> BsStatus {
    if sim.is_null() {
        return BsStatus::NullHandle;
    }
    guard(|| panic!("deliberate spike panic, to prove the boundary catches it"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn layout_is_what_the_header_promises() {
        assert_eq!(std::mem::size_of::<BsBeliefHeader>(), 72);
        assert_eq!(std::mem::align_of::<BsBeliefHeader>(), 8);
        assert_eq!(std::mem::size_of::<BsBeliefPoint>(), 16);
        assert_eq!(std::mem::align_of::<BsBeliefPoint>(), 4);
        assert_eq!(bs_belief_header_size(), 72);
        assert_eq!(bs_belief_point_size(), 16);
    }

    #[test]
    fn create_step_snapshot_destroy() {
        let s = bs_sim_create(0xDEAD_BEEF, 1024);
        assert!(!s.is_null());
        let mut bytes = 0u32;
        assert_eq!(
            unsafe { bs_sim_belief_bytes(s, 0, &mut bytes) },
            BsStatus::Ok
        );
        assert_eq!(bytes as usize, 72 + 1024 * 16);
        let mut buf = vec![0u8; bytes as usize];
        let mut written = 0u32;
        assert_eq!(
            unsafe { bs_sim_belief_snapshot(s, 0, buf.as_mut_ptr(), bytes, &mut written) },
            BsStatus::Ok
        );
        assert_eq!(written, bytes);
        assert_eq!(unsafe { bs_sim_step(s, 10) }, BsStatus::Ok);
        let mut t = 0u64;
        assert_eq!(unsafe { bs_sim_tick(s, &mut t) }, BsStatus::Ok);
        assert_eq!(t, 10);
        let mut h = [0u8; 32];
        assert_eq!(unsafe { bs_sim_state_hash(s, h.as_mut_ptr()) }, BsStatus::Ok);
        assert_ne!(h, [0u8; 32]);
        unsafe { bs_sim_destroy(s) };
    }

    /// Two sims from one seed agree tick for tick through the C API, including the bytes
    /// the renderer would draw. This is the canary's property re-checked at the boundary:
    /// if the FFI ever introduced state of its own, this is what would catch it.
    #[test]
    fn the_c_api_is_deterministic_for_a_seed() {
        let a = bs_sim_create(7, 256);
        let b = bs_sim_create(7, 256);
        let mut buf_a = vec![0u8; 72 + 256 * 16];
        let mut buf_b = vec![0u8; 72 + 256 * 16];
        for _ in 0..200 {
            unsafe { bs_sim_step(a, 1) };
            unsafe { bs_sim_step(b, 1) };
            let n = buf_a.len() as u32;
            unsafe {
                bs_sim_belief_snapshot(a, 0, buf_a.as_mut_ptr(), n, std::ptr::null_mut());
                bs_sim_belief_snapshot(b, 0, buf_b.as_mut_ptr(), n, std::ptr::null_mut());
            }
            assert_eq!(buf_a, buf_b);
        }
        unsafe {
            bs_sim_destroy(a);
            bs_sim_destroy(b);
        }
    }

    #[test]
    fn the_snapshot_changes_every_tick() {
        let s = bs_sim_create(3, 64);
        let n = (72 + 64 * 16) as u32;
        let mut prev = vec![0u8; n as usize];
        unsafe { bs_sim_belief_snapshot(s, 0, prev.as_mut_ptr(), n, std::ptr::null_mut()) };
        for _ in 0..50 {
            unsafe { bs_sim_step(s, 1) };
            let mut cur = vec![0u8; n as usize];
            unsafe { bs_sim_belief_snapshot(s, 0, cur.as_mut_ptr(), n, std::ptr::null_mut()) };
            assert_ne!(cur, prev);
            prev = cur;
        }
        unsafe { bs_sim_destroy(s) };
    }

    #[test]
    fn every_argument_error_is_a_status_and_not_a_crash() {
        assert_eq!(
            unsafe { bs_sim_step(std::ptr::null_mut(), 1) },
            BsStatus::NullHandle
        );
        assert_eq!(
            unsafe { bs_sim_tick(std::ptr::null(), std::ptr::null_mut()) },
            BsStatus::NullHandle
        );
        assert!(bs_sim_create(1, BS_MAX_BELIEF_POINTS + 1).is_null());
        let s = bs_sim_create(1, 16);
        let mut t = 0u64;
        assert_eq!(
            unsafe { bs_sim_tick(s, std::ptr::null_mut()) },
            BsStatus::NullOut
        );
        assert_eq!(unsafe { bs_sim_tick(s, &mut t) }, BsStatus::Ok);
        let mut bytes = 0u32;
        assert_eq!(
            unsafe { bs_sim_belief_bytes(s, 99, &mut bytes) },
            BsStatus::BadAgent
        );
        let mut small = [0u8; 8];
        assert_eq!(
            unsafe { bs_sim_belief_snapshot(s, 0, small.as_mut_ptr(), 8, std::ptr::null_mut()) },
            BsStatus::BufferTooSmall
        );
        // A too-small buffer must not have been touched.
        assert_eq!(small, [0u8; 8]);
        unsafe { bs_sim_destroy(s) };
        // Destroying null is a documented no-op.
        unsafe { bs_sim_destroy(std::ptr::null_mut()) };
    }

    #[test]
    fn a_panic_becomes_a_status_instead_of_an_abort() {
        let s = bs_sim_create(1, 16);
        let prev = std::panic::take_hook();
        std::panic::set_hook(Box::new(|_| {}));
        let r = unsafe { bs_sim_spike_force_panic(s) };
        std::panic::set_hook(prev);
        assert_eq!(r, BsStatus::Panic);
        // ...and the process is still here to say so, and the sim still answers.
        let mut t = 0u64;
        assert_eq!(unsafe { bs_sim_tick(s, &mut t) }, BsStatus::Ok);
        unsafe { bs_sim_destroy(s) };
    }
}
