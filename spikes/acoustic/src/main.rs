//! BLD-64 acoustic propagation spike. Throwaway measurement code.
//!
//!   cargo run --release -- bench [sizes=200x120,400x240,800x480] [gens=ca,tree] [seeds=3]
//!                                [ticks=9600] [agents=8] [ancients=2] [crashes=4] [motion_every=10]
//!                                [ping=170] [motion=40] [ancient=80] [echo=0] [models=A,AC,AL,ABC,ABL,B,BC]
//!   gens: ca (cellular automata, fill 0.47, an open field), cat (cellular automata, fill 0.50,
//!         just above the percolation cliff), tree (chambers joined by passages, Phase 1's shape)
//!   models: A cell Dijkstra rebuilt per tick; AC cached per emission; AL resumable lazy, cached;
//!           ABC/ABL the same with a Dial bucket queue; B graph Dijkstra per tick; BC cached
//!   cargo run --release -- caves  [sizes=...] [gens=...] [seed=1] [fill=0.5] [ascii=1]   stats + thumbnails
//!   cargo run --release -- accuracy [sizes=...] [gens=...] [pairs=2000]       model B against model A
//!   cargo run --release -- single [size=400x240] [gen=ca] [seed=1]            per-emission cost by range
//!   cargo run --release -- probe [size=200x120] [gen=tree] [seed=1] [range=170]   decompose B underestimates
//!   cargo run --release -- fixture                                            straight corridor and L-bend

mod cave;
mod grid;
mod rng;
mod sim;
mod skel;

use cave::Cave;
use rng::Rng;
use sim::{GraphModel, GridMode, GridModel, Model, Params, Report, Schedule};
use std::collections::HashMap;
use std::time::Instant;

const CA_FILL_OPEN: f64 = 0.47;
const CA_FILL_TIGHT: f64 = 0.50; // 0.52+ falls off the percolation cliff: a few thousand cells
const UNIT_HEAP: u32 = 1024;
const UNIT_BUCKET: u32 = 64;
const CA_ITERS: usize = 5;
const FLOOD_FRAC: f64 = 0.12;

fn parse_args() -> (String, HashMap<String, String>) {
    let mut args = std::env::args().skip(1);
    let cmd = args.next().unwrap_or_else(|| "bench".to_string());
    let mut kv = HashMap::new();
    for a in args {
        if let Some((k, v)) = a.split_once('=') {
            kv.insert(k.to_string(), v.to_string());
        }
    }
    (cmd, kv)
}

fn sizes(kv: &HashMap<String, String>, key: &str, default: &str) -> Vec<(usize, usize)> {
    kv.get(key).map(|s| s.as_str()).unwrap_or(default)
        .split(',')
        .map(|s| {
            let (w, h) = s.split_once('x').expect("size as WxH");
            (w.parse().unwrap(), h.parse().unwrap())
        })
        .collect()
}

fn gens(kv: &HashMap<String, String>, key: &str, default: &str) -> Vec<String> {
    kv.get(key).map(|s| s.as_str()).unwrap_or(default).split(',').map(|s| s.to_string()).collect()
}

fn num<T: std::str::FromStr>(kv: &HashMap<String, String>, key: &str, default: T) -> T {
    kv.get(key).and_then(|v| v.parse().ok()).unwrap_or(default)
}

fn make_cave(gen: &str, w: usize, h: usize, seed: u64) -> Cave {
    make_cave_fill(gen, w, h, seed, None)
}

fn make_cave_fill(gen: &str, w: usize, h: usize, seed: u64, fill: Option<f64>) -> Cave {
    match gen {
        "ca" => cave::gen_ca(seed, w, h, fill.unwrap_or(CA_FILL_OPEN), CA_ITERS, FLOOD_FRAC),
        "cat" => {
            let mut c = cave::gen_ca(seed, w, h, fill.unwrap_or(CA_FILL_TIGHT), CA_ITERS, FLOOD_FRAC);
            c.name = c.name.replace("ca-", "cat-");
            c
        }
        "tree" => cave::gen_tree(seed, w, h, FLOOD_FRAC),
        other => panic!("unknown generator {other}"),
    }
}

