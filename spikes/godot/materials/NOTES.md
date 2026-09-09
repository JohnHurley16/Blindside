# Spike — a procedural PBR material library, and whether "photoreal" is reachable

**The ask.** DESIGN-PRINCIPLES §6, today:

> *"yeah, j agree the materials and underfoot stuff sucks right now. start working on
> that. it needs to look photoreal"*

**What this directory is.** The material system on its own, with no level generation in it,
so it can be judged and tuned as a thing and then adopted by both environment spikes. One
shader family, twenty-seven materials, a testbed that shows them on four forms under the
three lighting conditions this game actually has, a wetness slider that drives every
material at once, and a calibration view that makes the physics checkable rather than a
matter of taste.

**Answer, honestly.**

* **The underfoot case is transformed.** Aggregate and ballast now read as loose stone with
  real depth, half-buried, each stone its own value, with the gaps between them closing.
  That was the designer's named case and it is the strongest result here.
* **The discipline is now enforceable.** Every material's albedo is measured off a
  screenshot in linear units and checked against a stated range. `calib.py` passes on all
  27. That check is worth more than any of the tuning, because it is the thing that stops
  the next pass from drifting.
* **The cost is the problem.** The natural materials are 28–48 ms at 1080p when they cover
  the frame at close range. The dominant cost is that the parallax march evaluates a 3D
  voronoi, and §4 has the numbers and the fix.
* **Shallow water works; deep water and iron do not.** Shallow water over silt reads
  correctly — absorption, refraction, a waterline on anything standing in it. Deep water and
  bare iron both fail for the same reason, and it is a design finding rather than a shader
  bug: under one lamp with zero ambient there is nothing for a mirror or a metal to
  reflect. See §7.

Nothing outside `spikes/godot/materials/` was modified. Nothing was committed.

---

## 1. How to run it

```
GODOT="C:/Users/jackh/Downloads/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64.exe"

"$GODOT" --path spikes/godot/materials --resolution 1920x1080            # interactive
"$GODOT" --path spikes/godot/materials --resolution 1280x720 -- --shots  # the 36 PNGs, ~70 s
"$GODOT" --path spikes/godot/materials --resolution 1280x720 -- --cost   # the cost table
"$GODOT" --path spikes/godot/materials --resolution 1280x720 -- --expo   # the ART 2.2 ratios
"$GODOT" --path spikes/godot/materials --resolution 1280x720 -- --diag   # light budget probe
./check.sh          # parse/compile gate, headless
python lum.py       # the ART 2.9 exposure contract, on LINEARISED luminance
python calib.py     # every material's albedo, measured off the chart
```

Interactive keys: `1 2 3` lighting, `Q W E R T` view, `[ ]` wetness, `D` debug channel,
`P` parallax, `N` normals, `M` detail bands, `S` screen-space reflection, `F1` re-shoot.
There is a wetness slider on screen; it drives every material at once through one global
shader parameter.

**Resolution.** As in the cave spike: the desktop is 1920×1080 at 125% scaling, so a
1920×1080 *window* cannot exist in logical coordinates. Everything renders into a
`SubViewport` fixed at exactly 1920×1080 inside a smaller window. Every PNG and every
number below is a true 1080p render.

**GPU.** `RenderingServer.get_video_adapter_name()` reports **NVIDIA GeForce RTX 3080
Laptop GPU**, Vulkan 1.4.312, Forward+, Godot 4.7.2-stable. Not the Intel UHD.

| file | what it is |
|---|---|
| `bs_noise.gdshaderinc` | hash, gradient noise, fbm, ridged, voronoi, triplanar weights |
| `bs_surface_core.gdshaderinc` | **the shader family.** Every opaque material is this file |
| `bs_surface.gdshader` | the full variant: all six feature blocks compiled in |
| `bs_surface_lean.gdshader` | rock / granular / concrete: no metal, timber or label code |
| `bs_surface_far.gdshader` | no parallax, no voronoi, no bedding — the distance variant |
| `bs_water_core.gdshaderinc` + 2 `.gdshader` | shallow (refracting) and deep (opaque, so SSR can run) |
| `bs_calib.gdshader` | the unlit reference ramp |
| `library.gd` | **the material table.** 27 materials, each a dictionary of uniforms |
| `forms.gd` | the four test forms, procedural `ArrayMesh` |
| `mat_root.gd` | scene, five views, three lighting rigs, shots, cost and exposure harnesses |
| `lum.py`, `calib.py` | the two measurement scripts |
| `shots/` | 36 PNGs at 1920×1080, plus `calib_rects.json` |
| `cost.txt` | the raw output of `--cost` |

---

## 2. How the shader family is parameterised

**There is no per-material code anywhere in this project.** A material is a dictionary of
uniform values. The family is a stack of layers, each with an amplitude in metres and a
frequency in cycles per metre, and a material is a set of amplitudes. A material that does
not want a layer sets its amplitude to zero and the branch is skipped — a uniform branch is
coherent across a draw call, so a rock pays nothing for the rust code.

### 2.1 The stack, top to bottom

