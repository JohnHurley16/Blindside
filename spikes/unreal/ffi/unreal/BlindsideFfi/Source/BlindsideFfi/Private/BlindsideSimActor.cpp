#include "BlindsideSimActor.h"

#include "BlindsideFfi.h"
#include "BlindsideRust.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformTime.h"
#include "Misc/CommandLine.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"

ABlindsideSimActor::ABlindsideSimActor()
{
	PrimaryActorTick.bCanEverTick = true;
}

void ABlindsideSimActor::BeginPlay()
{
	Super::BeginPlay();
	// -ForcePanicAtTick=N, so the panic demonstration is a command-line switch and not a
	// checkbox somebody has to remember to tick before taking the screenshot.
	int32 FromCmdLine = 0;
	if (FParse::Value(FCommandLine::Get(), TEXT("ForcePanicAtTick="), FromCmdLine))
	{
		ForcePanicAtTick = FromCmdLine;
	}
	OpenSim();
}

void ABlindsideSimActor::EndPlay(const EEndPlayReason::Type Reason)
{
	CloseSim();
	Super::EndPlay(Reason);
}

void ABlindsideSimActor::OpenSim()
{
	CloseSim();

	Rust = new FBlindsideRust();
	FString Error;
	if (!Rust->Load(Error))
	{
		Status = FString::Printf(TEXT("rust library not loaded: %s"), *Error);
		UE_LOG(LogBlindside, Error, TEXT("%s"), *Status);
		DllPath = Rust->SourcePath;
		delete Rust;
		Rust = nullptr;
		// Deliberately do NOT record the timestamp: a load that failed because the poll
		// caught cargo mid-write must be retried on the next poll, not treated as seen.
		return;
	}
	DllPath = Rust->SourcePath;

	Sim = Rust->bs_sim_create((uint64)Seed, (uint32)FMath::Max(0, BeliefPoints));
	if (Sim == nullptr)
	{
		Status = TEXT("bs_sim_create returned null");
		UE_LOG(LogBlindside, Error, TEXT("%s"), *Status);
		return;
	}

	// Size the buffer once. The library never allocates for us and never frees for us.
	uint32 Bytes = 0;
	const BsStatus S = Rust->bs_sim_belief_bytes(Sim, 0, &Bytes);
	if (S != BS_STATUS_OK)
	{
		Status = FString::Printf(TEXT("bs_sim_belief_bytes: %hs"), Rust->bs_status_message(S));
		UE_LOG(LogBlindside, Error, TEXT("%s"), *Status);
		return;
	}
	SnapshotBuffer.SetNumUninitialized((int32)Bytes);

	DllStamp = IFileManager::Get().GetTimeStamp(*DllPath);

	AgentCount = 0;
	Rust->bs_sim_agent_count(Sim, &AgentCount);
	Status = FString::Printf(TEXT("running: %u agents, %d bytes/snapshot"), AgentCount, (int32)Bytes);
	UE_LOG(LogBlindside, Display,
		TEXT("sim opened: seed 0x%llX, %d belief points, %u bytes per snapshot, %d Hz"),
		(uint64)Seed, BeliefPoints, Bytes, SimTicksPerSecond);
}

void ABlindsideSimActor::CloseSim()
{
	if (Rust != nullptr && Sim != nullptr)
	{
		Rust->bs_sim_destroy(Sim);
	}
	Sim = nullptr;
	delete Rust;
	Rust = nullptr;
	Accumulator = 0.0;
	TicksRun = 0;
}

void ABlindsideSimActor::ReloadRustLibrary()
{
	UE_LOG(LogBlindside, Display, TEXT("reloading the Rust library"));
	// The sim's state lives inside the DLL being replaced, so it cannot survive the swap.
	// It does not need to: the sim is deterministic, so re-creating from the same seed and
	// re-stepping to the same tick reproduces it exactly. That is the whole reason a
	// deterministic core makes hot reload tractable at all.
	const uint64 Resume = (uint64)GetSimTick();
	const double T0 = FPlatformTime::Seconds();
	OpenSim();
	if (Sim != nullptr && Resume > 0)
	{
		Rust->bs_sim_step(Sim, (uint32)FMath::Min<uint64>(Resume, TNumericLimits<uint32>::Max()));
	}
	++ReloadCount;
	const double Millis = (FPlatformTime::Seconds() - T0) * 1000.0;
	Status = FString::Printf(
		TEXT("hot reload #%d: new blindside_ffi.dll, replayed %llu ticks in %.0f ms"),
		ReloadCount, Resume, Millis);
	UE_LOG(LogBlindside, Display, TEXT("%s"), *Status);
}

void ABlindsideSimActor::ForcePanic()
{
	if (Rust != nullptr && Sim != nullptr)
	{
		const BsStatus S = Rust->bs_sim_spike_force_panic(Sim);
		Status = FString::Printf(TEXT("forced panic returned %d (%hs) -- still here"),
			(int32)S, Rust->bs_status_message(S));
		UE_LOG(LogBlindside, Warning, TEXT("%s"), *Status);
	}
}

int64 ABlindsideSimActor::GetSimTick() const
{
	uint64 T = 0;
	if (Rust != nullptr && Sim != nullptr)
	{
		Rust->bs_sim_tick(Sim, &T);
	}
	return (int64)T;
}

FString ABlindsideSimActor::GetStateHashHex() const
{
	if (Rust == nullptr || Sim == nullptr)
	{
		return TEXT("--");
	}
	uint8 H[32] = {};
	if (Rust->bs_sim_state_hash(Sim, H) != BS_STATUS_OK)
	{
		return TEXT("--");
	}
	FString Hex;
	Hex.Reserve(64);
	for (int32 i = 0; i < 32; ++i)
	{
		Hex += FString::Printf(TEXT("%02x"), H[i]);
	}
	return Hex;
}