fn cmd_caves(kv: &HashMap<String, String>) {
    let seed: u64 = num(kv, "seed", 1);
    let fill: Option<f64> = kv.get("fill").and_then(|v| v.parse().ok());
    println!("| cave | cells | free | free % | flooded % | median half-width | p90 half-width | skeleton px | nodes | edges | graph build ms (thin/prune/graph/map) |");
    println!("|---|---|---|---|---|---|---|---|---|---|---|");
    for g in gens(kv, "gens", "ca,tree") {
        for (w, h) in sizes(kv, "sizes", "200x120,400x240,800x480") {
            let c = make_cave_fill(&g, w, h, seed, fill);
            let s = c.stats();
            let t0 = Instant::now();
            let graph = skel::Graph::build(&c);
            let ms = t0.elapsed().as_secs_f64() * 1e3;
            println!(
                "| {} | {} | {} | {:.1} | {:.1} | {} | {} | {} | {} | {} | {:.1} ({:.1}/{:.1}/{:.1}/{:.1}) |",
                c.name, w * h, s.free, 100.0 * s.free as f64 / (w * h) as f64,
                100.0 * s.flooded as f64 / s.free.max(1) as f64, s.median_halfwidth, s.p90_halfwidth,
                graph.skel_cell.len(), graph.nodes.len(), graph.edges.len(), ms,
                graph.times.thin, graph.times.prune, graph.times.graph, graph.times.map
            );
            if kv.get("ascii").is_some() {
                println!("\n{}\n", c.ascii(100));
            }
        }
    }
}

fn wrap(a: f32) -> f32 {
    let mut a = a;
    while a > std::f32::consts::PI { a -= 2.0 * std::f32::consts::PI; }
    while a < -std::f32::consts::PI { a += 2.0 * std::f32::consts::PI; }
    a
}

fn cmd_accuracy(kv: &HashMap<String, String>) {
    let pairs: usize = num(kv, "pairs", 2000);
    let seed: u64 = num(kv, "seed", 1);
    println!("| cave | range | pairs in Euclid range | A hears | B hears | both | B misses | B false | mean dd cells | p90 dd | max dd | mean bearing err deg | p90 | max | bearing err by listener offset: <=1 cell (n) | 2-3 (n) | >=4 (n) |");
    println!("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|");
    for g in gens(kv, "gens", "ca,tree") {
        for (w, h) in sizes(kv, "sizes", "200x120,400x240,800x480") {
            let c = make_cave(&g, w, h, seed);
            let graph = skel::Graph::build(&c);
            let mut slot = grid::Slot::new(c.cells.len(), UNIT_HEAP, grid::Queue::Heap);
            let mut field = skel::GraphField::new(&graph);
            let walk = c.walkable_cells();
            let mut rng = Rng::new(seed * 7 + 3);
            for range in [170.0f32, 80.0, 40.0] {
                let (mut n, mut a_hears, mut b_hears, mut both, mut miss, mut false_pos) = (0, 0, 0, 0, 0, 0);
                let mut dd: Vec<f32> = Vec::new();
                let mut db: Vec<f32> = Vec::new();
                let mut by_off: [(f32, usize); 3] = [(0.0, 0); 3];
                let mut tries = 0;
                while n < pairs && tries < pairs * 50 {
                    tries += 1;
                    let e = walk[rng.below(walk.len())] as usize;
                    let l = walk[rng.below(walk.len())] as usize;
                    let (ex, ey) = c.centre(e);
                    let (lx, ly) = c.centre(l);
                    if (ex - lx).powi(2) + (ey - ly).powi(2) > range * range || e == l {
                        continue;
                    }
                    n += 1;
                    slot.begin(&c, e as u32, range);
                    let ra = slot.arrival(&c, lx, ly, true);
                    slot.release();
                    field.build(&graph, e as u32, range);
                    let rb = field.arrival(&graph, lx, ly);
                    match (ra, rb) {
                        (Some((da, ba)), Some((dbv, bb))) => {
                            a_hears += 1;
                            b_hears += 1;
                            both += 1;
                            dd.push((da - dbv).abs());
                            let err = wrap(ba - bb).abs().to_degrees();
                            db.push(err);
                            let off_cells = graph.off_of_cell[l] as f32 / 1024.0;
                            let bin = if off_cells <= 1.5 { 0 } else if off_cells < 4.0 { 1 } else { 2 };
                            by_off[bin].0 += err;
                            by_off[bin].1 += 1;
                        }
                        (Some(_), None) => { a_hears += 1; miss += 1; }
                        (None, Some(_)) => { b_hears += 1; false_pos += 1; }
                        (None, None) => {}
                    }
                }
                let stat = |v: &mut Vec<f32>| -> (f32, f32, f32) {
                    if v.is_empty() { return (0.0, 0.0, 0.0); }
                    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
                    (v.iter().sum::<f32>() / v.len() as f32, v[(v.len() - 1) * 9 / 10], *v.last().unwrap())
                };
                let (dm, d90, dmax) = stat(&mut dd);
                let (bm, b90, bmax) = stat(&mut db);
                let bo = |k: usize| -> String {
                    if by_off[k].1 == 0 { "-".to_string() } else { format!("{:.1} ({})", by_off[k].0 / by_off[k].1 as f32, by_off[k].1) }
                };
                println!("| {} | {} | {} | {} | {} | {} | {} | {} | {:.2} | {:.2} | {:.2} | {:.1} | {:.1} | {:.1} | {} | {} | {} |",
                    c.name, range, n, a_hears, b_hears, both, miss, false_pos, dm, d90, dmax, bm, b90, bmax, bo(0), bo(1), bo(2));
            }
        }
    }
}

