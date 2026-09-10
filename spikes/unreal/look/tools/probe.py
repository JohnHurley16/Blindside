import unreal, os
out = open(r"C:/Users/jackh/documents/programming/Blindside/spikes/unreal/look/tools/probe.txt","w")
w = lambda s: out.write(str(s)+"\n")
allattrs = dir(unreal)
w("=== geometry-ish ===")
for a in allattrs:
    if "Geometry" in a or "Nanite" in a: w(a)
w("=== key presence ===")
for n in ["Landscape","LandscapeProxy","LandscapeEditorSubsystem","DynamicMesh","DynamicMeshActor",
          "MaterialEditingLibrary","MaterialExpressionNoise","MaterialExpressionWorldPosition",
          "SceneCaptureComponent2D","SceneCapture2D","TextureRenderTarget2D","RenderingLibrary",
          "VolumetricCloud","SkyAtmosphere","ExponentialHeightFog","SkyLight","DirectionalLight",
          "PostProcessVolume","StaticMeshActor","CameraActor","LevelSequence","MoviePipelineQueueSubsystem",
          "EditorAssetLibrary","EditorLevelLibrary","EditorActorSubsystem","LevelEditorSubsystem",
          "AssetToolsHelpers","StaticMesh","AssetImportTask","AutomationLibrary","Texture2DFactoryNew",
          "InstancedStaticMeshComponent","HierarchicalInstancedStaticMeshComponent","MaterialInstanceConstant",
          "MaterialFactoryNew","TextureFactory","NaniteSettings","MeshNaniteSettings","PointLight","SpotLight",
          "NiagaraSystem","LocalFogVolume","HeterogeneousVolume","SparseVolumeTexture"]:
    w("HAS %-42s %s" % (n, hasattr(unreal,n)))
out.close()
