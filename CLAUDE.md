# BLINDSIDE — agent operating instructions

Working title. Renaming is a `git mv`; do not spend time on it.

You are building a competitive game about teaching autonomous machines to work in a
place where they cannot be controlled. Read `docs/GLOSSARY.md` first — the domain
vocabulary is precise and used consistently throughout this repo.

---

## The one invariant

**An agent's policy may never observe ground truth.**

The simulation holds two separate representations: `World` (what is actually true) and
`Belief` (what an agent's sensors and estimator have produced). Policies, predicates,
the client, and the renderer see `Belief` only.

The sensor layer is the only code permitted to read both. It lives in one module so it
can be audited by reading it.

If you find yourself wanting to pass `&World` anywhere downstream of the sensor layer —
for convenience, for debugging, for a "just this once" special case — **stop and ask.**
That leak silently converts this from a game about autonomy into a game about robots,
and the damage will not be visible for months.

---

## Build order

Phases are ordered by *how much damage a wrong answer does, weighted by uncertainty*.
Each has a gate with a stated kill criterion. **Do not start a phase whose predecessor's
gate has not been met.** If a gate fails, stop and report; do not work around it.

| Phase | Doc | Language | Status |
|---|---|---|---|
| 1 — Spectator Test | `docs/PHASE-1-SPECTATOR-TEST.md` | Python, throwaway | **start here** |
| 2 — Junction Test | `docs/ROADMAP.md` | Python, throwaway | blocked on 1 |
| 0 — Harness | `docs/PHASE-0-HARNESS.md` | Rust | do immediately before 3 |
| 3 — Sim core | `docs/ARCHITECTURE.md` | Rust | blocked on 1, 2, 0 |
| 4+ | `docs/ROADMAP.md` | — | not yet specified |

Phase 0 is numbered before Phase 1 for historical reasons but is tooling for a sim that
does not exist until Phase 3. Build Phase 1 first.

**Phases 1 and 2 are deliberately throwaway.** Do not engineer them. Do not add
abstraction layers, plugin systems, config files, or test suites beyond what the gate
requires. Their only job is to answer a question cheaply. Code quality standards in this
document apply from Phase 3 onward.

---

## Reference documents

| File | What it is |
|---|---|
| `docs/GLOSSARY.md` | Domain vocabulary. Read first. |
| `docs/ARCHITECTURE.md` | Crate layout, core types, extension rules |
| `docs/DETERMINISM.md` | Hard constraints on the sim crate |
| `docs/ROADMAP.md` | All phases, risk register, deferred work |
| `docs/DESIGN.html` | Full game design. Background, not spec. |

Where `DESIGN.html` and a phase spec disagree, **the phase spec wins.** The design
document is a snapshot of intent; specs are current.

---

## Working rules

**Ask rather than invent.** This design has many deliberate choices that look arbitrary
without context. If a spec is silent on something load-bearing — a number, a rule, a
behavior at an edge case — ask. Do not pick something reasonable and proceed. A wrong
guess that compiles is worse than a question.

**Flag design problems you find.** You will hit things the design does not survive. Say
so plainly rather than building the thing you were asked for. Known-weak areas: the
demonstration-to-policy induction (Phase 2), sensor noise that feels fair, automatic
failure attribution.

**Do not add features.** No convenience modes, no quality-of-life additions, no "while I
was in there". Every phase is scoped to answer one question.

**Small commits, one concern each.** Commit messages state what changed and why, not what
files were touched.

---

## Definition of done

A task is complete when:

1. The stated acceptance criteria in the phase spec pass
2. From Phase 3 onward: the desync canary passes on all three platforms
3. From Phase 3 onward: no new `f32`/`f64`, `HashMap` iteration, or `std::time` in
   `blindside-sim` (CI enforces this)
4. Anything you guessed at is listed explicitly in the summary

Do not report a phase gate as met. Gates involve human playtesting. Report that the
build is ready for the gate.

---

## What this project is actually for

Long-term, the behavior authoring layer is intended to run on real hardware, not only in
simulation. Sensor and actuator interfaces should be designed as though a hardware
backend will exist — not building it, just not foreclosing it. This is a few days of care
in Phase 3 and the difference between possible and impossible later.
