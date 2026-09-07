//! Procedural caves for the benchmark. Two generators:
//!  - `ca`:   cellular automata over seeded noise, DESIGN.html's stated method (its demo:
//!            45% initial rock, 4/5 rule, 5 iterations), largest 8-connected component kept.
//!  - `tree`: chambers joined by bent passages of width 4-6 on a spanning tree plus a few
//!            loops -- the shape of Phase 1's hand-authored cave, scaled by area.
//! Flooding: random blobs until ~12% of free cells are flooded (Phase 1: 460/3831 = 12%).
//! Cell values match Phase 1: 0 rock, 1 dry passage, 2 flooded. Sound passes 1 and 2.

use crate::rng::Rng;

pub const ROCK: u8 = 0;
pub const DRY: u8 = 1;
pub const FLOODED: u8 = 2;

pub const NEIGH: [(i32, i32); 8] = [
    (-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1),
];

#[derive(Clone)]
pub struct Cave {
    pub w: usize,
    pub h: usize,
    pub cells: Vec<u8>,
    pub name: String,
}

pub struct CaveStats {
    pub free: usize,
    pub flooded: usize,
    pub median_halfwidth: f32,
    pub p90_halfwidth: f32,
}

impl Cave {
    #[inline]
    pub fn idx(&self, x: usize, y: usize) -> usize {
        y * self.w + x
    }
    #[inline]
    pub fn free(&self, i: usize) -> bool {
        self.cells[i] != ROCK
    }
    pub fn xy(&self, i: usize) -> (usize, usize) {
        (i % self.w, i / self.w)
    }
    pub fn centre(&self, i: usize) -> (f32, f32) {
        let (x, y) = self.xy(i);
        (x as f32 + 0.5, y as f32 + 0.5)
    }
    pub fn cell_of(&self, x: f32, y: f32) -> Option<usize> {
        if x < 0.0 || y < 0.0 {
            return None;
        }
        let (xi, yi) = (x as usize, y as usize);
        if xi >= self.w || yi >= self.h {
            return None;
        }
        Some(self.idx(xi, yi))
    }
    pub fn walkable_cells(&self) -> Vec<u32> {
        (0..self.cells.len()).filter(|&i| self.cells[i] == DRY).map(|i| i as u32).collect()
    }
    pub fn free_cells(&self) -> Vec<u32> {
        (0..self.cells.len()).filter(|&i| self.cells[i] != ROCK).map(|i| i as u32).collect()
    }
    pub fn free_count(&self) -> usize {
        self.cells.iter().filter(|&&c| c != ROCK).count()
    }

    /// Chebyshev distance to the nearest rock cell, for every free cell (0 for rock).
    pub fn distance_to_rock(&self) -> Vec<u16> {
        let n = self.cells.len();
        let mut dt = vec![u16::MAX; n];
        let mut queue = std::collections::VecDeque::new();
        for i in 0..n {
            if !self.free(i) {
                dt[i] = 0;
                queue.push_back(i);
            }
        }
        while let Some(c) = queue.pop_front() {
            let (x, y) = self.xy(c);
            for (dx, dy) in NEIGH {
                let nx = x as i32 + dx;
                let ny = y as i32 + dy;
                if nx < 0 || ny < 0 || nx >= self.w as i32 || ny >= self.h as i32 {
                    continue;
                }
                let ni = self.idx(nx as usize, ny as usize);
                if dt[ni] == u16::MAX {
                    dt[ni] = dt[c] + 1;
                    queue.push_back(ni);
                }
            }
        }
        dt
    }

    pub fn stats(&self) -> CaveStats {
        let dt = self.distance_to_rock();
        let mut hw: Vec<u16> = (0..self.cells.len()).filter(|&i| self.free(i)).map(|i| dt[i]).collect();
        hw.sort_unstable();
        let free = hw.len();
        let flooded = self.cells.iter().filter(|&&c| c == FLOODED).count();
        let med = if free > 0 { hw[free / 2] as f32 } else { 0.0 };
        let p90 = if free > 0 { hw[(free * 9) / 10] as f32 } else { 0.0 };
        CaveStats { free, flooded, median_halfwidth: med, p90_halfwidth: p90 }
    }

