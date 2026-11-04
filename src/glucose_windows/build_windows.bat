@echo off
REM =========================================================================
REM Reproducible Windows Build Script for Glucose 4.2.1
REM Compiler: MinGW-w64 G++ 14+ (C++11 standard)
REM Libraries: -lz (zlib for gzipped CNF), -lpsapi (process memory metrics)
REM =========================================================================

setlocal
cd /d "%~dp0"

echo Building glucose-simp for Windows in %CD%...

g++ -O3 -std=c++11 -DNDEBUG -D__STDC_LIMIT_MACROS -D__STDC_FORMAT_MACROS ^
    -I. -Icore -Isimp -Imtl -Iutils ^
    core/Solver.cc core/lcm.cc simp/SimpSolver.cc simp/Main.cc utils/Options.cc utils/System.cc ^
    -lz -lpsapi -o glucose-simp.exe

set BUILD_STATUS=%ERRORLEVEL%

if %BUILD_STATUS% EQU 0 (
    echo Build succeeded: %CD%\glucose-simp.exe
) else (
    echo Build failed with error %BUILD_STATUS%
)

endlocal & exit /b %BUILD_STATUS%
