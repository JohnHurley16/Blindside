import unreal, os, sys, json, math
sys.path.append(r"C:/Users/jackh/documents/programming/Blindside/spikes/unreal/look/tools")
from ue_common import *

FORCE = os.environ.get("BS_REBUILD_MESH", "0") == "1"
meta = json.load(open(os.path.join(GEN, "valley.json")))

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.new_level("/Game/Maps/Valley")

# ------------------------------------------------------------------ textures
tex = {}
for k in ("main", "near", "back"):
    tex[k+"_h"] = import_texture(os.path.join(GEN, k+"_h.png"), "/Game/T", k+"_h")
    tex[k+"_m"] = import_texture(os.path.join(GEN, k+"_m.png"), "/Game/T", k+"_m", nearest=False)
log("textures in")

# ------------------------------------------------------------------ terrain material
TERRAIN_HLSL = r"""
float3 P  = WP * 0.01;
float3 N  = normalize(VN);
float  Zm = P.z;
float  dist = max(CD, 1.0) * 0.01;
float  up = saturate(N.z);

// ---------------- snow, BY SLOPE FIRST. The Godot pass put snow everywhere.
float snow = smoothstep(0.58, 0.90, up);
snow *= saturate(0.40 + 0.60 * smoothstep(-60.0, 1100.0, Zm));   // snowline +1100 m

float3 nf = float3(N.x, N.y, 0.0001);
float aspect = dot(normalize(nf), float3(-0.80, -0.60, 0.0));
snow += 0.13 * aspect * (1.0 - up);

snow += (MK.b - 0.5) * 0.60;                     // concave collects, convex is scoured
snow -= saturate(MK.r * 2.2 - 0.30) * 0.62;      // drainage / avalanche chutes strip it
snow -= saturate(MK.g * 1.6) * 0.34;             // talus is too loose and too steep
snow += N2 * 0.16 + N3 * 0.055;                  // break the contour up
snow  = smoothstep(0.32, 0.68, snow);

// ---------------- rock
float trim = smoothstep(285.0, 335.0, Zm + N2*28.0);   // the trimline, +310 m
float wet  = saturate(MK.r * 1.9);
float tal  = saturate(MK.g * 1.7);

float3 rock_dark = float3(0.048, 0.043, 0.039);
float3 rock_warm = float3(0.152, 0.124, 0.096);
float3 rock_cold = float3(0.084, 0.089, 0.101);

float3 rock = lerp(rock_cold, rock_warm, saturate(0.5 + N1*0.95));
rock = lerp(rock_dark, rock, saturate(0.34 + N4*0.85 + N1*0.35));
rock = lerp(rock * float3(0.70,0.75,0.88), rock, trim);
rock = lerp(rock, rock * float3(1.26,1.15,0.95), trim*saturate(0.5+N4));
rock = lerp(rock, rock*1.30 + 0.010, tal);
rock = lerp(rock, rock*0.52, wet*0.85);

// ---------------- snow colour: albedo 0.795 linear
float3 snowc = float3(0.795, 0.806, 0.832) * (0.94 + 0.06*N3);
snowc = lerp(snowc*float3(0.85,0.85,0.88), snowc, saturate(smoothstep(-30.0,700.0,Zm)+0.34));

float3 base = lerp(rock, snowc, snow);

// ---------------- roughness / spec
float rr = lerp(lerp(0.88, 0.63, trim), 0.95, tal);
rr = lerp(rr, 0.33, wet*0.75);
float sr = lerp(0.44, 0.23, saturate(N3*0.5+0.5));
OutR = lerp(rr, sr, snow);
OutS = lerp(0.5, 0.66, snow);

// ---------------- subsurface. Snow does not read without it and Godot had no term.
OutSSS = float3(0.60, 0.71, 0.96) * snow;
OutO   = snow * 0.70;

// ---------------- world-space detail normal, distance faded
float k = saturate(1.0 - dist/300.0);
float3 gg = float3(G1-G0, G2-G0, G3-G0);
gg -= N * dot(gg, N);
OutN = normalize(N + gg * lerp(0.85, 0.22, snow) * k * 7.0);

return base;
"""

