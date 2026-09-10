<#
.SYNOPSIS
    Photograph the running BlindsideFfi window.

.DESCRIPTION
    Unreal draws the readout with GEngine->AddOnScreenDebugMessage, which HighResShot does
    not capture, so this grabs the window off the desktop instead.

    It also dismisses the Windows Firewall prompt that Unreal's trace-control listener
    triggers on every run. Dismissing is WM_CLOSE, which is the same as walking away: it
    grants nothing and changes no firewall rule. Do not "fix" this by clicking Allow --
    the spike has no business opening a port on anybody's machine.

.EXAMPLE
    .\shot.ps1 -Out shots\01-running.png
#>
param(
    [Parameter(Mandatory = $true)][string]$Out,
    [int]$Width = 1400,
    [int]$Height = 800
)

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class BsCapture {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
}
"@ -ErrorAction SilentlyContinue

function Close-FirewallPrompt {
    $cb = [BsCapture+EnumProc] {
        param($h, $l)
        if ([BsCapture]::IsWindowVisible($h)) {
            $sb = New-Object System.Text.StringBuilder 512
            [void][BsCapture]::GetWindowText($h, $sb, 512)
            if ($sb.ToString() -match 'Windows Security') {
                [void][BsCapture]::SendMessage($h, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
            }
        }
        return $true
    }
    [void][BsCapture]::EnumWindows($cb, [IntPtr]::Zero)
}

$p = Get-Process UnrealEditor -ErrorAction SilentlyContinue |
     Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $p) { Write-Host "no UnrealEditor window" -ForegroundColor Red; exit 1 }
$h = $p.MainWindowHandle

# HWND_TOPMOST, at the top-left so the readout is clear of a centred dialog.
[void][BsCapture]::SetWindowPos($h, [IntPtr](-1), 0, 0, $Width, $Height, 0x0040)
Close-FirewallPrompt
[void][BsCapture]::BringWindowToTop($h); [void][BsCapture]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 250
Close-FirewallPrompt
[void][BsCapture]::BringWindowToTop($h); [void][BsCapture]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 120

$r = New-Object BsCapture+RECT
[void][BsCapture]::GetWindowRect($h, [ref]$r)
$bmp = New-Object System.Drawing.Bitmap(($r.R - $r.L), ($r.B - $r.T))
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.L, $r.T, 0, 0, $bmp.Size)
$full = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $Out))
[void][System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($full))
$bmp.Save($full, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Host "saved $full"