    /// A collapse: every free cell within `radius` of a random walkable cell becomes rock.
    /// Returns the cells changed. The border is never touched.
    pub fn collapse(&mut self, rng: &mut Rng, radius: f32) -> Vec<u32> {
        let walk = self.walkable_cells();
        let c = walk[rng.below(walk.len())] as usize;
        let (cx, cy) = self.xy(c);
        let r = radius.ceil() as i32;
        let mut changed = Vec::new();
        for dy in -r..=r {
            for dx in -r..=r {
                if ((dx * dx + dy * dy) as f32) > radius * radius {
                    continue;
                }
                let x = cx as i32 + dx;
                let y = cy as i32 + dy;
                if x <= 0 || y <= 0 || x >= self.w as i32 - 1 || y >= self.h as i32 - 1 {
                    continue;
                }
                let i = self.idx(x as usize, y as usize);
                if self.free(i) {
                    self.cells[i] = ROCK;
                    changed.push(i as u32);
                }
            }
        }
        changed
    }

    /// Keep only the largest 8-connected free component; everything else becomes rock.
    fn keep_largest_component(&mut self) {
        let n = self.cells.len();
        let mut label = vec![u32::MAX; n];
        let mut sizes: Vec<usize> = Vec::new();
        let mut stack = Vec::new();
        for start in 0..n {
            if !self.free(start) || label[start] != u32::MAX {
                continue;
            }
            let id = sizes.len() as u32;
            let mut size = 0;
            label[start] = id;
            stack.push(start);
            while let Some(c) = stack.pop() {
                size += 1;
                let (x, y) = self.xy(c);
                for (dx, dy) in NEIGH {
                    let nx = x as i32 + dx;
                    let ny = y as i32 + dy;
                    if nx < 0 || ny < 0 || nx >= self.w as i32 || ny >= self.h as i32 {
                        continue;
                    }
                    let ni = self.idx(nx as usize, ny as usize);
                    if self.free(ni) && label[ni] == u32::MAX {
                        label[ni] = id;
                        stack.push(ni);
                    }
                }
            }
            sizes.push(size);
        }
        if sizes.is_empty() {
            return;
        }
        let best = (0..sizes.len()).max_by_key(|&i| sizes[i]).unwrap() as u32;
        for i in 0..n {
            if self.free(i) && label[i] != best {
                self.cells[i] = ROCK;
            }
        }
    }

    fn clear_border(&mut self) {
        for x in 0..self.w {
            let a = self.idx(x, 0);
            let b = self.idx(x, self.h - 1);
            self.cells[a] = ROCK;
            self.cells[b] = ROCK;
        }
        for y in 0..self.h {
            let a = self.idx(0, y);
            let b = self.idx(self.w - 1, y);
            self.cells[a] = ROCK;
            self.cells[b] = ROCK;
        }
    }

    /// Flood random blobs of free cells until `frac` of the free cells are flooded.
    fn flood_blobs(&mut self, rng: &mut Rng, frac: f64) {
        let free: Vec<u32> = self.free_cells();
        let target = (free.len() as f64 * frac) as usize;
        let mut flooded = 0usize;
        let mut guard = 0;
        while flooded < target && guard < 10_000 {
            guard += 1;
            let seed = free[rng.below(free.len())] as usize;
            if self.cells[seed] == FLOODED {
                continue;
            }
            let (cx, cy) = self.xy(seed);
            let radius = rng.range(6.0, 14.0);
            let r = radius.ceil() as i32;
            for dy in -r..=r {
                for dx in -r..=r {
                    if ((dx * dx + dy * dy) as f64) > radius * radius {
                        continue;
                    }
                    let x = cx as i32 + dx;
                    let y = cy as i32 + dy;
                    if x < 0 || y < 0 || x >= self.w as i32 || y >= self.h as i32 {
                        continue;
                    }
                    let i = self.idx(x as usize, y as usize);
                    if self.cells[i] == DRY {
                        self.cells[i] = FLOODED;
                        flooded += 1;
                    }
                }
            }
        }
    }