def build_terrain_material():
    b = MatBuilder("/Game/M", "M_Terrain")
    m = b.mat
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_SUBSURFACE)
    m.set_editor_property("tangent_space_normal", False)

    wp = b.n(unreal.MaterialExpressionWorldPosition, -3000, 0)
    uv = b.n(unreal.MaterialExpressionTextureCoordinate, -3000, 200)
    vn = b.n(unreal.MaterialExpressionVertexNormalWS, -3000, 400)
    pd = b.n(unreal.MaterialExpressionPixelDepth, -3000, 600)

    ts = b.n(unreal.MaterialExpressionTextureSampleParameter2D, -2600, 200)
    ts.set_editor_property("parameter_name", "Mask")
    ts.set_editor_property("texture", tex["main_m"])
    ts.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    b.link(uv, "", ts, "UVs")

    def off_noise(dx, dy, dz, scale, levels, func):
        if (dx or dy or dz):
            c = b.n(unreal.MaterialExpressionConstant3Vector)
            c.set_editor_property("constant", unreal.LinearColor(dx, dy, dz, 0))
            a = b.n(unreal.MaterialExpressionAdd)
            b.link(wp, "", a, "A"); b.link(c, "", a, "B")
            src = a
        else:
            src = wp
        return b.noise(src, scale, levels, func)

    GA = unreal.NoiseFunction.NOISEFUNCTION_GRADIENT_ALU
    VA = unreal.NoiseFunction.NOISEFUNCTION_VALUE_ALU
    n1 = off_noise(0,0,0, 1.0/160000.0, 4, GA)   # ~1.6 km  massif colour
    n2 = off_noise(0,0,0, 1.0/4200.0,   4, GA)   # ~42 m    snow/rock breakup
    n3 = off_noise(0,0,0, 1.0/95.0,     3, VA)   # ~1 m     fine
    n4 = off_noise(0,0,0, 1.0/26000.0,  3, GA)   # ~260 m   weathering
    e = 26.0
    g0 = off_noise(0,0,0, 1.0/130.0, 2, VA)
    g1 = off_noise(e,0,0, 1.0/130.0, 2, VA)
    g2 = off_noise(0,e,0, 1.0/130.0, 2, VA)
    g3 = off_noise(0,0,e, 1.0/130.0, 2, VA)

    F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1
    F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3
    c = b.custom(TERRAIN_HLSL,
                 ["WP","VN","MK","CD","N1","N2","N3","N4","G0","G1","G2","G3"], F3,
                 [("OutR", F1), ("OutS", F1), ("OutN", F3), ("OutSSS", F3), ("OutO", F1)],
                 "terrain")
    for (src, port, name) in ((wp,"","WP"), (vn,"","VN"), (ts,"RGBA","MK"), (pd,"","CD"),
                              (n1,"","N1"), (n2,"","N2"), (n3,"","N3"), (n4,"","N4"),
                              (g0,"","G0"), (g1,"","G1"), (g2,"","G2"), (g3,"","G3")):
        b.link(src, port, c, name)
    MP = unreal.MaterialProperty
    b.prop(c, "", MP.MP_BASE_COLOR)
    b.prop(c, "OutR", MP.MP_ROUGHNESS)
    b.prop(c, "OutS", MP.MP_SPECULAR)
    b.prop(c, "OutN", MP.MP_NORMAL)
    b.prop(c, "OutSSS", MP.MP_SUBSURFACE_COLOR)
    b.prop(c, "OutO", MP.MP_OPACITY)
    return b.done()

M_terrain = build_terrain_material()
log("terrain material built")

def mi(name, mask_tex):
    p = "/Game/M/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(p):
        unreal.EditorAssetLibrary.delete_asset(p)
    f = unreal.MaterialInstanceConstantFactoryNew()
    inst = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, "/Game/M", unreal.MaterialInstanceConstant, f)
    unreal.MaterialEditingLibrary.set_material_instance_parent(inst, M_terrain)
    unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(inst, "Mask", mask_tex)
    unreal.EditorAssetLibrary.save_loaded_asset(inst, only_if_is_dirty=False)
    return inst

MI = {k: mi("MI_" + k, tex[k+"_m"]) for k in ("main", "near", "back")}

