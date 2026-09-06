"""A cave to stand in, lights, camera, and render settings."""
import math
import random
import bpy
from mathutils import Vector
from . import geometry as G
from . import materials as M


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    return sc


def cave(radius=3.4, seed=3):
    col = G.new_collection("CAVE")
    rock = M.wet_rock()
    floor = G.plane("floor", radius * 3, (0, 0, 0), col=col, subdiv=60)
    disp = floor.modifiers.new("disp", "DISPLACE")
    tex = bpy.data.textures.new("floor_noise", "CLOUDS"); tex.noise_scale = 0.9; tex.noise_depth = 4
    disp.texture = tex; disp.strength = 0.10; disp.mid_level = 0.72
    floor.data.shade_smooth()
    G.set_material(floor, rock)
    # a flattened patch so the feet sit on something level near the origin
    sub = floor.modifiers.new("subsurf", "SUBSURF"); sub.levels = sub.render_levels = 1
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=radius, location=(0.6, 0, 1.2))
    dome = bpy.context.object; dome.name = "cave_walls"
    dome.scale = (1.6, 1.25, 0.8)
    bpy.ops.object.transform_apply(scale=True)
    d2 = dome.modifiers.new("disp", "DISPLACE")
    tex2 = bpy.data.textures.new("wall_noise", "CLOUDS"); tex2.noise_scale = 0.9; tex2.noise_depth = 6
    d2.texture = tex2; d2.strength = 1.4
    tex3 = bpy.data.textures.new("rock_noise", "CLOUDS"); tex3.noise_scale = 0.18; tex3.noise_depth = 5
    dome.data.shade_smooth()
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.flip_normals(); bpy.ops.object.mode_set(mode="OBJECT")
    G.set_material(dome, rock)
    for c in dome.users_collection:
        c.objects.unlink(dome)
    col.objects.link(dome)
    rng = random.Random(seed)
    for i in range(14):
        r = rng.uniform(0.08, 0.35)
        a = rng.uniform(0, 2 * math.pi); d = rng.uniform(1.2, 3.5)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=r, location=(math.cos(a) * d, math.sin(a) * d, r * 0.45))
        rk = bpy.context.object; rk.name = f"rock.{i}"
        rk.scale = (rng.uniform(0.7, 1.5), rng.uniform(0.7, 1.5), rng.uniform(0.4, 0.8))
        rk.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
        m = rk.modifiers.new("disp", "DISPLACE"); m.texture = tex3; m.strength = r * 0.9
        rk.data.shade_smooth()
        G.set_material(rk, rock)
        for c in rk.users_collection:
            c.objects.unlink(rk)
        col.objects.link(rk)
    # world: almost black with a whisper of blue, thin fog so the head lamp shows a beam
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes.get("Background") or nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.004, 0.006, 0.01, 1); bg.inputs["Strength"].default_value = 1.0
    out = nt.nodes.get("World Output") or nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    vol = nt.nodes.new("ShaderNodeVolumeScatter"); vol.inputs["Density"].default_value = 0.006
    vol.inputs["Anisotropy"].default_value = 0.4
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    return col


def lights(target=(0.1, 0, 0.35)):
    col = G.new_collection("LIGHTS")

    def area(name, loc, energy, color, size):
        d = bpy.data.lights.new(name, "AREA"); d.energy = energy; d.color = color; d.size = size
        o = bpy.data.objects.new(name, d); col.objects.link(o); o.location = loc
        tr = o.constraints.new("TRACK_TO"); tr.track_axis = "TRACK_NEGATIVE_Z"; tr.up_axis = "UP_Y"
        tgt = bpy.data.objects.new(name + "_aim", None); col.objects.link(tgt); tgt.location = target
        tr.target = tgt
        return o
    t = Vector(target)
    area("rim", t + Vector((-2.0, 1.4, 1.5)), 320, (0.55, 0.75, 1.0), 0.6)     # cold rim from behind-left
    area("key", t + Vector((1.4, -1.8, 1.6)), 22, (1.0, 0.85, 0.7), 1.0)       # faint warm key
    area("fill", t + Vector((0.3, 2.2, 0.4)), 6, (0.4, 0.6, 0.9), 2.5)
    area("under", t + Vector((0.8, -0.6, -0.1)), 4, (0.3, 0.8, 1.0), 1.5)      # a little bounce off the floor
    return col


