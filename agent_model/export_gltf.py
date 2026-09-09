"""Get the agent out of Blender: one .glb with the armature and one baked clip.

The model itself is not changed by anything in this file. Everything here runs
on the already-built scene, in this order:

  1. BAKE THE CONSTRAINTS. `build.py` drives the legs with IK to world-space
     FOOT empties and the head with track constraints to a LOOK empty. glTF has
     no constraints and no IK, so the pose has to be resolved to plain FK
     rotations on every bone of every frame before it can leave Blender. That
     is `nla.bake` with `visual_keying`, and it is the whole reason this file
     exists.
  2. ADD A `root` BONE. The body's own motion lives on the armature OBJECT, not
     on a bone, and the hull meshes are parented to the object rather than to a
     bone. A skinned glTF mesh needs every vertex to name a joint, so a single
     unanimated bone is added at the armature origin for them to name. It has
     no children and no keyframes, so it changes nothing about the rig.
  3. CONVERT BONE PARENTING TO VERTEX GROUPS. `build.py` parents ~150 separate
     mesh objects to bones. Exported as-is those arrive in Godot as ~150
     BoneAttachment3D nodes and ~150 draw calls. Rigid weights (every vertex of
     a part at weight 1.0 on its part's bone) say exactly the same thing as one
     skinned mesh, which is one draw call per material.
  4. BAKE THE ART-DIRECTION 4.1 WEAR MASKS INTO VERTEX COLOURS, and the part's
     material identity into the alpha. ART 4.1's finding is that the masks must
     have GRAVITY AND DIRECTION in them; gravity and direction are properties
     of the geometry, so they are computed here, on the rest geometry, and
     travel with the mesh:
         COLOR.r  mud    1 at the feet, 0 above the hull seam
         COLOR.g  dust   max(0, N.z)^3      (Blender's up)
         COLOR.b  scuff  max(0, N.x)^1.5    (Blender's forward)
         COLOR.a  part identity, index/15 -- see PART_INDEX
     and UV `meta`:
         u        emissive element index / 16 (the sonar bar's seven)
         v        exposure: how reachable this face is
     Baking on the REST normal is deliberate. Wear is HISTORY (ART 4.2), and
     the history of a femur blade's outboard face is its average orientation,
     not its orientation on this frame.
  5. JOIN, and strip the world travel so the clip is in place.

Blender materials are NOT meant to survive the trip. The surfacing is rebuilt
in Godot against ART-DIRECTION 4; the alpha channel above is what tells the
Godot shader which part it is looking at.
"""
import math
import os

import bpy
from mathutils import Matrix, Vector

# The part identity that survives the trip. Index / 15 goes in COLOR.a, so a
# 16-step quantisation anywhere on the path is still exact.
PART_INDEX = {
    "shell": 0,        # pale top shell            -- LIVERIED
    "chassis": 1,      # graphite lower body       -- LIVERIED
    "accent": 2,
    "metal": 3,        # bare metal, hull grade
    "dark": 4,
    "carbon": 5,       # the leg material: its bare colour must stay DARK (4.1)
    "rubber": 6,
    "sonar": 7,        # one element of the seven-element bar
    "eye": 8,          # the lamp emitter disc
    "lens": 9,
    "glass": 10,
    "estop": 11,       # painted, and NEVER emissive (ART 4.2)
    "retro": 12,       # the running lights -- see ART 4.5
    "pilot": 13,       # the tail status light
    "cap": 14,         # a beacon cap
    "reflector": 15,   # the lamp's dark housing
}

# How reachable a part is by mud, dust and a rock wall. 1.0 = a deck.
EXPOSE = {
    "rubber": 1.0, "carbon": 1.0, "metal": 0.9, "shell": 1.0,
    "chassis": 0.9, "dark": 0.7, "accent": 0.8, "lens": 0.25,
    "glass": 0.25, "sonar": 0.3, "eye": 0.2, "estop": 0.6,
    "retro": 0.5, "pilot": 0.4, "cap": 0.5, "reflector": 0.4,
}


