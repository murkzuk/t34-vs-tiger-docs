@echo off
setlocal
title TvT - WYSIWYG atmosphere (live sun, EDITOR)

REM Injects atmos_wysiwyg.dll into the LEVEL EDITOR (Editor.exe).
REM Open a mission in the editor, then press:
REM   F6 = sun to dawn (10 deg ENE)
REM   F7 = sun overhead
REM   F8 = sun low-west
REM The sky/lighting in the 3D viewport should change IMMEDIATELY.
REM
REM Log: K:\TvTDeepseek\atmos_wysiwyg\atmos_wysiwyg.log

set GAME=M:\T34vsTiger_ZW2015\Editor.exe
set DLL=K:\TvTDeepseek\atmos_wysiwyg\atmos_wysiwyg.dll
set INJ=K:\tvt_probe\tvt_inject.exe

if not exist "%GAME%" goto nogame
if not exist "%DLL%"  goto nodll
if not exist "%INJ%"  goto noinj

"%INJ%" "%GAME%" "%DLL%"
if errorlevel 1 goto failed
exit /b 0

:nogame
echo  Editor executable missing: %GAME%
goto hold
:nodll
echo  DLL missing: %DLL%  (build with build_atmos.bat)
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
