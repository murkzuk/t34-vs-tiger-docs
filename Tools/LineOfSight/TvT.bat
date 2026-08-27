@echo off
REM jm 2026-08-27: cmd cannot execute a .ps1 - "cmd /c launcher.ps1" merely
REM prints the source to the console. This runs it properly.
REM   -STA          WinForms requires a single-threaded apartment
REM   -NoProfile    do not let a user profile change behaviour
REM   -ExecutionPolicy Bypass   the script is local and unsigned
REM Forward slashes on purpose: PowerShell accepts them, and a backslash
REM before t/n/r keeps getting eaten by the tools that generate this file.
start "" powershell -NoProfile -ExecutionPolicy Bypass -STA -File "K:/tvt_los/TvT_Launcher.ps1"
