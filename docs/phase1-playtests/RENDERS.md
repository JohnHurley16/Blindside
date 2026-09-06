# Phase 1 renders

Videos are gitignored (`*.mp4`) and live at the repo root. This file is what makes them
reproducible: without it a render is an eight-minute video of nothing in particular.

Both were produced from the same seed and the same commit so that the only difference
between them is the sensor. Per the Part 4 decision in `PHASE-1-OPEN-QUESTIONS.md`, the
gate is **two viewings, sonar first**: viewing one is scored against the pass criteria,
viewing two is logged separately, because a tester who has seen both worlds compares
rather than reacts.

| | Viewing one — **gate** | Viewing two — sensor comparison |
|---|---|---|
| File | `phase1-sonar.mp4` | `phase1-lidar.mp4` |
| Command | `python -m phase1 --record phase1-sonar.mp4 --player-sensor sonar` | `python -m phase1 --record phase1-lidar.mp4 --player-sensor lidar` |
| Commit | `6ba476e` | `6ba476e` |
| Seed | 7 (`tuning.py` `SEED`) | 7 |
| Recall | not sent | not sent |
| Duration | 8:12 (8:00 match + reveal) | 8:12 |
| Video | h264 High, 1600x1000, 20 fps | h264 High, 1600x1000, 20 fps |
| Audio | AAC-LC 44.1 kHz stereo | AAC-LC 44.1 kHz stereo |
| Size / sha256 (first 16) | 51,950,962 B / `3d8812d87120cfd5` | 61,970,654 B / `6aa96c6eedb14f76` |

## What is known about these two

- Neither reaches `SEARCH`, because neither sends Recall. That means neither of them
  exercised the crash fixed in `7fcbe87` — **a render that includes the Recall beat must
  be made from `7fcbe87` or later**, or it will stop dead at the moment Recall pays off.
- The rival dies in the sonar viewing and survives in the lidar one. Measured over eight
  seeds on this tuning the rival dies 4/8 with sonar and 2/8 with lidar, so this is a
  property of these seeds, not of the sensors. The residual cause is the C3-to-machinery
  passage: the rival cannot reliably navigate it. That is a navigation-stack problem
  (`DEV-PLAN.md` BLD-101), not a Phase 1 one.
- The spoof fires in both; it fires on all eight seeds tested.
- The lidar viewing is the one that shows the sump read as a wall: the waterline returns
  as solid, the agent steers round it, and never learns what is on the far side.

## Storage

These are ~110 MB together and are not in git. Copy them somewhere durable before
`--record` is run again with the same filenames; the commands above regenerate them from
the stated commit, but only if the tuning at that commit is untouched.
