//! Model A: range-bounded Dijkstra over passage cells from the emitter, Phase 1's
//! SoundField with three changes that the fixed-point port will make anyway:
//!   - costs are integers in 1/`unit`-cell units (step `unit`, diagonal `unit`*1.4142,
//!     entering a flooded cell x0.55 as in Phase 1's FLOODED_COST);
//!   - the heap orders by (cost, cell id), so equal-cost ties break by stable cell id
//!     (BLD-79's acceptance criterion);
//!   - nothing is cleared per emission: touched cells are listed and reset on release.
//! Two queues: a binary heap, and a Dial bucket queue (one bucket per cost unit,
//! circular, max-step+1 buckets) which is O(1) per push/pop and is what integer costs
//! make possible. A `Slot` can be run to completion (A, A+cache) or resumed lazily until
//! a queried listener cell is settled (A-lazy): Dijkstra settles cells in non-decreasing
//! cost, so stopping at the farthest listener asked about is exact for every listener
//! asked. The arrival bearing is Phase 1's: walk five steps back along the shortest path
//! and point at that cell, so the bearing points down the passage the sound came through.

use crate::cave::{Cave, FLOODED, NEIGH};
use std::cmp::Reverse;
use std::collections::BinaryHeap;

pub const LOOKBACK: usize = 5;

#[derive(Clone, Copy, PartialEq)]
pub enum Queue {
    Heap,
    Bucket,
}

pub struct Slot {
    pub unit: u32,
    step: [u32; 8],
    step_flooded: [u32; 8],
    max_step: u32,
    queue: Queue,
    pub dist: Vec<u32>,
    pub pred: Vec<u8>, // direction index we arrived by (NEIGH[pred] reversed leads back)
    pub state: Vec<u8>, // 0 untouched, 1 reached, 2 settled
    pub touched: Vec<u32>,
    heap: BinaryHeap<Reverse<(u32, u32)>>,
    buckets: Vec<Vec<u32>>,
    bucket_cost: u32,
    bucket_pending: usize,
    pub src: u32,
    pub range: u32,
    pub exhausted: bool,
    pub pops: u64,
}

impl Slot {
    pub fn new(n: usize, unit: u32, queue: Queue) -> Self {
        let diag = ((unit as f64) * std::f64::consts::SQRT_2).round() as u32;
        let fl = |c: u32| ((c as f64) * 0.55).round().max(1.0) as u32;
        let step = [unit, unit, unit, unit, diag, diag, diag, diag];
        let step_flooded = [fl(unit), fl(unit), fl(unit), fl(unit), fl(diag), fl(diag), fl(diag), fl(diag)];
        let nb = if queue == Queue::Bucket { diag as usize + 1 } else { 0 };
        Slot {
            unit,
            step,
            step_flooded,
            max_step: diag,
            queue,
            dist: vec![u32::MAX; n],
            pred: vec![0; n],
            state: vec![0; n],
            touched: Vec::with_capacity(4096),
            heap: BinaryHeap::with_capacity(if queue == Queue::Heap { 4096 } else { 0 }),
            buckets: (0..nb).map(|_| Vec::with_capacity(64)).collect(),
            bucket_cost: 0,
            bucket_pending: 0,
            src: u32::MAX,
            range: 0,
            exhausted: true,
            pops: 0,
        }
    }

    pub fn bytes(&self) -> usize {
        self.dist.capacity() * 4 + self.pred.capacity() + self.state.capacity()
            + self.touched.capacity() * 4 + self.heap.capacity() * 8
            + self.buckets.iter().map(|b| b.capacity() * 4).sum::<usize>()
    }

    pub fn release(&mut self) {
        for &c in &self.touched {
            let c = c as usize;
            self.dist[c] = u32::MAX;
            self.state[c] = 0;
        }
        self.touched.clear();
        self.heap.clear();
        for b in &mut self.buckets {
            b.clear();
        }
        self.bucket_pending = 0;
        self.src = u32::MAX;
        self.exhausted = true;
    }

