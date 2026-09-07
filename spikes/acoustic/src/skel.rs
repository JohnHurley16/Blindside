//! Model B: a precomputed passage graph. The free mask is thinned (Zhang-Suen) to a
//! one-cell skeleton, spurs shorter than the local half-width are pruned, skeleton
//! pixels with one or three-plus skeleton neighbours become nodes (endpoints and
//! junctions, adjacent node pixels merged), and the runs between them become edges with
//! a per-pixel cumulative cost in the same units as the grid model. Every free cell is
//! mapped once to its nearest skeleton pixel (multi-source Dijkstra) with the cost of
//! getting there.
//!
//! Per emission: Dijkstra over the node graph only, range-bounded, seeded from the two
//! ends of the emitter's edge. Per listener: distance is the better of the two ends of
//! the listener's edge (or the direct along-edge distance when both are on one edge),
//! plus both off-skeleton offsets. The arrival bearing points from the listener at the
//! skeleton pixel five steps along the edge toward the end the sound came in by, which
//! is the passage direction -- the same look-back Phase 1 used on the cell path.

use crate::cave::{Cave, FLOODED, NEIGH};
use std::cmp::Reverse;
use std::collections::BinaryHeap;
use std::time::Instant;

pub const NONE: u32 = u32::MAX;
/// Look-along pixels per cell of listener offset from the skeleton (0 = Phase 1's fixed 5).
/// Tried at 3: mean bearing error 24.4 deg against 24.2 deg at 0 on tree-200x120-s1, so
/// the error is not the look-along; it is the skeleton path itself.
const LOOK_PER_OFFSET: u32 = 0;
const STEP: [u32; 8] = [1024, 1024, 1024, 1024, 1448, 1448, 1448, 1448];
const FLOOD_NUM: u32 = 563;

#[inline]
fn step_cost(dir: usize, into_flooded: bool) -> u32 {
    let s = STEP[dir];
    if into_flooded { (s * FLOOD_NUM) >> 10 } else { s }
}

pub struct Node {
    pub cell: u32,
    pub adj: Vec<(u32, u32, u32)>, // (edge, other node, length)
}

pub struct Edge {
    pub a: u32,
    pub b: u32,
    pub pixels: Vec<u32>, // cells, from a's pixel to b's pixel
    pub cum: Vec<u32>,    // cumulative cost from pixels[0]
}

pub struct BuildTimes {
    pub thin: f64,
    pub prune: f64,
    pub graph: f64,
    pub map: f64,
}

pub struct Graph {
    pub w: usize,
    pub skel_of_cell: Vec<u32>, // nearest skeleton pixel id, or NONE for rock
    pub off_of_cell: Vec<u32>,  // cost from the cell to that pixel
    pub skel_cell: Vec<u32>,    // pixel id -> cell
    pub skel_edge: Vec<u32>,    // pixel id -> edge id or NONE
    pub skel_idx: Vec<u32>,     // pixel id -> index in edge.pixels
    pub skel_node: Vec<u32>,    // pixel id -> node id or NONE
    pub nodes: Vec<Node>,
    pub edges: Vec<Edge>,
    pub times: BuildTimes,
}

fn neighbours8(w: usize, h: usize, c: usize) -> impl Iterator<Item = (usize, usize)> {
    let x = (c % w) as i32;
    let y = (c / w) as i32;
    NEIGH.iter().enumerate().filter_map(move |(dir, (dx, dy))| {
        let nx = x + dx;
        let ny = y + dy;
        if nx < 0 || ny < 0 || nx >= w as i32 || ny >= h as i32 {
            None
        } else {
            Some((dir, ny as usize * w + nx as usize))
        }
    })
}

