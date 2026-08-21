# T-34 vs Tiger launcher.
#
# One window to pick the build, the renderer and whether the AI can see. All of
# it was already possible from batch files and shortcuts; this just stops it
# being something you have to remember at 3 in the morning.
#
# Nothing here is clever. It reads the real state off disk every time it
# refreshes - which wrapper DLL is in place, whether the executable is
# large-address-aware, what the ini says - so it cannot drift out of step with
# what is actually installed.

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$BUILDS = @{
  'REDUX'   = @{ Root='M:\T34vsTiger';        Exe='TvsT_fullLOD_HARD_4GB.exe'; Editor='Editor.exe' }
  'ZeeWolf' = @{ Root='M:\T34vsTiger_ZW2015'; Exe='TvsT_fullLOD_HARD_4GB.exe'; Editor='Editor.exe' }
}
$DLL = 'K:\tvt_los\tvt_los_hook.dll'
$INJ = 'K:\tvt_probe\tvt_inject.exe'
$CHK = 'K:\tvt_los\check_los.ps1'

function Get-Wrapper([string]$root) {
  $p = Join-Path $root 'd3d9.dll'
  if (-not (Test-Path $p)) { return 'none' }
  if ((Get-Item $p).Length -gt 2000000) { 'DXVK' } else { 'dgVoodoo' }
}
function Get-Laa([string]$exe) {
  try {
    $fs=[IO.File]::OpenRead($exe); $br=New-Object IO.BinaryReader($fs)
    $fs.Position=0x3C; $pe=$br.ReadInt32(); $fs.Position=$pe+22; $ch=$br.ReadUInt16()
    $br.Close(); $fs.Close(); return (($ch -band 0x20) -ne 0)
  } catch { return $false }
}
function Get-Ini([string]$root,[string]$key,$fallback) {
  $p = Join-Path $root 'tvt_los.ini'
  if (-not (Test-Path $p)) { return $fallback }
  $m = Select-String -Path $p -Pattern ("^\s*" + $key + "\s*=\s*(.+?)\s*$") | Select-Object -First 1
  if ($m) { $m.Matches[0].Groups[1].Value } else { $fallback }
}
function Set-Ini([string]$root,[string]$key,[string]$val) {
  $p = Join-Path $root 'tvt_los.ini'
  if (-not (Test-Path $p)) { return }
  $out = Get-Content $p | ForEach-Object {
    if ($_ -match ("^\s*" + $key + "\s*=")) { "$key = $val" } else { $_ }
  }
  Set-Content -Path $p -Value $out -Encoding ASCII
}

# ---------------------------------------------------------------- the window
$f = New-Object System.Windows.Forms.Form
$f.Text = 'T-34 vs Tiger'
$f.Size = New-Object System.Drawing.Size(470, 470)
$f.FormBorderStyle = 'FixedDialog'
$f.MaximizeBox = $false
$f.StartPosition = 'CenterScreen'
$f.BackColor = [System.Drawing.Color]::FromArgb(32,32,34)
$f.ForeColor = [System.Drawing.Color]::Gainsboro
$fontH = New-Object System.Drawing.Font('Segoe UI', 11, [System.Drawing.FontStyle]::Bold)
$fontN = New-Object System.Drawing.Font('Segoe UI', 9)

function Add-Label($text,$x,$y,$w,$font,$colour) {
  $l = New-Object System.Windows.Forms.Label
  $l.Text=$text; $l.Left=$x; $l.Top=$y; $l.Width=$w; $l.Height=20
  $l.Font=$font; $l.ForeColor=$colour; $f.Controls.Add($l); return $l
}

