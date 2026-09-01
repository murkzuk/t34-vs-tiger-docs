@echo off
cd /d "%~dp0"
call "L:\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars32.bat" >nul 2>&1
cl /nologo /LD /O2 /W3 /DWIN32 /D_CRT_SECURE_NO_WARNINGS atmos_wysiwyg.cpp /link /OUT:atmos_wysiwyg.dll user32.lib
if errorlevel 1 (
  echo BUILD FAILED
  exit /b 1
)
echo BUILD OK - atmos_wysiwyg.dll