/// Zhang-Suen thinning of the free mask.
fn thin(cave: &Cave) -> Vec<u8> {
    let (w, h) = (cave.w, cave.h);
    let mut img: Vec<u8> = cave.cells.iter().map(|&c| (c != 0) as u8).collect();
    let mut marks: Vec<usize> = Vec::new();
    loop {
        let mut changed = false;
        for pass in 0..2 {
            marks.clear();
            for y in 1..h - 1 {
                for x in 1..w - 1 {
                    let i = y * w + x;
                    if img[i] == 0 {
                        continue;
                    }
                    let p2 = img[i - w];
                    let p3 = img[i - w + 1];
                    let p4 = img[i + 1];
                    let p5 = img[i + w + 1];
                    let p6 = img[i + w];
                    let p7 = img[i + w - 1];
                    let p8 = img[i - 1];
                    let p9 = img[i - w - 1];
                    let b = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9;
                    if !(2..=6).contains(&b) {
                        continue;
                    }
                    let seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2];
                    let a = seq.windows(2).filter(|s| s[0] == 0 && s[1] == 1).count();
                    if a != 1 {
                        continue;
                    }
                    let ok = if pass == 0 {
                        p2 * p4 * p6 == 0 && p4 * p6 * p8 == 0
                    } else {
                        p2 * p4 * p8 == 0 && p2 * p6 * p8 == 0
                    };
                    if ok {
                        marks.push(i);
                    }
                }
            }
            if !marks.is_empty() {
                changed = true;
                for &i in &marks {
                    img[i] = 0;
                }
            }
        }
        if !changed {
            break;
        }
    }
    img
}

fn degree(sk: &[u8], w: usize, h: usize, c: usize) -> usize {
    neighbours8(w, h, c).filter(|&(_, n)| sk[n] != 0).count()
}

/// Remove endpoint branches shorter than the half-width at the junction they hang off.
fn prune(cave: &Cave, sk: &mut [u8], dt: &[u16]) {
    let (w, h) = (cave.w, cave.h);
    for _round in 0..3 {
        let endpoints: Vec<usize> = (0..sk.len()).filter(|&c| sk[c] != 0 && degree(sk, w, h, c) == 1).collect();
        let mut removed_any = false;
        for e in endpoints {
            if sk[e] == 0 || degree(sk, w, h, e) != 1 {
                continue;
            }
            let mut path = vec![e];
            let mut prev = e;
            let mut cur = neighbours8(w, h, e).find(|&(_, n)| sk[n] != 0).map(|(_, n)| n);
            let mut junction = None;
            while let Some(c) = cur {
                let deg = degree(sk, w, h, c);
                if deg >= 3 {
                    junction = Some(c);
                    break;
                }
                if deg == 1 {
                    break; // an isolated segment; leave it
                }
                path.push(c);
                let next = neighbours8(w, h, c).find(|&(_, n)| sk[n] != 0 && n != prev).map(|(_, n)| n);
                prev = c;
                cur = next;
                if path.len() > 64 {
                    break;
                }
            }
            if let Some(j) = junction {
                if path.len() <= dt[j] as usize + 1 {
                    for &c in &path {
                        sk[c] = 0;
                    }
                    removed_any = true;
                }
            }
        }
        if !removed_any {
            break;
        }
    }
}

/// Zhang-Suen leaves staircases: an L-corner's two neighbours touch diagonally, so the
/// corner is never a simple point by the ring crossing number and whole diagonal runs
/// keep degree three. Those runs would merge into one huge "junction" node and their
/// length would vanish from the graph (the probe command showed 28-pixel nodes and graph
/// paths 60 cells shorter than the exact path between the same pixels). Delete 8-simple
/// points of degree >= 2 sequentially -- a point whose foreground ring neighbours form
/// one 8-connected component -- until none remain. Connectivity is preserved because
/// the neighbours stay joined through each other; endpoints (degree 1) are kept.
fn minimise(sk: &mut [u8], w: usize, h: usize) {
    // Ring order N, NE, E, SE, S, SW, W, NW. Two ring positions are 8-adjacent when they
    // are consecutive, or two apart with an orthogonal (even) position first.
    let offs: [isize; 8] = [-(w as isize), -(w as isize) + 1, 1, w as isize + 1, w as isize, w as isize - 1, -1, -(w as isize) - 1];
    loop {
        let mut changed = false;
        for y in 1..h - 1 {
            for x in 1..w - 1 {
                let i = y * w + x;
                if sk[i] == 0 {
                    continue;
                }
                let mut ring = [0u8; 8];
                let mut deg = 0;
                for k in 0..8 {
                    ring[k] = sk[(i as isize + offs[k]) as usize];
                    deg += ring[k] as usize;
                }
                if deg < 2 {
                    continue;
                }
                // Count components with a tiny union-find over the eight positions.
                let mut parent = [0usize, 1, 2, 3, 4, 5, 6, 7];
                fn find(p: &mut [usize; 8], a: usize) -> usize {
                    let mut a = a;
                    while p[a] != a {
                        a = p[a];
                    }
                    a
                }
                for k in 0..8 {
                    if ring[k] == 0 {
                        continue;
                    }
                    let k1 = (k + 1) % 8;
                    if ring[k1] != 0 {
                        let (ra, rb) = (find(&mut parent, k), find(&mut parent, k1));
                        parent[ra] = rb;
                    }
                    if k % 2 == 0 {
                        let k2 = (k + 2) % 8;
                        if ring[k2] != 0 {
                            let (ra, rb) = (find(&mut parent, k), find(&mut parent, k2));
                            parent[ra] = rb;
                        }
                    }
                }
                let mut comps = 0;
                for k in 0..8 {
                    if ring[k] != 0 && find(&mut parent, k) == k {
                        comps += 1;
                    }
                }
                if comps == 1 {
                    sk[i] = 0;
                    changed = true;
                }
            }
        }
        if !changed {
            break;
        }
    }
}

