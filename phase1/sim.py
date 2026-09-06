"""Match loop. Owns World, the sensor rigs, the beliefs and the policies.

Order each tick: policy(belief) -> world moves -> sensors sample -> belief fuses.
The renderer and audio get Belief objects only. The one exception is
`reveal_after_end`, which hands truth to the display once the match is over.
"""
import math
import numpy as np
from . import tuning as T
from . import world as Wd
from .belief import Belief
from .sensors import SensorRig
from .policy import Policy


def _snap(t):
    return round(t / T.DT) * T.DT


class Sim:
    def __init__(self, seed=T.SEED):
        self.world = Wd.World()
        self.t = 0.0
        self.tick = 0
        self.over = False
        self.result = None
        places = {n: (c[0], c[1]) for n, c in Wd.CHAMBERS.items()}
        rng = np.random.default_rng(seed)
        self.beliefs = {}
        self.rigs = {}
        self.policies = {}
        for name, a in self.world.agents.items():
            kp = dict(places); kp["HOME"] = Wd.SHAFTS[name]
            self.beliefs[name] = Belief(name, a.x, a.y, a.heading, kp, np.random.default_rng(rng.integers(1 << 30)))
            self.rigs[name] = SensorRig(name, rng.integers(1 << 30))
            # the shaft beacon is survey-placed: its believed position is its true one
            self.beliefs[name].beacons[f"shaft_{name}"] = [Wd.SHAFTS[name][0], Wd.SHAFTS[name][1], -1.0]
        routes_p = {"out_A": Wd.ROUTES["player_out_A"], "A_to_B": Wd.ROUTES["player_A_to_B"],
                    "home_from_A": Wd.ROUTES["player_home_from_A"], "home_from_B": Wd.ROUTES["player_home_from_B"]}
        self.policies["player"] = Policy(self.beliefs["player"], routes_p, cautious=True)
        self.policies["rival"] = Policy(self.beliefs["rival"], {"out": Wd.ROUTES["rival_out"]}, cautious=False)
        self.recall_at = None
        self.recall_used = False
        self.spoof_armed_drop = None   # id of the first beacon dropped after SPOOF_AFTER_S
        self.echo_times = [_snap(2 * 60 + 15), _snap(2 * 60 + 16.5)]
        for et in self.echo_times:
            self.world.pending_sounds.append((et, Wd.ECHO_POS[0], Wd.ECHO_POS[1], "ping"))
        self.timeline = []      # (t, who, text) merged belief/truth log for the headless runner

    # ---- the single player input ----------------------------------------------------
    def recall(self):
        if self.recall_used or self.over:
            return False
        self.recall_used = True
        self.recall_at = self.t + T.RECALL_DELAY_S
        self.beliefs["player"].log.append((self.t, "RECALL sent"))
        return True

    # ---- one tick --------------------------------------------------------------------
    def step(self):
        if self.over:
            return
        self.tick += 1
        self.t = self.tick * T.DT
        w = self.world
        w.t = self.t; w.tick = self.tick
        if self.recall_at is not None and self.t >= self.recall_at:
            self.policies["player"].recall(self.t)
            self.recall_at = None
        self._script()
        for name, a in w.agents.items():
            b = self.beliefs[name]; pol = self.policies[name]; rig = self.rigs[name]
            if not a.alive or a.extracted:
                continue
            cmd = pol.step(self.t)
            a.move(cmd["heading"], cmd["speed"], T.DT)
            if cmd["drop"]:
                bid = w.drop_beacon(name)
                b.note_beacon_drop(bid, self.t)
                rig.beacons_in_range.add(bid)      # you are standing on it; no fix until you come back
            if cmd["ping"]:
                b.note_ping(self.t)
                w.log("ping", agent=name, x=a.x, y=a.y)
            w.step_loading(name, cmd["load"])
            returns = rig.sample(w, a, cmd, self.t)
            b.fuse(returns, self.t)
        w.step_hazards()
        w.pending_sounds = [p for p in w.pending_sounds if p[0] > self.t - T.DT]
        self._extraction()
        if self.t >= T.MATCH_SECONDS:
            self._finish("time")

    def _script(self):
        """The spoof: after SPOOF_AFTER_S, wait for the victim's next beacon drop, then
        when it has walked SPOOF_LIE - SPOOF_AHEAD cells past it, the clone appears
        SPOOF_AHEAD cells ahead. The lie is therefore SPOOF_LIE cells, back along the
        victim's own path."""
        w = self.world
        if w.spoof_done or self.t < T.SPOOF_AFTER_S:
            return
        b = self.beliefs["player"]; pol = self.policies["player"]; a = w.agents["player"]
        if not a.alive or pol.mode != "travel" or not b.beacon_order:
            return
        last = b.beacon_order[-1]
        if self.spoof_armed_drop is None:
            if b.dist_since_drop < 1.0:
                self.spoof_armed_drop = last
            return
        if last == self.spoof_armed_drop and b.dist_since_drop >= T.SPOOF_LIE_CELLS - T.SPOOF_AHEAD_CELLS:
            w.spoof("player", last)

    def _extraction(self):
        w = self.world
        if self.t < T.EXTRACT_WINDOW_OPENS:
            return
        for name, a in w.agents.items():
            sx, sy = Wd.SHAFTS[name]
            if a.alive and not a.extracted and math.hypot(a.x - sx, a.y - sy) < T.EXTRACT_RADIUS:
                a.extracted = True
                w.log("extracted", agent=name, cargo=a.cargo)
        if all((not a.alive) or a.extracted for a in w.agents.values()):
            self._finish("all resolved")

    def _finish(self, why):
        self.over = True
        p = self.world.agents["player"]
        outcome = "extracted" if p.extracted else ("destroyed" if not p.alive else "lost in the cave")
        self.result = {"why": why, "player": outcome, "cargo": p.cargo if p.extracted else 0,
                       "recall_used": self.recall_used}
        self.world.log("end", **self.result)

    # ---- truth, only after the end ----------------------------------------------------
    def reveal_after_end(self):
        assert self.over, "truth is never rendered during the run"
        w = self.world
        ys, xs = np.nonzero(Wd.GRID == 0)
        # only rock cells adjacent to free space: the true wall outline
        pad = np.pad(Wd.FREE, 1)
        edge = (pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]) & (Wd.GRID == 0)
        wy, wx = np.nonzero(edge)
        return {"walls": np.column_stack([wx + 0.5, wy + 0.5]),
                "flooded": np.column_stack(np.nonzero(Wd.GRID == 2)[::-1]) + 0.5,
                "agents": {n: (a.x, a.y, a.alive, a.extracted) for n, a in w.agents.items()},
                "beacons": {bid: (b.x, b.y, b.owner) for bid, b in w.beacons.items()},
                "ancient": (w.ancient.x, w.ancient.y, T.ANCIENT_RADIUS),
                "deposits": dict(w.deposits),
                "truth_trail": self.truth_trail}

    # ---- headless helpers ----------------------------------------------------------------
    truth_trail = None


