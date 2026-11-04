# Baseline Solver Build & Verification Report: Glucose 4.2.1 on Windows

**Project:** Adaptive Restart and Nogood Management for Constraint Satisfaction Solvers  
**Date:** 2026-10-29  
**Platform:** Windows 11 x64 (MSYS2 UCRT64 / MinGW-w64 G++ 14.2.0)  

---

## 1. Upstream Source & Version Identification

- **Official Repository:** `https://github.com/audemard/glucose.git`
- **Selected Version:** Glucose 4.2.1
- **Upstream Tag:** `4.2.1`
- **Exact Commit Hash:** `084d7375975408a06a1397cc4bc645a73b97fa65`
- **License:** MIT License
- **Upstream Reference Directory:** `base_solver/`
- **Pristine Verification:** Confirmed `base_solver/` has zero uncommitted changes (`working tree clean`) and zero diffs against the upstream tag.

---

## 2. Directory Separation Strategy

To ensure scientific reproducibility and avoid tampering with the upstream solver:
1. `base_solver/` remains **completely untouched**.
2. All Windows compatibility adaptations are isolated in `src/glucose_windows/`.
3. Test benchmark instances are stored in `benchmarks/smoke_test/`.

---

## 3. Compatibility Changes Made in `src/glucose_windows/`

Only non-algorithmic system differences were addressed. **No modifications were made to branching heuristics, restart policies, conflict analysis, LBD computations, or clause database reduction algorithms.**

| File | Modification | Technical Justification |
| :--- | :--- | :--- |
| `utils/System.h` | Implemented Windows `cpuTime()` via Win32 `GetProcessTimes()` with fallback to `clock()`. Implemented `realTime()` via standard C++11 `<chrono>` (`steady_clock`). | Replaced Unix `gettimeofday()` and `getrusage()` which are not present on Windows. |
| `utils/System.cc` | Implemented Windows `memUsed()` and `memUsedPeak()` using Win32 API `GetProcessMemoryInfo()` (`psapi.h`). Defined fallback for unsupported OS. | Replaced Linux `/proc/self/statm` and `/proc/self/status` parsing with native Windows resident set size metrics. |
| `simp/Main.cc` | 1. Guarded `#include <sys/resource.h>` under `#ifndef _WIN32`.<br>2. Guarded `SIGXCPU` signal registration.<br>3. Replaced POSIX `setrlimit()` calls with informative runtime warning.<br>4. Connected `memUsedPeak()` to solver statistics output. | `<sys/resource.h>`, `RLIMIT_CPU`, and `SIGXCPU` do not exist on Windows. In-process OS resource limits must be managed by external process wrappers. |
| `core/Solver.cc` | Replaced POSIX `putc_unlocked` with standard ANSI C `putc` in `write_char` (line 337). | `putc_unlocked` is a non-standard POSIX function unavailable in MinGW C runtime. Standard `putc` provides identical binary output. |

---

## 4. Build Commands & Reproducibility

### Native Compiler Command
Executed using MinGW-w64 G++ 14.2.0:
```cmd
cd src\glucose_windows
g++ -O3 -std=c++11 -DNDEBUG -D__STDC_LIMIT_MACROS -D__STDC_FORMAT_MACROS ^
    -I. -Icore -Isimp -Imtl -Iutils ^
    core/Solver.cc core/lcm.cc simp/SimpSolver.cc simp/Main.cc utils/Options.cc utils/System.cc ^
    -lz -lpsapi -o glucose-simp.exe
```

### Reproducible Build Scripts
- **Batch Script:** `src/glucose_windows/build_windows.bat`
- **PowerShell Script:** `src/glucose_windows/build_windows.ps1`

### Build Outcome
- Exit status: `0` (Success)
- Output binary: `src/glucose_windows/glucose-simp.exe` (488,243 bytes)
- Zero warnings or errors during compilation.

---

## 5. Correctness Verification (Smoke Tests)

