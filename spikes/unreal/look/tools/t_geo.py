import unreal, os, json
ROOT = r"C:/Users/jackh/documents/programming/Blindside/spikes/unreal/look"
LOG = open(os.path.join(ROOT, "tools", "t_geo.txt"), "w", encoding="utf-8")
def w(s):
    LOG.write(str(s)+"\n"); LOG.flush(); unreal.log("TG "+str(s))

def import_tex(src, dest_dir, name, comp, srgb):
    task = unreal.AssetImportTask()
    task.filename = src
    task.destination_path = dest_dir
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    obj = unreal.EditorAssetLibrary.load_asset(dest_dir + "/" + name)
    if obj is None:
        w("IMPORT FAILED " + name); return None
    obj.set_editor_property("compression_settings", comp)
    obj.set_editor_property("srgb", srgb)
    obj.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    obj.set_editor_property("filter", unreal.TextureFilter.TF_NEAREST)
    obj.set_editor_property("never_stream", True)
    unreal.EditorAssetLibrary.save_loaded_asset(obj, only_if_is_dirty=False)
    w("imported %s  %sx%s  srcfmt=%s" % (name, obj.blueprint_get_size_x(), obj.blueprint_get_size_y(),
                                         obj.get_editor_property("source") if False else "?"))
    return obj

meta = json.load(open(os.path.join(ROOT, "gen", "valley.json")))
m = meta["main"]

tex = import_tex(os.path.join(ROOT, "gen", "main_h.png"), "/Game/T", "main_h",
                 unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP, False)

mesh = unreal.DynamicMesh()
po = unreal.GeometryScriptPrimitiveOptions()
steps = 512
mesh = unreal.GeometryScript_Primitives.append_rectangle_xy(
    mesh, po, unreal.Transform(), m["extent"]*100.0, m["extent"]*100.0, steps, steps)
w("MQ: " + ",".join(m for m in dir(unreal.GeometryScript_MeshQueries) if not m.startswith("_")))

opt = unreal.GeometryScriptDisplaceFromTextureOptions()
opt.magnitude = (m["hi"]-m["lo"])*100.0
opt.center = 0.0
opt.image_channel = 0
opt.uv_scale = unreal.Vector2D(1.0, 1.0)
sel = unreal.GeometryScriptMeshSelection()
tess = unreal.GeometryScriptAdaptiveTessellationOptions() if hasattr(unreal, "GeometryScriptAdaptiveTessellationOptions") else None
try:
    mesh = unreal.GeometryScript_MeshDeformers.apply_displace_from_texture_map(mesh, tex, sel, opt, tess, 0)
except Exception as e:
    w("displace ERR %s" % e)

bb = unreal.GeometryScript_MeshQueries.get_mesh_bounding_box(mesh)
w("bbox min=%s max=%s" % (bb.min, bb.max))
w("expected z span cm = %.0f" % ((m["hi"]-m["lo"])*100.0))

# precision probe: how many distinct Z values in a row of vertices
try:
    r = unreal.GeometryScript_MeshQueries.get_all_vertex_positions(mesh, unreal.GeometryScriptVectorList(), True)
    vl = r[1] if isinstance(r, tuple) else r
    lst = vl.get_editor_property("list") if hasattr(vl,"get_editor_property") else None
    if lst is not None:
        zs = sorted(set(round(v.z,2) for v in list(lst)[:4000]))
        w("distinct z in first 4000 verts: %d  sample %s" % (len(zs), zs[:6]))
except Exception as e:
    w("getpos ERR %r" % (e,))

opts = unreal.GeometryScriptCreateNewStaticMeshAssetOptions()
opts.enable_nanite = True
opts.enable_recompute_normals = True
opts.enable_recompute_tangents = True
opts.enable_collision = False
sm, outcome = unreal.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(mesh, "/Game/T/SM_test", opts)
w("staticmesh %s outcome %s" % (sm, outcome))
unreal.EditorAssetLibrary.save_asset("/Game/T/SM_test", only_if_is_dirty=False)
w("DONE")
LOG.close()
