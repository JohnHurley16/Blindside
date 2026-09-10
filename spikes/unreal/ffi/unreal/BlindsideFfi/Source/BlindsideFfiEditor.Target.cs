using UnrealBuildTool;

public class BlindsideFfiEditorTarget : TargetRules
{
	public BlindsideFfiEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V5;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_6;
		ExtraModuleNames.Add("BlindsideFfi");
	}
}