    /// Downsampled ASCII picture for eyeballing.
    pub fn ascii(&self, cols: usize) -> String {
        let scale = (self.w as f32 / cols as f32).max(1.0);
        let rows = (self.h as f32 / scale / 2.0) as usize; // terminal cells are ~2:1
        let mut s = String::new();
        for r in 0..rows {
            for c in 0..cols {
                let x0 = (c as f32 * scale) as usize;
                let y0 = (r as f32 * scale * 2.0) as usize;
                let x1 = (((c + 1) as f32 * scale) as usize).min(self.w);
                let y1 = (((r + 1) as f32 * scale * 2.0) as usize).min(self.h);
                let mut best = ROCK;
                for y in y0..y1 {
                    for x in x0..x1 {
                        best = best.max(self.cells[self.idx(x, y)]);
                    }
                }
                s.push(match best {
                    ROCK => '#',
                    DRY => ' ',
                    _ => '~',
                });
            }
            s.push('\n');
        }
        s
    }
}

pub fn gen_ca(seed: u64, w: usize, h: usize, fill: f64, iters: usize, flood_frac: f64) -> Cave {
    let mut rng = Rng::new(seed);
    let n = w * h;
    let mut g: Vec<u8> = (0..n)
        .map(|i| {
            let (x, y) = (i % w, i / w);
            let edge = x < 2 || y < 2 || x > w - 3 || y > h - 3;
            if edge || rng.f64() < fill { ROCK } else { DRY }
        })
        .collect();
    for _ in 0..iters {
        let mut next = g.clone();
        for y in 0..h {
            for x in 0..w {
                let mut c = 0;
                for dy in -1i32..=1 {
                    for dx in -1i32..=1 {
                        if dx == 0 && dy == 0 {
                            continue;
                        }
                        let nx = x as i32 + dx;
                        let ny = y as i32 + dy;
                        if nx < 0 || ny < 0 || nx >= w as i32 || ny >= h as i32 {
                            c += 1;
                        } else if g[ny as usize * w + nx as usize] == ROCK {
                            c += 1;
                        }
                    }
                }
                let i = y * w + x;
                next[i] = if c > 4 { ROCK } else if c < 4 { DRY } else { g[i] };
            }
        }
        g = next;
    }
    let mut cave = Cave { w, h, cells: g, name: format!("ca-{}x{}-s{}", w, h, seed) };
    cave.clear_border();
    cave.keep_largest_component();
    cave.flood_blobs(&mut rng, flood_frac);
    cave
}

