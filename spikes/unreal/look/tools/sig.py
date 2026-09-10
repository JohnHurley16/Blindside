import unreal, os, inspect
P = r"C:/Users/jackh/documents/programming/Blindside/spikes/unreal/look/tools/sig.txt"
out = open(P, "w", encoding="utf-8")
def dump(cls, filt):
    out.write("\n===== %s =====\n" % cls.__name__)
    for m in dir(cls):
        if m.startswith("_"): continue
        if filt and not any(k in m.lower() for k in filt): continue
        f = getattr(cls, m)
        d = (f.__doc__ or "").strip().splitlines()
        out.write("  %s :: %s\n" % (m, d[0] if d else ""))

dump(unreal.GeometryScript_Primitives, ["rect","grid","disc","sweep","revolve","box","sphere","cylinder","tube"])
dump(unreal.GeometryScript_MeshDeformers, ["displace","perlin","warp","smooth"])
dump(unreal.GeometryScript_NewAssetUtils, [])
dump(unreal.GeometryScript_Normals, ["recompute","tangent","normal"])
dump(unreal.GeometryScript_MeshTransforms, ["transform","translate","scale"])
dump(unreal.GeometryScript_MeshVoxelProcessing, [])
dump(unreal.GeometryScript_MeshBooleans, [])
dump(unreal.GeometryScript_MeshEdits, ["append","buffers","extrude"])
dump(unreal.GeometryScript_UVs, ["plane","box","set"])
dump(unreal.GeometryScript_MeshSelection, ["select","plane","box"])
dump(unreal.GeometryScript_PolyPath, [])
dump(unreal.GeometryScript_MeshRepair, ["weld","normals"])
dump(unreal.GeometryScript_MeshSubdivide, [])

out.write("\n===== structs =====\n")
for s in ["GeometryScriptPrimitiveOptions","GeometryScriptDisplaceFromTextureOptions",
          "GeometryScriptSampleTextureOptions","GeometryScriptCreateNewStaticMeshAssetOptions",
          "GeometryScriptCalculateNormalsOptions","GeometryScriptNaniteOptions",
          "GeometryScriptRevolveOptions","GeometryScriptSolidifyOptions",
          "GeometryScriptMorphologyOptions","GeometryScriptMeshBooleanOptions",
          "GeometryScriptPerlinNoiseOptions","GeometryScriptPerlinNoiseLayerOptions",
          "MeshNaniteSettings","GeometryScriptIterativeMeshSmoothingOptions"]:
    c = getattr(unreal, s, None)
    if c is None:
        out.write("%s MISSING\n" % s); continue
    out.write("\n-- %s\n" % s)
    try:
        for k, v in c.__dict__.items():
            if isinstance(v, property) or type(v).__name__ == "getset_descriptor":
                out.write("     .%s\n" % k)
    except Exception as e:
        out.write("   err %s\n" % e)
    out.write("   doc: %s\n" % (c.__doc__ or "")[:1400].replace("\n", "\n   "))

out.write("\n===== material fns =====\n")
dump(unreal.MaterialEditingLibrary, [])
out.close()
unreal.log("SIGDONE")