impl Graph {
    pub fn build(cave: &Cave) -> Graph {
        let (w, h) = (cave.w, cave.h);
        let n = w * h;
        let t0 = Instant::now();
        let mut sk = thin(cave);
        minimise(&mut sk, w, h);
        let t_thin = t0.elapsed().as_secs_f64() * 1e3;
        let t1 = Instant::now();
        let dt = cave.distance_to_rock();
        prune(cave, &mut sk, &dt);
        minimise(&mut sk, w, h);
        let t_prune = t1.elapsed().as_secs_f64() * 1e3;

        let t2 = Instant::now();
        // Pixel ids.
        let mut pix_of_cell = vec![NONE; n];
        let mut skel_cell: Vec<u32> = Vec::new();
        for c in 0..n {
            if sk[c] != 0 {
                pix_of_cell[c] = skel_cell.len() as u32;
                skel_cell.push(c as u32);
            }
        }
        let np = skel_cell.len();
        let deg: Vec<u8> = skel_cell.iter().map(|&c| degree(&sk, w, h, c as usize) as u8).collect();
        // Node pixels: degree != 2. Cluster adjacent node pixels.
        let mut skel_node = vec![NONE; np];
        let mut nodes: Vec<Node> = Vec::new();
        let mut stack = Vec::new();
        for p in 0..np {
            if deg[p] == 2 || skel_node[p] != NONE {
                continue;
            }
            let id = nodes.len() as u32;
            skel_node[p] = id;
            stack.push(p);
            while let Some(q) = stack.pop() {
                for (_, nc) in neighbours8(w, h, skel_cell[q] as usize) {
                    let np2 = pix_of_cell[nc];
                    if np2 != NONE && deg[np2 as usize] != 2 && skel_node[np2 as usize] == NONE {
                        skel_node[np2 as usize] = id;
                        stack.push(np2 as usize);
                    }
                }
            }
            nodes.push(Node { cell: skel_cell[p], adj: Vec::new() });
        }
        // Edges: trace runs of degree-2 pixels between node pixels.
        let mut skel_edge = vec![NONE; np];
        let mut skel_idx = vec![0u32; np];
        let mut edges: Vec<Edge> = Vec::new();
        let cost_between = |from: usize, to: usize| -> u32 {
            let (fx, fy) = ((from % w) as i32, (from / w) as i32);
            let (tx, ty) = ((to % w) as i32, (to / w) as i32);
            let dir = NEIGH.iter().position(|&(dx, dy)| fx + dx == tx && fy + dy == ty).unwrap();
            step_cost(dir, cave.cells[to] == FLOODED)
        };
        let finish_edge = |pixels: Vec<u32>, edges: &mut Vec<Edge>, skel_edge: &mut Vec<u32>, skel_idx: &mut Vec<u32>, nodes: &mut Vec<Node>| {
            let a = skel_node[pix_of_cell[pixels[0] as usize] as usize];
            let b = skel_node[pix_of_cell[*pixels.last().unwrap() as usize] as usize];
            let mut cum = Vec::with_capacity(pixels.len());
            let mut acc = 0u32;
            cum.push(0);
            for k in 1..pixels.len() {
                acc += cost_between(pixels[k - 1] as usize, pixels[k] as usize);
                cum.push(acc);
            }
            let id = edges.len() as u32;
            for (k, &c) in pixels.iter().enumerate() {
                let p = pix_of_cell[c as usize] as usize;
                if deg[p] == 2 {
                    skel_edge[p] = id;
                    skel_idx[p] = k as u32;
                }
            }
            nodes[a as usize].adj.push((id, b, acc));
            if a != b {
                nodes[b as usize].adj.push((id, a, acc));
            }
            edges.push(Edge { a, b, pixels, cum });
        };
        let mut visited = vec![false; np];
        for p in 0..np {
            if deg[p] == 2 {
                continue;
            }
            let pc = skel_cell[p] as usize;
            for (_, qc) in neighbours8(w, h, pc) {
                let q = pix_of_cell[qc];
                if q == NONE {
                    continue;
                }
                let q = q as usize;
                if deg[q] != 2 {
                    // Node pixel to node pixel: an edge of one step if different nodes.
                    if skel_node[q] != skel_node[p] && p < q {
                        finish_edge(vec![pc as u32, qc as u32], &mut edges, &mut skel_edge, &mut skel_idx, &mut nodes);
                    }
                    continue;
                }
                if visited[q] {
                    continue;
                }
                let mut pixels = vec![pc as u32, qc as u32];
                let mut prev = pc;
                let mut cur = qc;
                visited[q] = true;
                loop {
                    let next = neighbours8(w, h, cur).find(|&(_, nc)| pix_of_cell[nc] != NONE && nc != prev).map(|(_, nc)| nc);
                    match next {
                        None => break,
                        Some(nc) => {
                            let nq = pix_of_cell[nc] as usize;
                            pixels.push(nc as u32);
                            if deg[nq] != 2 {
                                break;
                            }
                            if visited[nq] {
                                break;
                            }
                            visited[nq] = true;
                            prev = cur;
                            cur = nc;
                        }
                    }
                }
                let last = pix_of_cell[*pixels.last().unwrap() as usize] as usize;
                if deg[last] != 2 {
                    finish_edge(pixels, &mut edges, &mut skel_edge, &mut skel_idx, &mut nodes);
                }
            }
        }
        // Any degree-2 pixels never reached belong to pure rings: make one a node and trace.
        for p in 0..np {
            if deg[p] == 2 && !visited[p] {
                let id = nodes.len() as u32;
                nodes.push(Node { cell: skel_cell[p], adj: Vec::new() });
                skel_node[p] = id;
                let pc = skel_cell[p] as usize;
                let mut pixels = vec![pc as u32];
                let mut prev = pc;
                let mut cur = neighbours8(w, h, pc).find(|&(_, nc)| pix_of_cell[nc] != NONE).map(|(_, nc)| nc);
                visited[p] = true;
                while let Some(c) = cur {
                    let q = pix_of_cell[c] as usize;
                    pixels.push(c as u32);
                    if q == p || visited[q] {
                        break;
                    }
                    visited[q] = true;
                    let next = neighbours8(w, h, c).find(|&(_, nc)| pix_of_cell[nc] != NONE && nc != prev).map(|(_, nc)| nc);
                    prev = c;
                    cur = next;
                }
                if pixels.len() >= 2 {
                    let a = id;
                    let mut cum = vec![0u32];
                    let mut acc = 0;
                    for k in 1..pixels.len() {
                        acc += cost_between(pixels[k - 1] as usize, pixels[k] as usize);
                        cum.push(acc);
                    }
                    let eid = edges.len() as u32;
                    for (k, &c) in pixels.iter().enumerate() {
                        let pp = pix_of_cell[c as usize] as usize;
                        if pp != p {
                            skel_edge[pp] = eid;
                            skel_idx[pp] = k as u32;
                        }
                    }
                    nodes[a as usize].adj.push((eid, a, acc));
                    edges.push(Edge { a, b: a, pixels, cum });
                }
            }
        }
        let t_graph = t2.elapsed().as_secs_f64() * 1e3;

        // Map every free cell to its nearest skeleton pixel.
        let t3 = Instant::now();
        let mut skel_of_cell = vec![NONE; n];
        let mut off_of_cell = vec![u32::MAX; n];
        let mut heap: BinaryHeap<Reverse<(u32, u32)>> = BinaryHeap::with_capacity(np * 2);
        for (p, &c) in skel_cell.iter().enumerate() {
            skel_of_cell[c as usize] = p as u32;
            off_of_cell[c as usize] = 0;
            heap.push(Reverse((0, c)));
        }
        while let Some(Reverse((d, c))) = heap.pop() {
            let ci = c as usize;
            if d > off_of_cell[ci] {
                continue;
            }
            for (dir, nc) in neighbours8(w, h, ci) {
                let cell = cave.cells[nc];
                if cell == 0 {
                    continue;
                }
                let nd = d + step_cost(dir, cell == FLOODED);
                if nd < off_of_cell[nc] {
                    off_of_cell[nc] = nd;
                    skel_of_cell[nc] = skel_of_cell[ci];
                    heap.push(Reverse((nd, nc as u32)));
                }
            }
        }
        let t_map = t3.elapsed().as_secs_f64() * 1e3;

        Graph {
            w,
            skel_of_cell,
            off_of_cell,
            skel_cell,
            skel_edge,
            skel_idx,
            skel_node,
            nodes,
            edges,
            times: BuildTimes { thin: t_thin, prune: t_prune, graph: t_graph, map: t_map },
        }
    }

