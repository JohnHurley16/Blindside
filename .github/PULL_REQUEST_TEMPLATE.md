<!--
BLD-34. These five boxes are the determinism rules no lint can check.

docs/DETERMINISM.md rules 5, 7 and 8 are about intent, not spelling: a `// SAFETY:` line
can be false, `BTreeMap<NameHash, _>` reads perfectly and is still non-deterministic, and
a parallel reduction is order-independent or it is not — none of that is in the token
stream, which is all `tools/determinism-lint` sees (docs/HARNESS.md §9, "what it cannot
see"). The rest of the checklist is the two procedures that go wrong quietly: a serialised
field that changes without a schema bump, and a golden hash re-pinned because it was
failing rather than because something changed.

Delete a line only if it is genuinely not applicable — an unticked box is a question for
review, and "n/a" with a reason is an answer. CLAUDE.md: do not add process beyond what
the rules require, so nothing else belongs in this file.
-->

## What changed and why

<!-- One or two sentences. CLAUDE.md: state what changed and why, not what files were
     touched. -->

## Determinism checklist

- [ ] **`unsafe`** — every `unsafe` block or item and every `#[allow(unsafe_code)]` /
      `#[expect(unsafe_code)]` in `blindside-sim`, `blindside-vm`, `blindside-gen` or
      `blindside-content` carries a `// SAFETY:` comment directly above it, and the
      justification is written out below (rule 8). A crate-wide `#![allow(unsafe_code)]`
      is never a justification. *n/a if this PR adds no `unsafe`.*

- [ ] **Threading inside a tick** — if this PR runs anything concurrently within one tick,
      the proof that the reduction is order-independent is attached below, not asserted
      (rule 5). Parallelism *between* matches (`harness batch`) needs no proof and is not
      what this box is about. *n/a if the tick is still single-threaded.*

- [ ] **Stable IDs** — new IDs are assigned explicitly in content data files, never derived
      from a name hash, registration order or a vector index, and no retired ID is reused
      (rule 7; ARCHITECTURE.md extension rule 1). *n/a if this PR adds no IDs.*

- [ ] **Schema bump** — if a serialised format changed (`MatchRecord`, a policy, a content
      entry, the state-hash layout), the matching version was bumped in the same commit —
      `MATCH_RECORD_SCHEMA`, `CONTENT_SCHEMA`, `hash::LAYOUT_VERSION` — and a `migrate` arm
      for the old version was added where one applies. *n/a if nothing serialised changed.*

- [ ] **Golden hash change** — if a checked-in hash moved (`GOLDEN_SEED_DEADBEEF_TICK_*`,
      `PIN_SEED_DEADBEEF_TICK_1000`, `golden_tables.rs`, `EMPTY_PACK_HASH`,
      `fixtures/*.record`), it carries a schema bump *or* a content-pack change in this same
      PR, and the reason is stated below. A hash that moved for none of those reasons is a
      **desync**, and the fix is not to re-pin it (docs/HARNESS.md §8). *n/a if no pinned
      hash changed.*

## Justification

<!-- Required for any box ticked above whose rule asks for written reasoning: the SAFETY
     argument, the order-independence proof, why the golden hash moved. One paragraph is
     usually enough; "see the code" is not. -->

## Checks

<!-- CI must be green on all three OSes before merge: build-test-lint (x3),
     cross-platform, feature-gates, canary-injection, unsafe-policy, lint-rejects-f64.
     If the sim itself changed, say whether `tools/assert-empty-sim.sh` still passes and,
     if it does not, which gate report authorises the change (BLD-40, BLD-66). -->
