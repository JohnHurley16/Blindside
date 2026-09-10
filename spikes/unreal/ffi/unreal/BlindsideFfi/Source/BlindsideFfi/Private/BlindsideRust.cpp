#include "BlindsideRust.h"

#include "BlindsideFfi.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformProcess.h"
#include "Misc/Paths.h"

namespace
{
	/** Where blindside_ffi.dll is. Packaged build first, then cargo's target directory. */
	FString ResolveDllPath()
	{
		// Packaged: RuntimeDependencies in BlindsideSim.Build.cs staged it beside the exe.
		const FString Beside = FString(FPlatformProcess::BaseDir()) / TEXT("blindside_ffi.dll");
		if (FPaths::FileExists(Beside))
		{
			return Beside;
		}
		// In the editor, BaseDir is the engine's own Binaries directory, so we land here:
		// straight out of cargo's output, which is what makes Reload see a fresh build.
		return FString(TEXT(BLINDSIDE_RUST_DLL_DIR)) / TEXT("blindside_ffi.dll");
	}
}

bool FBlindsideRust::Load(FString& OutError)
{
	Unload();

	SourcePath = ResolveDllPath();
	if (!FPaths::FileExists(SourcePath))
	{
		OutError = FString::Printf(
			TEXT("blindside_ffi.dll not found at %s. Build the Rust first: "
				 "cargo build -p blindside-ffi --release"),
			*SourcePath);
		return false;
	}

	// Load a COPY under a name nothing else holds, so the original stays writable and a
	// `cargo build` mid-session succeeds instead of failing with "access denied".
	static int32 Generation = 0;
	const FString CopyDir = FPaths::ProjectIntermediateDir() / TEXT("BlindsideRust");
	IFileManager::Get().MakeDirectory(*CopyDir, true);
	const FString CopyPath = CopyDir / FString::Printf(TEXT("blindside_ffi_%u_%d.dll"),
		FPlatformProcess::GetCurrentProcessId(), Generation++);
	if (IFileManager::Get().Copy(*CopyPath, *SourcePath) != COPY_OK)
	{
		OutError = FString::Printf(TEXT("could not copy %s to %s"), *SourcePath, *CopyPath);
		return false;
	}

	Handle = FPlatformProcess::GetDllHandle(*CopyPath);
	if (Handle == nullptr)
	{
		OutError = FString::Printf(TEXT("GetDllHandle failed for %s"), *CopyPath);
		return false;
	}

#define BLINDSIDE_BIND_FN(FnName)                                                       \
	FnName = (decltype(FnName))FPlatformProcess::GetDllExport(Handle, TEXT(#FnName));    \
	if (FnName == nullptr)                                                               \
	{                                                                                    \
		OutError = TEXT("blindside_ffi.dll is missing the export " #FnName);              \
		Unload();                                                                        \
		return false;                                                                    \
	}
	BLINDSIDE_RUST_FUNCTIONS(BLINDSIDE_BIND_FN)
#undef BLINDSIDE_BIND_FN

	// The version handshake the generated header asks for. A DLL and a header that
	// disagree read every snapshot at the wrong offsets, and that is a silent bug, so it
	// is checked once, here, loudly.
	if (bs_abi_version() != BS_ABI_VERSION)
	{
		OutError = FString::Printf(TEXT("ABI mismatch: DLL reports %u, this build was "
			"compiled against %u. Rebuild the Unreal module."),
			bs_abi_version(), (uint32)BS_ABI_VERSION);
		Unload();
		return false;
	}
	if (bs_belief_header_size() != sizeof(BsBeliefHeader)
		|| bs_belief_point_size() != sizeof(BsBeliefPoint))
	{
		OutError = FString::Printf(TEXT("snapshot layout mismatch: DLL says %u/%u bytes, "
			"C++ sizeof says %u/%u."),
			bs_belief_header_size(), bs_belief_point_size(),
			(uint32)sizeof(BsBeliefHeader), (uint32)sizeof(BsBeliefPoint));
		Unload();
		return false;
	}

	UE_LOG(LogBlindside, Log, TEXT("loaded %s (abi %u, belief schema %u)"),
		*SourcePath, bs_abi_version(), bs_belief_schema());
	return true;
}

void FBlindsideRust::Unload()
{
	if (Handle != nullptr)
	{
		FPlatformProcess::FreeDllHandle(Handle);
		Handle = nullptr;
	}
#define BLINDSIDE_CLEAR_FN(FnName) FnName = nullptr;
	BLINDSIDE_RUST_FUNCTIONS(BLINDSIDE_CLEAR_FN)
#undef BLINDSIDE_CLEAR_FN
}
