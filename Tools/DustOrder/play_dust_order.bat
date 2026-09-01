@echo off
setlocal
title TvT - dust_order capture (pins the see-through-wheat mechanism)

REM   play_dust_order          REDUX  (M:\T34vsTiger)
REM   play_dust_order zw       ZeeWolf 2015
REM
REM PURE OBSERVATION - this changes nothing in the game. It only logs.
REM
REM WHAT TO DO
REM   1. Load a mission where you can see the see-through wheat.
REM   2. Drive the tank so it throws dust across the wheat, and look at the artefact.
REM      A few seconds is plenty - it captures the first 8 dust draws it sees.
REM   3. EXIT THE GAME NORMALLY (quit to menu, then exit).
REM      The log is written when the game shuts down, so DO NOT Alt+F4 or kill it,
REM      or there will be no log.
REM
REM Log: K:\TvTDeepseek\dust_order\dust_order_pid<PID>.log  (one per run - a
REM      throwaway test run can no longer overwrite a real capture)

set GAME=M:\T34vsTiger\TvsT_fullLOD_HARD_4GB.exe
if /I "%1"=="zw" set GAME=M:\T34vsTiger_ZW2015\TvsT_fullLOD_HARD_4GB.exe

set DLL=K:\TvTDeepseek\dust_order\dust_order.dll
set INJ=K:\tvt_probe\tvt_inject.exe

if not exist "%GAME%" goto nogame
if not exist "%DLL%"  goto nodll
if not exist "%INJ%"  goto noinj

echo.
echo  Launching with the dust_order capture attached.
echo  Drive through the wheat until you see the artefact, then EXIT NORMALLY.
echo.

"%INJ%" "%GAME%" "%DLL%"
if errorlevel 1 goto failed
exit /b 0

:nogame
echo  Game executable missing: %GAME%
goto hold
:nodll
echo  DLL missing: %DLL%  (build with build.bat)
goto hold
:noinj
echo  Injector missing: %INJ%
goto hold
:failed
echo.
echo  The injector refused or failed - reason above.
goto hold
:hold
echo.
echo  Nothing was launched. Press any key to close.
pause >nul
exit /b 1