    pub fn bytes(&self) -> usize {
        self.skel_of_cell.len() * 8
            + self.skel_cell.len() * 16
            + self.nodes.iter().map(|n| 8 + n.adj.len() * 12).sum::<usize>()
            + self.edges.iter().map(|e| 8 + e.pixels.len() * 8).sum::<usize>()
    }

    /// (edge, index) if the pixel lies on an edge, else the node it belongs to.
    fn locate(&self, pixel: u32) -> Loc {
        let p = pixel as usize;
        if self.skel_edge[p] != NONE {
            Loc::Edge(self.skel_edge[p], self.skel_idx[p])
        } else {
            Loc::Node(self.skel_node[p])
        }
    }
}

#[derive(Clone, Copy, PartialEq)]
enum Loc {
    Edge(u32, u32),
    Node(u32),
}

/// One emission's Dijkstra over the node graph.
pub struct GraphField {
    dist: Vec<u32>,
    pred_edge: Vec<u32>,
    stamp: Vec<u32>,
    gen: u32,
    heap: BinaryHeap<Reverse<(u32, u32)>>,
    src_loc: Loc,
    src_off: u32,
    src_cell: u32,
    range: u32,
    pub pops: u64,
    pub built: bool,
}

impl GraphField {
    pub fn new(g: &Graph) -> Self {
        GraphField {
            dist: vec![u32::MAX; g.nodes.len()],
            pred_edge: vec![NONE; g.nodes.len()],
            stamp: vec![0; g.nodes.len()],
            gen: 0,
            heap: BinaryHeap::with_capacity(256),
            src_loc: Loc::Node(NONE),
            src_off: 0,
            src_cell: NONE,
            range: 0,
            pops: 0,
            built: false,
        }
    }