fn cmd_single(kv: &HashMap<String, String>) {
    let (w, h) = sizes(kv, "size", "400x240")[0];
    let g = gens(kv, "gen", "ca")[0].clone();
    let seed: u64 = num(kv, "seed", 1);
    let c = make_cave(&g, w, h, seed);
    let graph = skel::Graph::build(&c);
    let walk = c.walkable_cells();
    let mut rng = Rng::new(seed + 99);
    let emitters: Vec<usize> = (0..200).map(|_| walk[rng.below(walk.len())] as usize).collect();
    let mut slot = grid::Slot::new(c.cells.len(), UNIT_HEAP, grid::Queue::Heap);
    let mut bslot = grid::Slot::new(c.cells.len(), UNIT_BUCKET, grid::Queue::Bucket);
    let mut field = skel::GraphField::new(&graph);
    println!("cave {} ({} free cells, graph {} nodes {} edges)", c.name, c.free_count(), graph.nodes.len(), graph.edges.len());
    println!("| range | A heap build us mean | max | A bucket build us mean | max | cells reached mean | max | B build us mean | max | nodes popped mean | A lookup us | B lookup us |");
    println!("|---|---|---|---|---|---|---|---|---|---|---|---|");
    for range in [170.0f32, 80.0, 40.0, 20.0] {
        let mut ta = Vec::new();
        let mut tab = Vec::new();
        let mut reach = Vec::new();
        let mut tb = Vec::new();
        let mut pops = Vec::new();
        for &e in &emitters {
            let t0 = Instant::now();
            slot.begin(&c, e as u32, range);
            slot.run_until(&c, None);
            ta.push(t0.elapsed().as_nanos() as f64 / 1e3);
            reach.push(slot.reached() as f64);
            slot.release();
            let t0 = Instant::now();
            bslot.begin(&c, e as u32, range);
            bslot.run_until(&c, None);
            tab.push(t0.elapsed().as_nanos() as f64 / 1e3);
            bslot.release();
            let t1 = Instant::now();
            field.build(&graph, e as u32, range);
            tb.push(t1.elapsed().as_nanos() as f64 / 1e3);
            pops.push(field.pops as f64);
        }
        // lookups
        slot.begin(&c, emitters[0] as u32, range);
        slot.run_until(&c, None);
        field.build(&graph, emitters[0] as u32, range);
        let listeners: Vec<(f32, f32)> = (0..1000).map(|_| c.centre(walk[rng.below(walk.len())] as usize)).collect();
        let t0 = Instant::now();
        let mut sink = 0.0;
        for &(lx, ly) in &listeners {
            if let Some((d, b)) = slot.arrival(&c, lx, ly, false) { sink += d + b; }
        }
        let la = t0.elapsed().as_nanos() as f64 / 1e3 / listeners.len() as f64;
        let t1 = Instant::now();
        for &(lx, ly) in &listeners {
            if let Some((d, b)) = field.arrival(&graph, lx, ly) { sink += d + b; }
        }
        let lb = t1.elapsed().as_nanos() as f64 / 1e3 / listeners.len() as f64;
        std::hint::black_box(sink);
        slot.release();
        let mean = |v: &Vec<f64>| v.iter().sum::<f64>() / v.len() as f64;
        let max = |v: &Vec<f64>| v.iter().cloned().fold(0.0, f64::max);
        println!("| {} | {:.1} | {:.1} | {:.1} | {:.1} | {:.0} | {:.0} | {:.2} | {:.2} | {:.0} | {:.3} | {:.3} |",
            range, mean(&ta), max(&ta), mean(&tab), max(&tab), mean(&reach), max(&reach), mean(&tb), max(&tb), mean(&pops), la, lb);
    }
}

