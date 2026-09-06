"""What an agent thinks. Assembled only from sensor returns.

**This package must never import `phase1.truth`.** A policy reads this object and
nothing else, so anything that leaks in here leaks into the policy.
"""
from __future__ import annotations

import math

import numpy as np

from .. import geometry as G
from .. import tuning as T
from ..point_source import PointSource
from ..sensing.returns import (
    BearingReturn,
    BeaconFixReturn,
    CargoReturn,
    OdometryReturn,
    RangeBearingReturn,
    Return,
)
from ..sound_character import SoundCharacter
from .bearing_tracker import BearingTracker
from .contact import Contact
from .fix_record import FixRecord
from .heard_sound import HeardSound
from .known_beacon import KnownBeacon
from .own_ping import OwnPing
from .point_cloud import PointCloud
from .pose_correction import PoseCorrection


class Belief:
    """Pose estimate, map, contacts, beacons, inventory. Frequently wrong."""

    def __init__(self, name: str, x: float, y: float, heading: float,
                 known_places: dict[str, tuple[float, float]],
                 rng: np.random.Generator) -> None:
        self.name: str = name
        self.x: float = float(x)
        self.y: float = float(y)
        self.theta: float = float(heading)
        self.rng: np.random.Generator = rng
        self.known_places: dict[str, tuple[float, float]] = dict(known_places)

        # uncertainty
        self.dist_since_fix: float = 0.0
        self.ticks_since_fix: int = 0
        self.dist_total: float = 0.0          # monotonic odometry integral
        self.sigma_theta: float = T.EST_HEADING_SIGMA_AFTER_FIX
        self.epoch_t: float = 0.0
        self.epoch_x: float = self.x
        self.epoch_y: float = self.y

        # map
        self.cloud: PointCloud = PointCloud(T.MAX_POINTS, rng)
        self.trail: list[tuple[float, float, float]] = [(self.x, self.y, 0.0)]

        # contacts, beacons, inventory
        self.contacts: list[Contact] = []
        self.beacons: dict[str, KnownBeacon] = {}
        self.beacon_order: list[str] = []
        self.cargo: int = 0
        self.dist_since_drop: float = 0.0
        self.ticks_since_ping: int = 10 ** 6

        # steering input and display streams, all belief-derived
        self.recent_near: list[tuple[float, float, float]] = []
        self.own_pings: list[OwnPing] = []
        self.heard: list[HeardSound] = []
        self.signature: HeardSound | None = None
        # What it has worked out about things it can only hear. Bearings crossed over
        # time give a position; until it has moved enough, these stay empty.
        self.hazard_track: BearingTracker = BearingTracker(memory_seconds=240.0)
        self.rival_track: BearingTracker = BearingTracker(memory_seconds=70.0)
        self.last_fix: FixRecord | None = None
        self.fixes: list[FixRecord] = []
        self.log: list[tuple[float, str]] = []

    # ---- uncertainty -------------------------------------------------------------------
    def sigma_along(self) -> float:
        return T.EST_SIGMA_AFTER_FIX + T.EST_SIGMA_ALONG_PER_CELL * self.dist_since_fix

    def sigma_cross(self) -> float:
        return T.EST_SIGMA_AFTER_FIX + 0.5 * self.dist_since_fix * self.sigma_theta

    def sigma_pos(self) -> float:
        return math.hypot(self.sigma_along(), self.sigma_cross())

    def ellipse(self) -> tuple[float, float, float]:
        """(along, cross, angle) for the uncertainty ellipse, in the belief frame."""
        vx, vy = self.x - self.epoch_x, self.y - self.epoch_y
        angle = math.atan2(vy, vx) if math.hypot(vx, vy) > 1.0 else self.theta
        return self.sigma_along(), self.sigma_cross(), angle

    # ---- fusion -------------------------------------------------------------------------
    def fuse(self, returns: list[Return], t: float) -> None:
        self.ticks_since_fix += 1
        self.ticks_since_ping += 1
        for r in returns:
            match r:
                case OdometryReturn():
                    self._integrate(r, t)
                case RangeBearingReturn():
                    self._add_point(r, t)
                case BearingReturn():
                    self._add_contact(r, t)
                case BeaconFixReturn():
                    self._apply_fix(r, t)
                case CargoReturn():
                    if r.count != self.cargo:
                        self.cargo = r.count
                        self.log.append((t, f"cargo now {self.cargo}"))
        self.recent_near = [h for h in self.recent_near if t - h[0] < 1.5]
        self.hazard_track.forget_before(t)
        self.rival_track.forget_before(t)
        cutoff = t - T.CONTACT_FADE_S
        self.contacts = [c for c in self.contacts if c.t_last > cutoff]

    def _integrate(self, r: OdometryReturn, t: float) -> None:
        self.theta = G.wrap(self.theta + r.turn)
        self.x += math.cos(self.theta) * r.forward
        self.y += math.sin(self.theta) * r.forward
        self.dist_since_fix += r.forward
        self.dist_since_drop += r.forward
        self.dist_total += r.forward
        self.sigma_theta += T.EST_SIGMA_HEADING_RAD_PER_CELL * r.forward
        if r.forward > 0.0 and G.dist(self.x, self.y, self.trail[-1][0], self.trail[-1][1]) > 0.5:
            self.trail.append((self.x, self.y, t))

    def body_to_belief(self, r: float, bearing_body: float) -> tuple[float, float]:
        a = self.theta + bearing_body
        return self.x + math.cos(a) * r, self.y + math.sin(a) * r

    def _add_point(self, r: RangeBearingReturn, t: float) -> None:
        wx, wy = self.body_to_belief(r.range, r.bearing_body)
        if r.source is PointSource.NEAR:
            self.recent_near.append((t, wx, wy))
        self.cloud.add(wx, wy, r.quality, t, r.source, T.WALL_POINT_HEIGHT)

    def _add_contact(self, r: BearingReturn, t: float) -> None:
        bw = G.wrap(self.theta + r.bearing_body)
        heard = HeardSound(t, bw, r.quality, r.character)
        if r.character is SoundCharacter.SIGNATURE:
            self.signature = heard
            self.hazard_track.add(self.x, self.y, bw, r.quality, t)
            self.hazard_track.invalidate()
            return
        if r.character is SoundCharacter.PING and r.quality > 0.25:
            self.rival_track.add(self.x, self.y, bw, r.quality, t)
            self.rival_track.invalidate()
        self.heard.append(heard)
        for c in self.contacts:
            if c.matches(bw, t, T.CONTACT_MERGE_DEG, T.CONTACT_MERGE_S):
                c.absorb(bw, r.quality, r.character, t)
                return
        self.contacts.append(Contact(bw, r.quality, r.character, t, t))
        self.log.append((t, f"new contact {r.character} brg {math.degrees(bw):.0f} q {r.quality:.2f}"))

    # ---- fixes ---------------------------------------------------------------------------
    def _apply_fix(self, r: BeaconFixReturn, t: float) -> None:
        known = self.beacons.get(r.beacon_id)
        if known is None:
            return                                   # a beacon we never recorded is not trusted
        pre_x, pre_y = self.x, self.y
        sigma_before = self.sigma_pos()

        # Position implied by the recorded beacon position and the measured offset.
        est_x = known.x - math.cos(self.theta + r.bearing_body) * r.range
        est_y = known.y - math.sin(self.theta + r.bearing_body) * r.range

        # A single beacon gives position, not heading. But the direction from the
        # epoch to the fix, compared with the direction we thought we had travelled,
        # is evidence about heading error, so take a fraction of it. This is the
        # cheap stand-in for terrain-relative matching, and it is what makes the map
        # rotate back rather than merely slide.
        dtheta = 0.0
        vpx, vpy = pre_x - self.epoch_x, pre_y - self.epoch_y
        vfx, vfy = est_x - self.epoch_x, est_y - self.epoch_y
        if math.hypot(vpx, vpy) > 3.0 and math.hypot(vfx, vfy) > 3.0:
            raw = G.wrap(math.atan2(vfy, vfx) - math.atan2(vpy, vpx))
            dtheta = G.clamp(raw, -math.radians(25.0), math.radians(25.0)) * T.HEADING_FIX_GAIN

        self.theta = G.wrap(self.theta + dtheta)
        post_x = known.x - math.cos(self.theta + r.bearing_body) * r.range
        post_y = known.y - math.sin(self.theta + r.bearing_body) * r.range

        correction = PoseCorrection.between(self.epoch_t, t, self.epoch_x, self.epoch_y,
                                            pre_x, pre_y, post_x, post_y, dtheta)
        self._relax(correction, exclude=r.beacon_id)
        self.x, self.y = post_x, post_y

        record = FixRecord(t, r.beacon_id, pre_x, pre_y, post_x, post_y, dtheta, sigma_before)
        self.last_fix = record
        self.fixes.append(record)
        self.log.append((t, f"fix {r.beacon_id} jump {record.jump:.1f} "
                            f"dtheta {math.degrees(dtheta):.1f} surprise {record.surprise:.1f}x"))

        self.epoch_t = t
        self.epoch_x, self.epoch_y = post_x, post_y
        self.dist_since_fix = 0.0
        self.ticks_since_fix = 0
        self.sigma_theta = T.EST_HEADING_SIGMA_AFTER_FIX

    def _relax(self, correction: PoseCorrection, exclude: str) -> None:
        """Drag the map, the trail, the other beacons and the contacts along."""
        self.cloud.relax(correction)
        if self.trail:
            tx = np.array([p[0] for p in self.trail])
            ty = np.array([p[1] for p in self.trail])
            tt = np.array([p[2] for p in self.trail])
            nx, ny = correction.apply(tx, ty, tt)
            self.trail = list(zip(nx.tolist(), ny.tolist(), tt.tolist()))
        for bid, known in self.beacons.items():
            if known.t_placed > correction.epoch_t and bid != exclude and not known.truth_anchor:
                known.x, known.y = correction.apply_one(known.x, known.y, known.t_placed)
        for c in self.contacts:
            c.rotate(correction.dtheta, correction.weight_at(c.t_last))
        self.hazard_track.relax(correction)
        self.rival_track.relax(correction)

    # ---- actions the policy tells us about -------------------------------------------------
    def note_beacon_drop(self, beacon_id: str, t: float) -> None:
        self.beacons[beacon_id] = KnownBeacon(beacon_id, self.x, self.y, t)
        self.beacon_order.append(beacon_id)
        self.dist_since_drop = 0.0
        self.log.append((t, f"drop {beacon_id}"))

    def note_surveyed_beacon(self, beacon_id: str, x: float, y: float) -> None:
        """The shaft: placed by survey, so its recorded position is its true one."""
        self.beacons[beacon_id] = KnownBeacon(beacon_id, x, y, -1.0, truth_anchor=True)

    def note_ping(self, t: float) -> None:
        self.ticks_since_ping = 0
        self.own_pings.append(OwnPing(t, self.x, self.y, self.theta))
        self.log.append((t, "ping"))

    def points_ahead(self, radius: float = 12.0) -> int:
        return self.cloud.count_ahead(self.x, self.y, math.cos(self.theta),
                                      math.sin(self.theta), radius)