```
world position P
  └ parallax occlusion march on the FORM band  ->  shading position S
      ├ FORM    fbm3 / ridged  +  bedding  +  voronoi (joints or stones)     ~0.1 - 2 m
      ├ DETAIL  fbm3  +  second voronoi (fines)  +  grain / weave            ~1 - 10 cm
      └ MICRO   two octaves of gradient noise                                ~1 - 10 mm
  each band -> its own normal, by forward difference along two tangent
               directions (2 extra evaluations per band, no tangent attribute)
  all three -> one scalar `field`, which drives albedo, roughness, occlusion
               and where the water stands
```

Everything is world-space and triplanar by construction: the height field is a true 3D
function of world position, so there is no seam, no UV and no tangent basis anywhere. The
one exception is the printed label, which reads `UV` — a label is applied to a manufactured
part in a factory, and a manufactured part has an authored surface.

**The bands fade by pixel footprint, not by a hand-tuned distance.** `length(fwidth(P))` is
the world size of a pixel; a band fades out as its wavelength approaches it. That is
automatically correct at any resolution, any field of view and any camera speed, and it is
why nothing in the library shimmers at range. **What a faded band turns into is roughness**
(`rough_micro`): geometry smaller than a pixel *is* roughness, and folding it back in is
what stops a surface going glossy and plastic at eight metres. That is the single most
common cause of "it looked fine in the close-up".

### 2.2 The parameters, grouped

| group | uniforms | what it is |
|---|---|---|
| albedo | `alb_lo` `alb_hi` `alb_curve` `alb_cell` | **linear** reflectance at field 0 and 1. Not sRGB, not a `Color`, no `source_color` hint |
| | `macro_var` `macro_freq` | low-frequency value variation, independent of the height field |
| | `stain_col` `stain_amt` `stain_freq` `stain_sharp` | mineral staining — the one place this family carries hue |
| specular | `rough_lo` `rough_hi` `rough_micro` `metallic` `spec` | roughness at field 0 and 1; `rough_micro` is what the micro band becomes at range |
| form | `form_freq` `form_amp` `form_ridge` | `form_ridge` 0 = billowy (weathered), 1 = ridged (freshly broken) |
| | `bed_freq` `bed_amp` `bed_value` | bedding bands in world Y |
| | `voro_freq` `voro_amp` `voro_pebble` `voro_warp` | `voro_pebble` 0 = crack relief, 1 = domed stones |
| detail | `detail_freq` `detail_amp` `voro2_*` | |
| | `grain_*` `weave_*` | timber grain, 2×2 composite twill |
| micro | `micro_freq` `micro_amp` | |
| depth | `pom_depth` `pom_far` `pom_steps_near/far` | metres of apparent relief and the distance ramp |
| occlusion | `ao_strength` `ao_radius` | four-tap horizon estimate on a cheap form band |
| water | `wet_gain` `wet_bias` `wet_darken` `wet_rough` `pool_gain` `wet_fill` | how this material answers the global wetness |
| metal | `rust_amt/freq/col/col_old` `paint_amt/col/rough` `chip_amt` | |
| manufactured | `lay_amt/freq/axis` `edge_wear` `print_*` | machining lay, edge polish, printed label |

### 2.3 The five global controls

Declared `global uniform`, registered in `project.godot` under `[shader_globals]`, so one
call changes every material in the world at once:

```gdscript
RenderingServer.global_shader_parameter_set("bs_wet", 0.6)
```

| name | what it does |
|---|---|
| `bs_wet` | **the wetness slider.** 0 dry, 1 drowned. Every material answers through its own `wet_gain` and `wet_bias` |
| `bs_debug` | 0 shaded, 1 albedo, 2 roughness, 3 normal, 4 AO, 5 field, 6 metallic |
| `bs_pom_on` | master parallax scale — set to 0 on low settings |
| `bs_normal_gain` | master normal amplitude |
| `bs_detail_gain` | detail + micro band enable |

### 2.4 The wetness model, which is the part most worth copying

```
w    = bs_wet * wet_gain + wet_bias          this material's local wetness
film = w * 0.85                              a film everywhere
lvl  = w * w * 0.55 * pool_gain              where the water surface stands, in
                                             the height field's own 0..1 range
pool = smoothstep(0, 0.11, lvl - field)      standing water fills from the bottom up

albedo    *= mix(1, wet_darken, film)  then  *= mix(1, 0.74, pool)
roughness  = mix(rough, max(wet_rough, 0.26), film * 0.72)
             then mix(that, max(wet_rough*0.55, 0.075), pool)
normals    = normals * mix(1, 1 - wet_fill*0.85, pool)     water fills the micro first
CLEARCOAT  = pool * 0.65 + film * 0.18
```

Two things in there took the longest to get right and are the reason a first pass of this
looks like wet ceramic:

1. **`lvl` must be conservative.** The first version put half of every surface under
   standing water at slider 0.35, and standing water at roughness 0.04 under a lamp beside
   the camera returns nothing but a hotspot. Correct physics, unreadable image, and the
   whole library rendered black. Water fills from the bottom of the height field upward and
   at w = 0.5 it should cover about a seventh of the area.
