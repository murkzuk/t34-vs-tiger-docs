@echo off
setlocal
title ZeeWolf 2015 - line of sight

REM Play the ZeeWolf 2015 build with line of sight.
REM
REM ZW's engine binaries are byte-identical to REDUX's, so this is the same DLL
REM with no rebuild. What was different, and is now handled, is the map size:
REM ZW missions run 9000 to 36000 metres across and the size is read per
REM mission from that mission folder's WorldMatricies.script.
REM
REM Settings live in M:\T34vsTiger_ZW2015\tvt_los.ini - a separate file from
REM the REDUX one, because ZW's woods are thicker and may want their own
REM sight_scale. The log lands in M:\T34vsTiger_ZW2015\tvt_los.log; look for
REM "world NNNN m across" and "enforcement live" near the top.
REM
REM Which installs may run this is decided by K:\tvt_los\tvt_los_allow.txt.
REM
REM Nothing on disk is modified - launch ZW normally for a stock ZW.

set GAME=M:\T34vsTiger_ZW2015\TvsT_fullLOD_HARD_4GB.exe
set DLL=K:\tvt_los\tvt_los_hook.dll
set INJ=K:\tvt_probe\tvt_inject.exe

if not exist "%GAME%" goto nogame
if not exist "%DLL%"  goto nodll
if not exist "%INJ%"  goto noinj

"%INJ%" "%GAME%" "%DLL%"
if errorlevel 1 goto failed
exit /b 0

:nogame
echo.
echo  The ZW executable is missing:
echo    %GAME%
goto hold

:nodll
echo.
echo  The line-of-sight DLL is missing:
echo    %DLL%
echo  Build it with K:\tvt_los\build.bat
goto hold

:noinj
echo.
echo  The injector is missing:
echo    %INJ%
echo  Build it with K:\tvt_probe\build.bat
goto hold

:failed
echo.
echo  The injector refused or failed - its reason is printed above.
echo.
echo  The usual causes:
echo    - M:\T34vsTiger_ZW2015 is not listed in K:\tvt_los\tvt_los_allow.txt
echo    - the game is already running
echo    - antivirus blocked the injection
goto hold

:hold
echo.
echo  ---------------------------------------------------------------
echo  Nothing was launched. Press any key to close this window.
echo  ---------------------------------------------------------------
pause >nul
exit /b 1
