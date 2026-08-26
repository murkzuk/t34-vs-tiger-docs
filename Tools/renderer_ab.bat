@echo off
setlocal
title TvT renderer A/B  -  DXVK  <->  native D3D9

REM jm 2026-08-26.  Profiling showed 21%% of the frame in
REM NtWaitForAlertByThreadId, and 65%% of all syscall time is called from
REM DXVK's d3d9.dll - the game thread waiting on the DXVK command-stream
REM thread.  TvT issues only ~454 draw calls a frame, which native D3D9
REM handles trivially, so DXVK may be paying threading overhead for a
REM benefit this engine never collects.
REM
REM This ONLY renames a file, and renames it back.  Nothing is deleted.

set G=M:\T34vsTiger

if /I "%1"=="native" goto native
if /I "%1"=="dxvk"   goto dxvk
if /I "%1"=="status" goto status
goto usage

:native
if not exist "%G%\d3d9.dll" echo Already on native D3D9. & goto status
ren "%G%\d3d9.dll" d3d9.dll.dxvk
if errorlevel 1 (echo RENAME FAILED - is the game still running? & goto hold)
echo Switched to NATIVE D3D9.
goto status

:dxvk
if exist "%G%\d3d9.dll" echo Already on DXVK. & goto status
ren "%G%\d3d9.dll.dxvk" d3d9.dll
if errorlevel 1 (echo RENAME FAILED - is the game still running? & goto hold)
echo Switched back to DXVK.
goto status

:status
echo.
if exist "%G%\d3d9.dll"      echo   CURRENT: DXVK        (d3d9.dll present)
if not exist "%G%\d3d9.dll"  echo   CURRENT: native D3D9 (d3d9.dll renamed aside)
echo.
goto hold

:usage
echo.
echo   renderer_ab native   - rename DXVK aside, use Windows D3D9
echo   renderer_ab dxvk     - put DXVK back
echo   renderer_ab status   - which is active right now
echo.
echo   Note: the DXVK on-screen HUD only works on DXVK.  Measure the A/B
echo   with the drawcall probe instead - it reports fps on either renderer.

:hold
pause
