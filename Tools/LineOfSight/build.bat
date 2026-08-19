@echo off
REM Build the vision-function watcher. x86, because TvT is a 32-bit process
REM (machine 0x014c) - a 64-bit DLL cannot be injected into it.
call "L:\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars32.bat" >nul
cd /d K:\tvt_los
echo --- building tvt_los_hook.dll (x86) ---
cl /nologo /LD /O2 /W3 /DWIN32 hook.cpp /link /OUT:tvt_los_hook.dll
