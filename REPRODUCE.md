# Complete Reproduction Guide

**Project:** Adaptive Restart and Nogood Management for Constraint Satisfaction Solvers  
**Authors:** Manav Garg (25125026) & Kugashiya Bhavy (25125024)  
**Advisor:** Prof. Manoj Kumar  

---

## 1. System Requirements & Environment

- **Operating System:** Windows 10 or Windows 11 (64-bit)
- **Compiler:** MinGW-w64 G++ 14+ (MSYS2 UCRT64 distribution recommended)
- **C++ Standard:** C++11 or higher
- **Required Libraries:**
  - `zlib` (`-lz` for reading gzipped CNFs)
  - `psapi` (`-lpsapi` for measuring Windows process working set memory)
- **Python Environment:** Python 3.10+ (with standard libraries: `os`, `sys`, `json`, `csv`, `subprocess`, `argparse`, `pathlib`)
- **Optional Python Libraries:** `matplotlib` (only needed for generating PNG performance plots)

---

## 2. Compilation Instructions

From the root of the repository, open PowerShell or Command Prompt:

### Step 1: Navigate to Solver Source
```cmd
cd src\glucose_windows
```

### Step 2: Build the Main Solver (`glucose-simp.exe`)
```cmd
.\build_windows.bat
```
*Expected Output:*
```text
Building glucose-simp for Windows in ...
Build succeeded: ...\glucose-simp.exe
```

### Step 3: Build the Stagnation-Gated QRE Solver (`glucose-qre-gated.exe`)
```cmd
.\build_qre_gated.bat
```

### Step 4: Build the Portfolio-MAB Solver (`glucose-portfolio-mab.exe`)
```cmd
.\build_portfolio_mab.bat
```

*Note: Pre-compiled 64-bit release binaries are already included in `src/glucose_windows/` for immediate execution without requiring compilation.*

---

## 3. Basic Execution & Verification Tests

Return to the repository root:
```cmd
cd ..\..
```

### Quick Smoke Test (SAT Instance)
```cmd
.\src\glucose_windows\glucose-simp.exe benchmarks\smoke_test\test_sat.cnf
```
*Expected Result:* `s SATISFIABLE` (Exit code: 10)

### Quick Smoke Test (UNSAT Instance)
```cmd
.\src\glucose_windows\glucose-simp.exe benchmarks\smoke_test\test_unsat.cnf
```
*Expected Result:* `s UNSATISFIABLE` (Exit code: 20)

### Running Solver with Specific Heuristics
```cmd
:: 1. Baseline Glucose (Native EWMA + Native LBD Reduction)
.\src\glucose_windows\glucose-simp.exe -restart-strategy=baseline -reduction-strategy=baseline benchmarks\smoke_test\test_sat.cnf

:: 2. V3 Maximum Drawdown + Adaptive-Fixed Clause Retention (Winning Development Strategy)
.\src\glucose_windows\glucose-simp.exe -restart-strategy=v3 -reduction-strategy=adaptive-fixed benchmarks\smoke_test\test_sat.cnf

:: 3. Baseline Restarts + Adaptive-Fixed Clause Retention (Winning Holdout Strategy)
.\src\glucose_windows\glucose-simp.exe -restart-strategy=baseline -reduction-strategy=adaptive-fixed benchmarks\smoke_test\test_sat.cnf
```

---

## 4. Automated Reproduction Harnesses

### 1. Fast End-to-End Test Framework (Takes < 5 seconds)
Validates solver options, telemetry outputs, and model verifier:
```cmd
python experiments/test_framework.py
```

### 2. Verify Algorithm Telemetry Invariance
Confirms that shadow and diagnostic calculations do not alter the deterministic search path:
```cmd
python experiments/verify_qre_gated_invariance.py
python experiments/verify_portfolio_mab_invariance.py
```

### 3. Re-Evaluate Development Benchmark Suite
Runs the 36-instance development suite across configurations (648 runs):
```cmd
python experiments/run_qre_gated_full_development.py
```

### 4. Acquire & Re-Evaluate Final Holdout Suite
To re-evaluate the 48 unseen holdout benchmarks, acquire and validate the suite first:
```cmd
:: Step A: Download & cryptographically verify the 48 SATLIB / DIMACS benchmarks
python benchmarks/final_holdout/acquire_holdout_suite.py
python benchmarks/final_holdout/validate_holdout_suite.py

:: Step B: Execute the full factorial holdout evaluation (1,152 runs under 30.0 s timeout)
python experiments/run_final_holdout_evaluation.py
```

### 5. Regenerate Holdout Performance Plots
Aggregates the holdout master CSV and redraws the 7 publication plots in `docs/figures/final_holdout/`:
```cmd
python experiments/plot_final_holdout.py
```