fn cmd_bench(kv: &HashMap<String, String>) {
    let seeds: u64 = num(kv, "seeds", 3);
    let mut p = Params::default();
    p.ticks = num(kv, "ticks", p.ticks);
    p.agents = num(kv, "agents", p.agents);
    p.ancients = num(kv, "ancients", p.ancients);
    p.crashes = num(kv, "crashes", p.crashes);
    p.ping_range = num(kv, "ping", p.ping_range);
    p.motion_range = num(kv, "motion", p.motion_range);
    p.ancient_range = num(kv, "ancient", p.ancient_range);
    p.crash_range = p.ping_range;
    p.echo_per_ping = num(kv, "echo", p.echo_per_ping);
    p.motion_every = num(kv, "motion_every", p.motion_every);
    let which = gens(kv, "models", "A,AC,AL,ABC,ABL,B,BC");
    println!("params: ticks {} agents {} ancients {} crashes {} ranges ping {} motion {} ancient {} crash {} echo/ping {} seeds {}",
        p.ticks, p.agents, p.ancients, p.crashes, p.ping_range, p.motion_range, p.ancient_range, p.crash_range, p.echo_per_ping, seeds);
    println!();
    println!("| cave | free cells | model | mean us/tick | p50 | p99 | worst us | total ms/match | builds | pops (cells or nodes) | listens | heard | memory KB | collapse ms |");
    println!("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|");
    for g in gens(kv, "gens", "ca,tree") {
        for (w, h) in sizes(kv, "sizes", "200x120,400x240,800x480") {
            for seed in 1..=seeds {
                let base = make_cave(&g, w, h, seed);
                let sched = Schedule::generate(&base, p, seed);
                let free = base.free_count();
                let mut reports: Vec<Report> = Vec::new();
                for m in &which {
                    let mut cave = base.clone();
                    let mut model: Box<dyn Model> = match m.as_str() {
                        "A" => Box::new(GridModel::new(&cave, GridMode::PerTick, UNIT_HEAP, grid::Queue::Heap)),
                        "AC" => Box::new(GridModel::new(&cave, GridMode::Cached, UNIT_HEAP, grid::Queue::Heap)),
                        "AL" => Box::new(GridModel::new(&cave, GridMode::Lazy, UNIT_HEAP, grid::Queue::Heap)),
                        "AB" => Box::new(GridModel::new(&cave, GridMode::PerTick, UNIT_BUCKET, grid::Queue::Bucket)),
                        "ABC" => Box::new(GridModel::new(&cave, GridMode::Cached, UNIT_BUCKET, grid::Queue::Bucket)),
                        "ABL" => Box::new(GridModel::new(&cave, GridMode::Lazy, UNIT_BUCKET, grid::Queue::Bucket)),
                        "B" => Box::new(GraphModel::new(&cave, false)),
                        "BC" => Box::new(GraphModel::new(&cave, true)),
                        other => panic!("unknown model {other}"),
                    };
                    let r = sim::replay(&mut cave, &sched, model.as_mut(), seed * 31);
                    reports.push(r);
                }
                for r in &reports {
                    println!("| {} | {} | {} | {:.2} | {:.2} | {:.1} | {:.1} | {:.1} | {} | {} | {} | {} | {} | {:.2} |",
                        base.name, free, r.name, r.mean_us(), r.pct_us(0.5), r.pct_us(0.99), r.max_us(), r.total_ms(),
                        r.builds, r.pops, r.listens, r.heard, r.bytes / 1024, r.collapse_ms);
                }
                eprintln!("  {} schedule: {}", base.name, sched.counts());
            }
        }
    }
}