    pub fn bytes(&self) -> usize {
        self.dist.capacity() * 12 + self.heap.capacity() * 8
    }

    #[inline]
    fn d(&self, node: u32) -> u32 {
        if self.stamp[node as usize] == self.gen { self.dist[node as usize] } else { u32::MAX }
    }

    fn relax(&mut self, node: u32, d: u32, via: u32) {
        let n = node as usize;
        if self.stamp[n] != self.gen {
            self.stamp[n] = self.gen;
            self.dist[n] = u32::MAX;
            self.pred_edge[n] = NONE;
        }
        if d < self.dist[n] {
            self.dist[n] = d;
            self.pred_edge[n] = via;
            self.heap.push(Reverse((d, node)));
        }
    }

    pub fn build(&mut self, g: &Graph, src_cell: u32, range_cells: f32) {
        self.gen = self.gen.wrapping_add(1);
        if self.gen == 0 {
            self.stamp.iter_mut().for_each(|s| *s = 0);
            self.gen = 1;
        }
        self.heap.clear();
        self.pops = 0;
        self.built = true;
        self.src_cell = src_cell;
        self.range = (range_cells * 1024.0) as u32;
        let pix = g.skel_of_cell[src_cell as usize];
        if pix == NONE {
            self.src_loc = Loc::Node(NONE);
            return;
        }
        self.src_off = g.off_of_cell[src_cell as usize];
        self.src_loc = g.locate(pix);
        match self.src_loc {
            Loc::Node(n) => self.relax(n, self.src_off, NONE),
            Loc::Edge(e, i) => {
                let edge = &g.edges[e as usize];
                let len = *edge.cum.last().unwrap();
                let ci = edge.cum[i as usize];
                self.relax(edge.a, self.src_off + ci, e);
                self.relax(edge.b, self.src_off + (len - ci), e);
            }
        }
        while let Some(Reverse((d, n))) = self.heap.pop() {
            self.pops += 1;
            if d > self.dist[n as usize] {
                continue;
            }
            if d > self.range {
                break;
            }
            let adj = &g.nodes[n as usize].adj;
            for k in 0..adj.len() {
                let (e, other, len) = adj[k];
                let nd = d + len;
                if nd <= self.range {
                    self.relax(other, nd, e);
                }
            }
        }
    }