2. **A damp surface is not a shiny surface.** Water inside the pores darkens; water standing
   on top reflects. Letting the film drive roughness all the way down is what makes
   everything look glazed.

### 2.5 ART-DIRECTION §3.1's four rock scalars

`BSLibrary.rock_from_scalars(wet, fracture, bedding, worked)` returns a uniform dictionary
and is the function the cave dressing layer should call per cell.

| ART scalar | range | family uniforms |
|---|---|---|
| `wet` | 0→1 | `wet_bias` directly |
| `fracture` | 3→14 | `voro_freq` 3→14, `voro_amp` 0.004→0.020 m, `form_ridge` 0→0.8 |
| `bedding` | 0.4→3.5 | `bed_freq` 1.7→4.0 (beds 0.60 m→0.25 m), `bed_amp`, `bed_value` 0.03→0.40 |
| `worked` | 0→1 | `stain_amt` 0.55→0.15, `rough_lo` 0.66→0.52, `alb_hi` ×1.0→×1.35 |

`shots/08_scalars_lamp.png` is that function swept, five steps per scalar, on a slab and a
bevelled block. `worked` is mostly *geometry* — a flat trammed floor, a sprung arch,
shot-hole scars on a 1.6 m round — and the cave spike already owns the shot-hole term. What
the material family contributes is the scour: worked ground is lighter, less stained and
less rough where the industry trammed over it.

---

## 3. How another project adopts it

1. Copy `bs_noise.gdshaderinc`, `bs_surface_core.gdshaderinc`, the three thin
   `bs_surface*.gdshader` wrappers, the two water shaders, and `library.gd`.
2. Copy the `[shader_globals]` block out of `project.godot`.
3. ```gdscript
   var mat := ShaderMaterial.new()
   mat.shader = load("res://bs_surface_lean.gdshader")
   for k in preset: mat.set_shader_parameter(k, preset[k])
   ```
   That is the whole API.
4. **Pick the variant per surface class, not per material.** This is where the cost is won
   or lost — see §4.3.
5. The meshes need normals and nothing else. No UVs (except a label), no tangents. That is
   deliberate: a generated cave has neither.

**Adding a variant of an existing family member is a dictionary. Adding a new *layer* is a
shader edit**, and it costs every material that compiles that variant, so it should arrive
with its own `#define`.

---

## 4. What it costs

Measured with `--cost` at 1920×1080 on the RTX 3080 Laptop GPU, the material covering the
whole frame, one spot light with shadows, no glow, median of the per-frame GPU time the
renderer reports for the viewport. Two conditions, because one number is not enough to
budget with:

* **underfoot** — an 80 m plane filling the frame with its near edge at 0.4 m. Every pixel
  runs the parallax march at full step count and every normal band is on. This is the worst
  case in the game and it is what a machine standing still is looking at.
* **at range** — the same plane from 6 m at a shallower angle, so the pixel footprint has
  faded the micro band out and the parallax has expired over most of the frame.

Baseline (a `StandardMaterial3D` at albedo 0.18 in the same frame): **0.77 ms** underfoot,
**0.69 ms** at range. Subtract it to get the material's own cost.

### 4.1 The table

| material | underfoot ms | at range ms | affordable at full-screen coverage? |
|---|---:|---:|---|
| rock_wet | 35.7 | 13.4 | no — close range only, and not the whole floor |
| rock_fresh | 44.5 | 15.7 | no |
| rock_weathered | 39.0 | 18.0 | no |
| rock_stained | 40.6 | 17.5 | no |
| rock_tidemark | 34.1 | 13.2 | no — but it is a 0.12 m band, never full screen |
| silt_dry | 27.7 | 10.4 | no |
| silt_damp | 27.9 | 10.5 | no |
| mud_saturated | 11.0 | 4.4 | **marginal** — large surfaces, watch near coverage |
| **aggregate** | **41.5** | **14.0** | no — the designer's case, and the most expensive |
| **ballast** | **43.7** | **17.8** | no |
| water_shallow | 2.6 | 2.2 | **yes** — any range, any coverage |
| water_deep | 1.9 | 1.7 | **yes** |
| concrete_weathered | 29.6 | 11.7 | no |
| hardstanding | 34.8 | 16.2 | no |
| iron_painted | 33.5 | 23.5 | no |
| iron_bare | 30.5 | 19.4 | no |
| steel_rusted | 30.6 | 18.4 | no |
| iron_rotten | 32.0 | 25.6 | no |
| timber_wet | 12.0 | 5.1 | **marginal** |
| timber_rotten | 36.4 | 10.4 | no |
| alu_machined | 4.3 | 2.9 | **yes** |
| alu_anodised | 4.3 | 2.8 | **yes** |
| composite | 4.3 | 2.9 | **yes** |
| polymer | 4.1 | 2.7 | **yes** |
| powdercoat | 4.1 | 2.4 | **yes** |
| rubber | 6.5 | 4.4 | **yes**, watch near coverage |
| label | 4.4 | 2.9 | **yes** |

