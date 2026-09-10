import unreal, os, sys, json, time
sys.path.append(r"C:/Users/jackh/documents/programming/Blindside/spikes/unreal/look/tools")
from ue_common import *

LEVEL = os.environ.get("BS_LEVEL", "/Game/Maps/Valley")
SHOTS = os.path.join(ROOT, "shots")
ONLY  = os.environ.get("BS_ONLY", "")
EV    = os.environ.get("BS_EV", "")
WARM  = int(os.environ.get("BS_WARM", "40"))
SS = int(os.environ.get("BS_SS", "2"))
W, H  = 1920*SS, 1080*SS
os.makedirs(SHOTS, exist_ok=True)

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level(LEVEL)
world = unreal.EditorLevelLibrary.get_editor_world()

for cmd in ["r.ScreenPercentage 100",
            "r.AntiAliasingMethod 0",
            "r.Lumen.ScreenProbeGather.RadianceCache.ProbeResolution 32",
            "r.Lumen.TraceMeshSDFs 1",
            "r.Lumen.ScreenProbeGather.DownsampleFactor 8",
            "r.SkyLight.RealTimeReflectionCapture 1",
            "r.VolumetricFog.GridPixelSize 4",
            "r.VolumetricFog.GridSizeZ 160",
            "r.Shadow.Virtual.ResolutionLodBiasDirectional -1.5",
            "r.Nanite.MaxPixelsPerEdge 0.5",
            "r.Streaming.PoolSize 3000",
            "foliage.DitheredLOD 0"]:
    unreal.SystemLibrary.execute_console_command(world, cmd)

PPVS = [a for a in unreal.EditorLevelLibrary.get_all_level_actors()
        if isinstance(a, unreal.PostProcessVolume)]
def set_ev(v):
    for a in PPVS:
        st = a.get_editor_property("settings")
        st.set_editor_property("override_auto_exposure_bias", True)
        st.set_editor_property("auto_exposure_bias", float(v))
        a.set_editor_property("settings", st)
if EV:
    set_ev(EV)
BRACKET = os.environ.get("BS_BRACKET", "")

# render target + capture
rt = unreal.RenderingLibrary.create_render_target2d(world, W, H,
        unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cap = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.SceneCapture2D, unreal.Vector(0,0,0), unreal.Rotator(0,0,0))
cc = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
cc.set_editor_property("texture_target", rt)
cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
cc.set_editor_property("capture_every_frame", False)
cc.set_editor_property("capture_on_movement", False)
cc.set_editor_property("always_persist_rendering_state", True)
cc.set_editor_property("post_process_blend_weight", 0.0)
cc.set_editor_property("primitive_render_mode",
        unreal.SceneCapturePrimitiveRenderMode.PRM_RENDER_SCENE_PRIMITIVES)
sf = cc.get_editor_property("show_flag_settings")
cc.set_editor_property("use_ray_tracing_if_enabled", False)

cams = [a for a in unreal.EditorLevelLibrary.get_all_level_actors()
        if isinstance(a, unreal.CameraActor) and a.get_actor_label().startswith("CAM_")]
cams.sort(key=lambda a: a.get_actor_label())
log("cameras found: %d" % len(cams))

for a in cams:
    nm = a.get_actor_label()[4:]
    if ONLY and ONLY not in nm:
        continue
    cap.set_actor_location_and_rotation(a.get_actor_location(), a.get_actor_rotation(), False, True)
    cc.set_editor_property("fov_angle", a.get_component_by_class(unreal.CameraComponent).get_editor_property("field_of_view"))
    evs = [x for x in BRACKET.split(",") if x] or [None]
    for ev in evs:
        if ev is not None:
            set_ev(ev)
        t0 = time.time()
        for i in range(WARM):
            cc.capture_scene()
        suffix = ("_ev%s" % ev) if ev is not None else ""
        unreal.RenderingLibrary.export_render_target(world, rt, SHOTS, nm + suffix + ".png")
        log("shot %s%s  %.1fs" % (nm, suffix, time.time()-t0))

log("SHOOT DONE")