Add-Label 'Build' 20 14 200 $fontH ([System.Drawing.Color]::White) | Out-Null
$script:rbRedux = New-Object System.Windows.Forms.RadioButton
$rbRedux.Text='TvT REDUX'; $rbRedux.Left=24; $rbRedux.Top=38; $rbRedux.Width=170
$rbRedux.Checked=$true; $rbRedux.Font=$fontN; $rbRedux.ForeColor='Gainsboro'
$script:rbZw = New-Object System.Windows.Forms.RadioButton
$rbZw.Text='ZeeWolf 2015'; $rbZw.Left=210; $rbZw.Top=38; $rbZw.Width=200
$rbZw.Font=$fontN; $rbZw.ForeColor='Gainsboro'
# ALL RadioButtons sharing one parent form a SINGLE mutually-exclusive group.
# Build and Renderer were both children of the form, so picking a renderer
# unchecked the build - and since Refresh-State sets the renderer radio from
# disk, choosing ZeeWolf immediately unchecked itself and Play launched REDUX.
# Each pair needs its own container to be its own group.
$pnlBuild = New-Object System.Windows.Forms.Panel
$pnlBuild.Left=20; $pnlBuild.Top=32; $pnlBuild.Width=420; $pnlBuild.Height=28
$pnlBuild.BackColor=$f.BackColor
$script:rbRedux.Left=4;   $script:rbRedux.Top=4
$script:rbZw.Left=190;    $script:rbZw.Top=4
$pnlBuild.Controls.AddRange(@($script:rbRedux,$script:rbZw))
$f.Controls.Add($pnlBuild)

Add-Label 'Renderer' 20 74 200 $fontH ([System.Drawing.Color]::White) | Out-Null
$script:rbDg = New-Object System.Windows.Forms.RadioButton
$rbDg.Text='dgVoodoo  (the Editor needs this)'; $rbDg.Left=24; $rbDg.Top=98; $rbDg.Width=280
$rbDg.Font=$fontN; $rbDg.ForeColor='Gainsboro'
$script:rbDx = New-Object System.Windows.Forms.RadioButton
$rbDx.Text='DXVK  (usually faster)'; $rbDx.Left=24; $rbDx.Top=120; $rbDx.Width=280
$rbDx.Font=$fontN; $rbDx.ForeColor='Gainsboro'
$pnlRend = New-Object System.Windows.Forms.Panel
$pnlRend.Left=20; $pnlRend.Top=92; $pnlRend.Width=420; $pnlRend.Height=50
$pnlRend.BackColor=$f.BackColor
$script:rbDg.Left=4; $script:rbDg.Top=2
$script:rbDx.Left=4; $script:rbDx.Top=24
$pnlRend.Controls.AddRange(@($script:rbDg,$script:rbDx))
$f.Controls.Add($pnlRend)

Add-Label 'Options' 20 154 200 $fontH ([System.Drawing.Color]::White) | Out-Null
$script:cbLos = New-Object System.Windows.Forms.CheckBox
$cbLos.Text='Line of sight  (the AI cannot see through hills or woods)'
$cbLos.Left=24; $cbLos.Top=178; $cbLos.Width=400; $cbLos.Checked=$true
$cbLos.Font=$fontN; $cbLos.ForeColor='Gainsboro'
$script:cbHud = New-Object System.Windows.Forms.CheckBox
$cbHud.Text='Performance HUD  (fps, draw calls, GPU - DXVK only)'
$cbHud.Left=24; $cbHud.Top=200; $cbHud.Width=400
$cbHud.Font=$fontN; $cbHud.ForeColor='Gainsboro'
$f.Controls.AddRange(@($cbLos,$cbHud))

$lblScale = Add-Label 'Forest density (sight_scale)' 24 232 190 $fontN ([System.Drawing.Color]::Gainsboro)
$script:tbScale = New-Object System.Windows.Forms.TextBox
$tbScale.Left=220; $tbScale.Top=229; $tbScale.Width=70
$tbScale.BackColor=[System.Drawing.Color]::FromArgb(50,50,54); $tbScale.ForeColor='White'
$tbScale.BorderStyle='FixedSingle'
$f.Controls.Add($tbScale)
Add-Label 'lower = denser woods' 298 232 160 $fontN ([System.Drawing.Color]::Gray) | Out-Null