    /// Bearing from the listener toward the pixel LOOKBACK steps along `edge` from
    /// index `i` in the direction of `toward_a`.
    fn edge_bearing(&self, g: &Graph, edge: u32, i: u32, toward_a: bool, lx: f32, ly: f32, off_cells: u32) -> f32 {
        let px = &g.edges[edge as usize].pixels;
        // Look further along the edge the further the listener sits off the skeleton, so
        // the bearing follows the passage instead of tilting toward the skeleton.
        let look = (crate::grid::LOOKBACK as u32).max(off_cells * LOOK_PER_OFFSET);
        let k = if toward_a {
            i.saturating_sub(look)
        } else {
            (i + look).min(px.len() as u32 - 1)
        };
        let c = px[k as usize] as usize;
        let cx = (c % g.w) as f32 + 0.5;
        let cy = (c / g.w) as f32 + 0.5;
        if (cx - lx).abs() < 1e-3 && (cy - ly).abs() < 1e-3 {
            return 0.0;
        }
        (cy - ly).atan2(cx - lx)
    }

    fn node_bearing(&self, g: &Graph, node: u32, lx: f32, ly: f32, off_cells: u32) -> f32 {
        let pe = self.pred_edge[node as usize];
        if pe == NONE {
            let c = self.src_cell as usize;
            let cx = (c % g.w) as f32 + 0.5;
            let cy = (c / g.w) as f32 + 0.5;
            return (cy - ly).atan2(cx - lx);
        }
        let edge = &g.edges[pe as usize];
        if edge.a == node {
            self.edge_bearing(g, pe, 0, false, lx, ly, off_cells)
        } else {
            self.edge_bearing(g, pe, edge.pixels.len() as u32 - 1, true, lx, ly, off_cells)
        }
    }

    pub fn arrival(&self, g: &Graph, lx: f32, ly: f32) -> Option<(f32, f32)> {
        if !self.built || lx < 0.0 || ly < 0.0 {
            return None;
        }
        let xi = lx as usize;
        let yi = ly as usize;
        if xi >= g.w {
            return None;
        }
        let cell = yi * g.w + xi;
        if cell >= g.skel_of_cell.len() {
            return None;
        }
        let pix = g.skel_of_cell[cell];
        if pix == NONE || self.src_loc == Loc::Node(NONE) {
            return None;
        }
        let off = g.off_of_cell[cell];
        let off_cells = (off + 512) / 1024;
        let loc = g.locate(pix);
        let (dist, bearing) = match loc {
            Loc::Node(n) => {
                let d = self.d(n);
                if d == u32::MAX {
                    return None;
                }
                (d + off, self.node_bearing(g, n, lx, ly, off_cells))
            }
            Loc::Edge(e, i) => {
                let edge = &g.edges[e as usize];
                let len = *edge.cum.last().unwrap();
                let ci = edge.cum[i as usize];
                let via_a = self.d(edge.a).saturating_add(ci);
                let via_b = self.d(edge.b).saturating_add(len - ci);
                let mut best = via_a;
                let mut toward_a = true;
                if via_b < best {
                    best = via_b;
                    toward_a = false;
                }
                if let Loc::Edge(se, si) = self.src_loc {
                    if se == e {
                        let sc = edge.cum[si as usize];
                        let direct = self.src_off + if sc > ci { sc - ci } else { ci - sc };
                        if direct < best {
                            best = direct;
                            toward_a = sc < ci;
                        }
                    }
                }
                if best == u32::MAX {
                    return None;
                }
                (best + off, self.edge_bearing(g, e, i, toward_a, lx, ly, off_cells))
            }
        };
        if dist > self.range {
            return None;
        }
        Some((dist as f32 / 1024.0, bearing))
    }
}
