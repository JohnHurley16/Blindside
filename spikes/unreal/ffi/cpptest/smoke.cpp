// A C++ smoke test with no Unreal in it at all.
//
// It exists to answer two questions that the Unreal project cannot answer cleanly,
// because Unreal's build settings would be doing half the work:
//
//   1. Does the cbindgen-generated header compile as C++ under MSVC, on its own, with
//      warnings as errors? If it does not, the problem is the header and not the engine.
//   2. Does the staticlib link under Unreal's CRT setting (/MD, dynamic CRT), and what
//      does it cost? See NOTES.md, "staticlib vs cdylib".
//
// Built two ways by cpptest/build.cmd: once against blindside_ffi.dll.lib (the import
// library for the cdylib) and once against blindside_ffi.lib (the staticlib).

#include <cstdio>
#include <cstring>
#include <vector>

#include "blindside_sim.h"

static int failures = 0;

static void check(bool ok, const char* what)
{
    std::printf("  %-46s %s\n", what, ok ? "ok" : "FAILED");
    if (!ok) ++failures;
}

int main()
{
    std::printf("blindside C++ smoke test (%s)\n",
#ifdef BLINDSIDE_STATIC
        "staticlib"
#else
        "cdylib via import library"
#endif
    );

    check(bs_abi_version() == BS_ABI_VERSION, "abi version matches the header");
    check(bs_belief_header_size() == sizeof(BsBeliefHeader), "header size agrees with sizeof");
    check(bs_belief_point_size() == sizeof(BsBeliefPoint), "point size agrees with sizeof");
    check(sizeof(BsBeliefHeader) == 72 && sizeof(BsBeliefPoint) == 16, "layout is 72 + 16");

    BsSim* sim = bs_sim_create(0xB11D51DEull, 11500);
    check(sim != nullptr, "bs_sim_create");
    if (sim == nullptr) return 1;

    uint32_t bytes = 0;
    check(bs_sim_belief_bytes(sim, 0, &bytes) == BS_STATUS_OK, "bs_sim_belief_bytes");
    check(bytes == 72u + 11500u * 16u, "snapshot is 184072 bytes");

    std::vector<unsigned char> buf(bytes);
    uint32_t written = 0;
    check(bs_sim_belief_snapshot(sim, 0, buf.data(), bytes, &written) == BS_STATUS_OK,
          "bs_sim_belief_snapshot");
    check(written == bytes, "wrote exactly what it said it would");

    check(bs_sim_step(sim, 100) == BS_STATUS_OK, "bs_sim_step(100)");
    uint64_t tick = 0;
    check(bs_sim_tick(sim, &tick) == BS_STATUS_OK && tick == 100, "tick is 100");

    unsigned char hash[32] = {};
    check(bs_sim_state_hash(sim, hash) == BS_STATUS_OK, "bs_sim_state_hash");
    std::printf("  tick %llu  hash ", (unsigned long long)tick);
    for (int i = 0; i < 32; ++i) std::printf("%02x", hash[i]);
    std::printf("\n");

    // The whole point: errors are status codes, not crashes.
    check(bs_sim_belief_snapshot(sim, 0, buf.data(), 8, nullptr) == BS_STATUS_BUFFER_TOO_SMALL,
          "a short buffer is refused, not overrun");
    check(bs_sim_belief_bytes(sim, 99, &bytes) == BS_STATUS_BAD_AGENT, "a bad agent is refused");
    check(bs_sim_tick(nullptr, &tick) == BS_STATUS_NULL_HANDLE, "a null handle is refused");
    check(std::strcmp(bs_status_message(BS_STATUS_OK), "ok") == 0, "bs_status_message");

    // A Rust panic must come back as a status code with the process intact. This is what
    // stops one bad tick from taking the editor and the user's unsaved work with it.
    check(bs_sim_spike_force_panic(sim) == BS_STATUS_PANIC, "a panic becomes a status code");
    check(bs_sim_tick(sim, &tick) == BS_STATUS_OK, "and the process is still running");

    bs_sim_destroy(sim);
    bs_sim_destroy(nullptr); // documented no-op

    // Reference hashes at named ticks for seed 0xB11D51DE.
    //
    // These are quoted in NOTES.md and are the actual point of the exercise: the same
    // numbers must come out of the Rust test binary, out of this C++ executable linked
    // two different ways, and out of Unreal. If a hash printed on screen in the engine
    // does not match the one printed here, the boundary changed the simulation, and a
    // boundary that changes the simulation is not a boundary this project can use.
    std::printf("\nreference hashes, seed 0xB11D51DE:\n");
    BsSim* ref = bs_sim_create(0xB11D51DEull, 1);
    uint64_t marks[] = {0, 1, 100, 101, 1000, 2071, 2171};
    uint64_t at = 0;
    for (uint64_t m : marks)
    {
        if (m > at) { bs_sim_step(ref, (uint32_t)(m - at)); at = m; }
        unsigned char h[32] = {};
        bs_sim_state_hash(ref, h);
        std::printf("  tick %6llu  ", (unsigned long long)m);
        for (int i = 0; i < 32; ++i) std::printf("%02x", h[i]);
        std::printf("\n");
    }
    bs_sim_destroy(ref);

    std::printf("%s: %d failure(s)\n", failures ? "FAIL" : "PASS", failures);
    return failures == 0 ? 0 : 1;
}
