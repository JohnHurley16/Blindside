<#
.SYNOPSIS
    Build the Rust simulation library and then the Unreal module that calls it.

.DESCRIPTION
    One command, from clean, on this machine. Order matters and is not negotiable:

      1. cargo builds blindside_ffi.dll and, via build.rs + cbindgen, blindside_sim.h.
      2. Unreal Build Tool compiles the C++ module, which #includes that header and
         copies that DLL.

    Step 2 refuses to run if step 1's artefacts are absent (see BlindsideSim.Build.cs),
    which is deliberate: a missing header is a clearer error than a stale one.

.PARAMETER Run
    After building, launch the game windowed so you can see the thing work.

.PARAMETER Clean
    cargo clean and delete the Unreal Intermediate/Binaries first. Use this to check that
    the build really is reproducible from nothing.

.PARAMETER Test
    Run the Rust test suite too, including the tests that audit the generated header.

.PARAMETER Bench
    Run the boundary cost benchmark and print the table that NOTES.md quotes.

.PARAMETER Engine
    Unreal install root. Default: the UE 5.6 launcher path. 5.8 does NOT build on this
    machine -- see NOTES.md, "Engine version".

.EXAMPLE
    .\build.ps1 -Clean -Test -Run
#>
[CmdletBinding()]
param(
    [switch]$Run,
    [switch]$Clean,
    [switch]$Test,
    [switch]$Bench,
    [string]$Engine = "C:\Program Files\Epic Games\UE_5.6",
    [ValidateSet("Development", "DebugGame", "Shipping")]
    [string]$Configuration = "Development"
)

# NOT "Stop". Windows PowerShell turns any native command's stderr into a terminating
# NativeCommandError under Stop, and cargo writes its progress and its clean summary to
# stderr on success. Every step below is gated on $LASTEXITCODE instead, which is the
# thing that actually says whether the command worked.
$ErrorActionPreference = "Continue"

$Spike    = $PSScriptRoot
$RustDir  = Join-Path $Spike "rust"
$Uproject = Join-Path $Spike "unreal\BlindsideFfi\BlindsideFfi.uproject"
$UeProj   = Split-Path $Uproject -Parent
$BuildBat = Join-Path $Engine "Engine\Build\BatchFiles\Build.bat"
$Editor   = Join-Path $Engine "Engine\Binaries\Win64\UnrealEditor.exe"

function Step($Text) { Write-Host "`n=== $Text ===" -ForegroundColor Cyan }
function Die($Text)  { Write-Host "FAILED: $Text" -ForegroundColor Red; exit 1 }

# --- Preconditions, checked before anything is built ------------------------------
Step "checking the toolchain"
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) { Die "cargo is not on PATH" }
if (-not (Test-Path $BuildBat)) { Die "no Unreal at $Engine (pass -Engine)" }
cargo --version
Write-Host "unreal:  $Engine"

if ($Clean) {
    Step "clean"
    Push-Location $RustDir
    cargo clean
    if ($LASTEXITCODE -ne 0) { Pop-Location; Die "cargo clean" }
    Pop-Location
    foreach ($d in @("Intermediate", "Binaries", "Saved", "DerivedDataCache")) {
        $p = Join-Path $UeProj $d
        if (Test-Path $p) { Remove-Item -Recurse -Force $p }
    }
}

# --- 1. Rust ----------------------------------------------------------------------
# --release, not --debug: the workspace's release profile keeps overflow-checks and
# debug-assertions on (copied from the main workspace root), so this is the profile that
# produces the hashes CI produces. A debug build would be a different sim.
Step "building the Rust (cargo, release)"
Push-Location $RustDir
cargo build -p blindside-ffi --release
if ($LASTEXITCODE -ne 0) { Pop-Location; Die "cargo build" }

if ($Test) {
    Step "rust tests (includes the generated-header audit)"
    cargo test -p blindside-ffi --release
    if ($LASTEXITCODE -ne 0) { Pop-Location; Die "cargo test" }
}
if ($Bench) {
    Step "boundary cost"
    cargo run -p blindside-ffi --release --bin bench-snapshot
    if ($LASTEXITCODE -ne 0) { Pop-Location; Die "bench" }
}
Pop-Location

$Dll = Join-Path $RustDir "target\release\blindside_ffi.dll"
$Hdr = Join-Path $RustDir "crates\blindside-ffi\include\blindside_sim.h"
if (-not (Test-Path $Dll)) { Die "cargo did not produce $Dll" }
if (-not (Test-Path $Hdr)) { Die "cbindgen did not produce $Hdr" }
Write-Host ("dll:     {0} ({1:N0} bytes)" -f $Dll, (Get-Item $Dll).Length)
Write-Host ("header:  {0} ({1:N0} bytes)" -f $Hdr, (Get-Item $Hdr).Length)

# --- 2. Unreal --------------------------------------------------------------------
Step "building the Unreal module (UnrealBuildTool)"
& $BuildBat BlindsideFfiEditor Win64 $Configuration -Project="$Uproject" -WaitMutex
if ($LASTEXITCODE -ne 0) { Die "UnrealBuildTool" }

Write-Host "`nBuilt." -ForegroundColor Green
Write-Host "  open the editor:  `"$Editor`" `"$Uproject`""
Write-Host "  or run the game:  `"$Editor`" `"$Uproject`" -game -windowed -ResX=1400 -ResY=800"

if ($Run) {
    Step "running"
    & $Editor "$Uproject" -game -windowed -ResX=1400 -ResY=800 -ForceRes
}
