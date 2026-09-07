//! The emitter load. Agents random-walk the cave at Phase 1 speeds; sonar pings on
//! Phase 1 cooldowns (8 s aggressive, 24 s cautious); 1-2 static ancient signatures on
//! Phase 1's 75 s cycle (13 s audible per cycle); motion noise from every moving agent
//! every MOTION_LISTEN_PERIOD (0.5 s = 10 ticks); a few crashes. Listener sampling
//! cadence copies Phase 1's sensor rig: pings every 10 ticks for 60 ticks, ancient every
//! 5 ticks, motion once per period, crash once. The schedule is generated once and
//! replayed identically through every model, so the numbers are comparable.

use crate::cave::Cave;
use crate::grid::{Queue, Slot};
use crate::rng::Rng;
use crate::skel::{Graph, GraphField};
use std::collections::VecDeque;
use std::time::Instant;

pub const TICK_HZ: f32 = 20.0;

#[derive(Clone, Copy)]
pub struct Params {
    pub ticks: usize,
    pub agents: usize,
    pub ancients: usize,
    pub crashes: usize,
    pub ping_range: f32,
    pub motion_range: f32,
    pub ancient_range: f32,
    pub crash_range: f32,
    pub ping_audible_ticks: u32,
    pub ping_sample_every: u32,
    pub ancient_sample_every: u32,
    pub motion_every: u32,
    pub aggressive_cooldown_s: f32,
    pub cautious_cooldown_s: f32,
    pub ancient_period_s: f32,
    pub ancient_audible_s: f32,
    pub echo_per_ping: usize,
}

impl Default for Params {
    fn default() -> Self {
        Params {
            ticks: 9600,
            agents: 8,
            ancients: 2,
            crashes: 4,
            ping_range: 170.0,
            motion_range: 40.0,
            ancient_range: 80.0,
            crash_range: 170.0,
            ping_audible_ticks: 60,
            ping_sample_every: 10,
            ancient_sample_every: 5,
            motion_every: 10,
            aggressive_cooldown_s: 8.0,
            cautious_cooldown_s: 24.0,
            ancient_period_s: 75.0,
            ancient_audible_s: 13.0,
            echo_per_ping: 0,
        }
    }
}

#[derive(Clone, Copy, PartialEq, Debug)]
pub enum Kind {
    Ping,
    Echo,
    Ancient,
    Motion,
    Crash,
}

#[derive(Clone, Copy)]
pub struct Emission {
    pub id: u32,
    pub kind: Kind,
    pub cell: u32,
    pub x: f32,
    pub y: f32,
    pub range: f32,
    pub start: u32,
    pub end: u32, // exclusive
    pub emitter: usize, // agent index or usize::MAX
}

pub struct Schedule {
    pub p: Params,
    pub pos: Vec<(f32, f32)>, // [tick * agents + a]
    pub emissions: Vec<Emission>, // sorted by start
    pub ancient_pos: Vec<(f32, f32)>,
}

fn bfs_path(cave: &Cave, walk_ok: &[bool], from: usize, to: usize) -> Vec<usize> {
    let n = cave.cells.len();
    let mut pred = vec![u32::MAX; n];
    let mut q = VecDeque::new();
    pred[from] = from as u32;
    q.push_back(from);
    while let Some(c) = q.pop_front() {
        if c == to {
            break;
        }
        let (x, y) = cave.xy(c);
        for (dx, dy) in crate::cave::NEIGH {
            let nx = x as i32 + dx;
            let ny = y as i32 + dy;
            if nx < 0 || ny < 0 || nx >= cave.w as i32 || ny >= cave.h as i32 {
                continue;
            }
            let ni = cave.idx(nx as usize, ny as usize);
            if walk_ok[ni] && pred[ni] == u32::MAX {
                pred[ni] = c as u32;
                q.push_back(ni);
            }
        }
    }
    if pred[to] == u32::MAX {
        return vec![from];
    }
    let mut path = vec![to];
    let mut c = to;
    while c != from {
        c = pred[c] as usize;
        path.push(c);
    }
    path.reverse();
    path
}