**Read this correctly.** These are *full-screen* numbers for a 16.6 ms frame. No frame in
this game is 100% one material: the cave spike's own frames are nine-tenths black, the rock
shell is maybe 40% of the lit pixels and iron is under 5%. A material at 30 ms full screen
costs 12 ms at 40% coverage and 1.5 ms at 5%. The column that matters for the environment
spikes is therefore *coverage × cost*, and the two rows to worry about are the ones that
cover the ground.

### 4.2 What each feature costs, on `aggregate`

| | ms, underfoot |
|---|---:|
| everything on | 41.5 |
| no parallax | 13.2 |
| no detail + micro bands | 34.8 |
| neither | 10.2 |

**Parallax is 68% of the cost of the underfoot case**, and it is also the single biggest
visual win in it (`shots/05_macro_aggregate_no_parallax.png` against
`shots/04_macro_aggregate.png`). That is the trade, stated in one line.

The reason it is so expensive is specific and fixable: the march evaluates the FORM band,
and for aggregate the FORM band *is* a 3D voronoi with a domain warp — about 50 hash calls
per evaluation, 13 to 17 times per pixel. Two things already done here took it from 56 ms
to 41.5:

* **four bisection steps after the linear march**, so the linear march only has to find the
  bracketing interval and the step count halves;
* **a cheap form band for the occlusion taps** (`bs_form_ao`), which drops the domain warp
  and two fbm octaves. That one change was worth 14 ms on aggregate.

The next step, not done here, is to **march a cheaper proxy**: a 2D cellular evaluated on
the dominant triplanar axis instead of the 3D one, used only by the march. Estimated at
another 2× and it is the first thing to try.

### 4.3 The variants, and the finding that matters most

Identical uniforms (`rock_weathered`), underfoot:

| variant | ms | what is compiled out |
|---|---:|---|
| `bs_surface.gdshader` (full) | 47.1 | nothing |
| `bs_surface_lean.gdshader` | 38.9 | metal, timber grain, printed label |
| `bs_surface_far.gdshader` | **5.6** | also parallax, voronoi, bedding |

**Removing unused branches buys 17%. Removing the parallax and the voronoi buys 88%.** The
`#define` slimming is worth doing, but it is not the lever — a uniform branch that is never
taken costs almost nothing at runtime, it only costs register pressure. The lever is having
a genuinely simpler shader for everything past the parallax range, and switching to it by
distance. `bs_surface_far.gdshader` at 5.6 ms full screen is affordable everywhere.

### 4.4 What the environment spikes should do with this

* **Floor and rock shell inside 5 m:** `bs_surface_lean`, parallax on. Budget it at
  ~40% coverage → 12–16 ms. That is most of a 60 fps frame and it is the thing to argue
  about.
* **Everything past 5 m:** `bs_surface_far`. Swap by `visibility_range` on the chunk, the
  same mechanism §4.4 of `PROCEDURAL-AND-GODOT.md` already uses instead of mesh LOD.
* **Scatter, props, the kit:** the manufactured and metal presets are 3–6 ms full screen
  and are never more than a few percent of it. Free.
* **Water:** free. 2 ms full screen. Use it.

**Measurement caveat, stated plainly:** this is a laptop GPU and its clocks move. Numbers
*within* one table are one run and are comparable; numbers between runs in this document's
history moved by up to 15% on identical code. Anything under a 20% difference between two
rows here should not be treated as real.

---

## 5. The physical values, and where they come from

Every `alb_*` in `library.gd` is **linear reflectance**, and `shots/07_calibration_albedo.png`
renders each material's `ALBEDO` unlit, orthographically, with the tone mapper set to
LINEAR at exposure 1.0, so the value in the PNG *is* the number. `calib.py` reads it back
against `shots/calib_rects.json` (which the scene writes at the same moment, so nothing has
to guess at the layout) and fails if a material leaves plausible albedo.

Current result: **PASS, all 27**, inside the plausible band and inside their own claims.

```
material                   p02    mean     p98   claimed
rock_wet                0.0229  0.0349  0.0436   0.030 - 0.095
rock_fresh              0.0458  0.0713  0.0873   0.045 - 0.140
rock_weathered          0.0160  0.0267  0.0330   0.020 - 0.080
silt_dry                0.0568  0.0875  0.1010   0.070 - 0.175
mud_saturated           0.0145  0.0155  0.0171   0.010 - 0.055
aggregate               0.0258  0.0434  0.0659   0.025 - 0.125
concrete_weathered      0.1303  0.2054  0.2346   0.180 - 0.350
hardstanding            0.0867  0.1321  0.1845   0.090 - 0.310
iron_bare               0.1540  0.3990  0.4287   0.140 - 0.570   (F0, not diffuse)
alu_machined            0.8702  0.8872  0.9035   0.850 - 0.930   (F0, not diffuse)
composite               0.0222  0.0238  0.0253   0.012 - 0.038
rubber                  0.0169  0.0180  0.0195   0.010 - 0.030
```

The reasoning behind each band:

