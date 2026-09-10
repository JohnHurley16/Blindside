@echo off
REM Build and run the C++ smoke test twice: against the cdylib's import library and
REM against the staticlib. /MD is the CRT setting Unreal uses on Win64 (bUseStaticCRT is
REM false by default), so this is the link Unreal would be doing.
REM
REM Usage: cpptest\build.cmd     (from spikes\unreal\ffi)

setlocal
set SPIKE=%~dp0..
set INC=%SPIKE%\rust\crates\blindside-ffi\include
set LIBDIR=%SPIKE%\rust\target\release
set OUT=%SPIKE%\cpptest\out
if not exist "%OUT%" mkdir "%OUT%"

call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 (echo could not find vcvars64.bat & exit /b 1)

echo === cdylib, via the import library ===
cl /nologo /std:c++17 /EHsc /W4 /WX /MD /O2 /I "%INC%" ^
   /Fo"%OUT%\\" /Fe"%OUT%\smoke_dll.exe" "%SPIKE%\cpptest\smoke.cpp" ^
   /link "%LIBDIR%\blindside_ffi.dll.lib"
if errorlevel 1 exit /b 1
copy /y "%LIBDIR%\blindside_ffi.dll" "%OUT%\" >nul
"%OUT%\smoke_dll.exe"
if errorlevel 1 exit /b 1

echo.
echo === staticlib ===
cl /nologo /std:c++17 /EHsc /W4 /WX /MD /O2 /DBLINDSIDE_STATIC /I "%INC%" ^
   /Fo"%OUT%\\" /Fe"%OUT%\smoke_static.exe" "%SPIKE%\cpptest\smoke.cpp" ^
   /link "%LIBDIR%\blindside_ffi.lib" ^
   ws2_32.lib userenv.lib advapi32.lib bcrypt.lib ntdll.lib synchronization.lib
if errorlevel 1 exit /b 1
"%OUT%\smoke_static.exe"
if errorlevel 1 exit /b 1

echo.
for %%F in ("%OUT%\smoke_dll.exe" "%OUT%\smoke_static.exe" "%LIBDIR%\blindside_ffi.dll") do @echo %%~zF bytes  %%~nxF
endlocal
