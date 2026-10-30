@echo off
cd /d "%~dp0"
call "L:\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars32.bat" >nul
cl /nologo /O2 /W3 /DWIN32 /D_CRT_SECURE_NO_WARNINGS test_gpa.c /Fe:test_gpa.exe >nul
if errorlevel 1 (echo BUILD FAILED & exit /b 1)
echo BUILD OK - test_gpa.exe