def _part_key(obj, mat_name):
    """Which PART_INDEX this object is. Material name first, then the object
    name where one material covers two jobs -- `light` is both the running
    light strip and the sonar bar, and ART 4.5 wants them to be different
    things."""
    n = obj.name
    if "sonar_el" in n:
        return "sonar"
    if n.startswith("strip."):
        return "retro"
    if n.startswith("status_light"):
        return "pilot"
    if "beacon_cap" in n:
        return "cap"
    if "_reflector" in n:
        return "reflector"
    base = mat_name.split(".")[0] if mat_name else "chassis"
    for k in ("shell_paint", "chassis_paint"):
        if base == k:
            return k.split("_")[0]
    if base in PART_INDEX:
        return base
    if base == "light":
        return "retro"
    if base in ("dark_metal",):
        return "dark"
    if base in ("dark_glass",):
        return "glass"
    if base.startswith("estop"):
        return "estop"
    if base.startswith("bare") or base.startswith("metal"):
        return "metal"
    return "chassis"


# ART 4.2 rungs 0.30 and 0.50 shed a part. Object names do not survive the
# join, so the parts that can be shed carry a stable id out in the UV instead,
# and the Godot shader discards them. Nothing is deleted here: damage is
# runtime state, not export state.
SHED_ID = {
    "hatch_battery": 9,     # rung 0.50: "a hull panel is simply not built"
    "belt_cover.0": 10,     # rung 0.30: "one hip actuator sheds its cover"
    "hatch_compute": 11,
}


def _element_index(obj):
    """1..7 for the sonar bar's elements, 1..4 for beacon caps, 9..11 for the
    parts damage may shed, else 0."""
    n = obj.name
    if n in SHED_ID:
        return SHED_ID[n]
    for tag in ("sonar_el", "beacon_cap"):
        if tag in n:
            tail = n.split(tag)[1]
            digits = ""
            for ch in tail:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            if digits:
                return int(digits) + 1
    return 0


# ---------------------------------------------------------------------------
def _bake_constraints(arm, f0, f1):
    """Resolve IK and the track constraints to plain FK keys on every bone.

    Without this the exported clip is a T-pose: glTF carries no constraint and
    no solver, so an un-baked rig arrives in Godot with the body animated and
    the legs rigid."""
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    # Blender 5.x removed `Bone.select`; the operator is the portable way, and
    # `only_selected=False` below means the selection is belt and braces.
    try:
        bpy.ops.pose.select_all(action="SELECT")
    except RuntimeError:
        pass
    bpy.ops.nla.bake(
        frame_start=f0, frame_end=f1, step=1,
        only_selected=False, visual_keying=True,
        clear_constraints=True, clear_parents=False,
        use_current_action=True, bake_types={"POSE", "OBJECT"},
    )
    bpy.ops.object.mode_set(mode="OBJECT")


def _add_root_bone(arm, name="root"):
    """One unanimated bone at the armature origin, for the hull meshes to name.
    No parent, no children, no keys: the rig is unchanged."""
    if name in arm.data.bones:
        return name
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    b = arm.data.edit_bones.new(name)
    b.head = Vector((0, 0, 0))
    b.tail = Vector((0, 0, 0.08))
    bpy.ops.object.mode_set(mode="OBJECT")
    return name


