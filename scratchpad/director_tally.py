import sys, collections
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
import dataclasses
from phase1.ancient_phase import AncientPhase
from phase1.match.sim import Sim
import phase1.view.director as D

real_choose = D.Director._choose


def old_choose(self, frame, fix_easing):
    a = frame.ancient
    if a.phase in (AncientPhase.SLEW.value, AncientPhase.LOCKED.value):
        frame = dataclasses.replace(frame, ancient=dataclasses.replace(
            a, phase=AncientPhase.LISTENING.value))
    return real_choose(self, frame, fix_easing)


sim = Sim(7, stage=True)
new, old = D.Director(0.55), D.Director(0.55)
tn, to = collections.Counter(), collections.Counter()
cuts_n = cuts_o = 0
last_n = last_o = None
while not sim.over:
    sim.step()
    if sim.tick % 3:
        continue
    f = sim.stage()
    new.update(f, 0.15, False)
    D.Director._choose = old_choose
    old.update(f, 0.15, False)
    D.Director._choose = real_choose
    tn[new._shot.key] += 0.15
    to[old._shot.key] += 0.15
    cuts_n += new._shot.key != last_n
    cuts_o += old._shot.key != last_o
    last_n, last_o = new._shot.key, old._shot.key
print(f"{'shot':<18}{'NEW s':>8}{'OLD s':>8}")
for k in sorted(set(tn) | set(to), key=lambda k: -max(tn[k], to[k])):
    print(f"{k:<18}{tn[k]:8.1f}{to[k]:8.1f}")
print(f"\nsubject changes over the match: NEW {cuts_n}, OLD {cuts_o}")