| material | linear albedo | why |
|---|---|---|
| dark rock, wet | 0.030 – 0.095 | the brief's stated band for dark rock (0.04–0.12), shifted down for a wet iron mine. Warm ratio kept from ART §3.1 (+22% R / −28% B off neutral) |
| rock, freshly broken | 0.045 – 0.140 | a fresh break has no patina and is lighter and greyer than the weathered outside. This is the strongest readable difference between the two |
| rock, long weathered | 0.020 – 0.080 | iron patina darkens; the joints have opened and hold shadow |
| tide-mark crust | 0.090 – 0.240 | ART §3.5 says albedo ×1.7 and matte. ×1.7 off 0.06 is 0.10; the top of the band is a thick mineral crust |
| silt / fines, dry | 0.070 – 0.175 | dry silt and clay measure 0.15–0.25; iron-rich mine fines are darker |
| mud, saturated | 0.010 – 0.055 | water in the pores roughly halves it again |
| aggregate / ballast | 0.025 – 0.130 | the same rock, but each stone is a different stone: `alb_cell` scatters ±34% per voronoi cell |
| weathered concrete | 0.180 – 0.350 | the brief's stated band (0.25–0.35), extended down for the dirty end |
| industrial hardstanding | 0.090 – 0.310 | concrete with exposed aggregate, oil (0.014, near black) and tyre polish |
| iron / steel, bare | F0 **0.56, 0.565, 0.57** | the standard measured F0 of iron. **For a metal the albedo channel is not diffuse reflectance at all** — it is specular reflectance at normal incidence, and that is why the iron entries look "too bright" next to a rock in the chart |
| aluminium | F0 **0.91, 0.92, 0.92** | the standard measured F0 of aluminium |
| anodised aluminium | 0.20 – 0.35 | still metallic, tinted oxide, roughness 0.34–0.50 |
| rust | 0.098, 0.041, 0.018 fresh; 0.046, 0.025, 0.015 old | iron oxide, and it is **not** metallic — `METALLIC` goes to 0 across the transition |
| timber, wet | 0.013 – 0.098 | soaked sawn softwood; the grain is worth ±46% of value on its own |
| polymer, rubber, composite | 0.012 – 0.038 | moulded blacks. Nothing in the real world is 0.0; soot is 0.02 |
| printed label | 0.660 bg / 0.018 ink | matte white label stock and process black |
| water | IOR 1.333 → F0 **0.0203**, `SPECULAR` 0.25 in Godot's parameterisation (0.5 = F0 0.04) | |
| mine water absorption | 0.85, 0.30, 0.18 per metre | clear water eats red first (≈0.35/0.045/0.015); mine water is loaded with iron fines, so the coefficients are raised and flattened. This is why depth reads blue-green with **no blue anywhere in the palette** — ART §3.5's requirement, satisfied physically |

**Metallic is 0 or 1 everywhere except across the rust transition**, which is the one place
in this world where a surface really is part oxide and part metal inside one pixel.
`shots/11_debug_metallic.png` shows the channel.

### 5.1 The conflict with ART-DIRECTION §3.1's stated rock values, which needs a ruling

ART §3.1 gives `dry, lit (0.340, 0.260, 0.175) #9E8B74`. Those triples are exactly the
linear form of those hex codes, so they are being stated as albedo. **0.34 linear is a pale
limestone or new plaster.** It is 4× the reflectance of the dark wet rock the brief asks
for and about 5× what an iron mine's walls measure.

This is not a small disagreement, and I think it is the direct cause of what the designer
was looking at: `spikes/godot/cave/rock.gdshader` uses ART's numbers verbatim, and
`spikes/godot/cave/shots/03_underfoot.png` is a peach-coloured surface with blown highlights
and no shadow in it. **A too-bright albedo is the fastest way to make a surface look like
painted plastic**, because the specular response stops being able to carry any shape.

This library uses the measured band and keeps ART's *hue ratio*. Someone has to rule on
whether ART's triples were intended as albedo or as the rendered value under the lamp. If
they were the rendered value they are consistent with §2.2's "floor 3 m ahead ≈ 0.08" only
at a much lower irradiance than either spike uses.

### 5.2 The exposure contract, ART §2.9 and §2.2

`lum.py` computes on **linearised** luminance, per §2.9's own warning. The `falloff` view is
the instrument: a 30 m aggregate floor with a rock wall down one side, one lamp on the
camera, exposure fixed at 1.0 and the lamp at its calibrated power — the only framed shot in
`shots/` that is not exposed for its framing.

Measured, linear, at the shipped `LAMP_ENERGY` (140, inverse-square decay).
Reproduce with `-- --expo`, which sweeps 120 / 140 / 170 and prints this table:

| ART §2.2 target | ART wants | measured |
|---|---|---|
| floor 3 m ahead, grazing | ≈ 0.08 | **0.088** |
| near floor at 1.6 m | blown deliberately | 0.264 |
| wall at 8 m | ≈ 0.06 | **0.012** |
| wall at 25 m | black | < 0.001 |
| brightest : dimmest legible across three metres | **≈ 90 : 1** | **≈ 7 : 1** (floor 1.6 m 0.264 against floor 4.6 m ≈ 0.037) |

**Two of ART §2.2's five numbers are not reachable with a physically correct lamp, and they
are not reachable together.**