    #[inline]
    fn push(&mut self, cost: u32, cell: u32) {
        match self.queue {
            Queue::Heap => self.heap.push(Reverse((cost, cell))),
            Queue::Bucket => {
                let nb = self.buckets.len() as u32;
                self.buckets[(cost % nb) as usize].push(cell);
                self.bucket_pending += 1;
            }
        }
    }

    #[inline]
    fn pop(&mut self) -> Option<(u32, u32)> {
        match self.queue {
            Queue::Heap => self.heap.pop().map(|Reverse(x)| x),
            Queue::Bucket => {
                if self.bucket_pending == 0 {
                    return None;
                }
                let nb = self.buckets.len() as u32;
                loop {
                    let b = (self.bucket_cost % nb) as usize;
                    if let Some(c) = self.buckets[b].pop() {
                        self.bucket_pending -= 1;
                        return Some((self.bucket_cost, c));
                    }
                    self.bucket_cost += 1;
                }
            }
        }
    }

    pub fn begin(&mut self, cave: &Cave, src: u32, range_cells: f32) {
        debug_assert!(self.touched.is_empty());
        self.src = src;
        self.range = (range_cells * self.unit as f32).round() as u32;
        self.exhausted = false;
        self.pops = 0;
        self.bucket_cost = 0;
        if !cave.free(src as usize) {
            self.exhausted = true;
            return;
        }
        self.dist[src as usize] = 0;
        self.state[src as usize] = 1;
        self.touched.push(src);
        self.push(0, src);
    }

    /// Pop until `target` is settled (or everything within range is, when None).
    pub fn run_until(&mut self, cave: &Cave, target: Option<u32>) {
        if self.exhausted {
            return;
        }
        let w = cave.w;
        let cells = &cave.cells;
        while let Some((d, c)) = self.pop() {
            self.pops += 1;
            let ci = c as usize;
            if self.state[ci] == 2 || d > self.dist[ci] {
                continue;
            }
            self.state[ci] = 2;
            let x = ci % w;
            let y = ci / w;
            for (dir, (dx, dy)) in NEIGH.iter().enumerate() {
                // The border is rock, so the neighbour is always in bounds.
                let ni = ((y as i32 + dy) as usize) * w + (x as i32 + dx) as usize;
                let cell = cells[ni];
                if cell == 0 {
                    continue;
                }
                let nd = d + if cell == FLOODED { self.step_flooded[dir] } else { self.step[dir] };
                if nd <= self.range && nd < self.dist[ni] {
                    if self.state[ni] == 0 {
                        self.state[ni] = 1;
                        self.touched.push(ni as u32);
                    }
                    self.dist[ni] = nd;
                    self.pred[ni] = dir as u8;
                    self.push(nd, ni as u32);
                }
            }
            // Return only after expanding: a settled-but-unexpanded target would leave a
            // later listener whose shortest path runs through it with a longer route or
            // none (first version of this spike heard 0.3% fewer sounds lazily than fully).
            if target == Some(c) {
                return;
            }
        }
        self.exhausted = true;
    }

    /// (path distance in cells, arrival bearing in world radians), or None if inaudible.
    pub fn arrival(&mut self, cave: &Cave, lx: f32, ly: f32, lazy: bool) -> Option<(f32, f32)> {
        let l = cave.cell_of(lx, ly)? as u32;
        if lazy && self.state[l as usize] != 2 {
            self.run_until(cave, Some(l));
        }
        if self.state[l as usize] != 2 {
            return None;
        }
        let d = self.dist[l as usize];
        if d > self.range {
            return None;
        }
        let w = cave.w;
        let mut c = l as usize;
        for _ in 0..LOOKBACK {
            if c == self.src as usize {
                break;
            }
            let (dx, dy) = NEIGH[self.pred[c] as usize];
            let x = (c % w) as i32 - dx;
            let y = (c / w) as i32 - dy;
            c = y as usize * w + x as usize;
        }
        let bearing = if c == l as usize {
            0.0
        } else {
            let (cx, cy) = cave.centre(c);
            (cy - ly).atan2(cx - lx)
        };
        Some((d as f32 / self.unit as f32, bearing))
    }

    pub fn reached(&self) -> usize {
        self.touched.len()
    }

    pub fn max_step(&self) -> u32 {
        self.max_step
    }
}
