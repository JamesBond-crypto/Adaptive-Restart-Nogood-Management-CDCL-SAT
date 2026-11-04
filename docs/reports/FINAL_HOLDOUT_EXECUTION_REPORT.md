# Final Holdout Execution Report

> **Step 36 Research Milestone & Execution Document**  
> **Project:** Adaptive Restart and Nogood Reuse for Constraint Satisfaction  
> **Solver Testbed:** Glucose 4.2.1 (Windows x86_64, MinGW-w64 G++ 14.2.0)  
> **Campaign Target:** 8 Frozen Configurations $\times$ 48 Holdout Benchmarks $\times$ 3 Repetitions (1,152 Planned Runs)  
> **Execution Status:** **COMPLETED SUCCESSFULLY (1,152 / 1,152 Runs)**  
> **Dataset Status:** **READY FOR STEP 37 STATISTICAL ANALYSIS**  

---

## 1. Execution Environment & Testbed Specifications

| Attribute | Specification |
| :--- | :--- |
| **Operating System** | Windows 11 Enterprise (AMD64 / x86_64) |
| **Compiler** | MinGW-w64 `g++.exe (Rev2, Built by MSYS2 project) 14.2.0` |
| **Build Flags** | `-O3 -std=c++11 -DNDEBUG -D__STDC_LIMIT_MACROS -D__STDC_FORMAT_MACROS -I. -Icore -Isimp -Imtl -Iutils -lz -lpsapi` |
| **Python Runtime** | Python 3.13.0 (with `psutil 7.2.2` process profiling) |
| **Working Directory** | [`D:\DAC_203@Project`](file:///D:/DAC_203@Project) (Available disk space: 62.7 GB) |
| **Wall-Clock Timeout** | 30.00 seconds per execution (PAR-2 penalty = 60.00s) |

---

## 2. Frozen Binary & Source Identifiers

| Component | Identifier / Verification Hash | Status |
| :--- | :--- | :---: |
| **Source Commit** | [`16ad544bd3d20d88a054aea3b962784e380ae9be`](file:///D:/DAC_203@Project) (branch `master`) | Verified Clean Tree |
| **Release Binary Path** | [`src/glucose_windows/glucose-simp.exe`](file:///D:/DAC_203@Project/src/glucose_windows/glucose-simp.exe) | Verified Untouched |
| **Release Binary SHA-256** | `e811005ab18256aa70efba2945ad5a578f5a38abec7e5c563d0989fd69e06b66` | Match Expected |
| **Release Binary Size** | 520,422 bytes | Match Expected |
| **`base_solver/` Status** | Unmodified reference Glucose 4.2.1 repository | Clean Working Tree |

---

## 3. Dataset and Configuration Counts

- **Frozen Configurations (8):** Loaded from [`experiments/frozen_configurations.json`](file:///D:/DAC_203@Project/experiments/frozen_configurations.json):
  - `cfg01_baseline_base`: Baseline restarts + Baseline reduction
  - `cfg02_v1_base`: Adaptive Restart V1 ($\theta=0.60$) + Baseline reduction
  - `cfg03_v3dd_base`: V3 Drawdown-Only ($D_t \ge 0.75, 30\text{ cfc}$) + Baseline reduction
  - `cfg04_noheuristic_base`: No-Heuristic restart + Baseline reduction
  - `cfg05_baseline_adaptfix`: Baseline restarts + Adaptive-Fixed reduction ($0.50/0.40/0.10$)
  - `cfg06_v1_adaptfix`: Adaptive Restart V1 + Adaptive-Fixed reduction
  - `cfg07_v3dd_adaptfix`: V3 Drawdown-Only + Adaptive-Fixed reduction
  - `cfg08_noheuristic_adaptfix`: No-Heuristic restart + Adaptive-Fixed reduction
- **Holdout Benchmark Suite (48):** Loaded from [`benchmarks/final_holdout/holdout_manifest.json`](file:///D:/DAC_203@Project/benchmarks/final_holdout/holdout_manifest.json):
  - 8 Industrial / Circuit Verification (`bf`, `ssa`)
  - 6 Application / Planning (`logistics`, `hanoi`)
  - 14 Crafted / Combinatorial UNSAT (`dubois`, `pret`, `aim-no`)
  - 8 Combinatorial Graph 3-Coloring (`flat100`, `flat150`)
  - 12 Uniform Random 3-SAT (`uf200`, `uuf200`)
- **Total Planned Executions:** $8 \text{ configs} \times 48 \text{ benchmarks} \times 3 \text{ repetitions} = \mathbf{1,152\text{ runs}}$.

---

## 4. Execution Scheduling & Resumption Protocol

The test harness [`experiments/run_final_holdout_evaluation.py`](file:///D:/DAC_203@Project/experiments/run_final_holdout_evaluation.py) was deployed with the following features:
1. **Balanced Cyclic Execution Schedule:**
   For repetition $r \in [1, 2, 3]$:
   - For benchmark index $b \in [0..47]$ (sorted deterministically `HOLDOUT_01` to `HOLDOUT_48`):
     - For offset $o \in [0..7]$:
       - $\text{config\_idx} = (o + b + (r - 1)) \bmod 8$
       - Generates a balanced cyclic permutation ensuring all configurations are rotated across benchmarks and repetitions.
2. **Safe Resumption & Atomic Record Writes:**
   - Pre-checks [`experiments/results/final_holdout/master_results.csv`](file:///D:/DAC_203@Project/experiments/results/final_holdout/master_results.csv) upon startup.
   - Skips already completed runs with valid status and wall-clock records.
   - Flushes and syncs (`os.fsync`) every newly completed row immediately.
   - Saves raw stdout and stderr to individual per-run logs in [`experiments/results/final_holdout/logs/`](file:///D:/DAC_203@Project/experiments/results/final_holdout/logs/).

---

## 5. Incident Resolution: Run 9 Label Contradiction

During initial execution, Run 9 triggered a halt under Section 5 protocol safeguards due to a label discrepancy on `bf1355-075.cnf`. The incident was audited and resolved via authorized Path A:
- **Root Cause:** A clerical inversion in the Step 34 acquisition dictionary had marked undetectable circuit faults as `SAT` instead of `UNSAT`.
- **Literature Evidence:** Official DIMACS Challenge (1993) and UBC SATLIB tables confirm `bf1355-075.cnf`, `ssa0432-003.cnf`, `ssa2670-130.cnf`, and `ssa2670-141.cnf` are provably **UNSAT**, while `ssa7552-158.cnf` is **SAT**.
- **Preservation & Amendment:** Original manifests were archived with timestamped backups, an append-only amendment record was logged in [`benchmarks/final_holdout/LABEL_AMENDMENT_RECORD.md`](file:///D:/DAC_203@Project/benchmarks/final_holdout/LABEL_AMENDMENT_RECORD.md), and Run 9 was reconciled as `VERIFIED_UNSAT` without erasing the historical incident.
- **Resumption:** Execution resumed cleanly from Run 10 without re-running prior runs or double-counting.

---

## 6. Final Campaign Execution Accounting

| Metric | Pre-Registered Target | Completed Execution | Status |
| :--- | :---: | :---: | :---: |
| **Total Planned Runs** | 1,152 | 1,152 | **100.0% Complete** |
| **Unique Run IDs** | 1,152 | 1,152 | **0 Duplicates** |
| **Contiguous Execution Orders**| 1 to 1,152 | 1 to 1,152 | **100% Contiguous** |
| **Runs per Configuration** | 144 | 144 (across all 8 configs) | **100% Balanced** |
| **Runs per Benchmark** | 24 | 24 (across all 48 instances) | **100% Balanced** |
| **Runs per Repetition** | 384 | 384 (Rep 1, 2, 3) | **100% Balanced** |
| **Satisfiable Solves (SAT)** | — | **504 runs** | **100.0% Verified by Model Checker** |
| **Unsatisfiable Solves (UNSAT)**| — | **648 runs** | **100.0% Cross-Checked by Literature**|
| **Timeouts ($> 30.0\text{s}$)** | — | **0 runs** | **0 Timeouts** |
| **Solver Crashes / Errors** | 0 | **0 runs** | **0 Errors** |
| **Unresolved Contradictions** | 0 | **0 runs** | **0 Contradictions** |
| **Total Execution Wall Time** | — | **317.07 seconds (5.28 minutes)**| **High-Throughput Execution** |

---

## 7. Model Verification & Correctness Audit

- **Independent Model Verifier:** Standalone script [`experiments/verify_model.py`](file:///D:/DAC_203@Project/experiments/verify_model.py).
- **Total SAT Instances Verified:** **504 / 504 (100.0%)**
- **Model Checker Status:** Every reported truth assignment was tested against every clause of the raw unsimplified DIMACS CNF files. Exactly zero clause violations or contradictory literal assignments occurred.
- **UNSAT Proof Consistency:** All 648 UNSAT outcomes matched the proven academic ground truth documented in [`benchmarks/final_holdout/LABEL_AMENDMENT_RECORD.md`](file:///D:/DAC_203@Project/benchmarks/final_holdout/LABEL_AMENDMENT_RECORD.md).

---

## 8. Telemetry Coverage & Data Quality

Every record in [`experiments/results/final_holdout/master_results.csv`](file:///D:/DAC_203@Project/experiments/results/final_holdout/master_results.csv) includes:
- True high-resolution wall-clock time (`wall_time_s`).
- Process CPU time (`process_cpu_time_s`) and internal solver CPU time (`solver_cpu_time_s`).
- Peak resident set size memory (`process_peak_rss_mb`) and internal solver reported memory (`solver_memory_mb`).
- Search counters: conflicts, decisions, propagations, genuine restarts, blocked restarts.
- V1 adaptive restart metrics: adaptive requests, adaptive restarts, rolling Sharpe scores ($S_W, S_{\text{global}}$).
- V3 active restart metrics: drawdown requests, executed restarts, mean returns, fast/slow EWMAs, max observed drawdown.
- Clause retention metrics: `reduce_db_count`, removed learned clauses, DL2 glue clauses, adaptive postpone evaluations and increments.
- Path to raw execution log in [`experiments/results/final_holdout/logs/`](file:///D:/DAC_203@Project/experiments/results/final_holdout/logs/).

---

## 9. Exact Paths to Saved Artifacts

- **Harness Script:** [`experiments/run_final_holdout_evaluation.py`](file:///D:/DAC_203@Project/experiments/run_final_holdout_evaluation.py)
- **Master Results CSV:** [`experiments/results/final_holdout/master_results.csv`](file:///D:/DAC_203@Project/experiments/results/final_holdout/master_results.csv)
- **Execution Logs Directory:** [`experiments/results/final_holdout/logs/`](file:///D:/DAC_203@Project/experiments/results/final_holdout/logs/) (contains all 1,152 individual `.log` files)
- **Checkpoint JSON:** [`experiments/results/final_holdout/checkpoint.json`](file:///D:/DAC_203@Project/experiments/results/final_holdout/checkpoint.json)
- **Completion Summary JSON:** [`experiments/results/final_holdout/completion_summary.json`](file:///D:/DAC_203@Project/experiments/results/final_holdout/completion_summary.json)
- **Label Amendment Record:** [`benchmarks/final_holdout/LABEL_AMENDMENT_RECORD.md`](file:///D:/DAC_203@Project/benchmarks/final_holdout/LABEL_AMENDMENT_RECORD.md)
- **Audit Document:** [`docs/FINAL_HOLDOUT_LABEL_CORRECTION_AUDIT.md`](file:///D:/DAC_203@Project/docs/FINAL_HOLDOUT_LABEL_CORRECTION_AUDIT.md)

---

## 10. Readiness for Step 37 Statistical Analysis

**Current Status: FULLY READY FOR STEP 37 STATISTICAL ANALYSIS**

The final evaluation campaign is complete:
1. Exactly 1,152 valid, non-duplicated execution records exist in `master_results.csv`.
2. All 504 SAT models are independently verified.
3. All 648 UNSAT outcomes are cross-checked against proven ground truth.
4. The dataset is balanced: exactly 144 runs per configuration and 24 runs per benchmark across 3 repetitions.
5. All telemetry fields are populated.
6. The data is ready to be loaded by the statistical analysis tools to evaluate hypotheses H1–H4 in Step 37.