* A point source is inverse-square. From 1.6 m to 4.6 m that is 8.3 : 1 before anything
  else; adding the cone falloff and the grazing cosine gets 7–10 : 1 on a floor. **To reach
  90 : 1 across three metres you need falloff of about d^-4.3**, which is not a lamp. The
  90 : 1 figure is reachable across the *whole* frame (near floor to far wall is 32 : 1
  here, and 90 : 1 across 1.6 m → 12 m), so I think §2.2 means the frame's dynamic range
  rather than a three-metre span, but it should say which.
* "Floor at 3 m = 0.08" and "wall at 8 m = 0.06" cannot both hold: they are a ratio of 1.3
  across a distance that inverse-square makes 7.1, even with the wall at normal incidence
  and the floor grazing. One of the two numbers has to move.

Per-frame contract on the shipped shots, against §2.9's targets for a lamp frame
(≤3% blown, 3–20% legible, ≥70% true black):

```
shot                                    >0.5   >0.18  >0.05   <0.02
01_library_lamp                         3.4%   25.1%  38.3%   52.3%
02_00 rock group                        0.0%    3.1%   9.7%   87.6%
02_02 underfoot group                   0.0%    1.9%   6.9%   89.3%
02_05 iron group                        0.8%    6.4%  11.5%   87.0%
03_wet_soaked_underfoot                 0.0%    0.0%   3.0%   92.5%
09_falloff_lamp                         0.6%   14.0%  29.7%   62.1%
```

The four-at-a-time group shots sit inside the contract. The three whole-library overviews do
not, and they are not supposed to: a 27-sample grid deliberately fills the frame with lit
material, which is the opposite of a cave frame. `09_falloff_lamp` is the one that is shaped
like a real frame, and it lands at 0.6% blown / 29.7% legible / 62.1% true black — slightly
too legible and not quite black enough, which is what you would expect from a 3.2 m wide
corridor with no ceiling and nothing to occlude.

### 5.3 How the shots are exposed, and why that is a departure

Every framed shot is lit as though **the lamp were always `LAMP_REF_M` = 4.8 m away**
(`light_energy = LAMP_ENERGY × (distance / 4.8)²`) and rendered at **exposure 1.0**. So the
irradiance on the subject is the same in every shot and a dark material comes out dark: at
albedo 0.012, rubber is 25× darker than concrete in `shots/02_08` and in
`shots/02_04`, and that comparison is the point of a library.

I built an auto-exposure meter first (`_meter()`, still in the file, still callable) and
then deliberately stopped using it for the shots, because metering each frame to the same
mid-grey makes rubber and concrete come out the same value and turns the chart into a lie.
`falloff` and `calib` are exposed at 1.0 with the lamp at its true calibrated power, and
they are the two that carry the physics.

This is a departure from ART §2.3 ("do not compress the ramp"), and it is deliberate and
scoped: a game frame must show the falloff, a material chart must not be a picture of its
own framing.

---

## 6. The art rules I bent, and the one I tested

### 6.1 Bent: §9's "no hue axis on anything"

`stain_amt` / `stain_col` puts hue on rock, and the strongest case (`rock_stained`) is an
iron ochre at (0.115, 0.052, 0.018) — clearly orange, not a value change. Rust is worse:
(0.098, 0.041, 0.018) is unambiguously a colour.

DESIGN-PRINCIPLES §6 already names this collision and says the intent binds while the letter
is amendable. What I did with that:

* **Hue is a material property, never an axis.** Nothing in the library changes hue with
  depth, rock type, magnetic character, structural integrity or biome. Staining is a
  function of *position*, at 0.22–0.50 cycles per metre, so two adjacent cells of the same
  rock type differ, and the same rock type in two parts of the cave differs. It cannot be
  used as a legend.
* **The rock family is still one warm buff.** Every rock preset shares the same hue ratio;
  what varies is value, and the stain rides on top of it.
* The risk is real and it is the one ART is right about: a stain parameter is one designer
  request away from being "the deep biome is greener". If that ruling goes the other way,
  set `stain_amt` to 0 in `library.gd` and the family still works — the staining is
  additive, not structural.

### 6.2 Bent: §9's "no image texture, UV map or bitmap"

No bitmap is loaded, generated or sampled anywhere. But the printed label reads `UV`, and
that is a UV map. The intent — a generated cave cannot be unwrapped — is untouched: every
world surface is world-space triplanar and there is not one UV on any of them. A label on a
moulded polymer housing is not a generated surface; it is a part with an authored face.
This is question 5's territory and should be settled with it.

### 6.3 Bent: "overcast daylight with no ambient term"

The `day` condition uses `AMBIENT_SOURCE_SKY` at energy 0.55, matching what
`spikes/godot/surface/scripts/weather.gd:34` already does. §9's "no sky term" is written for
the cave, where light arriving from infinity is light through solid rock. On the surface the
sky is a real source that is in the frame. `shots/10_day_sky_ambient_on.png` and
`10_day_sky_ambient_off.png` are the same frame with it and without: without it the shadowed
sides of every sample go to true black and the surface reads as a night scene with one hard
sun, which is not overcast daylight and is not what the pit-head is. Ambient is off, hard,
in both cave conditions.