def _stamp_meta(obj, key, z_seam):
    """Everything Godot needs about this part, written into TWO UV LAYERS.

    MEASURED, twice, and both measurements are why this is not in a colour
    attribute. (1) `object.join()` keeps the ACTIVE object's colour attribute
    and defaults the other 149 to flat white, whatever `active_color_name`
    says. (2) Even with the attribute baked correctly on the JOINED mesh --
    verified by reading all 11,850 values back -- Blender's glTF exporter
    writes real COLOR_0 for the first primitive and 1,1,1,1 for the other
    eleven. UV layers survive both, so the four channels live there:

        UV .x   (part * 16 + element) / 256   part identity and shed id
        UV .y   mud    1 at the feet, 0 above the hull seam
        UV2.x   dust   max(0, N.z)^3      (Blender's up)
        UV2.y   scuff  max(0, N.x)^1.5    (Blender's forward)

    ART 4.1 diagnoses every earlier wear pass as having "no gravity and no
    direction in it". Gravity and direction are properties of the geometry, so
    they are computed on the geometry, here, once, and travel with the mesh.

    The masks use the POLYGON normal, not the averaged vertex normal: these are
    flat-shaded machined parts, and the averaged normal at a box corner points
    along the diagonal, which would put dust on a vertical face.

    Baked on the REST geometry deliberately -- wear is HISTORY (ART 4.2), and
    the history of a femur blade's outboard face is its average orientation,
    not its orientation on any one frame."""
    me = obj.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    while me.color_attributes:
        me.color_attributes.remove(me.color_attributes[0])
    me.uv_layers.new(name="meta")
    me.uv_layers.new(name="wear")

    mw = obj.matrix_world
    nm = mw.to_3x3().inverted().transposed()
    ident = (PART_INDEX[key] * 16 + _element_index(obj)) / 256.0
    span = max(0.02, z_seam)
    n_loops = len(me.loops)
    a = [0.0] * (n_loops * 2)
    b = [0.0] * (n_loops * 2)
    for poly in me.polygons:
        n = (nm @ poly.normal).normalized()
        dust = max(0.0, n.z) ** 3.0
        scuff = max(0.0, n.x) ** 1.5
        for li in poly.loop_indices:
            p = mw @ me.vertices[me.loops[li].vertex_index].co
            mud = min(1.0, max(0.0, 1.0 - p.z / span)) ** 2.2
            a[li * 2] = ident
            # MEASURED: the glTF exporter flips V (glTF's UV origin is top
            # left, Blender's is bottom left) and does not touch U. So the two
            # values that ride in V are written inverted here and arrive the
            # right way up, and nothing downstream has to know.
            a[li * 2 + 1] = 1.0 - mud
            b[li * 2] = dust
            b[li * 2 + 1] = 1.0 - scuff
    me.uv_layers["meta"].uv.foreach_set("vector", a)
    me.uv_layers["wear"].uv.foreach_set("vector", b)


def _apply_modifiers(obj):
    """Apply everything except the armature. `build.py` puts BEVEL modifiers on
    the hull and the shell, and the chamfer they cut is most of what makes the
    body read as a pressed enclosure rather than a box. The glTF exporter has
    to run with export_apply=False (it would otherwise apply the armature and
    destroy the skin), so the bevels have to be applied here or they are simply
    not in the file."""
    bpy.context.view_layer.objects.active = obj
    for m in list(obj.modifiers):
        if m.type == "ARMATURE":
            continue
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except RuntimeError:
            obj.modifiers.remove(m)


def _rigid_skin(objs, arm, root_bone, z_seam):
    """Bone parenting -> vertex groups at weight 1.0, and the identity stamp.

    THE ARMATURE IS FORCED TO REST FIRST, and this is not a nicety. `nla.bake`
    leaves the scene on the last baked frame, and a bone-parented object's
    `matrix_world` is its POSED world matrix. Converting on a posed rig bakes
    the last frame of the walk into the mesh -- every part frozen where that
    frame put it -- and then the armature modifier deforms it a second time.
    The mud mask is measured against height, so it also comes out reading the
    posed height rather than the standing one."""
    prev_pose = arm.data.pose_position
    prev_mat = arm.matrix_basis.copy()
    arm.data.pose_position = "REST"
    arm.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    meshes = []
    for obj in objs:
        if obj.type != "MESH":
            continue
        bone = obj.parent_bone if obj.parent_type == "BONE" else root_bone
        if bone not in arm.data.bones:
            bone = root_bone
        mw = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = mw
        _apply_modifiers(obj)
        mat_name = obj.data.materials[0].name if obj.data.materials else ""
        _stamp_meta(obj, _part_key(obj, mat_name), z_seam)
        obj.vertex_groups.clear()
        vg = obj.vertex_groups.new(name=bone)
        vg.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
        obj.parent = arm
        obj.matrix_parent_inverse = Matrix.Identity(4)
        md = obj.modifiers.new("skin", "ARMATURE")
        md.object = arm
        meshes.append(obj)
    arm.data.pose_position = prev_pose
    arm.matrix_basis = prev_mat
    bpy.context.view_layer.update()
    return meshes


