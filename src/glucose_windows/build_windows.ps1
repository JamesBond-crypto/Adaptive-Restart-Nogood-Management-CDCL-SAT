# Reproducible PowerShell Build Script for Glucose 4.2.1 on Windows
# Switches execution context to script directory using $PSScriptRoot

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
}

Push-Location $ScriptDir

try {
    Write-Host "Building glucose-simp for Windows in $ScriptDir using g++..." -ForegroundColor Cyan

    $sources = @(
        "core/Solver.cc",
        "core/lcm.cc",
        "simp/SimpSolver.cc",
        "simp/Main.cc",
        "utils/Options.cc",
        "utils/System.cc"
    )

    $includes = @("-I.", "-Icore", "-Isimp", "-Imtl", "-Iutils")
    $defines = @("-DNDEBUG", "-D__STDC_LIMIT_MACROS", "-D__STDC_FORMAT_MACROS")
    $flags = @("-O3", "-std=c++11")
    $libs = @("-lz", "-lpsapi")

    $argsList = $flags + $defines + $includes + $sources + $libs + @("-o", "glucose-simp.exe")

    $process = Start-Process -FilePath "g++" -ArgumentList $argsList -WorkingDirectory $ScriptDir -NoNewWindow -Wait -PassThru

    if ($process.ExitCode -eq 0) {
        $exePath = Join-Path $ScriptDir "glucose-simp.exe"
        Write-Host "Build succeeded: $exePath" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "Build failed with exit code $($process.ExitCode)" -ForegroundColor Red
        exit $process.ExitCode
    }
} finally {
    Pop-Location
}
