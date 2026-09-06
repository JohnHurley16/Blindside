"""Run the spectator test.

    python -m phase1.main                 play (window + sound), R to recall
    python -m phase1.main --recall 300    scripted recall at 5:00, for testing
    python -m phase1.main --snap 60,200   render belief-view PNGs at those times, no window
"""
import argparse
from vispy import app
from . import tuning as T
from .sim import Sim


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=T.SEED)
    ap.add_argument("--recall", type=float, default=None, help="auto-recall at this many seconds")
    ap.add_argument("--snap", type=str, default=None, help="comma-separated sim times; render PNGs headless")
    ap.add_argument("--no-audio", action="store_true")
    a = ap.parse_args()
    from .view import pick_backend, View
    backend = pick_backend()
    sim = Sim(a.seed)
    if a.snap:
        sim.truth_trail = {"player": [], "rival": []}
        view = View(sim, audio=None, show=False)
        times = sorted(float(x) for x in a.snap.split(","))
        for ts in times:
            while sim.t < ts and not sim.over:
                if a.recall is not None and sim.t >= a.recall:
                    sim.recall()
                sim.step()
                if sim.tick % 10 == 0:
                    for n, ag in sim.world.agents.items():
                        sim.truth_trail[n].append((ag.x, ag.y, sim.t))
            path = f"snap_{int(ts):03d}.png"
            view.snapshot(path)
            print("wrote", path, "sim t", round(sim.t, 1), "over" if sim.over else "")
        return
    audio = None if a.no_audio else __import__("phase1.audio", fromlist=["Audio"]).Audio()
    view = View(sim, audio=audio, show=True)
    if a.recall is not None:
        def auto(ev):
            if sim.t >= a.recall and not sim.recall_used:
                sim.recall()
        app.Timer(interval=0.5, connect=auto, start=True)
    print(f"backend {backend}; audio {'on' if audio and audio.ok else 'silent'}. R = Recall.")
    app.run()
    if audio:
        audio.close()


if __name__ == "__main__":
    main()
