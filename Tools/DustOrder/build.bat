@echo off
rem dust_order build - x86 MSVC, /LD for a DLL, /O2, /W3, WIN32.
cd /d "%~dp0"
call "L:\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars32.bat" >nul
cl /nologo /LD /O2 /W3 /DWIN32 /D_CRT_SECURE_NO_WARNINGS dust_order.cpp /link /OUT:dust_order.dll user32.lib
if errorlevel 1 (
  echo BUILD FAILED
  exit /b 1
)
echo BUILD OK - dust_order.dll