def _join(meshes, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    j = bpy.context.view_layer.objects.active
    j.name = name
    return j


def _in_place(arm):
    """Strip the world travel from the clip and keep the bob, the pitch and the
    roll. The gait plants feet in WORLD space, so removing the body's forward
    translation leaves the stance feet travelling backwards under the body at
    exactly the gait's speed -- which is what a loopable in-place cycle is. The
    caller moves the machine forward at that speed and the feet plant.

    Only location x/y and rotation z are flattened. `_key_all` puts the bob on
    location z and the pitch and roll on rotation x/y, and those are the gait,
    not the travel."""
    ad = arm.animation_data
    if not ad or not ad.action:
        return
    for fc in _all_fcurves(ad.action):
        if fc.data_path == "location" and fc.array_index in (0, 1):
            if not fc.keyframe_points:
                continue
            v0 = fc.keyframe_points[0].co[1]
            for kp in fc.keyframe_points:
                kp.co[1] = v0
                kp.handle_left[1] = v0
                kp.handle_right[1] = v0
        elif fc.data_path == "rotation_euler" and fc.array_index == 2:
            if not fc.keyframe_points:
                continue
            v0 = fc.keyframe_points[0].co[1]
            for kp in fc.keyframe_points:
                kp.co[1] = v0
                kp.handle_left[1] = v0
                kp.handle_right[1] = v0


def _all_fcurves(act):
    if hasattr(act, "fcurves") and len(act.fcurves):
        return list(act.fcurves)
    out = []
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


def _gltf_kwargs(path, f0, f1, clip):
    """Only pass options this Blender actually has, so the exporter does not
    fail on a version difference."""
    want = dict(
        filepath=os.path.abspath(path),
        export_format="GLB",
        use_selection=True,
        export_apply=False,          # NEVER True: it applies the armature modifier
        export_skins=True,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_bake_animation=True,
        export_frame_range=True,
        export_optimize_animation_size=False,
        export_vertex_color="NONE",
        export_all_vertex_colors=False,
        export_active_vertex_color_when_no_material=True,
        export_attributes=False,
        export_materials="EXPORT",
        export_yup=True,
        export_cameras=False,
        export_lights=False,
        export_extras=False,
    )
    valid = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    return {k: v for k, v in want.items() if k in valid}


def export_glb(built, path, clip="clip", f0=1, f1=None, in_place=True, fps=30):
    """Bake, rigidly skin, join and write one .glb. Returns a stats dict."""
    arm = built.arm
    sc = bpy.context.scene
    f1 = f1 or sc.frame_end
    sc.frame_start, sc.frame_end = f0, f1
    sc.render.fps = fps

    z_seam = float(arm["hull_center_z"]) * 1.05
    bpy.ops.object.mode_set(mode="OBJECT")
    _bake_constraints(arm, f0, f1)
    root = _add_root_bone(arm)
    if in_place:
        _in_place(arm)

    meshes = _rigid_skin(list(built.parts), arm, root, z_seam)
    body = _join(meshes, "AGENT_BODY")

    act = arm.animation_data.action if arm.animation_data else None
    if act:
        act.name = clip
        if hasattr(act, "use_fake_user"):
            act.use_fake_user = True

    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = arm
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    bpy.ops.export_scene.gltf(**_gltf_kwargs(path, f0, f1, clip))

    return {
        "path": path,
        "clip": clip,
        "frames": f1 - f0 + 1,
        "fps": fps,
        "verts": len(body.data.vertices),
        "tris": sum(max(0, len(p.vertices) - 2) for p in body.data.polygons),
        "materials": len(body.data.materials),
        "bones": len(arm.data.bones),
        "bytes": os.path.getsize(path) if os.path.exists(path) else 0,
    }