impl Schedule {
    pub fn generate(cave: &Cave, p: Params, seed: u64) -> Schedule {
        let mut rng = Rng::new(seed ^ 0x5151);
        let walk = cave.walkable_cells();
        let walk_ok: Vec<bool> = cave.cells.iter().map(|&c| c == crate::cave::DRY).collect();
        let n_agents = p.agents;
        let mut pos = vec![(0.0f32, 0.0f32); p.ticks * n_agents];
        // Agents: even index aggressive (fast, 8 s cooldown), odd cautious (24 s).
        let speeds: Vec<f32> = (0..n_agents).map(|a| if a % 2 == 0 { 1.4 } else { 1.1 }).collect();
        let cooldown: Vec<f32> = (0..n_agents).map(|a| if a % 2 == 0 { p.aggressive_cooldown_s } else { p.cautious_cooldown_s }).collect();
        let mut emissions: Vec<Emission> = Vec::new();
        let mut next_id = 0u32;
        // Ancients: static, in walkable cells.
        let ancient_pos: Vec<(f32, f32)> = (0..p.ancients).map(|_| cave.centre(walk[rng.below(walk.len())] as usize)).collect();
        let mut next_ping: Vec<u32> = (0..n_agents).map(|a| (rng.f64() * cooldown[a] as f64 * TICK_HZ as f64) as u32).collect();
        let mut cur: Vec<(f32, f32)> = Vec::new();
        let mut paths: Vec<Vec<usize>> = Vec::new();
        let mut seg: Vec<usize> = vec![0; n_agents];
        let mut frac: Vec<f32> = vec![0.0; n_agents];
        for _ in 0..n_agents {
            let c = walk[rng.below(walk.len())] as usize;
            cur.push(cave.centre(c));
            paths.push(vec![c]);
        }
        let crash_ticks: Vec<u32> = (0..p.crashes).map(|_| (rng.f64() * p.ticks as f64) as u32).collect();
        for t in 0..p.ticks as u32 {
            for a in 0..n_agents {
                // Advance along the path at speed cells/s.
                let mut budget = speeds[a] / TICK_HZ;
                while budget > 0.0 {
                    if seg[a] + 1 >= paths[a].len() {
                        let from = *paths[a].last().unwrap();
                        let to = walk[rng.below(walk.len())] as usize;
                        let path = bfs_path(cave, &walk_ok, from, to);
                        paths[a] = path;
                        seg[a] = 0;
                        frac[a] = 0.0;
                        if paths[a].len() < 2 {
                            break;
                        }
                    }
                    let (ax, ay) = cave.centre(paths[a][seg[a]]);
                    let (bx, by) = cave.centre(paths[a][seg[a] + 1]);
                    let seglen = ((bx - ax).powi(2) + (by - ay).powi(2)).sqrt();
                    let remaining = (1.0 - frac[a]) * seglen;
                    if budget >= remaining {
                        budget -= remaining;
                        seg[a] += 1;
                        frac[a] = 0.0;
                    } else {
                        frac[a] += budget / seglen;
                        budget = 0.0;
                    }
                }
                let (ax, ay) = cave.centre(paths[a][seg[a]]);
                let (bx, by) = if seg[a] + 1 < paths[a].len() { cave.centre(paths[a][seg[a] + 1]) } else { (ax, ay) };
                cur[a] = (ax + (bx - ax) * frac[a], ay + (by - ay) * frac[a]);
                pos[t as usize * n_agents + a] = cur[a];
                if t >= next_ping[a] {
                    next_ping[a] = t + (cooldown[a] * TICK_HZ * (0.9 + 0.2 * rng.f64() as f32)) as u32;
                    let cell = cave.cell_of(cur[a].0, cur[a].1).unwrap() as u32;
                    emissions.push(Emission { id: next_id, kind: Kind::Ping, cell, x: cur[a].0, y: cur[a].1, range: p.ping_range, start: t, end: t + p.ping_audible_ticks, emitter: a });
                    next_id += 1;
                    for _ in 0..p.echo_per_ping {
                        let ec = walk[rng.below(walk.len())] as usize;
                        let (ex, ey) = cave.centre(ec);
                        emissions.push(Emission { id: next_id, kind: Kind::Echo, cell: ec as u32, x: ex, y: ey, range: p.ping_range, start: t + 20, end: t + 20 + p.ping_audible_ticks, emitter: usize::MAX });
                        next_id += 1;
                    }
                }
            }
            // Motion noise: one emission per agent per period (agents always move here).
            if t % p.motion_every == 0 {
                for a in 0..n_agents {
                    let cell = cave.cell_of(cur[a].0, cur[a].1).unwrap() as u32;
                    emissions.push(Emission { id: next_id, kind: Kind::Motion, cell, x: cur[a].0, y: cur[a].1, range: p.motion_range, start: t, end: t + 1, emitter: a });
                    next_id += 1;
                }
            }
            for &ct in &crash_ticks {
                if ct == t {
                    let a = rng.below(n_agents);
                    let cell = cave.cell_of(cur[a].0, cur[a].1).unwrap() as u32;
                    emissions.push(Emission { id: next_id, kind: Kind::Crash, cell, x: cur[a].0, y: cur[a].1, range: p.crash_range, start: t, end: t + 1, emitter: usize::MAX });
                    next_id += 1;
                }
            }
        }
        // Ancients: one emission per audible window.
        let period = (p.ancient_period_s * TICK_HZ) as u32;
        let audible = (p.ancient_audible_s * TICK_HZ) as u32;
        for (k, &(ax, ay)) in ancient_pos.iter().enumerate() {
            let phase = (k as u32 * 610) % period;
            let mut start = period - audible + phase;
            while start < p.ticks as u32 {
                let cell = cave.cell_of(ax, ay).unwrap() as u32;
                emissions.push(Emission { id: next_id, kind: Kind::Ancient, cell, x: ax, y: ay, range: p.ancient_range, start, end: (start + audible).min(p.ticks as u32), emitter: usize::MAX });
                next_id += 1;
                start += period;
            }
        }
        emissions.sort_by_key(|e| (e.start, e.id));
        Schedule { p, pos, emissions, ancient_pos }
    }