/// Find pairs where model B claims a shorter path than the exact model and decompose them.
fn cmd_probe(kv: &HashMap<String, String>) {
    let (w, h) = sizes(kv, "size", "200x120")[0];
    let g = gens(kv, "gen", "tree")[0].clone();
    let seed: u64 = num(kv, "seed", 1);
    let range: f32 = num(kv, "range", 170.0);
    let c = make_cave(&g, w, h, seed);
    let graph = skel::Graph::build(&c);
    let mut slot = grid::Slot::new(c.cells.len(), UNIT_HEAP, grid::Queue::Heap);
    let mut field = skel::GraphField::new(&graph);
    let walk = c.walkable_cells();
    let mut rng = Rng::new(seed * 7 + 3);
    let mut shown = 0;
    let mut cluster_sizes = vec![0usize; graph.nodes.len()];
    for &n in &graph.skel_node {
        if n != skel::NONE {
            cluster_sizes[n as usize] += 1;
        }
    }
    let biggest = cluster_sizes.iter().cloned().max().unwrap_or(0);
    let big = cluster_sizes.iter().filter(|&&s| s > 3).count();
    println!("cave {}: {} nodes, {} edges, biggest node cluster {} px, clusters over 3 px: {}", c.name, graph.nodes.len(), graph.edges.len(), biggest, big);
    let exact = |slot: &mut grid::Slot, from: usize, to: usize| -> Option<f32> {
        slot.begin(&c, from as u32, 100_000.0);
        let (tx, ty) = c.centre(to);
        let r = slot.arrival(&c, tx, ty, true).map(|(d, _)| d);
        slot.release();
        r
    };
    for _ in 0..200_000 {
        if shown >= 5 {
            break;
        }
        let e = walk[rng.below(walk.len())] as usize;
        let l = walk[rng.below(walk.len())] as usize;
        let (ex, ey) = c.centre(e);
        let (lx, ly) = c.centre(l);
        if (ex - lx).powi(2) + (ey - ly).powi(2) > range * range || e == l {
            continue;
        }
        let da = exact(&mut slot, e, l);
        field.build(&graph, e as u32, range);
        let rb = field.arrival(&graph, lx, ly);
        let (da, db) = match (da, rb) {
            (Some(da), Some((db, _))) if db < da - 2.0 => (da, db),
            (None, Some((db, _))) => (f32::INFINITY, db),
            _ => continue,
        };
        shown += 1;
        let pe = graph.skel_of_cell[e] as usize;
        let pl = graph.skel_of_cell[l] as usize;
        let ce = graph.skel_cell[pe] as usize;
        let cl = graph.skel_cell[pl] as usize;
        let off_e = graph.off_of_cell[e] as f32 / 1024.0;
        let off_l = graph.off_of_cell[l] as f32 / 1024.0;
        let exact_e_off = exact(&mut slot, e, ce);
        let exact_l_off = exact(&mut slot, l, cl);
        let exact_skel = exact(&mut slot, ce, cl);
        println!(
            "pair e={:?} l={:?}: A {:.2}  B {:.2} = off_e {:.2} + graph {:.2} + off_l {:.2} | exact e->pix {:?} l->pix {:?} pix->pix {:?} | e loc edge {} node {} | l loc edge {} node {}",
            c.xy(e), c.xy(l), da, db, off_e, db - off_e - off_l, off_l, exact_e_off, exact_l_off, exact_skel,
            graph.skel_edge[pe], graph.skel_node[pe], graph.skel_edge[pl], graph.skel_node[pl]
        );
    }
}

