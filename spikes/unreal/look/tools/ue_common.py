import unreal, os, json

ROOT = r"C:/Users/jackh/documents/programming/Blindside/spikes/unreal/look"
GEN = os.path.join(ROOT, "gen")

_LOGF = os.path.join(ROOT, "tools", "build.log")
def log(s):
    unreal.log("BS| " + str(s))
    try:
        with open(_LOGF, "a", encoding="utf-8") as f:
            f.write(str(s) + chr(10))
    except Exception:
        pass

def setp(obj, name, value):
    """set_editor_property that reports instead of aborting the build"""
    try:
        obj.set_editor_property(name, value); return True
    except Exception as e:
        log("PROPFAIL %s.%s : %s" % (obj.get_class().get_name(), name, e)); return False

# ------------------------------------------------------------------ assets
def import_texture(png, pkg, name, srgb=False,
                   comp=None, nearest=True):
    if comp is None:
        comp = unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP
    t = unreal.AssetImportTask()
    t.filename = png
    t.destination_path = pkg
    t.destination_name = name
    t.automated = True; t.replace_existing = True; t.save = False
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    o = unreal.EditorAssetLibrary.load_asset(pkg + "/" + name)
    if o is None:
        raise RuntimeError("texture import failed " + png)
    o.set_editor_property("compression_settings", comp)
    o.set_editor_property("srgb", srgb)
    o.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    o.set_editor_property("filter", unreal.TextureFilter.TF_NEAREST if nearest
                          else unreal.TextureFilter.TF_BILINEAR)
    o.set_editor_property("never_stream", True)
    unreal.EditorAssetLibrary.save_loaded_asset(o, only_if_is_dirty=False)
    return o

def make_terrain_mesh(pkg, name, height_tex, extent_m, steps, lo_m, hi_m,
                      nanite=True, z_offset_m=0.0, force=False):
    path = pkg + "/" + name
    if not force and unreal.EditorAssetLibrary.does_asset_exist(path):
        log("reuse " + path)
        return unreal.EditorAssetLibrary.load_asset(path)
    mesh = unreal.DynamicMesh()
    po = unreal.GeometryScriptPrimitiveOptions()
    mesh = unreal.GeometryScript_Primitives.append_rectangle_xy(
        mesh, po, unreal.Transform(), extent_m*100.0, extent_m*100.0, steps, steps)
    opt = unreal.GeometryScriptDisplaceFromTextureOptions()
    opt.magnitude = (hi_m - lo_m) * 100.0
    opt.center = 0.0
    opt.image_channel = 0
    sel = unreal.GeometryScriptMeshSelection()
    tess = unreal.GeometryScriptAdaptiveTessellationOptions()
    mesh = unreal.GeometryScript_MeshDeformers.apply_displace_from_texture_map(
        mesh, height_tex, sel, opt, tess, 0)
    unreal.GeometryScript_MeshTransforms.translate_mesh(
        mesh, unreal.Vector(0, 0, (lo_m + z_offset_m) * 100.0))
    co = unreal.GeometryScriptCalculateNormalsOptions()
    co.angle_weighted = True; co.area_weighted = True
    mesh = unreal.GeometryScript_Normals.recompute_normals(mesh, co)
    o = unreal.GeometryScriptCreateNewStaticMeshAssetOptions()
    o.enable_nanite = nanite
    o.enable_recompute_normals = False
    o.enable_recompute_tangents = True
    o.enable_collision = False
    sm, outcome = unreal.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(
        mesh, path, o)
    unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
    log("built %s outcome=%s" % (path, outcome))
    return sm

# ------------------------------------------------------------------ materials
class MatBuilder(object):
    def __init__(self, pkg, name):
        self.path = pkg + "/" + name
        if unreal.EditorAssetLibrary.does_asset_exist(self.path):
            unreal.EditorAssetLibrary.delete_asset(self.path)
        f = unreal.MaterialFactoryNew()
        self.mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, pkg, unreal.Material, f)
        self.x = -2400; self.y = 0
        self.MEL = unreal.MaterialEditingLibrary

    def n(self, cls, x=None, y=None):
        if x is None:
            x = self.x; self.y += 160
            if self.y > 2400: self.y = 0; self.x += 320
            y = self.y
        return self.MEL.create_material_expression(self.mat, cls, x, y)

    def const(self, v, x=None, y=None):
        e = self.n(unreal.MaterialExpressionConstant, x, y); e.set_editor_property("r", float(v)); return e

    def const3(self, r, g, b, x=None, y=None):
        e = self.n(unreal.MaterialExpressionConstant3Vector, x, y)
        e.set_editor_property("constant", unreal.LinearColor(r, g, b, 1.0)); return e

    def link(self, a, ao, b, bi):
        ok = self.MEL.connect_material_expressions(a, ao, b, bi)
        if not ok:
            log("LINK FAILED %s.%s -> %s.%s" % (a.get_class().get_name(), ao,
                                                b.get_class().get_name(), bi))
        return ok

    def prop(self, a, ao, p):
        ok = self.MEL.connect_material_property(a, ao, p)
        if not ok: log("PROP FAILED %s -> %s" % (ao, p))
        return ok

    def noise(self, pos_expr, scale, levels=4, func=None, turb=False,
              omin=-1.0, omax=1.0, lscale=2.07):
        e = self.n(unreal.MaterialExpressionNoise)
        e.set_editor_property("scale", float(scale))
        e.set_editor_property("levels", int(levels))
        e.set_editor_property("output_min", float(omin))
        e.set_editor_property("output_max", float(omax))
        e.set_editor_property("level_scale", float(lscale))
        e.set_editor_property("turbulence", bool(turb))
        e.set_editor_property("quality", 2)
        e.set_editor_property("noise_function",
                              func or unreal.NoiseFunction.NOISEFUNCTION_GRADIENT_ALU)
        if pos_expr is not None:
            for cand in ("Position", "", "position", "Pos"):
                if self.MEL.connect_material_expressions(pos_expr, "", e, cand):
                    break
            else:
                log("NOISE POSITION LINK FAILED (inputs unknown)")
        return e

    def custom(self, code, inputs, out_type=None, extra_outputs=None, desc="X"):
        e = self.n(unreal.MaterialExpressionCustom, self.x, self.y)
        e.set_editor_property("code", code)
        e.set_editor_property("description", desc)
        e.set_editor_property("output_type",
                              out_type or unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        ins = []
        for nm in inputs:
            ci = unreal.CustomInput()
            ci.set_editor_property("input_name", nm)
            ins.append(ci)
        e.set_editor_property("inputs", ins)
        if extra_outputs:
            outs = []
            for (nm, ty) in extra_outputs:
                co = unreal.CustomOutput()
                co.set_editor_property("output_name", nm)
                co.set_editor_property("output_type", ty)
                outs.append(co)
            e.set_editor_property("additional_outputs", outs)
        return e

    def done(self):
        self.MEL.recompile_material(self.mat)
        unreal.EditorAssetLibrary.save_loaded_asset(self.mat, only_if_is_dirty=False)
        return self.mat

# ------------------------------------------------------------------ actors
def spawn(cls, loc=(0, 0, 0), rot=(0, 0, 0), label=None):
    a = unreal.EditorLevelLibrary.spawn_actor_from_class(
        cls, unreal.Vector(*loc), unreal.Rotator(*rot))
    if label:
        a.set_actor_label(label)
    return a