    pub fn counts(&self) -> String {
        let c = |k: Kind| self.emissions.iter().filter(|e| e.kind == k).count();
        format!("pings {} echoes {} ancient windows {} motion {} crashes {}", c(Kind::Ping), c(Kind::Echo), c(Kind::Ancient), c(Kind::Motion), c(Kind::Crash))
    }
}

/// What a model must do. `listen` returns (path distance, bearing) or None.
pub trait Model {
    fn name(&self) -> &'static str;
    fn listen(&mut self, cave: &Cave, e: &Emission, lx: f32, ly: f32) -> Option<(f32, f32)>;
    fn end_tick(&mut self, live: &[Emission]);
    fn bytes(&self) -> usize;
    fn work(&self) -> (u64, u64); // (builds, pops)
    fn cave_changed(&mut self, cave: &Cave) -> f64; // ms
}

// ---- Model A family --------------------------------------------------------------------

#[derive(Clone, Copy, PartialEq)]
pub enum GridMode {
    PerTick, // build fully, discard at end of tick
    Cached,  // build fully once, keep for the emission's life
    Lazy,    // resume to the farthest listener asked, keep for the emission's life
}

pub struct GridModel {
    mode: GridMode,
    unit: u32,
    queue: Queue,
    slots: Vec<Slot>,
    owner: Vec<u32>, // emission id per slot, NONE if free
    n: usize,
    builds: u64,
    pops: u64,
    pub peak_slots: usize,
}

impl GridModel {
    pub fn new(cave: &Cave, mode: GridMode, unit: u32, queue: Queue) -> Self {
        GridModel { mode, unit, queue, slots: Vec::new(), owner: Vec::new(), n: cave.cells.len(), builds: 0, pops: 0, peak_slots: 0 }
    }
    fn slot_for(&mut self, id: u32) -> Option<usize> {
        self.owner.iter().position(|&o| o == id)
    }
    fn take_slot(&mut self, id: u32) -> usize {
        if let Some(i) = self.owner.iter().position(|&o| o == u32::MAX) {
            self.owner[i] = id;
            return i;
        }
        self.slots.push(Slot::new(self.n, self.unit, self.queue));
        self.owner.push(id);
        self.peak_slots = self.peak_slots.max(self.slots.len());
        self.slots.len() - 1
    }
}