### 6.4 Tested and reported, not adopted: screen-space reflection

`shots/06_water_deep_ssr_off.png` and `06_water_deep_ssr_on.png` are the same frame with
Godot's `Environment.ssr_enabled` off and on. Deep water is rendered **opaque** specifically
so SSR can run on it, since Godot's SSR does not apply to the transparent pass.

**Flagging it as the rule I am testing:** SSR is not an ambient term in the sense §9
forbids. It has no source at infinity; it is the reflection of *actually lit geometry that
is in this frame*, and if the frame goes black the reflection goes black with it. That is
categorically different from a sky term, which invents light where there is none.

**But it did not earn its place here, and the honest reason is that there is nothing to
reflect.** Under one lamp with zero ambient, nine-tenths of the frame is black, so a mirror
returns black. The measured difference between the two shots is 0.0049 vs 0.0058 at p90 —
under 1%. SSR costs about 5 ms and buys almost nothing in this world. **Leave it off.**

The interesting consequence is in §7.

---

## 7. What is still not photoreal

**In order of how much it costs the frame.**

1. **Wetness has nothing to reflect, and that undermines the strongest photoreal cue.**
   (Shallow water is the exception, because what it shows is the bottom through it rather
   than the world above it — see `shots/06_water_shallow_lamp.png`, where the absorption
   tint and the waterline on the crust block both read.) A
   wet surface is convincing because it reflects a world. Under one carried lamp with zero
   ambient, a pool reflects one hotspot and otherwise reflects black. `shots/
   03_wet_soaked_underfoot.png` is *correct* — a flooded floor under a headlamp really is
   dark — and it is also less convincing than the dry version, which is the opposite of what
   the brief expects. This is a design finding, not a shader bug: **the wetness cue and the
   no-ambient rule are in tension, and the resolution is content, not code** — put something
   lit near the water. ART §2.8's residual lighting circuit would fix it at a stroke, and so
   would a beacon pilot light. Someone should decide which.
2. **Iron does not read as iron.** It is the worst material in the library, and the reason
   is the same one: a metal has no diffuse term at all, so all it can show is a reflection of
   its surroundings, and its surroundings are black. Under the lamp, bare and rusted iron
   read as a flat pale sheen — see `shots/02_05`. Under daylight in `shots/01_library_day.png`
   they read much better, because the sky gives them something to reflect. The rust mask is
   also still too blotchy: at range it reads as terrazzo rather than as oxide, and it needs
   to be driven by a downward-flow field (gravity) rather than by isotropic noise.
3. **The family has a signature, and it is the voronoi.** Rock joints, mud cracks, concrete
   cracks, aggregate stones and rotten-timber cubical rot are all the same cellular function
   at different frequencies, and at a glance they look related in a way real materials of
   those kinds do not. Silt and concrete are now at very different cell sizes (6.5/m against
   1.05/m), which helps, but the family tell is there. The fix is a second pattern primitive
   — anisotropic, directional, flow-shaped — which nothing here has.
4. **A flat plane with a heightfield on it is still a flat plane.** POM gives apparent depth
   and it works well (compare `04_macro_aggregate.png` with
   `05_macro_aggregate_no_parallax.png`) but the silhouette is unchanged, so at grazing the
   ground shows a clean straight edge and stones do not break the horizon. DESIGN-PRINCIPLES
   §6 says the last metre and a half needs "apparent **or real** displacement, half-buried
   aggregate". The material system delivers the apparent half. The other half is instanced
   geometry and it belongs to the environment spikes.
5. **No self-shadowing in the height field.** Godot 4 removed contact shadows, and SSAO does
   nothing under zero ambient because it only modulates ambient. What is here instead is a
   four-tap horizon estimate in the shader, feeding `AO` with `AO_LIGHT_AFFECT = 1.0` so it
   affects direct light. That closes the gaps between stones convincingly, but it is
   view- and light-independent, so a stone never casts a shadow on the stone beside it. A
   six-step parallax shadow march along the light vector would fix it — but Godot's spatial
   shader does not expose the light direction in `fragment()`, so it needs a custom `light()`
   function, which means writing the whole BRDF. That is the biggest single remaining item
   and it is a day of work.
6. **The natural forms read as organic.** The `lump` test mesh is a noise-displaced sphere
   and at high material frequency it reads as coral or dough rather than as broken rock. It
   is a testbed prop rather than a shipping asset, but it is a fair warning: **this material
   family on a rounded form looks wrong**, and the cave's breakdown blocks must be angular.
7. **Everything is slightly milky.** AgX at `tonemap_white = 6.0` desaturates hard and lifts
   the low mids. It is the right tone mapper for this world (ART §2.3 is explicit) but Godot
   4.7 added `tonemap_agx_contrast` and `tonemap_agx_white` and neither has been touched
   here. Worth an hour.

---

## 8. The screenshots

36 PNGs at 1920×1080 in `shots/`.

