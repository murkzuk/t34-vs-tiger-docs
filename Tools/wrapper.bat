@echo off
REM Switch REDUX between the two graphics wrappers.
REM
REM   wrapper dgvoodoo   dgVoodoo 2.86.4 - D3D9 + DirectDraw. Lighter on a
REM                      32-bit process's address space. The Editor wants the
REM                      DirectDraw half, so this is the one that lets it open.
REM   wrapper dxvk       DXVK - Vulkan. Usually smoother, but hungrier on
REM                      address space, and it provides no DirectDraw so
REM                      ddraw.dll gets parked.
REM   wrapper status     show which is active
REM
REM ReShade is NOT affected either way: it loads from
REM C:\ProgramData\ReShade\ReShade32.dll via its own global injector, not
REM through d3d9.dll.

setlocal
cd /d "%~dp0"

if /I "%1"=="dgvoodoo" goto dgvoodoo
if /I "%1"=="dxvk"     goto dxvk
if /I "%1"=="native"   goto native
if /I "%1"=="status"   goto status
goto usage

:dgvoodoo
if exist d3d9.dll.dgvoodoo (
  if exist d3d9.dll ren d3d9.dll d3d9.dll.dxvk
  ren d3d9.dll.dgvoodoo d3d9.dll
)
if exist ddraw.dll.off ren ddraw.dll.off ddraw.dll
echo Now using dgVoodoo.
goto status

:dxvk
if exist d3d9.dll.dxvk (
  if exist d3d9.dll ren d3d9.dll d3d9.dll.dgvoodoo
  ren d3d9.dll.dxvk d3d9.dll
)
if exist ddraw.dll ren ddraw.dll ddraw.dll.off
echo Now using DXVK - DirectDraw parked, the Editor may not open.
goto status

REM jm 2026-08-26: NATIVE - no wrapper at all, Windows' own d3d9.dll.
REM Measured 2026-08-26: native is +1.9%% vs DXVK, which is inside the +/-4%%
REM noise floor - i.e. the same speed. Kept as an option for diagnosing
REM whether a visual bug comes from the wrapper or from the game.
REM Note the DXVK HUD does not exist on native; use F9 (costs fps) instead.
:native
if exist d3d9.dll (
  for %%A in (d3d9.dll) do if %%~zA GTR 2000000 (ren d3d9.dll d3d9.dll.dxvk) else (ren d3d9.dll d3d9.dll.dgvoodoo)
)
if exist ddraw.dll ren ddraw.dll ddraw.dll.off
echo Now using NATIVE D3D9 - no wrapper.
goto status

:status
echo.
if exist d3d9.dll  echo   d3d9.dll   active
if exist ddraw.dll echo   ddraw.dll  active
if exist d3d9.dll.dxvk     echo   d3d9.dll.dxvk      parked
if exist d3d9.dll.dgvoodoo echo   d3d9.dll.dgvoodoo  parked
if exist ddraw.dll.off     echo   ddraw.dll.off      parked
echo.
goto :eof

:usage
echo.
echo   wrapper dgvoodoo ^| dxvk ^| status
echo.
goto status