impl Model for GridModel {
    fn name(&self) -> &'static str {
        match (self.mode, self.queue) {
            (GridMode::PerTick, Queue::Heap) => "A cell Dijkstra (heap), per tick",
            (GridMode::Cached, Queue::Heap) => "A+C cell Dijkstra (heap), cached",
            (GridMode::Lazy, Queue::Heap) => "A-lazy resumable (heap), cached",
            (GridMode::PerTick, Queue::Bucket) => "A cell Dijkstra (bucket), per tick",
            (GridMode::Cached, Queue::Bucket) => "A+C cell Dijkstra (bucket), cached",
            (GridMode::Lazy, Queue::Bucket) => "A-lazy resumable (bucket), cached",
        }
    }
    fn listen(&mut self, cave: &Cave, e: &Emission, lx: f32, ly: f32) -> Option<(f32, f32)> {
        let dx = lx - e.x;
        let dy = ly - e.y;
        if dx * dx + dy * dy > e.range * e.range {
            return None;
        }
        let lazy = matches!(self.mode, GridMode::Lazy);
        let s = match self.slot_for(e.id) {
            Some(s) => s,
            None => {
                let s = self.take_slot(e.id);
                self.slots[s].begin(cave, e.cell, e.range);
                if !lazy {
                    self.slots[s].run_until(cave, None);
                }
                self.builds += 1;
                s
            }
        };
        let before = self.slots[s].pops;
        let r = self.slots[s].arrival(cave, lx, ly, lazy);
        self.pops += self.slots[s].pops - before;
        r
    }
    fn end_tick(&mut self, live: &[Emission]) {
        for i in 0..self.owner.len() {
            let id = self.owner[i];
            if id == u32::MAX {
                continue;
            }
            let keep = match self.mode {
                GridMode::PerTick => false,
                _ => live.iter().any(|e| e.id == id),
            };
            if !keep {
                self.slots[i].release();
                self.owner[i] = u32::MAX;
            }
        }
    }
    fn bytes(&self) -> usize {
        self.slots.iter().map(|s| s.bytes()).sum()
    }
    fn work(&self) -> (u64, u64) {
        (self.builds, self.pops)
    }
    fn cave_changed(&mut self, _cave: &Cave) -> f64 {
        // Nothing precomputed. Live fields are invalid: release them; the next listen rebuilds.
        let t0 = Instant::now();
        for i in 0..self.owner.len() {
            if self.owner[i] != u32::MAX {
                self.slots[i].release();
                self.owner[i] = u32::MAX;
            }
        }
        t0.elapsed().as_secs_f64() * 1e3
    }
}

// ---- Model B family --------------------------------------------------------------------

pub struct GraphModel {
    cached: bool,
    graph: Graph,
    fields: Vec<GraphField>,
    owner: Vec<u32>,
    builds: u64,
    pops: u64,
    pub graph_build_ms: f64,
}

impl GraphModel {
    pub fn new(cave: &Cave, cached: bool) -> Self {
        let t0 = Instant::now();
        let graph = Graph::build(cave);
        let ms = t0.elapsed().as_secs_f64() * 1e3;
        GraphModel { cached, graph, fields: Vec::new(), owner: Vec::new(), builds: 0, pops: 0, graph_build_ms: ms }
    }
    pub fn graph(&self) -> &Graph {
        &self.graph
    }
    fn take(&mut self, id: u32) -> usize {
        if let Some(i) = self.owner.iter().position(|&o| o == u32::MAX) {
            self.owner[i] = id;
            return i;
        }
        self.fields.push(GraphField::new(&self.graph));
        self.owner.push(id);
        self.fields.len() - 1
    }
}

