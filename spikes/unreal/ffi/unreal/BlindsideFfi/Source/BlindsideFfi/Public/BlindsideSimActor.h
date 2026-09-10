#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

#include "BlindsideSimActor.generated.h"

// Opaque. The generated C header is included only in the .cpp, so Unreal Header Tool
// never has to parse it and no UObject header in the project sees a `Bs*` type.
struct BsSim;
struct FBlindsideRust;

/**
 * Steps the Rust simulation at a fixed rate and shows what came back.
 *
 * The whole point of this actor is what it CANNOT do. It holds an opaque `BsSim*` and
 * fourteen function pointers; there is no call available to it that returns ground truth,
 * because the generated header does not declare one. A renderer written against this can
 * be careless and still cannot cheat.
 *
 * Drop one in a level, or let the module spawn one (see BlindsideSimActor.cpp).
 */
UCLASS(BlueprintType)
class ABlindsideSimActor : public AActor
{
	GENERATED_BODY()

public:
	ABlindsideSimActor();

	/** Match seed. int64 because Blueprint has no unsigned 64-bit type; reinterpreted, not clamped. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Blindside")
	int64 Seed = 0x0B11D51DE;

	/**
	 * Stand-in point-cloud size per agent, 0 for the library's default.
	 *
	 * Realistic magnitudes, from docs/BELIEF-CATALOGUE.md 1.2 and spikes/godot/cloud/
	 * LIDAR.md 6: about 11,500 new returns per 20 Hz tick from a real scanning sensor,
	 * and an accumulated map of ~500,000 points after a 40 m drive once voxel-downsampled
	 * at 30 mm. Try those numbers here; NOTES.md has what they cost.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Blindside")
	int32 BeliefPoints = 11500;

	/**
	 * Simulation ticks per second. 20 Hz, from PHASE-3-OPEN-QUESTIONS.md 19 (Phase 1 ran
	 * 20 Hz and its 33 ms worst tick rules out 60). The sim is a fixed-timestep,
	 * deterministic machine, so the render frame rate must never be allowed to change how
	 * many ticks it runs -- hence the accumulator in Tick() rather than one step a frame.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Blindside")
	int32 SimTicksPerSecond = 20;

	/** Cap on catch-up steps in one frame, so a hitch cannot spiral. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Blindside")
	int32 MaxCatchUpTicks = 8;

	/**
	 * Watch blindside_ffi.dll's timestamp and reload when cargo writes a new one.
	 *
	 * This is the hot-reload answer, and it is worth more than a button: `cargo build -p
	 * blindside-ffi --release` in another window and the running editor picks it up. It
	 * works because the sim is deterministic -- see ReloadRustLibrary.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Blindside")
	bool bAutoReloadOnRebuild = true;

	/**
	 * Call bs_sim_spike_force_panic at this tick; 0 means never. Overridden by
	 * -ForcePanicAtTick=N on the command line. Exists so the screenshot can show a Rust
	 * panic arriving as a status code with the game still running.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Blindside")
	int32 ForcePanicAtTick = 0;

	/** Rebuild the Rust with cargo, then press this. No editor restart. */
	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Blindside")
	void ReloadRustLibrary();

	/** Proves a Rust panic comes back as a status code and does not take the editor down. */
	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Blindside")
	void ForcePanic();

	UFUNCTION(BlueprintPure, Category = "Blindside")
	int64 GetSimTick() const;

	/** The 32-byte state hash, hex. The same number the desync canary compares. */
	UFUNCTION(BlueprintPure, Category = "Blindside")
	FString GetStateHashHex() const;

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
	virtual void Tick(float DeltaSeconds) override;

private:
	void OpenSim();
	void CloseSim();
	/** One fixed-rate simulation tick plus the snapshot copy, timed. */
	void StepAndSnapshot();

	// A raw pointer, not a TUniquePtr: Unreal Header Tool generates a constructor for
	// this class in a translation unit that does not see FBlindsideRust's definition, and
	// a smart pointer's destructor cannot be instantiated against an incomplete type
	// there. Ownership is still exactly one place -- OpenSim news it, CloseSim deletes it.
	FBlindsideRust* Rust = nullptr;
	BsSim* Sim = nullptr;

	/** The caller-provided buffer. Sized once, at BeginPlay, and never reallocated. */
	TArray<uint8> SnapshotBuffer;

	double Accumulator = 0.0;
	FString Status;

	/** Where blindside_ffi.dll is, and its last-seen write time, for bAutoReloadOnRebuild.
	 *  Kept outside FBlindsideRust so a failed load (a poll that caught cargo mid-write)
	 *  still leaves something to retry against. */
	FString DllPath;
	FDateTime DllStamp = FDateTime::MinValue();
	int32 ReloadCount = 0;
	uint32 AgentCount = 0;

	/** Rolling averages of what the boundary costs, in microseconds. */
	double StepMicros = 0.0;
	double CopyMicros = 0.0;
	double HashMicros = 0.0;
	uint64 TicksRun = 0;
};
