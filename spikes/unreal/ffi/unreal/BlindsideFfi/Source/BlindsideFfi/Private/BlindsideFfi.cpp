#include "BlindsideFfi.h"

#include "BlindsideSimActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Modules/ModuleManager.h"

DEFINE_LOG_CATEGORY(LogBlindside);

namespace
{
	/**
	 * Spawn one ABlindsideSimActor into any game world that does not already have one.
	 *
	 * This exists so the spike runs against a stock engine map and carries no .umap of its
	 * own: `UnrealEditor.exe BlindsideFfi.uproject -game` is enough to see it work, and
	 * there is no binary asset in the repository for a reviewer to take on trust. A
	 * designer who drags an ABlindsideSimActor into a level gets that one instead.
	 */
	void SpawnIfAbsent(const FActorsInitializedParams& Params)
	{
		UWorld* World = Params.World;
		if (World == nullptr || !World->IsGameWorld())
		{
			return;
		}
		for (TActorIterator<ABlindsideSimActor> It(World); It; ++It)
		{
			UE_LOG(LogBlindside, Display, TEXT("level already has a sim actor; using it"));
			return;
		}
		FActorSpawnParameters Spawn;
		Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		World->SpawnActor<ABlindsideSimActor>(ABlindsideSimActor::StaticClass(),
			FVector::ZeroVector, FRotator::ZeroRotator, Spawn);
		UE_LOG(LogBlindside, Display, TEXT("spawned a sim actor into %s"), *World->GetName());
	}

	FDelegateHandle GSpawnHook;
}

class FBlindsideFfiGameModule : public FDefaultGameModuleImpl
{
public:
	virtual void StartupModule() override
	{
		GSpawnHook = FWorldDelegates::OnWorldInitializedActors.AddStatic(&SpawnIfAbsent);
	}

	virtual void ShutdownModule() override
	{
		FWorldDelegates::OnWorldInitializedActors.Remove(GSpawnHook);
	}
};

IMPLEMENT_PRIMARY_GAME_MODULE(FBlindsideFfiGameModule, BlindsideFfi, "BlindsideFfi");
