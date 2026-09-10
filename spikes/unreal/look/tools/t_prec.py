import unreal, os, json
ROOT = r"C:/Users/jackh/documents/programming/Blindside/spikes/unreal/look"
LOG = open(os.path.join(ROOT, "tools", "t_prec.txt"), "w", encoding="utf-8")
def w(s):
    LOG.write(str(s)+"\n"); LOG.flush()

meta = json.load(open(os.path.join(ROOT, "gen", "valley.json")))
m = meta["main"]

def imp(name, comp):
    t = unreal.AssetImportTask()
    t.filename = os.path.join(ROOT, "gen", "main_h.png")
    t.destination_path = "/Game/T"; t.destination_name = name
    t.automated = True; t.replace_existing = True; t.save = False
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    o = unreal.EditorAssetLibrary.load_asset("/Game/T/" + name)
    o.set_editor_property("compression_settings", comp)
    o.set_editor_property("srgb", False)
    o.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    o.set_editor_property("filter", unreal.TextureFilter.TF_NEAREST)
    o.set_editor_property("never_stream", True)
    unreal.EditorAssetLibrary.save_loaded_asset(o, only_if_is_dirty=False)
    return o

def probe(tex, label):
    mesh = unreal.DynamicMesh()
    po = unreal.GeometryScriptPrimitiveOptions()
    steps = 600
    mesh = unreal.GeometryScript_Primitives.append_rectangle_xy(
        mesh, po, unreal.Transform(), m["extent"]*100.0, m["extent"]*100.0, steps, steps)
    opt = unreal.GeometryScriptDisplaceFromTextureOptions()
    opt.magnitude = (m["hi"]-m["lo"])*100.0
    opt.center = 0.0; opt.image_channel = 0
    sel = unreal.GeometryScriptMeshSelection()
    tess = unreal.GeometryScriptAdaptiveTessellationOptions()
    mesh = unreal.GeometryScript_MeshDeformers.apply_displace_from_texture_map(mesh, tex, sel, opt, tess, 0)
    n = unreal.GeometryScript_MeshQueries.get_vertex_count(mesh)
    zs = []
    for i in range(0, 6000):
        p = unreal.GeometryScript_MeshQueries.get_vertex_position(mesh, i)
        v = p[0] if isinstance(p, tuple) else p
        zs.append(round(float(v.z), 3))
    zs2 = sorted(set(zs))
    diffs = sorted(set(round(zs2[i+1]-zs2[i], 2) for i in range(len(zs2)-1)))
    w("%s verts=%d distinct=%d  min-step-cm=%s" % (label, n, len(zs2), diffs[:6]))

for (nm, cs) in (("h_vd", unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP),
                 ("h_sf", unreal.TextureCompressionSettings.TC_SINGLE_FLOAT),
                 ("h_hdr", unreal.TextureCompressionSettings.TC_HDR)):
    try:
        probe(imp(nm, cs), nm)
    except Exception as e:
        w("%s ERR %r" % (nm, e))
LOG.close()