# ------------------------------------------------------------------ town material
TOWN_HLSL = r"""
float3 P = WP * 0.01;
float3 N = normalize(VN);
float up = saturate(N.z);
float side = 1.0 - up;

float a = saturate((P.z - 90.0)/430.0);          // higher on the wall is older
float3 wall = lerp(float3(0.088,0.086,0.085), float3(0.058,0.050,0.042), a);
wall *= (0.80 + 0.40*frac(sin(dot(floor(P*0.31), float3(12.9,78.2,45.1)))*43758.5));

float sn = smoothstep(0.55, 0.86, up);           // snow on every roof and ledge
float3 base = lerp(wall, float3(0.79,0.80,0.83), sn);

float2 q = float2(dot(P.xy, float2(0.74,0.74)), P.z*0.66);
float2 c = frac(q);
float win = step(0.20, c.x)*step(c.x, 0.64) * step(0.26, c.y)*step(c.y, 0.74);
float cellr = frac(sin(dot(floor(q), float2(41.7, 19.3)))*24634.6);
float bl = frac(sin(dot(floor(P.xy*0.09), float2(31.7, 71.3)))*9137.4);
win *= side * step(0.52, cellr*0.5 + bl*0.6);

OutE = float3(1.00, 0.60, 0.26) * win * 34.0;
OutR = lerp(0.74, 0.42, sn);
return base;
"""

def build_town_material():
    b = MatBuilder("/Game/M", "M_Town")
    b.mat.set_editor_property("tangent_space_normal", False)
    wp = b.n(unreal.MaterialExpressionWorldPosition, -1800, 0)
    vn = b.n(unreal.MaterialExpressionVertexNormalWS, -1800, 200)
    F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1
    F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3
    c = b.custom(TOWN_HLSL, ["WP","VN"], F3, [("OutE", F3), ("OutR", F1)], "town")
    b.link(wp,"",c,"WP"); b.link(vn,"",c,"VN")
    MP = unreal.MaterialProperty
    b.prop(c, "", MP.MP_BASE_COLOR)
    b.prop(c, "OutE", MP.MP_EMISSIVE_COLOR)
    b.prop(c, "OutR", MP.MP_ROUGHNESS)
    return b.done()

M_town = build_town_material()

# ------------------------------------------------------------------ falling snow
SNOW_PP_HLSL = r"""
// Screen-space falling snow, depth aware. Niagara is the right tool and is not
// scriptable headless; this is the stand-in and NOTES.md says so.
float2 uv = UV;
float d = max(SD, 1.0) * 0.01;
float acc = 0;
for (int i = 0; i < 3; i++)
{
    float layer = (float)i;
    float sc = 22.0 * pow(2.2, layer);
    float2 p = float2(uv.x*1.7777, uv.y) * sc;
    p.y += TIME * (0.45 + 0.40*layer);
    p.x += sin(TIME*0.5 + layer*2.0 + p.y*0.35) * 0.5;
    float2 ip = floor(p), fp = frac(p);
    float h  = frac(sin(dot(ip, float2(27.13, 61.7)) + layer*13.0) * 43758.5453);
    float h2 = frac(h*197.31);
    float2 ctr = float2(0.2+0.6*h, 0.2+0.6*h2);
    float r = length(fp - ctr);
    float rad = 0.050 + 0.085*h2;
    float flake = smoothstep(rad, rad*0.2, r);
    flake *= step(0.66, frac(h*53.7));
    acc += flake * saturate(1.0 - layer*0.30) * saturate(d/8.0);
}
return SCN + float3(acc, acc, acc) * DENS;
"""

