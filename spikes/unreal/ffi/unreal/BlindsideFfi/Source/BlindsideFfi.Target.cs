using UnrealBuildTool;

public class BlindsideFfiTarget : TargetRules
{
	public BlindsideFfiTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V5;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_6;
		ExtraModuleNames.Add("BlindsideFfi");
	}
}