void ABlindsideSimActor::StepAndSnapshot()
{
	const double T0 = FPlatformTime::Seconds();
	Rust->bs_sim_step(Sim, 1);
	const double T1 = FPlatformTime::Seconds();

	uint32 Written = 0;
	const BsStatus S = Rust->bs_sim_belief_snapshot(
		Sim, 0, SnapshotBuffer.GetData(), (uint32)SnapshotBuffer.Num(), &Written);
	const double T2 = FPlatformTime::Seconds();

	if (S != BS_STATUS_OK)
	{
		Status = FString::Printf(TEXT("snapshot failed: %hs"), Rust->bs_status_message(S));
		return;
	}

	// The snapshot is a header followed by points, in the caller's buffer. Reading it back
	// here is what a renderer would do to build its point cloud; it is done so the
	// on-screen readout can prove the bytes are real and not a size that happens to match.
	const BsBeliefHeader* Header = reinterpret_cast<const BsBeliefHeader*>(SnapshotBuffer.GetData());
	checkf(Header->schema == BS_BELIEF_SCHEMA, TEXT("belief schema mismatch"));

	const double T3 = FPlatformTime::Seconds();
	GetStateHashHex();
	const double T4 = FPlatformTime::Seconds();

	// Exponential moving average; the first tick is all page faults and would skew a mean.
	const double A = 0.02;
	StepMicros = FMath::Lerp(StepMicros, (T1 - T0) * 1e6, TicksRun == 0 ? 1.0 : A);
	CopyMicros = FMath::Lerp(CopyMicros, (T2 - T1) * 1e6, TicksRun == 0 ? 1.0 : A);
	HashMicros = FMath::Lerp(HashMicros, (T4 - T3) * 1e6, TicksRun == 0 ? 1.0 : A);
	++TicksRun;

	if (TicksRun % 100 == 1)
	{
		UE_LOG(LogBlindside, Display,
			TEXT("tick %llu  hash %s  snapshot %u B (%u pts, ticks_since_fix %u)  "
				 "step %.2f us  copy %.2f us  hash %.2f us"),
			Header->tick, *GetStateHashHex(), Written, Header->point_count,
			Header->ticks_since_fix, StepMicros, CopyMicros, HashMicros);
	}
}

void ABlindsideSimActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	if (Rust != nullptr && Sim != nullptr && SimTicksPerSecond > 0)
	{
		// Fixed timestep. The renderer's frame rate must never change how many sim ticks
		// run, or two machines watching the same match compute different states.
		const double Period = 1.0 / (double)SimTicksPerSecond;
		Accumulator += (double)DeltaSeconds;
		int32 Budget = FMath::Max(1, MaxCatchUpTicks);
		while (Accumulator >= Period && Budget-- > 0)
		{
			Accumulator -= Period;
			StepAndSnapshot();
		}
		if (Accumulator > Period * 4.0)
		{
			Accumulator = 0.0; // gave up catching up; a real client would report the drop
		}

		if (ForcePanicAtTick > 0 && GetSimTick() >= (int64)ForcePanicAtTick)
		{
			ForcePanicAtTick = 0;
			ForcePanic();
		}
	}

	// Poll the DLL's timestamp about twice a second. A stat() is far too cheap to matter
	// next to a frame, and this is the whole of "rebuild the Rust and see it".
	if (bAutoReloadOnRebuild && !DllPath.IsEmpty() && (TicksRun % 10) == 0)
	{
		const FDateTime Now = IFileManager::Get().GetTimeStamp(*DllPath);
		if (Now != FDateTime::MinValue() && Now != DllStamp)
		{
			UE_LOG(LogBlindside, Display, TEXT("blindside_ffi.dll changed on disk"));
			ReloadRustLibrary();
		}
	}

	if (GEngine == nullptr)
	{
		return;
	}
	// With bNewerOnTop = false, keyed messages render in ASCENDING key order down the
	// screen: key 1 is the top line. Text scale 1.5 so the numbers survive a screenshot,
	// and the 64-character hash is split across two labelled lines so that every line
	// stays short enough to photograph -- and so that the halves cannot be read in the
	// wrong order even if a future engine version reverses the sort.
	const FColor Ok = FColor(140, 225, 255);
	const FVector2D Scale(1.5, 1.5);
	auto Line = [Scale](int32 Key, const FColor& C, const FString& Text)
	{
		GEngine->AddOnScreenDebugMessage(Key, 0.0f, C, Text, false, Scale);
	};
	const FString Hash = GetStateHashHex();
	Line(1, FColor::White, TEXT("BLINDSIDE: Rust sim, Unreal renderer, C ABI"));
	Line(2, Ok, FString::Printf(TEXT("tick        %lld  @ %d Hz"), GetSimTick(), SimTicksPerSecond));
	Line(3, Ok, FString::Printf(TEXT("hash  0:32  %s"), *Hash.Left(32)));
	Line(4, Ok, FString::Printf(TEXT("hash 32:64  %s"), *Hash.Mid(32)));
	Line(5, Ok, FString::Printf(TEXT("belief      %d B, %d pts, %u agents"),
		SnapshotBuffer.Num(), BeliefPoints, AgentCount));
	Line(6, Ok, FString::Printf(TEXT("boundary    step %.1fus  copy %.1fus"),
		StepMicros, CopyMicros));
	Line(7, FColor::Silver, FString::Printf(TEXT("dll         %s"),
		Rust != nullptr ? *FPaths::GetCleanFilename(DllPath) : TEXT("not loaded")));
	Line(8, FColor(255, 210, 120), Status);
}