def build_snow_pp():
    b = MatBuilder("/Game/M", "PP_Snow")
    b.mat.set_editor_property("material_domain", unreal.MaterialDomain.MD_POST_PROCESS)
    uv  = b.n(unreal.MaterialExpressionTextureCoordinate, -1800, 0)
    sd  = b.n(unreal.MaterialExpressionSceneDepth, -1800, 200)
    tm  = b.n(unreal.MaterialExpressionTime, -1800, 400)
    dn  = b.n(unreal.MaterialExpressionScalarParameter, -1800, 600)
    dn.set_editor_property("parameter_name", "Density")
    dn.set_editor_property("default_value", 0.85)
    scn = b.n(unreal.MaterialExpressionSceneTexture, -1800, 800)
    scn.set_editor_property("scene_texture_id", unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3
    c = b.custom(SNOW_PP_HLSL, ["UV","SD","TIME","DENS","SCN"], F3, None, "snow")
    b.link(uv,"",c,"UV"); b.link(sd,"",c,"SD"); b.link(tm,"",c,"TIME")
    b.link(dn,"",c,"DENS"); b.link(scn,"Color",c,"SCN")
    b.prop(c, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return b.done()

M_snowpp = build_snow_pp()
log("materials built")

# ------------------------------------------------------------------ meshes
SM = {}
for k, steps in (("main", 2048), ("near", 1536), ("back", 768)):
    m = meta[k]
    SM[k] = make_terrain_mesh("/Game/M", "SM_" + k, tex[k+"_h"],
                              m["extent"], steps, m["lo"], m["hi"], nanite=True,
                              z_offset_m=(-1.2 if k == "main" else (-9.0 if k == "back" else 0.0)),
                              force=FORCE)
log("meshes ready")

# ------------------------------------------------------------------ actors
def place(k, loc):
    a = spawn(unreal.StaticMeshActor, loc, (0,0,0), "T_"+k)
    c = a.static_mesh_component
    c.set_static_mesh(SM[k])
    c.set_material(0, MI[k])
    return a

place("main", (0, 0, 0))
place("back", (0, 0, 0))
nm = meta["near"]
place("near", (nm.get("cx", 0.0)*100.0, nm.get("cy", 0.0)*100.0, 5.0))

sun = spawn(unreal.DirectionalLight, (0, 0, 200000), (0,0,0), "Sun")
sr = unreal.Rotator(); sr.set_editor_property("pitch", -3.4); sr.set_editor_property("yaw", 168.0)
sun.set_actor_rotation(sr, False)
sc = sun.get_component_by_class(unreal.DirectionalLightComponent)
sc.set_mobility(unreal.ComponentMobility.MOVABLE)
setp(sc, "intensity", 110000.0)
setp(sc, "light_source_angle", 0.72)
setp(sc, "atmosphere_sun_light", True)
setp(sc, "dynamic_shadow_distance_movable_light", 900000.0)
setp(sc, "dynamic_shadow_cascades", 4)
setp(sc, "cascade_distribution_exponent", 3.6)
setp(sc, "cast_volumetric_shadow", True)

sky = spawn(unreal.SkyAtmosphere, (0, 0, 0), (0,0,0), "Atmosphere")
skc = sky.get_component_by_class(unreal.SkyAtmosphereComponent)
setp(skc, "aerial_pespective_view_distance_scale", 2.2)
setp(skc, "multi_scattering_factor", 0.9)

sl = spawn(unreal.SkyLight, (0, 0, 60000), (0,0,0), "SkyLight")
slc = sl.get_component_by_class(unreal.SkyLightComponent)
slc.set_mobility(unreal.ComponentMobility.MOVABLE)
setp(slc, "real_time_capture", True)
setp(slc, "volumetric_scattering_intensity", 1.0)

cl = spawn(unreal.VolumetricCloud, (0, 0, 0), (0,0,0), "Clouds")
clc = cl.get_component_by_class(unreal.VolumetricCloudComponent)
setp(clc, "layer_bottom_altitude", 3.4)
setp(clc, "layer_height", 5.0)

fog = spawn(unreal.ExponentialHeightFog, (0, 0, 0), (0,0,0), "Fog")
fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
setp(fc, "fog_density", 0.022)
setp(fc, "fog_height_falloff", 0.055)
setp(fc, "fog_max_opacity", 0.85)
setp(fc, "directional_inscattering_exponent", 24.0)
setp(fc, "directional_inscattering_start_distance", 20000.0)
setp(fc, "directional_inscattering_luminance", unreal.LinearColor(0.55, 0.42, 0.35, 1.0))
setp(fc, "second_fog_data", unreal.ExponentialHeightFogData(fog_density=0.010, fog_height_falloff=0.30, fog_height_offset=-40.0))
setp(fc, "fog_inscattering_luminance", unreal.LinearColor(0.30, 0.44, 0.72, 1.0))
[setp(fc, n, True) for n in ("volumetric_fog","enable_volumetric_fog","b_enable_volumetric_fog")]
setp(fc, "volumetric_fog_scattering_distribution", 0.35)
setp(fc, "volumetric_fog_extinction_scale", 1.0)
setp(fc, "volumetric_fog_distance", 90000.0)

ppv = spawn(unreal.PostProcessVolume, (0, 0, 0), (0,0,0), "PP")
ppv.set_editor_property("unbound", True)
s = ppv.get_editor_property("settings")
def sp(k, v, ov=None):
    try:
        if ov: s.set_editor_property(ov, True)
        s.set_editor_property(k, v)
    except Exception as e:
        log("pp %s failed %r" % (k, e))
sp("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL, "override_auto_exposure_method")
sp("auto_exposure_bias", -3.0, "override_auto_exposure_bias")
sp("dynamic_global_illumination_method", unreal.DynamicGlobalIlluminationMethod.LUMEN,
   "override_dynamic_global_illumination_method")
sp("reflection_method", unreal.ReflectionMethod.LUMEN, "override_reflection_method")
sp("lumen_scene_lighting_quality", 2.0, "override_lumen_scene_lighting_quality")
sp("lumen_final_gather_quality", 2.0, "override_lumen_final_gather_quality")
sp("lumen_max_trace_distance", 900000.0, "override_lumen_max_trace_distance")
sp("bloom_intensity", 0.40, "override_bloom_intensity")
sp("motion_blur_amount", 0.0, "override_motion_blur_amount")
sp("vignette_intensity", 0.30, "override_vignette_intensity")
try:
    wb = unreal.WeightedBlendable()
    wb.set_editor_property("weight", 1.0)
    wb.set_editor_property("object", M_snowpp)
    wbs = unreal.WeightedBlendables()
    wbs.set_editor_property("array", [wb])
    s.set_editor_property("weighted_blendables", wbs)
except Exception as e:
    log("snow pp attach failed: %r" % (e,))
ppv.set_editor_property("settings", s)
log("lighting in")

# ------------------------------------------------------------------ town
town = json.load(open(os.path.join(GEN, "town.json")))
if unreal.EditorAssetLibrary.does_asset_exist("/Game/M/SM_box"):
    cube = unreal.EditorAssetLibrary.load_asset("/Game/M/SM_box")
else:
    box = unreal.DynamicMesh()
    box = unreal.GeometryScript_Primitives.append_box(
        box, unreal.GeometryScriptPrimitiveOptions(), unreal.Transform(),
        100.0, 100.0, 100.0, 1, 1, 1, unreal.GeometryScriptPrimitiveOriginMode.CENTER)
    bo = unreal.GeometryScriptCreateNewStaticMeshAssetOptions()
    bo.enable_nanite = True; bo.enable_recompute_normals = True
    bo.enable_recompute_tangents = True; bo.enable_collision = False
    cube, _ = unreal.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(
        box, "/Game/M/SM_box", bo)
    unreal.EditorAssetLibrary.save_asset("/Game/M/SM_box", only_if_is_dirty=False)

def put_boxes(items, mat, tag):
    n = 0
    for it in items:
        r = unreal.Rotator()
        r.set_editor_property("yaw", float(it.get("yaw", 0.0)))
        a = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(it["x"]*100.0, it["y"]*100.0, (it["z"] + it["sz"]*0.5)*100.0), r)
        c = a.static_mesh_component
        c.set_static_mesh(cube)
        c.set_material(0, mat)
        a.set_actor_scale3d(unreal.Vector(it["sx"], it["sy"], it["sz"]))
        n += 1
    log("%s: %d" % (tag, n))

put_boxes(town["buildings"], M_town, "buildings")
put_boxes(town["roads"], M_town, "roads")

# ------------------------------------------------------------------ cameras
cams = json.load(open(os.path.join(GEN, "cams.json")))
for c in cams:
    r = unreal.Rotator()
    r.set_editor_property("pitch", float(c["pitch"]))
    r.set_editor_property("yaw", float(c["yaw"]))
    r.set_editor_property("roll", 0.0)
    a = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.CameraActor, unreal.Vector(c["x"]*100.0, c["y"]*100.0, c["z"]*100.0), r)
    a.set_actor_label("CAM_" + c["name"])
    a.get_component_by_class(unreal.CameraComponent).set_editor_property("field_of_view", float(c["fov"]))
log("cameras: %d" % len(cams))

w = unreal.EditorLevelLibrary.get_editor_world()
acts = unreal.EditorLevelLibrary.get_all_level_actors()
log("world=%s actors=%d" % (w.get_path_name() if w else None, len(acts)))
ok1 = les.save_current_level()
log("save_current_level -> %s" % ok1)
try:
    ok2 = unreal.EditorLoadingAndSavingUtils.save_map(w, "/Game/Maps/Valley")
    log("save_map -> %s" % ok2)
except Exception as e:
    log("save_map err %r" % (e,))
try:
    log("save_dirty -> %s" % unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True))
except Exception as e:
    log("save_dirty err %r" % (e,))
log("VALLEY BUILD DONE")