# status panel
$lblState = New-Object System.Windows.Forms.Label
$lblState.Left=24; $lblState.Top=266; $lblState.Width=410; $lblState.Height=76
$lblState.Font = New-Object System.Drawing.Font('Consolas', 8.5)
$lblState.ForeColor=[System.Drawing.Color]::FromArgb(150,200,255)
$f.Controls.Add($lblState)

$btnPlay = New-Object System.Windows.Forms.Button
$btnPlay.Text='Play'; $btnPlay.Left=24; $btnPlay.Top=350; $btnPlay.Width=180; $btnPlay.Height=44
$btnPlay.FlatStyle='Flat'; $btnPlay.BackColor=[System.Drawing.Color]::FromArgb(27,94,32)
$btnPlay.ForeColor='White'; $btnPlay.Font=$fontH
$btnEdit = New-Object System.Windows.Forms.Button
$btnEdit.Text='Editor'; $btnEdit.Left=214; $btnEdit.Top=350; $btnEdit.Width=110; $btnEdit.Height=44
$btnEdit.FlatStyle='Flat'; $btnEdit.BackColor=[System.Drawing.Color]::FromArgb(55,55,60)
$btnEdit.ForeColor='White'; $btnEdit.Font=$fontN
$btnLog = New-Object System.Windows.Forms.Button
$btnLog.Text='Log'; $btnLog.Left=334; $btnLog.Top=350; $btnLog.Width=100; $btnLog.Height=44
$btnLog.FlatStyle='Flat'; $btnLog.BackColor=[System.Drawing.Color]::FromArgb(55,55,60)
$btnLog.ForeColor='White'; $btnLog.Font=$fontN
$f.Controls.AddRange(@($btnPlay,$btnEdit,$btnLog))

$lblWarn = New-Object System.Windows.Forms.Label
$lblWarn.Left=24; $lblWarn.Top=404; $lblWarn.Width=410; $lblWarn.Height=20
$lblWarn.Font=$fontN; $lblWarn.ForeColor=[System.Drawing.Color]::Orange
$f.Controls.Add($lblWarn)

# Resolved from the radio every time it is asked. Kept deliberately dumb:
# an earlier version launched REDUX no matter which build was picked, and the
# only way to be sure is to read the control and show the answer on screen.
function Current {
  if ($script:rbZw.Checked) { return $BUILDS['ZeeWolf'] }
  return $BUILDS['REDUX']
}

$script:loading = $false
function Refresh-State {
  $b = Current; $root = $b.Root; $exe = Join-Path $root $b.Exe
  $w = Get-Wrapper $root
  $script:loading = $true
  if ($w -eq 'DXVK') { $rbDx.Checked = $true } elseif ($w -eq 'dgVoodoo') { $rbDg.Checked = $true }
  $tbScale.Text = (Get-Ini $root 'sight_scale' '100')
  $script:loading = $false

  $laa = Get-Laa $exe
  $hookOk = (Test-Path $DLL) -and (Test-Path $INJ)
  $log = Join-Path $root 'tvt_los.log'
  $last = 'never run'
  if (Test-Path $log) {
    $t = (Get-Item $log).LastWriteTime
    $armed = (Select-String -Path $log -Pattern 'enforcement live' -Quiet)
    $last = "{0}  -  {1}" -f $t.ToString('ddd HH:mm'), $(if ($armed) {'occlusion armed'} else {'DID NOT arm'})
  }
  $lblState.Text = @(
    ("launches  {0}" -f $exe),
    ("renderer  {0}        4GB aware  {1}" -f $w, $(if($laa){'yes'}else{'NO'})),
    ("hook      {0}" -f $(if($hookOk){'present'}else{'MISSING - cannot enforce'})),
    ("last run  {0}" -f $last)
  ) -join "`r`n"

  $warn = @()
  if (-not $laa)    { $warn += 'That exe is capped at 2 GB - big maps will crash.' }
  if (-not $hookOk) { $warn += 'Hook missing: build with K:\tvt_los\build.bat' }
  if ($cbHud.Checked -and $w -ne 'DXVK') { $warn += 'The HUD only shows under DXVK.' }
  $lblWarn.Text = ($warn -join '  ')
}

