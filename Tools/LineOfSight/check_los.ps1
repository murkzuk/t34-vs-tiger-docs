# Watch tvt_los.log from OUTSIDE the game and say whether occlusion armed.
#
# A separate process on purpose: putting a dialog up from inside a fullscreen
# D3D process is a good way to black-screen it.
#
# First version was silent in practice - its message box opened BEHIND the
# fullscreen game and its success balloon needed System.Drawing, which was
# never loaded. Both fixed: everything here is topmost, self-closing, and
# cannot block forever.

param(
  [Parameter(Mandatory=$true)][string]$Log,
  [int]$WaitSeconds = 240
)

$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$start  = Get-Date
$armed  = $false
$gaveUp = $false

# The log is rewritten when the DLL attaches, so ignore a stale one from a
# previous run: only trust it once it is newer than our own start time.
while (((Get-Date) - $start).TotalSeconds -lt $WaitSeconds) {
    Start-Sleep -Seconds 3
    if (-not (Test-Path $Log)) { continue }
    if ((Get-Item $Log).LastWriteTime -lt $start) { continue }
    $txt = Get-Content $Log
    if ($txt -match 'enforcement live') { $armed = $true; break }
    if ($txt -match 'could not identify') { $gaveUp = $true }
}

function Show-Banner {
    param([string]$Text, [string]$Colour, [int]$Seconds)
    $f = New-Object System.Windows.Forms.Form
    $f.FormBorderStyle = 'None'
    $f.StartPosition   = 'Manual'
    $f.TopMost         = $true
    $f.ShowInTaskbar   = $false
    $f.BackColor       = [System.Drawing.ColorTranslator]::FromHtml($Colour)
    $f.Width = 520; $f.Height = 58
    $scr = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $f.Left = [int](($scr.Width - $f.Width) / 2); $f.Top = 24
    $l = New-Object System.Windows.Forms.Label
    $l.Dock = 'Fill'; $l.TextAlign = 'MiddleCenter'; $l.Text = $Text
    $l.ForeColor = 'White'
    $l.Font = New-Object System.Drawing.Font('Segoe UI', 12, [System.Drawing.FontStyle]::Bold)
    $f.Controls.Add($l)
    $t = New-Object System.Windows.Forms.Timer
    $t.Interval = $Seconds * 1000
    $t.Add_Tick({ $f.Close() })
    $t.Start()
    $f.ShowDialog() | Out-Null
    $f.Dispose()
}

if ($armed) {
    # Quiet confirmation. Green, brief, gone before it becomes annoying.
    Show-Banner -Text 'Line of sight is RUNNING - the AI cannot see through hills or woods' `
                -Colour '#1B5E20' -Seconds 6
    exit 0
}

# It never armed. Worth interrupting for: the whole session will otherwise be
# played against an AI that sees through terrain, and that has already been
# mistaken for a bug in the game.
$why = if ($gaveUp) { 'The hook attached but could not identify the mission.' }
       else { "No 'enforcement live' appeared within $WaitSeconds seconds." }
Show-Banner -Text 'LINE OF SIGHT IS NOT RUNNING - the AI can see through terrain' `
            -Colour '#B71C1C' -Seconds 12
[System.Windows.Forms.MessageBox]::Show(
  "LINE OF SIGHT IS NOT RUNNING.`n`n$why`n`nAnything you judge about AI behaviour this session will be misleading.`n`nLog: $Log",
  'T-34 vs Tiger - line of sight',
  [System.Windows.Forms.MessageBoxButtons]::OK,
  [System.Windows.Forms.MessageBoxIcon]::Warning,
  [System.Windows.Forms.MessageBoxDefaultButton]::Button1,
  [System.Windows.Forms.MessageBoxOptions]::ServiceNotification) | Out-Null
exit 1
