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


# ---- lofts and tubes (bmesh) ---------------------------------------------------------------
import bmesh


def _mesh_object(name, bm, col=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    (col or bpy.context.scene.collection).objects.link(o)
    if smooth:
        me.shade_smooth()
    return o


def loft(name, stations, col=None, cap=True, crease=0.0, subsurf=2):
    """stations: list of (x, [(y, z), ...]) rings with the same point count.
    Rings are bridged along X. Longitudinal edges get `crease` so a subsurf keeps
    soft panel edges instead of turning the body into a blob."""
    bm = bmesh.new()
    cl = bm.edges.layers.float.new("crease_edge") if crease > 0 else None
    rings = []
    for x, prof in stations:
        rings.append([bm.verts.new((x, y, z)) for (y, z) in prof])
    n = len(rings[0])
    long_edges = []
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            f = bm.faces.new((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]))
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            e = bm.edges.get((r0[i], r1[i]))
            if e:
                long_edges.append(e)
    if cap:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if cl is not None:
        for e in long_edges:
            e[cl] = crease
    o = _mesh_object(name, bm, col)
    if subsurf:
        m = o.modifiers.new("subsurf", "SUBSURF")
        m.levels = m.render_levels = subsurf
        m.use_creases = True
    return o


def tube_along(name, pts, r, verts=8, col=None, closed=False):
    """A tube of radius r following a polyline (list of Vectors)."""
    pts = [Vector(p) for p in pts]
    bm = bmesh.new()
    rings = []
    up = Vector((0, 0, 1))
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        n1 = t.cross(up if abs(t.dot(up)) < 0.95 else Vector((1, 0, 0))).normalized()
        n2 = t.cross(n1).normalized()
        ring = []
        for k in range(verts):
            a = 2 * math.pi * k / verts
            ring.append(bm.verts.new(p + (n1 * math.cos(a) + n2 * math.sin(a)) * r))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(verts):
            bm.faces.new((r0[i], r0[(i + 1) % verts], r1[(i + 1) % verts], r1[i]))
    if closed:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _mesh_object(name, bm, col)


def strut(name, a, b, w0, h0, w1, h1, col=None, bevel=0.004):
    """A tapered rectangular strut from a to b; w is across the leg's hinge axis (Y),
    h is fore-aft. Reads as a machined limb rather than a pipe."""
    a, b = Vector(a), Vector(b)
    d = b - a
    L = d.length
    bm = bmesh.new()
    prof = lambda w, h, z: [bm.verts.new((sx * h / 2, sy * w / 2, z)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    r0, r1 = prof(w0, h0, 0.0), prof(w1, h1, L)
    for i in range(4):
        bm.faces.new((r0[i], r0[(i + 1) % 4], r1[(i + 1) % 4], r1[i]))
    bm.faces.new(list(reversed(r0))); bm.faces.new(r1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _mesh_object(name, bm, col, smooth=False)
    o.matrix_world = Matrix.Translation(a) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    if bevel:
        m = o.modifiers.new("bevel", "BEVEL"); m.width = bevel; m.segments = 3; m.limit_method = "ANGLE"; m.harden_normals = True
    return o


def hull_profile(w, h, chamfer=0.35, belly=0.6, deck=0.7):
    """Chamfered octagon: flat deck on top, tucked belly. Points go around
    counter-clockwise seen from +X. Same point count for every station."""
    return [
        (-w / 2 * deck, h / 2), (-w / 2, h / 2 * chamfer), (-w / 2, -h / 2 * chamfer), (-w / 2 * belly, -h / 2),
        (w / 2 * belly, -h / 2), (w / 2, -h / 2 * chamfer), (w / 2, h / 2 * chamfer), (w / 2 * deck, h / 2),
    ]
