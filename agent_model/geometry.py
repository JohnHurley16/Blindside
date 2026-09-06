"""Mesh primitives with the transforms baked in. Everything returns a bpy Object."""
import math
import bpy
from mathutils import Vector, Matrix, Euler


def _finish(obj, name, col=None, smooth=False, bevel=None, bevel_segments=3):
    obj.name = name
    obj.data.name = name
    if smooth:
        obj.data.shade_smooth()
    if bevel:
        m = obj.modifiers.new("bevel", "BEVEL")
        m.width = bevel
        m.segments = bevel_segments
        m.limit_method = "ANGLE"
        m.harden_normals = True
    if col is not None:
        for c in obj.users_collection:
            c.objects.unlink(obj)
        col.objects.link(obj)
    return obj


def box(name, size, loc=(0, 0, 0), rot=(0, 0, 0), bevel=None, col=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return _finish(o, name, col, bevel=bevel)


def cyl(name, r1, r2, length, loc=(0, 0, 0), rot=(0, 0, 0), verts=24, col=None, bevel=None):
    """Tapered cylinder along local Z, centred on loc."""
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=length, location=loc, rotation=rot)
    return _finish(bpy.context.object, name, col, smooth=True, bevel=bevel, bevel_segments=2)


def segment(name, a, b, r1, r2, verts=20, col=None, bevel=None):
    """Tapered cylinder from point a to point b."""
    a, b = Vector(a), Vector(b)
    d = b - a
    rot = d.to_track_quat("Z", "Y").to_euler()
    return cyl(name, r1, r2, d.length, loc=(a + b) / 2, rot=rot, verts=verts, col=col, bevel=bevel)


def sphere(name, r, loc=(0, 0, 0), col=None, seg=32):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=seg // 2)
    return _finish(bpy.context.object, name, col, smooth=True)


def hemisphere(name, r, loc=(0, 0, 0), rot=(0, 0, 0), col=None):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(0, 0, 0), segments=32, ring_count=16)
    o = bpy.context.object
    # drop the lower half
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for v in o.data.vertices:
        v.select = v.co.z < -1e-4
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.edge_face_add()
    bpy.ops.object.mode_set(mode="OBJECT")
    o.location = loc
    o.rotation_euler = rot
    return _finish(o, name, col, smooth=True)


def torus(name, R, r, loc=(0, 0, 0), rot=(0, 0, 0), col=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot,
                                     major_segments=32, minor_segments=12)
    return _finish(bpy.context.object, name, col, smooth=True)


def plane(name, size, loc=(0, 0, 0), col=None, subdiv=0):
    bpy.ops.mesh.primitive_plane_add(size=size, location=loc)
    o = bpy.context.object
    if subdiv:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.subdivide(number_cuts=subdiv)
        bpy.ops.object.mode_set(mode="OBJECT")
    return _finish(o, name, col)


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.object
    o.name = name
    return o


def move_all(objs, offset):
    for o in objs:
        o.location = Vector(o.location) + Vector(offset)


def set_material(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def new_collection(name, parent=None):
    col = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(col)
    return col