### Test A: SAT Instance
- **Path:** `benchmarks/smoke_test/test_sat.cnf`
- **CNF Formulation:**
  ```text
  p cnf 2 2
  1 2 0
  -1 2 0
  ```
- **Execution Command:**
  ```powershell
  & "src\glucose_windows\glucose-simp.exe" -model "benchmarks\smoke_test\test_sat.cnf"
  ```
- **Observed Solver Output:**
  ```text
  c
  c This is glucose 4.2.1 --  based on MiniSAT (Many thanks to MiniSAT team)
  c
  c ========================================[ Problem Statistics ]===========================================
  c |                                                                                                       |
  c |  Number of variables:             2                                                                   |
  c |  Number of clauses:               2                                                                   |
  c |  Parse time:                   0.00 s                                                                 |
  c |                                                                                                       |
  c | Preprocesing is fully done
  c |  Eliminated clauses:           0.00 Mb                                                                |
  c |  Simplification time:          0.00 s                                                                 |
  c |                                                                                                       |
  ...
  c restarts              : 1 (0 conflicts in avg)
  c conflicts             : 0              (0 /sec)
  c decisions             : 1              (0.00 % random) (64 /sec)
  c propagations          : 1              (64 /sec)
  c Memory used           : 6.24 MB
  c CPU time              : 0.015625 s

  s SATISFIABLE
  v -1 2 0
  ```
- **Observed Exit Code:** `10` (Standard DIMACS code for `SATISFIABLE`).
- **Verification:** Assignment $x_1 = \text{False}, x_2 = \text{True}$ satisfies both clauses $(\neg x_1 \vee x_2)$ and $(x_1 \vee x_2)$. Correct.

---

### Test B: UNSAT Instance
- **Path:** `benchmarks/smoke_test/test_unsat.cnf`
- **CNF Formulation:**
  ```text
  p cnf 1 2
  1 0
  -1 0
  ```
- **Execution Command:**
  ```powershell
  & "src\glucose_windows\glucose-simp.exe" "benchmarks\smoke_test\test_unsat.cnf"
  ```
- **Observed Solver Output:**
  ```text
  c
  c This is glucose 4.2.1 --  based on MiniSAT (Many thanks to MiniSAT team)
  c
  c ========================================[ Problem Statistics ]===========================================
  c |                                                                                                       |
  c |  Number of variables:             1                                                                   |
  c |  Number of clauses:               0                                                                   |
  c |  Parse time:                   0.00 s                                                                 |
  c |                                                                                                       |
  c | Preprocesing is fully done
  c |  Simplification time:          0.00 s                                                                 |
  c |                                                                                                       |
  c =========================================================================================================
  Solved by simplification
  c restarts              : 0 (0 conflicts in avg)
  c conflicts             : 0              (nan /sec)
  c decisions             : 0              ( nan % random) (nan /sec)
  c propagations          : 1              (inf /sec)
  c Memory used           : 6.17 MB
  c CPU time              : 0 s

  s UNSATISFIABLE
  ```
- **Observed Exit Code:** `20` (Standard DIMACS code for `UNSATISFIABLE`).
- **Verification:** Formula contains $(x_1) \wedge (\neg x_1)$ which has no satisfying assignment. Directly solved by preprocessor simplification. Correct.

---

## 6. Telemetry & Measurement Limitations

1. **CPU Time Resolution:** Measured via `GetProcessTimes()`, tracking kernel + user CPU time dedicated to the process with ~10ms timer resolution on Windows.
2. **Wall-Clock Time Resolution:** Measured via `std::chrono::steady_clock`, providing microsecond/nanosecond resolution.
3. **Memory Reporting:** Peak working set memory is queried using `GetProcessMemoryInfo()`. In small test instances, memory reports baseline executable working set (~6.2 MB).
4. **Process Limit Enforcement:** In-process CPU time and memory hard-limits (`-cpu-lim` and `-mem-lim`) via Unix `setrlimit` are not supported natively by Windows. For future large-scale benchmarking, execution timeouts will be enforced externally by our Python experiment runner.

