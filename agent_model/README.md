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

| part | job | where |
|---|---|---|
| hull | sealed pressure body; the deck rail is the module mount | lofted, tapered |
| sensor head | turns to attend to things; carries the face slots | on the neck, damped-tracks `LOOK` |
| active sonar | forward-looking transducer strip | `face` slot, across the head |
| optical | lamp reflector + lens, small camera beside it; the only light the agent emits forward | `eye` slot, under the sonar strip |
| passive acoustic | hydrophone line array; a line of elements is how you get a bearing | `side_l` / `side_r`, along each flank |
| beacon rack | dispenser magazine with a chute; beacons drop behind you | rear deck |
| magnetometer | sensor pod on a boom, away from the leg actuators' magnetic noise | rear deck, boom aft and up |
| structural monitor | contact geophone pucks at the ankles (the feet already touch rock) plus a conditioner box | ankles + a deck slot |
| cargo bay | belly bay with a hatch | `belly` slot |
| comms mast | acoustic modem to the surface | tail |
| conduits | power to the hip actuators | hull to each hip |
| running lights | readable in the dark from its own light; part of the honest silhouette | low on each flank |
| legs | hex-section struts, linear actuators on femur and tibia, ankle joint, rubber pad | IK-driven |

Leg configuration is a few numbers per class: `knee_rise` below the hip reads as a dog,
above reads as a spider. Quadrupeds are dog-like; the Hauler is a six-legged insect.
A Scout with no optical module has no lamp: a quiet loadout looks quiet.