/// Hand-built fixtures: a straight corridor and an L-bend, both width 5. Prints A's and
/// B's distance and bearing at listeners along them, so a reader can see where the two
/// models agree (straight passage) and where they differ (the bend: shortest path hugs
/// the inner corner, the skeleton runs down the middle).
fn cmd_fixture() {
    let (w, h) = (80usize, 60usize);
    let mut cells = vec![0u8; w * h];
    let carve = |cells: &mut Vec<u8>, x0: usize, y0: usize, x1: usize, y1: usize| {
        for y in y0..=y1 {
            for x in x0..=x1 {
                cells[y * w + x] = 1;
            }
        }
    };
    // Straight corridor: y 5..9, x 5..74.
    carve(&mut cells, 5, 5, 74, 9);
    // L-bend: along x at y 30..34 from x 5..40, then up along y at x 36..40 from y 12..34.
    carve(&mut cells, 5, 30, 40, 34);
    carve(&mut cells, 36, 12, 40, 34);
    let c = Cave { w, h, cells, name: "fixture".to_string() };
    let graph = skel::Graph::build(&c);
    let mut slot = grid::Slot::new(c.cells.len(), UNIT_HEAP, grid::Queue::Heap);
    let mut field = skel::GraphField::new(&graph);
    println!("fixture graph: {} nodes, {} edges", graph.nodes.len(), graph.edges.len());
    println!("| case | emitter | listener | A dist | A bearing deg | B dist | B bearing deg | bearing diff |");
    println!("|---|---|---|---|---|---|---|---|");
    let cases: Vec<(&str, (usize, usize), Vec<(usize, usize)>)> = vec![
        ("straight, emitter mid-passage", (8, 7), vec![(30, 7), (60, 7), (60, 5), (60, 9)]),
        ("straight, emitter on wall", (8, 5), vec![(30, 7), (60, 9)]),
        ("L-bend, emitter at the far end of the x leg", (8, 32), vec![(30, 32), (38, 32), (38, 25), (38, 15), (40, 15), (36, 15)]),
        ("L-bend, emitter up the y leg", (38, 14), vec![(38, 28), (30, 32), (10, 32), (10, 30), (10, 34)]),
    ];
    for (name, (ex, ey), listeners) in cases {
        let e = c.idx(ex, ey);
        let (exf, eyf) = c.centre(e);
        field.build(&graph, e as u32, 170.0);
        for (lx, ly) in listeners {
            let (lxf, lyf) = c.centre(c.idx(lx, ly));
            slot.begin(&c, e as u32, 170.0);
            let a = slot.arrival(&c, lxf, lyf, true);
            slot.release();
            let b = field.arrival(&graph, lxf, lyf);
            let fmt = |r: Option<(f32, f32)>| match r {
                Some((d, br)) => (format!("{:.1}", d), format!("{:.0}", br.to_degrees())),
                None => ("-".to_string(), "-".to_string()),
            };
            let (ad, ab) = fmt(a);
            let (bd, bb) = fmt(b);
            let diff = match (a, b) {
                (Some((_, x)), Some((_, y))) => format!("{:.0}", wrap(x - y).abs().to_degrees()),
                _ => "-".to_string(),
            };
            println!("| {} | ({},{}) | ({},{}) | {} | {} | {} | {} | {} |", name, exf as i32, eyf as i32, lx, ly, ad, ab, bd, bb, diff);
        }
    }
}

fn main() {
    let (cmd, kv) = parse_args();
    match cmd.as_str() {
        "probe" => cmd_probe(&kv),
        "fixture" => cmd_fixture(),
        "bench" => cmd_bench(&kv),
        "caves" => cmd_caves(&kv),
        "accuracy" => cmd_accuracy(&kv),
        "single" => cmd_single(&kv),
        other => eprintln!("unknown command {other}"),
    }
}
