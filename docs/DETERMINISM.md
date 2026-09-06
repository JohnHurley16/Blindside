# Determinism constraints

Applies to `blindside-sim`, `blindside-vm`, and `blindside-gen`. Does not apply to the
client, tooling, or the throwaway Python phases.

---

## Why this is non-negotiable

Four things depend on identical results from identical inputs on every machine:

- **Replays** — stored as seed plus input log, a few kilobytes, re-run to reproduce
- **Market verification** — listed behaviors auto-evaluated against benchmark seeds
- **Server authority** — the server runs the sim; clients receive filtered state
- **Batch balance work** — thousands of headless matches run overnight

None can be retrofitted. A desync introduced in month 4 and discovered in month 14, in a
networked match that cannot be reproduced, is the failure mode to fear.

---

## Hard rules

1. **No `f32` or `f64`.** Fixed-point only: `type Fx = fixed::types::I32F32`.
2. **No `HashMap`/`HashSet` iteration** in sim logic. Use `BTreeMap` or `SlotMap` with
   explicit ordering.
3. **No `SystemTime`, `Instant`, thread IDs, or address-derived values.**
4. **No `rand`.** RNG is counter-based and stateless:
   `draw(seed, tick, entity_id, purpose_id) -> Fx`. Because it is stateless, the order of
   calls cannot affect results — this removes the most common desync source in a
   simulation with many actors.
5. **No threading inside a tick** unless the reduction is order-independent and proven.
6. **Entity iteration is by stable ID**, always. Never by insertion order or index.
7. **Stable IDs are assigned in content data files and never derived** from name hashes,
   registration order, or vector indices. Retired IDs are never reused.
8. **Any `unsafe` in these crates requires written justification** in the PR.

---

## Enforcement

**CI lint** rejects any of rules 1–4 appearing in the constrained crates. Add this before
writing sim code, not after.

**Desync canary** (see `PHASE-0-HARNESS.md`) runs on every commit across Linux, macOS,
and Windows. Two sim instances, identical inputs, state hash compared every tick, panic
on first divergence with the tick number and a state diff.

**Replays carry a content pack hash.** Without it, replays silently produce different
results after a balance change and nobody notices for months.

**Policies carry a schema version** with a migration path. The node format will change.

---

## Practical notes

Trig and `sqrt` are the usual culprits. Use fixed-point implementations from a single
module; never call platform math libraries from sim code.

When the canary fires, the tick number is usually enough to find it. Bisecting by tick and
dumping the state diff at divergence should be a one-command operation — build that
tooling in Phase 0, not the first time you need it.