function Switch-Wrapper([string]$want) {
  if ($script:loading) { return }
  $b = Current
  if ((Get-Wrapper $b.Root) -eq $want) { return }
  $arg = if ($want -eq 'DXVK') { 'dxvk' } else { 'dgvoodoo' }
  Start-Process cmd.exe -ArgumentList ('/c "' + (Join-Path $b.Root 'wrapper.bat') + '" ' + $arg) -WindowStyle Hidden -Wait
  Refresh-State
}

$rbRedux.Add_CheckedChanged({ if ($rbRedux.Checked) { Refresh-State } })
$rbZw.Add_CheckedChanged({    if ($rbZw.Checked)    { Refresh-State } })
$rbDx.Add_CheckedChanged({    if ($rbDx.Checked)    { Switch-Wrapper 'DXVK' } })
$rbDg.Add_CheckedChanged({    if ($rbDg.Checked)    { Switch-Wrapper 'dgVoodoo' } })
$cbHud.Add_CheckedChanged({ Refresh-State })

$btnLog.Add_Click({
  $p = Join-Path (Current).Root 'tvt_los.log'
  if (Test-Path $p) { Start-Process notepad.exe $p } else {
    [System.Windows.Forms.MessageBox]::Show('No log yet - play once first.','Log') | Out-Null }
})

$btnEdit.Add_Click({
  $b = Current
  if ((Get-Wrapper $b.Root) -ne 'dgVoodoo') {
    $r = [System.Windows.Forms.MessageBox]::Show(
      "The Editor needs dgVoodoo (DXVK provides no DirectDraw).`n`nSwitch to dgVoodoo and open the Editor?",
      'Editor', 'YesNo', 'Question')
    if ($r -ne 'Yes') { return }
    $rbDg.Checked = $true
  }
  Start-Process (Join-Path $b.Root $b.Editor) -WorkingDirectory $b.Root
})

$btnPlay.Add_Click({
  $b = Current; $root=$b.Root; $exe = Join-Path $root $b.Exe
  if (-not (Test-Path $exe)) {
    [System.Windows.Forms.MessageBox]::Show("Missing:`n$exe",'Cannot launch') | Out-Null; return }

  $s = $tbScale.Text.Trim()
  if ($s -match '^\d+$') { Set-Ini $root 'sight_scale' $s }

  if ($cbHud.Checked) {
    $env:DXVK_HUD='fps,drawcalls,gpuload'
    $env:DXVK_LOG_PATH='K:\dxvk_test'; $env:DXVK_STATE_CACHE_PATH='K:\dxvk_test'
  } else { $env:DXVK_HUD=$null }

  if ($cbLos.Checked) {
    if (-not ((Test-Path $DLL) -and (Test-Path $INJ))) {
      [System.Windows.Forms.MessageBox]::Show('The hook is missing - build it with K:\tvt_los\build.bat','Cannot enforce') | Out-Null
      return }
    Start-Process powershell -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "' + $CHK + '" -Log "' + (Join-Path $root 'tvt_los.log') + '"') -WindowStyle Hidden
    Start-Process $INJ -ArgumentList ('"' + $exe + '" "' + $DLL + '"') -WorkingDirectory $root
  } else {
    Start-Process $exe -WorkingDirectory $root
  }
  $f.WindowState = 'Minimized'
})

# The stock radio/check glyph is drawn dark-on-dark on this form and is
# effectively invisible. FlatStyle makes WinForms draw the circle and tick
# itself, using the control's own colours, so the selection shows. Layout is
# otherwise exactly as it was.
foreach ($c in @($rbRedux,$rbZw,$rbDg,$rbDx,$cbLos,$cbHud)) {
  $c.FlatStyle = 'Flat'
  $c.ForeColor = 'White'
  $c.FlatAppearance.CheckedBackColor = [System.Drawing.Color]::FromArgb(32,32,34)
  $c.FlatAppearance.BorderSize = 0
}

Refresh-State
[void]$f.ShowDialog()