def camera(follow, aim_offset=(0.1, 0, 0.32), frame=1, dist=2.1, azimuth_deg=-38, elevation_deg=14, focal=50, fstop=4.0):
    """Camera fixed in the world, placed relative to where `follow` (the armature) is at
    `frame`, and always aimed at its body. Azimuth is relative to the body's heading."""
    sc = bpy.context.scene
    sc.frame_set(frame)
    body = Vector(follow.matrix_world.translation)
    yaw = follow.rotation_euler.z
    cd = bpy.data.cameras.new("CAM"); cd.lens = focal
    cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
    cam = bpy.data.objects.new("CAM", cd)
    sc.collection.objects.link(cam)
    az, el = math.radians(azimuth_deg) + yaw, math.radians(elevation_deg)
    look_at = body + Vector((0, 0, aim_offset[2]))
    cam.location = look_at + Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * dist
    tgt = bpy.data.objects.new("CAM_aim", None); sc.collection.objects.link(tgt)
    tgt.parent = follow; tgt.location = aim_offset
    tr = cam.constraints.new("TRACK_TO"); tr.target = tgt; tr.track_axis = "TRACK_NEGATIVE_Z"; tr.up_axis = "UP_Y"
    cd.dof.focus_object = tgt
    bpy.context.scene.camera = cam
    return cam


def settings(samples=96, res=(1600, 1000), engine="CYCLES"):
    sc = bpy.context.scene
    sc.render.engine = engine
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    if engine == "CYCLES":
        cy = sc.cycles
        cy.device = "CPU"
        cy.samples = samples
        cy.use_denoising = True
        cy.max_bounces = 6; cy.volume_bounces = 1
        cy.volume_step_rate = 2.0; cy.volume_max_steps = 256
        cy.use_adaptive_sampling = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.render.film_transparent = False


def render_still(path, frame=None):
    sc = bpy.context.scene
    if frame is not None:
        sc.frame_set(frame)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def render_video(path, start=None, end=None, fps=24):
    """An H.264 MP4. Blender's own encoder when it has one (a normal install);
    otherwise PNG frames stitched by imageio-ffmpeg (the pip bpy module has no FFmpeg)."""
    sc = bpy.context.scene
    formats = {e.identifier for e in bpy.types.ImageFormatSettings.bl_rna.properties["file_format"].enum_items}
    if "FFMPEG" not in formats:
        import os
        frames_dir = os.path.splitext(path)[0] + "_frames"
        os.makedirs(frames_dir, exist_ok=True)
        render_animation(os.path.join(frames_dir, "f_"), start, end, 1)
        import imageio.v2 as iio
        names = sorted(f for f in os.listdir(frames_dir) if f.endswith(".png"))
        with iio.get_writer(path, fps=fps, codec="libx264", quality=8, macro_block_size=8) as w:
            for n in names:
                w.append_data(iio.imread(os.path.join(frames_dir, n)))
        return
    sc.render.image_settings.file_format = "FFMPEG"
    sc.render.ffmpeg.format = "MPEG4"
    sc.render.ffmpeg.codec = "H264"
    sc.render.ffmpeg.constant_rate_factor = "MEDIUM"
    sc.render.ffmpeg.gopsize = 12
    sc.render.fps = fps
    if start is not None:
        sc.frame_start = start
    if end is not None:
        sc.frame_end = end
    sc.frame_step = 1
    sc.render.filepath = path
    bpy.ops.render.render(animation=True)
    sc.render.image_settings.file_format = "PNG"


def render_animation(path_pattern, start=None, end=None, step=1):
    sc = bpy.context.scene
    if start is not None:
        sc.frame_start = start
    if end is not None:
        sc.frame_end = end
    sc.frame_step = step
    sc.render.filepath = path_pattern
    bpy.ops.render.render(animation=True)
