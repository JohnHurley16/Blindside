#pragma once

// The generated C header. This is the only Unreal file that includes it, and it is
// included from a header only because the function-pointer table below needs the
// declarations to take decltype of. Nothing else in the project sees a `Bs*` type except
// through this struct.
#include "blindside_sim.h"

#include "CoreMinimal.h"

/**
 * The exports this project uses, once. Adding a Rust function to the boundary means
 * adding one line here and nothing else -- the declaration, the function pointer, the
 * bind and the "missing export" error are all generated from this list.
 */
#define BLINDSIDE_RUST_FUNCTIONS(X) \
	X(bs_abi_version)               \
	X(bs_belief_schema)             \
	X(bs_belief_header_size)        \
	X(bs_belief_point_size)         \
	X(bs_sim_create)                \
	X(bs_sim_destroy)               \
	X(bs_sim_step)                  \
	X(bs_sim_tick)                  \
	X(bs_sim_seed)                  \
	X(bs_sim_state_hash)            \
	X(bs_sim_agent_count)           \
	X(bs_sim_belief_bytes)          \
	X(bs_sim_belief_snapshot)       \
	X(bs_status_message)            \
	X(bs_sim_spike_force_panic)

/**
 * A loaded blindside_ffi.dll and its exports.
 *
 * The DLL is resolved at runtime rather than imported through blindside_ffi.dll.lib, for
 * one reason: Windows locks a loaded DLL, so an imported one cannot be rebuilt while the
 * editor is running. Load copies the DLL to a fresh name under Intermediate/ first, so
 * cargo is always free to overwrite the original, and Reload picks up the new build in
 * place. That is the difference between a five-second Rust iteration and a ninety-second
 * one, every time, for the life of the project.
 *
 * Nothing here is thread-safe. The sim is stepped from the game thread.
 */
struct FBlindsideRust
{
#define BLINDSIDE_DECLARE_FN(Name) decltype(&::Name) Name = nullptr;
	BLINDSIDE_RUST_FUNCTIONS(BLINDSIDE_DECLARE_FN)
#undef BLINDSIDE_DECLARE_FN

	/** Load (or reload) the library. On failure returns false and fills OutError. */
	bool Load(FString& OutError);
	void Unload();
	bool IsLoaded() const { return Handle != nullptr; }

	/** The path the DLL was copied from, for the on-screen readout. */
	FString SourcePath;

private:
	void* Handle = nullptr;
};
