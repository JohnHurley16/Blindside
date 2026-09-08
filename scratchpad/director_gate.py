"""When the camera arrives at the machinery, old gate against new.

Runs the real Director over real StageFrames with no window: the only difference
between the two columns is the gate expression in `_choose`.
"""
import sys
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")

from phase1 import tuning as T
from phase1.ancient_phase import AncientPhase
from phase1.match.sim import Sim
from phase1.view.director import Director

sim = Sim(7, stage=True)
new = Director(0.55)
old = Director(0.55)

# the old gate, restored on a copy by monkeypatching the one expression
import phase1.view.director as D
real_choose = D.Director._choose


def old_choose(self, frame, fix_easing):
    a = frame.ancient
    saved = a.__class__
    # emulate the old gate by hiding the slew and lock from the rule
    if a.phase in (AncientPhase.SLEW.value, AncientPhase.LOCKED.value):
        import dataclasses
        frame = dataclasses.replace(frame, ancient=dataclasses.replace(
            a, phase=AncientPhase.LISTENING.value))
    return real_choose(self, frame, fix_easing)


rows = []
while sim.t < 352.0 and not sim.over:
    sim.step()
    if abs(sim.t / 0.5 - round(sim.t / 0.5)) > 1e-9 or sim.t < 318.0:
        continue
    f = sim.stage()
    new.update(f, 0.5, False)
    D.Director._choose = old_choose
    old.update(f, 0.5, False)
    D.Director._choose = real_choose
    rows.append((sim.t, f.ancient.phase, new._shot.key, old._shot.key,
                 new.cells, old.cells))

print(f"{'t':>7} {'rel':>7} {'phase':<10} {'NEW shot':<16} {'frame':>7}   "
      f"{'OLD shot':<16} {'frame':>7}")
for t, phase, nk, ok, nc, oc in rows:
    print(f"{t:7.1f} {t - 341:+7.1f} {phase:<10} {nk:<16} {nc:7.1f}   {ok:<16} {oc:7.1f}"
          + ("   <-- differs" if nk != ok else ""))
