import unreal, os, sys, json, time
sys.path.append(r"C:/Users/jackh/documents/programming/Blindside/spikes/unreal/look/tools")
from ue_common import *

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/Maps/Valley")
world = unreal.EditorLevelLibrary.get_editor_world()

acts = unreal.EditorLevelLibrary.get_all_level_actors()
log("actors %d" % len(acts))
for a in acts:
    lbl = a.get_actor_label()
    if lbl.startswith("T_"):
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        sm = c.static_mesh
        log("%s mesh=%s tris=%s nanite=%s bounds=%s loc=%s mat=%s" % (
            lbl, sm.get_name() if sm else None,
            sm.get_num_triangles(0) if sm else -1,
            sm.get_editor_property("nanite_settings").get_editor_property("enabled") if sm else "?",
            sm.get_bounding_box() if sm else None,
            a.get_actor_location(),
            c.get_material(0).get_name() if c.get_material(0) else None))

# a plain engine cube 6 m in front of the first camera
cams = sorted([a for a in acts if isinstance(a, unreal.CameraActor)],
              key=lambda x: x.get_actor_label())
cam = cams[0]
loc = cam.get_actor_location()
fwd = cam.get_actor_forward_vector()
cube = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube")
probe = unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.StaticMeshActor,
    unreal.Vector(loc.x + fwd.x*600, loc.y + fwd.y*600, loc.z + fwd.z*600),
    unreal.Rotator(0,0,0))
probe.get_component_by_class(unreal.StaticMeshComponent).set_static_mesh(cube)
probe.set_actor_scale3d(unreal.Vector(2,2,2))
log("probe cube at %s (cam %s fwd %s)" % (probe.get_actor_location(), loc, fwd))

# line trace straight down from the camera to see if terrain collision/geometry is there
for cmd in ["r.ScreenPercentage 100", "r.AntiAliasingMethod 0"]:
    unreal.SystemLibrary.execute_console_command(world, cmd)

rt = unreal.RenderingLibrary.create_render_target2d(world, 1280, 720,
        unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cap = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.SceneCapture2D, unreal.Vector(0,0,0), unreal.Rotator(0,0,0))
cc = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
cc.set_editor_property("texture_target", rt)
cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
cc.set_editor_property("capture_every_frame", False)
cc.set_editor_property("always_persist_rendering_state", True)
cc.set_editor_property("post_process_blend_weight", 0.0)
cap.set_actor_location_and_rotation(loc, cam.get_actor_rotation(), False, True)
cc.set_editor_property("fov_angle", 62.0)

for label, cmds in (("nanite_on",  []),
                    ("nanite_off", ["r.Nanite 0"]),
                    ("unlit",      ["r.Nanite 1", "showflag.Lighting 0"])):
    for c in cmds:
        unreal.SystemLibrary.execute_console_command(world, c)
    for i in range(12):
        cc.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, os.path.join(ROOT, "shots"),
                                                 "diag_" + label + ".png")
    log("diag " + label)
log("DIAG DONE")