def run_headless(recall_at=None, seed=T.SEED, report_every=30.0, quiet=False):
    """Run a full match with no display. Prints a merged timeline and, for tuning
    only, the truth-vs-belief pose error. That error line never leaves this function."""
    s = Sim(seed)
    s.truth_trail = {"player": [], "rival": []}
    next_report = 0.0
    seen = {"player": 0, "rival": 0}
    while not s.over:
        if recall_at is not None and s.t >= recall_at and not s.recall_used:
            s.recall()
        s.step()
        if s.tick % 10 == 0:
            for n, a in s.world.agents.items():
                s.truth_trail[n].append((a.x, a.y, s.t))
        if s.t >= next_report:
            next_report += report_every
            for n in ("player", "rival"):
                a = s.world.agents[n]; b = s.beliefs[n]
                err = math.hypot(a.x - b.x, a.y - b.y)
                herr = math.degrees((b.theta - a.heading + math.pi) % (2 * math.pi) - math.pi)
                s.timeline.append((s.t, n, f"[truth] pos err {err:.1f} hdg err {herr:.1f} sigma {b.sigma_pos():.1f} "
                                            f"truth ({a.x:.0f},{a.y:.0f}) belief ({b.x:.0f},{b.y:.0f}) mode {s.policies[n].mode} pts {b.n}"))
        for n in ("player", "rival"):
            lg = s.beliefs[n].log
            for (t, txt) in lg[seen[n]:]:
                s.timeline.append((t, n, txt))
            seen[n] = len(lg)
    for (t, kind, kw) in s.world.events:
        s.timeline.append((t, "TRUTH", f"{kind} {kw}"))
    s.timeline.sort(key=lambda e: e[0])
    if not quiet:
        for (t, who, txt) in s.timeline:
            print(f"{int(t)//60}:{t%60:04.1f} {who:6s} {txt}")
        print("RESULT", s.result)
    return s


if __name__ == "__main__":
    import sys
    ra = float(sys.argv[1]) if len(sys.argv) > 1 else None
    run_headless(recall_at=ra)
