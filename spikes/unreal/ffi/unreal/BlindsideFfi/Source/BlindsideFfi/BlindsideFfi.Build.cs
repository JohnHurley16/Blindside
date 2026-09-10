using UnrealBuildTool;

public class BlindsideFfi : ModuleRules
{
	public BlindsideFfi(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
		// The Rust. One line. That is the whole of "link the simulation into the engine".
		PrivateDependencyModuleNames.Add("BlindsideSim");
	}
}
