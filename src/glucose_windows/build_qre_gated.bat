@echo off
REM =========================================================================
REM Experimental Build Script for Stagnation-Gated QRE (Step 40)
REM Targets:
REM   - glucose-qre-gated.exe        (Optimized Release, -O3, -DNDEBUG)
REM   - glucose-qre-gated-debug.exe  (Assertion-Enabled Debug, -g, -O0, -DDEBUG)
REM =========================================================================

setlocal
cd /d "%~dp0"

echo [1/2] Building optimized release binary: glucose-qre-gated.exe...
g++ -O3 -std=c++11 -DNDEBUG -D__STDC_LIMIT_MACROS -D__STDC_FORMAT_MACROS ^
    -I. -Icore -Isimp -Imtl -Iutils ^
    core/Solver.cc core/lcm.cc simp/SimpSolver.cc simp/Main.cc utils/Options.cc utils/System.cc ^
    -lz -lpsapi -o glucose-qre-gated.exe

if %ERRORLEVEL% NEQ 0 (
    echo Error: Release build failed with code %ERRORLEVEL%!
    exit /b %ERRORLEVEL%
)
echo Release build succeeded: %CD%\glucose-qre-gated.exe

echo [2/2] Building assertion-enabled debug binary: glucose-qre-gated-debug.exe...
g++ -g -O0 -std=c++11 -DDEBUG -D__STDC_LIMIT_MACROS -D__STDC_FORMAT_MACROS ^
    -I. -Icore -Isimp -Imtl -Iutils ^
    core/Solver.cc core/lcm.cc simp/SimpSolver.cc simp/Main.cc utils/Options.cc utils/System.cc ^
    -lz -lpsapi -o glucose-qre-gated-debug.exe

if %ERRORLEVEL% NEQ 0 (
    echo Error: Debug build failed with code %ERRORLEVEL%!
    exit /b %ERRORLEVEL%
)
echo Debug build succeeded: %CD%\glucose-qre-gated-debug.exe

endlocal & exit /b 0

