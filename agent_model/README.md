# agent_model — the agent, parametric, in Blender

Python that builds the walker in Blender from a handful of numbers, rigs it with IK,
animates it from a one-line motion script, and renders it in a cave.

## Run

With a Blender install (Windows, any recent 4.x/5.x):

    blender -b -P agent_model/run.py -- --chassis surveyor --out renders/surveyor.png

With the pip module instead (`pip install bpy`, Python 3.11):

    python -m agent_model.run --chassis surveyor --out renders/surveyor.png

Useful flags:

| flag | what |
|---|---|
| `--chassis scout\|surveyor\|hauler\|swimmer` | class; sets hull, leg count, slots |
| `--modules top_f=active_sonar,belly=cargo_bay` | loadout by slot; silhouette is honest |
| `--skin team_a\|team_b\|salvage\|fresh` `--wear 0.6` `--light 1,0.5,0.2` | materials only; never the outline |
| `--move "stand 0.3; walk 3 0.5 20 trot; look 1.5,1,0.3 ride"` | motion script, see below |
| `--out still.png` `--pose-frame 40` | render one frame (default: mid-timeline) |
| `--anim renders/walk_ --frames 1,72,2` | render frames `walk_0001.png`... |
| `--save agent.blend` | write a .blend to open interactively |
| `--samples 96 --res 1600x1000 --cam -38,14,2.1` | quality and camera (azimuth, elevation, distance) |

## How it moves

`motion.Mover` is the whole movement API. You say what the body does; the gait
generator places the feet and Blender's IK solves the legs.

    m = Mover(built)
    m.stand(0.5)
    m.look_at((1.4, -0.8, 0.3), over=0.4, ride=True)   # head target rides with the body
    m.walk(3.0, speed=0.5, turn=20, gait="trot")        # seconds, m/s, deg/s
    m.crouch(0.06)
    m.finish()

Gaits: `trot` (diagonal pairs), `walk` (one foot at a time), `creep` (slow, three
feet always down), `bound`. Six-legged chassis use the tripod / wave equivalents.
Feet plant and stay planted while the body moves over them; each swing aims at
where the body will be at touchdown, so turning arcs work without special cases.

The same verbs are available as a script string for the CLI:
`stand S; walk S SPEED TURN GAIT; look X,Y,Z [OVER] [ride]; ahead; crouch DZ [OVER]`.

## Rig conventions

- `AGENT_RIG` (armature object) **is the body**. Root motion is its location/rotation.
- `FOOT.<i>` empties are the IK targets, in world space. Move one and the leg follows.
- `pole.<i>` bones are children of each hip, so the knee plane turns with the hip.
- Hips use a locked track (yaw only) to their foot; femur+tibia are a 2-bone IK chain.
- `LOOK` empty: the neck damped-tracks it, limited so the head cannot spin round.
- `arm["leg_neutral"]` holds each foot's neutral position relative to the body.

Open the `.blend`, grab a `FOOT.*` empty, and drag: that is the whole rig.

## Files

| file | role |
|---|---|
| `params.py` | chassis classes, leg geometry, slots, modules, skins. Change numbers here. |
| `geometry.py` | mesh primitives with transforms baked in |
| `materials.py` | painted metal with procedural wear and grime, rubber, lens, emissive, wet rock |
| `build.py` | assembles meshes, armature, IK, head lamp; returns the handles motion needs |
| `motion.py` | gait generator and the `Mover` API |
| `render.py` | cave, lights, camera, Cycles settings, still / animation output |
| `run.py` | CLI |

## Anatomy: every part has a job

Modelled on real quadruped robots (legs dominate, actuators visible at the hips, a broad
upper leg housing the knee drive, thin lower leg, rubber ball feet, knees back) and on
what makes film droids read: one silhouette, one dominant eye, two-tone panels with a
single accent, lived-in wear, every detail a mechanism, and a head on a real joint.

| part | job | where |
|---|---|---|
| lower chassis | sealed body: batteries, computer, IMU (dead reckoning lives here) | graphite, faceted |
| top shell | removable cover with battery and compute hatches and latches | pale, so it reads in the dark |
| deck rail, handle | hardpoints; the handle is the recovery hook (wrecks get salvaged) | top |
| hip stacks | abduction motor drum on the chassis corner; flexion + knee motors at the femur top | four corners |
| femur blade | broad upper leg housing the knee belt drive under a cover | pale |
| tibia | thin tapered strut, ankle, rubber ball foot | dark |
| pan-tilt head | pan drum on a chassis prow bracket, yoke, tilt motor one side, bearing the other; payload centred on the tilt axis | front |
| active sonar | forward-looking transducer strip | `face` slot on the head |
| optical | lamp reflector + lens and a camera; the only forward emission | `eye` slot on the head |
| passive acoustic | hydrophone line array along each flank; a line of elements gives a bearing | `side_l` / `side_r` at the seam |
| beacon rack | dispenser magazine with a chute at the tail edge | rear deck |
| magnetometer | pod on a hinged boom, away from the actuators' magnetic noise | rear deck |
| structural monitor | geophone collars at the ankles plus a conditioner box | ankles + deck |
| cargo bay | belly pannier with a hatch | `belly` slot |
| comms mast | acoustic modem to the surface | tail corner |
| cooling grilles, E-stop, charge port, cables | what a real machine has | flanks, rear |
| running lights | readable in the dark from its own light; part of the honest silhouette | flanks |

A Scout with no optical module has no lamp: a quiet loadout looks quiet. The Hauler is
the same anatomy with six legs.

