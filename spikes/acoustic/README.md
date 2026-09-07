# Acoustic propagation spike (BLD-64)

Throwaway measurement code. Not a workspace member; floats allowed; nothing here is sim
code. The write-up with the numbers is `docs/spikes/ACOUSTIC-BUDGET.md`.

```
cargo build --release
./target/release/acoustic-spike bench      # the per-tick tables (about 4 minutes)
./target/release/acoustic-spike single     # per-emission cost by range on one cave
./target/release/acoustic-spike accuracy   # model B against model A
./target/release/acoustic-spike caves      # cave statistics, add ascii=1 for thumbnails
./target/release/acoustic-spike fixture    # straight corridor and L-bend, both models
./target/release/acoustic-spike probe      # decompose pairs where B is shorter than A
```

All commands take `key=value` arguments; see the doc comment at the top of `src/main.rs`.

| file | what |
|---|---|
| `src/cave.rs` | cave generators: cellular automata (`ca`, `cat`) and chambers-plus-passages (`tree`); flooding; collapse |
| `src/grid.rs` | model A: range-bounded cell Dijkstra with integer costs, heap or Dial bucket queue, resumable |
| `src/skel.rs` | model B: skeleton passage graph (thin, minimise, prune, trace), per-emission graph Dijkstra, listener lookup |
| `src/sim.rs` | the emitter load (agents, pings, motion, ancients, crashes), model adapters, the timed replay |
| `src/main.rs` | commands and tables |
| `src/rng.rs` | SplitMix64 |
