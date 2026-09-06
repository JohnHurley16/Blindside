"""Every dimension of the agent, parametric. Units: metres. Forward is +X, up is +Z,
left is +Y (Blender convention).

The silhouette is always honest (DESIGN.html): chassis class and mounted modules
determine the outline. Skins may only change materials, wear, and light colour.
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Dict

Vec = Tuple[float, float, float]


@dataclass
class LegSpec:
    hip: Vec                 # hip position on the hull, body frame
    side: int                # +1 left, -1 right
    femur: float = 0.20      # upper leg length. Tibia length follows from ride height
    knee_rise: float = -0.14 # knee below the hip (negative): a dog
    knee_back: float = -0.11 # knee behind the hip (negative): knees back, like a robot dog
    foot_out: float = 0.0    # foot outboard (+) or inboard (-) of the flexion pivot
    foot_fwd: float = 0.0    # foot ahead of the hip in the neutral stance


@dataclass
class SlotSpec:
    name: str
    pos: Vec                 # body frame
    facing: Vec              # unit-ish direction the module points
    size: str = "m"          # s / m / l: which modules fit


@dataclass
class ChassisSpec:
    name: str
    hull: Vec                # length, width, height of the main hull box
    hull_bevel: float
    ride_height: float       # hull underside above ground at rest
    legs: List[LegSpec]
    slots: List[SlotSpec]
    head_neck: float         # neck length
    head_radius: float
    head_pos: Vec            # neck root on the hull, body frame
    spine_rail: bool = True
    noise_label: str = "quiet"


@dataclass
class ModuleSpec:
    name: str
    size: str
    label: str


@dataclass
class Skin:
    name: str = "team_a"
    base: Vec = (0.62, 0.60, 0.55)          # top shell: pale, so the machine reads in the dark
    chassis: Vec = (0.05, 0.055, 0.065)     # lower body and blades: graphite
    accent: Vec = (0.85, 0.45, 0.10)        # stripes and pads
    bare: Vec = (0.45, 0.45, 0.47)          # worn-through metal
    light: Vec = (0.2, 0.9, 1.0)            # emissive strips and the eye
    light_strength: float = 8.0
    wear: float = 0.35                      # 0 factory fresh .. 1 salvage
    grime: float = 0.4
    markings: str = "team_a"


@dataclass
class AgentConfig:
    chassis: str = "surveyor"
    modules: Dict[str, str] = field(default_factory=dict)   # slot name -> module name
    skin: Skin = field(default_factory=Skin)


# ---- chassis classes ------------------------------------------------------------------
def _quad_legs(L, W, front_x, rear_x, **kw):
    legs = []
    for x in (front_x, rear_x):
        for side in (1, -1):
            legs.append(LegSpec(hip=(x, side * W / 2, -0.01), side=side, foot_fwd=(0.02 if x > 0 else -0.03), **kw))
    return legs


def _hex_legs(L, W, **kw):
    legs = []
    for i, x in enumerate((L * 0.36, 0.0, -L * 0.36)):
        for side in (1, -1):
            legs.append(LegSpec(hip=(x, side * W / 2, -0.01), side=side, foot_fwd=(0.03, 0.0, -0.03)[i], **kw))
    return legs


CHASSIS: Dict[str, ChassisSpec] = {
    "scout": ChassisSpec(
        name="scout", hull=(0.40, 0.15, 0.085), hull_bevel=0.03, ride_height=0.25,
        legs=_quad_legs(0.40, 0.15, 0.15, -0.15, femur=0.15, knee_rise=-0.11, knee_back=-0.08),
        slots=[SlotSpec("eye", (0, 0, 0), (1, 0, 0), "s"), SlotSpec("top_r", (-0.12, 0, 0.055), (0, 0, 1), "m"),
               SlotSpec("side_l", (0.0, 0.075, -0.012), (0, 1, 0), "s"), SlotSpec("side_r", (0.0, -0.075, -0.012), (0, -1, 0), "s")],
        head_neck=0.07, head_radius=0.045, head_pos=(0.21, 0, 0.02), noise_label="quiet"),
    "surveyor": ChassisSpec(
        name="surveyor", hull=(0.58, 0.21, 0.12), hull_bevel=0.045, ride_height=0.32,
        legs=_quad_legs(0.58, 0.21, 0.21, -0.21),
        slots=[SlotSpec("face", (0, 0, 0), (1, 0, 0), "m"), SlotSpec("eye", (0, 0, 0), (1, 0, 0), "s"),
               SlotSpec("top_m", (-0.10, 0, 0.085), (0, 0, 1), "m"), SlotSpec("top_r", (-0.22, 0, 0.085), (0, 0, 1), "m"),
               SlotSpec("side_l", (0.0, 0.105, -0.015), (0, 1, 0), "s"), SlotSpec("side_r", (0.0, -0.105, -0.015), (0, -1, 0), "s"),
               SlotSpec("belly", (-0.02, 0, -0.06), (0, 0, -1), "l")],
        head_neck=0.10, head_radius=0.065, head_pos=(0.31, 0, 0.03), noise_label="moderate"),
    "hauler": ChassisSpec(
        name="hauler", hull=(0.90, 0.32, 0.18), hull_bevel=0.06, ride_height=0.34,
        legs=_hex_legs(0.90, 0.32, femur=0.22, knee_rise=-0.15, knee_back=-0.12),
        slots=[SlotSpec("face", (0, 0, 0), (1, 0, 0), "m"), SlotSpec("eye", (0, 0, 0), (1, 0, 0), "s")] +
              [SlotSpec(f"top_{i}", (0.1 - 0.15 * i, 0, 0.115), (0, 0, 1), "m") for i in range(4)] +
              [SlotSpec("side_l", (0.1, 0.16, -0.02), (0, 1, 0), "s"), SlotSpec("side_r", (0.1, -0.16, -0.02), (0, -1, 0), "s"),
               SlotSpec("belly", (-0.05, 0, -0.09), (0, 0, -1), "l")],
        head_neck=0.12, head_radius=0.08, head_pos=(0.45, 0, 0.04), noise_label="loud"),
    "swimmer": ChassisSpec(
        name="swimmer", hull=(0.66, 0.18, 0.10), hull_bevel=0.07, ride_height=0.27,
        legs=_quad_legs(0.66, 0.18, 0.22, -0.22, femur=0.17, knee_rise=-0.12, knee_back=-0.10),
        slots=[SlotSpec("face", (0, 0, 0), (1, 0, 0), "m"), SlotSpec("eye", (0, 0, 0), (1, 0, 0), "s"),
               SlotSpec("side_l", (0.04, 0.09, -0.012), (0, 1, 0), "s"), SlotSpec("side_r", (0.04, -0.09, -0.012), (0, -1, 0), "s"),
               SlotSpec("top_r", (-0.18, 0, 0.075), (0, 0, 1), "m"), SlotSpec("belly", (0.0, 0, -0.05), (0, 0, -1), "l")],
        head_neck=0.08, head_radius=0.06, head_pos=(0.35, 0, 0.0), spine_rail=False, noise_label="quiet"),
}

# ---- modules ----------------------------------------------------------------------------
MODULES: Dict[str, ModuleSpec] = {
    "passive_acoustic": ModuleSpec("passive_acoustic", "s", "hydrophone vanes"),
    "active_sonar": ModuleSpec("active_sonar", "m", "sonar transducer dome"),
    "beacon_rack": ModuleSpec("beacon_rack", "m", "rack of drop beacons"),
    "cargo_bay": ModuleSpec("cargo_bay", "l", "belly cargo bay"),
    "optical": ModuleSpec("optical", "s", "camera and lamp"),
    "magnetometer": ModuleSpec("magnetometer", "m", "anomaly boom"),
    "structural_monitor": ModuleSpec("structural_monitor", "s", "rock microphone spikes"),
}

SIZE_ORDER = {"s": 0, "m": 1, "l": 2}
MODULES["structural_monitor"].size = "s"


def default_config(chassis="surveyor"):
    """A sensible loadout for a first look at each class."""
    loadouts = {
        # scout: quiet. Listens, looks, carries nothing, no sonar to give it away
        "scout": {"eye": "optical", "side_l": "passive_acoustic", "side_r": "passive_acoustic", "top_r": "structural_monitor"},
        "surveyor": {"face": "active_sonar", "eye": "optical", "top_m": "magnetometer", "top_r": "beacon_rack",
                     "side_l": "passive_acoustic", "side_r": "passive_acoustic", "belly": "cargo_bay"},
        "hauler": {"face": "active_sonar", "eye": "optical", "top_0": "structural_monitor", "top_1": "magnetometer",
                   "top_2": "beacon_rack", "top_3": "beacon_rack", "side_l": "passive_acoustic",
                   "side_r": "passive_acoustic", "belly": "cargo_bay"},
        "swimmer": {"face": "active_sonar", "side_l": "passive_acoustic", "side_r": "passive_acoustic",
                    "top_r": "beacon_rack", "belly": "cargo_bay"},
    }
    return AgentConfig(chassis=chassis, modules=loadouts[chassis])


def validate(cfg: AgentConfig):
    ch = CHASSIS[cfg.chassis]
    slots = {s.name: s for s in ch.slots}
    for slot, mod in cfg.modules.items():
        if slot not in slots:
            raise ValueError(f"{cfg.chassis} has no slot {slot}")
        if SIZE_ORDER[MODULES[mod].size] > SIZE_ORDER[slots[slot].size]:
            raise ValueError(f"{mod} ({MODULES[mod].size}) does not fit slot {slot} ({slots[slot].size})")
    return ch