pub fn gen_tree(seed: u64, w: usize, h: usize, flood_frac: f64) -> Cave {
    let mut rng = Rng::new(seed ^ 0xABCD);
    let area = (w * h) as f64;
    let n_chambers = ((area / 24_000.0) * 11.0).round().max(4.0) as usize; // Phase 1: 11 on 200x120
    // Place chambers with a minimum spacing, by rejection.
    let mut chambers: Vec<(f64, f64, f64)> = Vec::new();
    let spacing = (area / n_chambers as f64).sqrt() * 0.55;
    let mut tries = 0;
    while chambers.len() < n_chambers && tries < 200_000 {
        tries += 1;
        let r = rng.range(5.0, 12.0);
        let x = rng.range(r + 3.0, w as f64 - r - 3.0);
        let y = rng.range(r + 3.0, h as f64 - r - 3.0);
        if chambers.iter().all(|&(cx, cy, cr)| ((cx - x).powi(2) + (cy - y).powi(2)).sqrt() > spacing.max(r + cr + 6.0)) {
            chambers.push((x, y, r));
        }
    }
    let m = chambers.len();
    // Spanning tree (Prim) plus ~30% extra loops on the shortest remaining pairs.
    let d = |a: usize, b: usize| ((chambers[a].0 - chambers[b].0).powi(2) + (chambers[a].1 - chambers[b].1).powi(2)).sqrt();
    let mut in_tree = vec![false; m];
    let mut edges: Vec<(usize, usize)> = Vec::new();
    in_tree[0] = true;
    for _ in 1..m {
        let mut best: Option<(f64, usize, usize)> = None;
        for a in 0..m {
            if !in_tree[a] {
                continue;
            }
            for b in 0..m {
                if in_tree[b] {
                    continue;
                }
                let dd = d(a, b);
                if best.map_or(true, |(bd, _, _)| dd < bd) {
                    best = Some((dd, a, b));
                }
            }
        }
        let (_, a, b) = best.unwrap();
        in_tree[b] = true;
        edges.push((a, b));
    }
    let mut extra: Vec<(f64, usize, usize)> = Vec::new();
    for a in 0..m {
        for b in a + 1..m {
            if !edges.contains(&(a, b)) && !edges.contains(&(b, a)) {
                extra.push((d(a, b), a, b));
            }
        }
    }
    extra.sort_by(|p, q| p.0.partial_cmp(&q.0).unwrap());
    let loops = (m as f64 * 0.3).round() as usize;
    for &(_, a, b) in extra.iter().take(loops) {
        edges.push((a, b));
    }
    // Rasterise, Phase 1 style: lumpy discs and bent passages.
    let mut cells = vec![ROCK; w * h];
    let idx = |x: usize, y: usize| y * w + x;
    for &(cx, cy, r) in &chambers {
        let p1 = rng.range(0.0, 6.0);
        let p2 = rng.range(0.0, 6.0);
        let rr = (r * 1.25).ceil() as i32;
        for dy in -rr..=rr {
            for dx in -rr..=rr {
                let x = cx as i32 + dx;
                let y = cy as i32 + dy;
                if x < 1 || y < 1 || x >= w as i32 - 1 || y >= h as i32 - 1 {
                    continue;
                }
                let fx = x as f64 - cx;
                let fy = y as f64 - cy;
                let ang = fy.atan2(fx);
                let wob = 1.0 + 0.12 * (3.0 * ang + p1).sin() + 0.08 * (5.0 * ang + p2).cos();
                if fx * fx + fy * fy <= (r * wob).powi(2) {
                    cells[idx(x as usize, y as usize)] = DRY;
                }
            }
        }
    }
    for &(a, b) in &edges {
        let (ax, ay, _) = chambers[a];
        let (bx, by, _) = chambers[b];
        let width = rng.range(4.0, 6.0);
        let (mut mx, mut my) = ((ax + bx) / 2.0, (ay + by) / 2.0);
        let (nx, ny) = (-(by - ay), bx - ax);
        let nl = (nx * nx + ny * ny).sqrt().max(1.0);
        let bend = rng.range(-0.18, 0.18) * nl;
        mx += nx / nl * bend;
        my += ny / nl * bend;
        for ((x0, y0), (x1, y1)) in [((ax, ay), (mx, my)), ((mx, my), (bx, by))] {
            let steps = (((x1 - x0).powi(2) + (y1 - y0).powi(2)).sqrt() * 2.0) as usize + 1;
            for i in 0..=steps {
                let f = i as f64 / steps as f64;
                let px = x0 + (x1 - x0) * f;
                let py = y0 + (y1 - y0) * f;
                let hw = (width / 2.0).ceil() as i32;
                for dy in -hw..=hw {
                    for dx in -hw..=hw {
                        let x = px as i32 + dx;
                        let y = py as i32 + dy;
                        if x < 1 || y < 1 || x >= w as i32 - 1 || y >= h as i32 - 1 {
                            continue;
                        }
                        let fx = x as f64 - px;
                        let fy = y as f64 - py;
                        if fx * fx + fy * fy <= (width / 2.0).powi(2) {
                            cells[idx(x as usize, y as usize)] = DRY;
                        }
                    }
                }
            }
        }
    }
    let mut cave = Cave { w, h, cells, name: format!("tree-{}x{}-s{}", w, h, seed) };
    cave.clear_border();
    cave.keep_largest_component();
    cave.flood_blobs(&mut rng, flood_frac);
    cave
}
