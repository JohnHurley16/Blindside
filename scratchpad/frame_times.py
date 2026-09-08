"""Live frame time, at the quiet part of the match and across the beat.

The median in --frame-times is measured from t=0, where the Assayer is LISTENING and
the lobe, the contours and the heave are all switched off. The number that matters is
the one during the wind and the four lethal seconds, where the image is repainted, both
contours are solved and three arcs of heave are rebuilt every frame.
"""
import statistics
import sys
import time

sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")

from vispy import app

from phase1.match.match_view import MatchView
from phase1.match.sim import Sim
from phase1.view.backend import pick_backend

pick_backend()
from phase1.view.view import View

match = MatchView(Sim(7, stage=True))
view = View(match, audio=None, show=True, size=(1600, 900))
view.canvas.show()
for _ in range(2):
    view.advance()
    view.canvas.render()
view._wall_clock_zero = None


def bench(n, warm=12):
    for _ in range(warm):          # the first frames after a jump carry the sim
        view.advance()             # catch-up and one shader compile per new visual
        app.process_events()
    out = []
    for _ in range(n):
        start = time.perf_counter()
        view.advance()
        app.process_events()
        out.append((time.perf_counter() - start) * 1000.0)
    out.sort()
    return out


def show(label, s):
    print(f"  {label:<44} median {statistics.median(s):5.1f}  mean {statistics.fmean(s):5.1f}  "
          f"p90 {s[int(0.9 * (len(s) - 1))]:5.1f}  worst {s[-1]:5.1f}  best {s[0]:5.1f}")


print("live frame time, ms, 1600x900:")
show("from t=0 (listening; no floor marks)", bench(300))
match.advance_to(323.0)
view.advance()
show("t=323->  (slew, lock, wind: the fill repaints)", bench(400))
match.advance_to(340.5)
view.advance()
show("t=340.5-> (fire and lethal: heave every frame)", bench(120))
print(f"  match clock now {match.t:.1f} s")