impl Model for GraphModel {
    fn name(&self) -> &'static str {
        if self.cached { "B+C graph Dijkstra, cached" } else { "B graph Dijkstra, per tick" }
    }
    fn listen(&mut self, _cave: &Cave, e: &Emission, lx: f32, ly: f32) -> Option<(f32, f32)> {
        let dx = lx - e.x;
        let dy = ly - e.y;
        if dx * dx + dy * dy > e.range * e.range {
            return None;
        }
        let s = match self.owner.iter().position(|&o| o == e.id) {
            Some(s) => s,
            None => {
                let s = self.take(e.id);
                self.fields[s].build(&self.graph, e.cell, e.range);
                self.builds += 1;
                self.pops += self.fields[s].pops;
                s
            }
        };
        self.fields[s].arrival(&self.graph, lx, ly)
    }
    fn end_tick(&mut self, live: &[Emission]) {
        for i in 0..self.owner.len() {
            let id = self.owner[i];
            if id == u32::MAX {
                continue;
            }
            let keep = self.cached && live.iter().any(|e| e.id == id);
            if !keep {
                self.owner[i] = u32::MAX;
            }
        }
    }
    fn bytes(&self) -> usize {
        self.graph.bytes() + self.fields.iter().map(|f| f.bytes()).sum::<usize>()
    }
    fn work(&self) -> (u64, u64) {
        (self.builds, self.pops)
    }
    fn cave_changed(&mut self, cave: &Cave) -> f64 {
        let t0 = Instant::now();
        self.graph = Graph::build(cave);
        self.fields.clear();
        self.owner.clear();
        t0.elapsed().as_secs_f64() * 1e3
    }
}

// ---- replay ----------------------------------------------------------------------------

pub struct Report {
    pub name: &'static str,
    pub tick_ns: Vec<u64>,
    pub builds: u64,
    pub pops: u64,
    pub bytes: usize,
    pub listens: u64,
    pub heard: u64,
    pub collapse_ms: f64,
}

impl Report {
    pub fn mean_us(&self) -> f64 {
        self.tick_ns.iter().sum::<u64>() as f64 / self.tick_ns.len() as f64 / 1e3
    }
    pub fn pct_us(&self, p: f64) -> f64 {
        let mut v = self.tick_ns.clone();
        v.sort_unstable();
        v[((v.len() - 1) as f64 * p) as usize] as f64 / 1e3
    }
    pub fn max_us(&self) -> f64 {
        *self.tick_ns.iter().max().unwrap() as f64 / 1e3
    }
    pub fn total_ms(&self) -> f64 {
        self.tick_ns.iter().sum::<u64>() as f64 / 1e6
    }
}

pub fn replay(cave: &mut Cave, sched: &Schedule, model: &mut dyn Model, collapse_seed: u64) -> Report {
    let p = sched.p;
    let mut tick_ns = vec![0u64; p.ticks];
    let mut live: Vec<Emission> = Vec::new();
    let mut next = 0usize;
    let mut listens = 0u64;
    let mut heard = 0u64;
    let mut sink = 0.0f32;
    for t in 0..p.ticks as u32 {
        let t0 = Instant::now();
        while next < sched.emissions.len() && sched.emissions[next].start == t {
            live.push(sched.emissions[next]);
            next += 1;
        }
        for e in &live {
            let sample = match e.kind {
                Kind::Ping | Kind::Echo => t % p.ping_sample_every == 0,
                Kind::Ancient => t % p.ancient_sample_every == 0,
                Kind::Motion | Kind::Crash => true,
            };
            if !sample {
                continue;
            }
            for a in 0..p.agents {
                if a == e.emitter {
                    continue;
                }
                let (lx, ly) = sched.pos[t as usize * p.agents + a];
                listens += 1;
                if let Some((d, b)) = model.listen(cave, e, lx, ly) {
                    heard += 1;
                    sink += d + b;
                }
            }
        }
        live.retain(|e| e.end > t + 1);
        model.end_tick(&live);
        tick_ns[t as usize] = t0.elapsed().as_nanos() as u64;
    }
    std::hint::black_box(sink);
    let (builds, pops) = model.work();
    let bytes = model.bytes();
    // A collapse after the match: measure what it costs the model.
    let mut rng = Rng::new(collapse_seed);
    let _changed = cave.collapse(&mut rng, 4.0);
    let collapse_ms = model.cave_changed(cave);
    Report { name: model.name(), tick_ns, builds, pops, bytes, listens, heard, collapse_ms }
}
