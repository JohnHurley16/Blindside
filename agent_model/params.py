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
    coxa: float = 0.05       # horizontal hip segment, outward
    femur: float = 0.16      # upper segment, outward and up. Tibia length follows from ride height.
    splay: float = 0.05      # knee outboard of the coxa tip
    knee_rise: float = -0.09 # knee above (+) or below (-) the hip. Below reads as a dog, above as a spider
    knee_back: float = -0.10 # knee behind (-) or ahead (+) of the hip
    foot_out: float = 0.0    # foot outboard (+) or inboard (-) of the knee
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
    base: Vec = (0.035, 0.045, 0.06)        # painted hull: deep blue-black
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
            legs.append(LegSpec(hip=(x, side * W / 2, -0.02), side=side, foot_fwd=(0.06 if x > 0 else 0.0), **kw))
    return legs


def _hex_legs(L, W, **kw):
    legs = []
    for i, x in enumerate((L * 0.36, 0.0, -L * 0.36)):
        for side in (1, -1):
            legs.append(LegSpec(hip=(x, side * W / 2, -0.02), side=side, foot_fwd=(0.06, 0.0, -0.06)[i], **kw))
    return legs


CHASSIS: Dict[str, ChassisSpec] = {
    "scout": ChassisSpec(
        name="scout", hull=(0.46, 0.16, 0.10), hull_bevel=0.03, ride_height=0.17,
        legs=_quad_legs(0.42, 0.18, 0.14, -0.14, coxa=0.035, femur=0.11, splay=0.04, knee_rise=-0.06, knee_back=-0.07),
        slots=[SlotSpec("eye", (0, 0, 0), (1, 0, 0), "s"), SlotSpec("top_r", (-0.12, 0, 0.05), (0, 0, 1), "m"),
               SlotSpec("side_l", (0.0, 0.08, -0.01), (0, 1, 0), "s"), SlotSpec("side_r", (0.0, -0.08, -0.01), (0, -1, 0), "s")],
        head_neck=0.07, head_radius=0.045, head_pos=(0.21, 0, 0.02), noise_label="quiet"),
    "surveyor": ChassisSpec(
        name="surveyor", hull=(0.66, 0.26, 0.15), hull_bevel=0.045, ride_height=0.24,
        legs=_quad_legs(0.62, 0.28, 0.20, -0.20),
        slots=[SlotSpec("face", (0, 0, 0), (1, 0, 0), "m"), SlotSpec("eye", (0, 0, 0), (1, 0, 0), "s"),
               SlotSpec("top_m", (0.02, 0, 0.075), (0, 0, 1), "m"), SlotSpec("top_r", (-0.2, 0, 0.075), (0, 0, 1), "m"),
               SlotSpec("side_l", (0.02, 0.125, 0.0), (0, 1, 0), "s"), SlotSpec("side_r", (0.02, -0.125, 0.0), (0, -1, 0), "s"),
               SlotSpec("belly", (-0.02, 0, -0.075), (0, 0, -1), "l")],
        head_neck=0.10, head_radius=0.065, head_pos=(0.31, 0, 0.03), noise_label="moderate"),
    "hauler": ChassisSpec(
        name="hauler", hull=(0.95, 0.38, 0.24), hull_bevel=0.06, ride_height=0.24,
        legs=_hex_legs(0.90, 0.42, coxa=0.06, femur=0.22, splay=0.17, knee_rise=0.03, knee_back=0.0, foot_out=-0.04),
        slots=[SlotSpec("face", (0, 0, 0), (1, 0, 0), "m"), SlotSpec("eye", (0, 0, 0), (1, 0, 0), "s")] +
              [SlotSpec(f"top_{i}", (0.22 - 0.17 * i, 0, 0.12), (0, 0, 1), "m") for i in range(4)] +
              [SlotSpec("side_l", (0.1, 0.18, 0.0), (0, 1, 0), "s"), SlotSpec("side_r", (0.1, -0.18, 0.0), (0, -1, 0), "s"),
               SlotSpec("belly", (-0.05, 0, -0.12), (0, 0, -1), "l")],
        head_neck=0.12, head_radius=0.08, head_pos=(0.45, 0, 0.04), noise_label="loud"),
    "swimmer": ChassisSpec(
        name="swimmer", hull=(0.74, 0.20, 0.13), hull_bevel=0.07, ride_height=0.19,
        legs=_quad_legs(0.70, 0.22, 0.20, -0.22, coxa=0.04, femur=0.15, splay=0.13, knee_rise=0.0, knee_back=0.0, foot_out=-0.04),
        slots=[SlotSpec("face", (0, 0, 0), (1, 0, 0), "m"), SlotSpec("eye", (0, 0, 0), (1, 0, 0), "s"),
               SlotSpec("side_l", (0.04, 0.095, 0.0), (0, 1, 0), "s"), SlotSpec("side_r", (0.04, -0.095, 0.0), (0, -1, 0), "s"),
               SlotSpec("top_r", (-0.16, 0, 0.065), (0, 0, 1), "m"), SlotSpec("belly", (0.0, 0, -0.065), (0, 0, -1), "l")],
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
        "surveyor": {"face": "active_sonar", "eye": "optical", "top_m": "beacon_rack", "top_r": "magnetometer",
                     "side_l": "passive_acoustic", "side_r": "passive_acoustic", "belly": "cargo_bay"},
        "hauler": {"face": "active_sonar", "eye": "optical", "top_0": "beacon_rack", "top_1": "beacon_rack",
                   "top_2": "structural_monitor", "top_3": "magnetometer", "side_l": "passive_acoustic",
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