| shot | what to look at |
|---|---|
| `01_library_lamp / _day / _machine` | the whole library under the three lighting conditions this game has |
| `02_00` … `02_08` | every material, four at a time, at a working distance, **at a fixed exposure** so values are comparable across shots |
| `03_wet_dry_*` / `03_wet_soaked_*` | the wetness slider at 0.0 and 1.0, driving every material at once |
| `04_macro_aggregate / ballast / silt_dry / mud_saturated` | the underfoot case, close |
| `05_macro_aggregate_no_parallax` | the same frame with parallax off — the biggest single win |
| `05_macro_aggregate_no_detail_bands` | the same frame with the detail and micro normals off |
| `06_water_shallow_lamp / _machine`, `06_water_deep_ssr_off / _on` | water at a grazing angle over a silt bed with tide-mark crust standing in it, so there is a waterline and something lit to reflect. Absorption, refraction and the waterline all read; the SSR pair is the before/after |
| `07_calibration_albedo` | the albedo chart: the linear ramp, every material's albedo unlit, and each material's claimed range ticked onto the ramp in orange and green |
| `07_calibration_sweeps` | roughness 0→1, metallic 0/1 at three roughnesses, normal+parallax scale 0→1 |
| `08_scalars_lamp` | ART §3.1's four rock scalars, five steps each |
| `09_falloff_lamp` | one lamp down a 30 m passage, exposure 1.0 — the ART §2.2 instrument |
| `10_day_sky_ambient_on / _off` | the ambient rule being tested on the surface |
| `11_debug_albedo / roughness / normal / metallic` | the channels, for the record |

---

## 9. Everything I guessed

1. **The albedo bands in §5.** Every one is reasoned from published measured ranges and from
   the brief's stated numbers, not measured by me from a real mine. The bands are stated in
   `library.gd` so they can be argued with and so `calib.py` fails when someone drifts.
2. **That ART §3.1's rock triples are wrong rather than differently defined.** §5.1. This is
   the biggest guess in the document and it changes every frame.
3. **That the 90:1 in ART §2.2 means the frame's dynamic range, not a three-metre span.**
   §5.2. I could not make a physical lamp do it across three metres.
4. **`LAMP_ENERGY` 140 with inverse-square decay** was picked to hit §2.2's "floor at 3 m ≈
   0.08" on the falloff strip. It is a Godot number and does not survive a renderer change,
   which is exactly what §2.2 warns about. The reproducible part is the ratio.
5. **`LAMP_REF_M` = 4.8 m** — the framing distance every shot is normalised to. Chosen so
   the mid-albedo materials sit near the middle of the curve and both ends of the albedo
   range stay on it. Arbitrary, and stated in one constant.
6. **The wetness curve** `lvl = w² × 0.55 × pool_gain`. There is no source for how much of a
   surface is under standing water at a given "wetness"; the curve was chosen so that at
   w = 0.5 roughly a seventh of the area holds water. §2.4 says why it matters.
7. **`macro_var`** — the low-frequency value variation. No physical basis at all. It is
   there because nothing real is one value over a square metre and it does more for
   photorealism at three metres than any of the normal bands.
8. **Machinery light colours.** ART §2.1 gives 2100 K as sRGB (1.00, 0.72, 0.42) and 12000 K
   as (0.60, 0.74, 1.00). I interpolated 1900 K and 2400 K between those and **linearised
   them** before handing them to `Light3D.light_color`, because Godot uses that colour as a
   raw linear multiplier. If ART's triples were already meant as linear, my machinery is one
   step too warm. Godot 4.7 has a `light_temperature` property that would settle it, but it
   only applies with physical light units enabled, which this project does not use.
9. **That a metal's `SPECULAR` should stay at 0.5 while `ALBEDO` carries F0.** That is how
   Godot's metallic workflow is meant to be driven, but I did not find it stated.
10. **The composite twill** is a 2×2 pattern at 260 tows per metre on the dominant triplanar
    axis. Real prepreg is 3K tow at about 1.7 mm; 260/m is 3.8 mm, so it is coarser than a
    real part. Chosen so it reads at a metre instead of aliasing.
11. **Anisotropy is faked.** Machined and brushed aluminium use a high-frequency roughness
    modulation along one axis rather than Godot's `ANISOTROPY`, because true anisotropy needs
    a tangent basis and this family exists to work without one. It reads correctly at the
    angles a player sees and it is not physically right.
12. **`INSTANCE_CUSTOM` is not read.** §3 says to drive per-instance variety through it and
    the family does not support that yet. Untested, and it is the first thing a MultiMesh
    scatter will need.
13. **`rock_from_scalars`'s mapping of `worked`** to stain, roughness and albedo. ART
    describes `worked` almost entirely as geometry and says nothing about what it does to the
    surface, so the scour interpretation is mine.
14. **The four test forms.** A bevelled block, a noise-displaced lump, a flat slab and a
    vertical panel yawed 74° for grazing incidence. The 74° is chosen because it is where a
    GGX lobe is widest and a wrong roughness is loudest; the number is not from anywhere.
15. **The measurement caveat in §4.4** — that sub-20% differences between cost runs are
    noise. Inferred from watching identical code move by 15% between runs on this laptop,
    not from a controlled experiment.
