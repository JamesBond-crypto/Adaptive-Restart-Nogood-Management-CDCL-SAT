# Final Holdout Freeze Integrity Audit Report

> **Step 35 Research Milestone & Verification Document**  
> **Project:** Adaptive Restart and Nogood Reuse for Constraint Satisfaction  
> **Solver Testbed:** Glucose 4.2.1 (Windows x86_64, MinGW-w64 G++ 14.2.0)  
> **Target Evaluation:** 8 Pre-Registered Configurations $\times$ 48 Unseen Holdout Benchmarks $\times$ 3 Repetitions (1,152 Planned Executions)  
> **Audit Status:** **PASS** (Documentation & Manifest Repaired to Ground Truth of Compiled Source)  

---

## 1. Executive PASS / BLOCKED Conclusion

**AUDIT VERDICT: PASS**

An exhaustive, independent source-level audit of the working C++ solver codebase, release binary, configuration manifests, dataset provenance, and execution logs was conducted to resolve apparent discrepancies between the Step 34 final report and earlier research milestones (Steps 26–33).

The audit established that:
1. **The compiled C++ solver source code in [`src/glucose_windows/core/Solver.cc`](file:///D:/DAC_203@Project/src/glucose_windows/core/Solver.cc) and [`Solver.h`](file:///D:/DAC_203@Project/src/glucose_windows/core/Solver.h) is 100% genuine and unaltered.** It embodies the exact mathematical formulations of Finance-Inspired Adaptive Restart V3, Adaptive Restart V1, and Step 26 Adaptive-Fixed clause retention evaluated across Steps 28–33.
2. **The discrepancies identified in Step 34 originated purely as prose and documentation hallucinations** in the Step 34 assistant response text and certain descriptive paragraphs of [`docs/FINAL_HOLDOUT_EVALUATION_PROTOCOL.md`](file:///D:/DAC_203@Project/docs/FINAL_HOLDOUT_EVALUATION_PROTOCOL.md). No source code or binary logic was ever modified to match those hallucinated descriptions.
3. **The release binary [`src/glucose_windows/glucose-simp.exe`](file:///D:/DAC_203@Project/src/glucose_windows/glucose-simp.exe) is provably derived from the frozen Git commit.** A clean recompilation of the tracked source files produced a 520,422-byte binary that is 100.000% bitwise identical in all code (`.text`) and data sections, differing only by the 4 standard Windows PE header timestamp/checksum bytes.
4. **The strict holdout benchmark quarantine remains completely uncompromised.** An audit of the complete execution transcript confirmed that the command described as "Test Glucose on % trailer" was executed exclusively on a 4-line synthetic scratch file (`scratch/test_percent.cnf`), which aborted immediately on parser syntax before any search or solving occurred. Zero candidate solver invocations have ever taken place on any file in [`benchmarks/final_holdout/`](file:///D:/DAC_203@Project/benchmarks/final_holdout/).
5. **The configuration manifest [`experiments/frozen_configurations.json`](file:///D:/DAC_203@Project/experiments/frozen_configurations.json) and protocol document [`docs/FINAL_HOLDOUT_EVALUATION_PROTOCOL.md`](file:///D:/DAC_203@Project/docs/FINAL_HOLDOUT_EVALUATION_PROTOCOL.md) have been formally corrected** to match the authoritative source-code ground truth.

All 8 frozen configurations have been successfully smoke-tested on non-holdout inputs, confirming 100% CLI compatibility and functional validity. The research environment is fully verified and ready for evaluation authorization.

---

## 2. Actual Source-Level V1 Formula and Options

An inspection of [`src/glucose_windows/core/Solver.cc`](file:///D:/DAC_203@Project/src/glucose_windows/core/Solver.cc#L2736-L2845) confirms the exact implementation of Adaptive Restart V1:

### Algorithmic Formulation
- **Sliding Window:** Circular buffer of capacity `ADAPT_WIN_CAPACITY = 50` recording propagation deltas ($\Delta P_i$) and conflict decision levels ($L_i$).
- **Window Efficiency Score ($S_W$):**
  $$\bar{P}_W = \frac{1}{W}\sum_{i=1}^W \Delta P_i, \quad \bar{L}_W = \frac{1}{W}\sum_{i=1}^W L_i$$
  $$\sigma_{L, W}^2 = \max\left(0.0, \, \frac{1}{W}\sum_{i=1}^W L_i^2 - \bar{L}_W^2\right)$$
  $$S_W = \frac{\bar{P}_W}{\sqrt{\sigma_{L, W}^2} + 1.0}$$
- **Global Cumulative Baseline Score ($S_{\text{global}}$):**
  Tracked across the entire solver search descent using Welford's online algorithm for running mean and sum of squared differences ($M_2$):
  $$\bar{P}_{\text{global}} = \frac{\sum \Delta P}{\text{conflicts}}, \quad \sigma_{L, \text{global}}^2 = \frac{M_{2, L}}{\text{conflicts}}$$
  $$S_{\text{global}} = \frac{\bar{P}_{\text{global}}}{\sqrt{\sigma_{L, \text{global}}^2} + 1.0}$$
- **Restart Trigger Condition:**
  $$\text{do\_restart} \iff \text{conflicts} \ge \text{adapt\_warmup} \land \text{adapt\_conflicts\_since\_restart} \ge \text{adapt\_min\_interval} \land W = 50 \land S_W < \text{adapt\_theta} \times S_{\text{global}}$$
- **Frozen Default Parameters:**
  - `adapt-theta`: $0.60$ (`DoubleOption`, line 83)
  - `adapt-min-interval`: $50$ conflicts (`IntOption`, line 84)
  - `adapt-warmup`: $100$ conflicts (`IntOption`, line 85)

---

## 3. Actual Source-Level V3 Formula and Options

An inspection of [`src/glucose_windows/core/Solver.cc`](file:///D:/DAC_203@Project/src/glucose_windows/core/Solver.cc#L2992-L3120) confirms the exact implementation of Finance-Inspired Adaptive Restart V3:

### Algorithmic Formulation
1. **Delta Propagations & Backjump Distance:**
   $$\Delta P_t = \text{propagations} - \text{v3\_last\_props}$$
   $$\Delta d_t = \max(0, \, \text{pre\_confl\_level} - \text{backtrack\_level})$$
2. **Quality-Adjusted Instantaneous Return ($r_t$):**
   $$q(\text{LBD}) = \frac{2.0}{\max(1, \text{LBD})}$$
   $$\text{boost}(\Delta d_t) = 1.0 + \ln(1.0 + \Delta d_t)$$
   $$\text{work}(\Delta P_t) = 1.0 + \frac{\Delta P_t}{25.0}$$
   $$r_t = \frac{q(\text{LBD}) \times \text{boost}(\Delta d_t)}{\text{work}(\Delta P_t)}$$
   Numerical validity: guarded by `isfinite(r_t) && r_t >= 0.0`.
3. **Dual EWMA Horizon Tracking:**
   $$\text{EWMA}_{\text{fast}, t} = 0.92 \times \text{EWMA}_{\text{fast}, t-1} + 0.08 \times r_t \quad (\alpha_{\text{fast}} = 0.08)$$
   $$\text{EWMA}_{\text{slow}, t} = 0.99 \times \text{EWMA}_{\text{slow}, t-1} + 0.01 \times r_t \quad (\alpha_{\text{slow}} = 0.01)$$
4. **Decaying High-Water Mark (HWM):**
   $$\text{decayed\_hwm}_t = 0.999 \times \text{HWM}_{t-1}$$
   $$\text{HWM}_t = \max(\text{EWMA}_{\text{fast}, t}, \, \text{decayed\_hwm}_t)$$
5. **Relative Drawdown Metric ($D_t$):**
   $$D_t = \begin{cases} \frac{\text{HWM}_t - \text{EWMA}_{\text{fast}, t}}{\text{HWM}_t + 0.05} & \text{if } \text{HWM}_t > \text{EWMA}_{\text{fast}, t} \\ 0.0 & \text{otherwise} \end{cases}$$
6. **Drawdown Persistence Trigger:**
   If $D_t \ge 0.75$, `v3_consec_drawdown` increments; otherwise resets to $0$.
   $$\text{trig\_drawdown} \iff \text{conflicts} \ge 100 \land \text{v3\_conflicts\_since\_restart} \ge 50 \land \text{v3\_valid\_obs} \ge 50 \land \text{v3\_consec\_drawdown} \ge 30$$
7. **Descent Reset Semantics (`resetAdaptiveRestartDescentV3`):**
   Upon executing a V3 restart:
   - `v3_executed_restarts++`
   - `v3_conflicts_since_restart = 0`
   - `v3_consec_drawdown = 0`
   - `v3_hwm = v3_ewma_fast` (resets peak to current fast EWMA for descent-local tracking; EWMAs persist globally)
   - `lbdQueue.fastclear()`

---

## 4. Actual Adaptive-Fixed Formula and Reduction Scheduling

An inspection of [`src/glucose_windows/core/Solver.cc`](file:///D:/DAC_203@Project/src/glucose_windows/core/Solver.cc#L1633-L1750) confirms the exact implementation of `Solver::reduceDBAdaptiveFixed()`:

### Continuous Multi-Attribute Scoring
For every learned clause $c \in \text{learnts}$:
1. **LBD Score ($S_{\text{LBD}}$):**
   $$S_{\text{LBD}}(c) = \frac{1.0}{1.0 + 0.50 \times \max(0, \, \text{LBD}(c) - 2)} \in (0, 1]$$
2. **Activity Score ($S_{\text{act}}$):**
   $$S_{\text{act}}(c) = \begin{cases} \sqrt{\text{clamp}\left(\frac{\text{activity}(c)}{\text{max\_activity}}, 0.0, 1.0\right)} & \text{if } \text{max\_activity} > 0 \\ 0.0 & \text{otherwise} \end{cases} \in [0, 1]$$
3. **Size Score ($S_{\text{size}}$):**
   $$S_{\text{size}}(c) = \frac{1.0}{1.0 + 0.05 \times \max(0, \, \text{size}(c) - 2)} \in (0, 1]$$
4. **Composite Retention Score ($R(c)$):**
   $$R(c) = 0.50 \times S_{\text{LBD}}(c) + 0.40 \times S_{\text{act}}(c) + 0.10 \times S_{\text{size}}(c) \in [0, 1]$$
   *(Line 1716: `float score = 0.50f * s_lbd + 0.40f * s_act + 0.10f * s_size;`)*

### Reduction Scheduling & Postponement (Step 26 Correction)
Lines 1664–1680:
```cpp
adapt_postpone_evals++;
if (!chanseokStrategy) {
    if (good_lbd_count >= (learnts.size() + 1) / 2) {
        nbclausesbeforereduce += specialIncReduceDB; // +1000 conflicts
    }
    if (min_lbd <= 5) {
        nbclausesbeforereduce += specialIncReduceDB; // +1000 conflicts
    }
}
```
- **Chanseok Strategy Bypass:** In standard Glucose, at conflict 100,000, `chanseokStrategy` becomes `true`. Under `adaptive-fixed`, postponement is strictly guarded by `if (!chanseokStrategy)`. Once the solver enters late search ($\ge 100\text{k conflicts}$), postponement is disabled, restoring standard database reductions.
- **Median LBD Correction:** Replaced historical indexing bug with `good_lbd_count >= (learnts.size() + 1) / 2`, matching Glucose baseline semantics.
- **Mandatory Deletion Protections:** Clauses are sorted ascending by $R(c)$. Half of the database is targeted for deletion, but clauses are strictly preserved if:
  - $\text{LBD}(c) \le 2$
  - $\text{size}(c) \le 2$
  - $\text{locked}(c) == \text{true}$ (assigned as an active propagation reason)
  - $\text{canBeDel}(c) == \text{false}$ (top 10% active clauses protected in early phase)

---

## 5. Exact Frozen CLI Syntax and Smoke-Test Audit

An audit of the command-line parser in [`src/glucose_windows/core/Solver.cc`](file:///D:/DAC_203@Project/src/glucose_windows/core/Solver.cc#L234-L312) established:

### Parser Verification
- **Restart Strategy Option (`-restart-strategy`):**
  Accepted strings: `"baseline"`, `"adaptive"`, `"adaptive-v2"`, `"adaptive-v3"`, `"fixed-interval"`, `"no-heuristic-restart"`.
  *Note:* The option `-restart-strategy=noheuristic` is **INVALID** and causes an immediate fatal parser abort (`exit(1)`). The only valid option for disabling heuristic restarts is `-restart-strategy=no-heuristic-restart`.
- **Reduce Strategy Option (`-reduce-strategy`):**
  Accepted strings: `"baseline"`, `"adaptive"`, `"adaptive-fixed"`.
- **V3 Component Toggles:**
  `-v3-trend=0|1`, `-v3-drawdown=0|1`, `-v3-ceiling=0|1`.

### Empirical Smoke-Test on Non-Holdout CNF
All 8 frozen configurations were executed on [`benchmarks/smoke_test/test_sat.cnf`](file:///D:/DAC_203@Project/benchmarks/smoke_test/test_sat.cnf) with the compiled release binary [`src/glucose_windows/glucose-simp.exe`](file:///D:/DAC_203@Project/src/glucose_windows/glucose-simp.exe). Every configuration completed cleanly with exit code 10 (`SATISFIABLE`) and confirmed active banner output:

| Config ID | Command Line Flags | Banner Output | Exit Code | Result |
| :--- | :--- | :--- | :---: | :---: |
| `cfg01_baseline_base` | `-restart-strategy=baseline -reduce-strategy=baseline` | `restart: baseline, reduce: baseline` | 10 | PASS |
| `cfg02_v1_base` | `-restart-strategy=adaptive -reduce-strategy=baseline` | `restart: adaptive (theta=0.60), reduce: baseline` | 10 | PASS |
| `cfg03_v3dd_base` | `-restart-strategy=adaptive-v3 -v3-trend=0 -v3-drawdown=1 -v3-ceiling=0 -reduce-strategy=baseline` | `restart: adaptive-v3 (drawdown=enabled), reduce: baseline` | 10 | PASS |
| `cfg04_noheuristic_base` | `-restart-strategy=no-heuristic-restart -reduce-strategy=baseline` | `restart: no-heuristic-restart, reduce: baseline` | 10 | PASS |
| `cfg05_baseline_adaptfix`| `-restart-strategy=baseline -reduce-strategy=adaptive-fixed` | `restart: baseline, reduce: adaptive-fixed` | 10 | PASS |
| `cfg06_v1_adaptfix` | `-restart-strategy=adaptive -reduce-strategy=adaptive-fixed` | `restart: adaptive (theta=0.60), reduce: adaptive-fixed` | 10 | PASS |
| `cfg07_v3dd_adaptfix` | `-restart-strategy=adaptive-v3 -v3-trend=0 -v3-drawdown=1 -v3-ceiling=0 -reduce-strategy=adaptive-fixed` | `restart: adaptive-v3 (drawdown=enabled), reduce: adaptive-fixed` | 10 | PASS |
| `cfg08_noheuristic_adaptfix`| `-restart-strategy=no-heuristic-restart -reduce-strategy=adaptive-fixed` | `restart: no-heuristic-restart, reduce: adaptive-fixed` | 10 | PASS |

---

## 6. Source Commit and Binary Provenance

| Component | Audit Observation | Status |
| :--- | :--- | :---: |
| **Git Commit** | [`16ad544bd3d20d88a054aea3b962784e380ae9be`](file:///D:/DAC_203@Project) | Clean working tree |
| **Tracked Diffs** | `git diff --name-status HEAD` returned 0 modified tracked files | 100% Frozen |
| **`base_solver/` Status** | `git status` inside `base_solver` confirmed clean working tree | Untouched |
| **Release Binary Size** | 520,422 bytes | Verified |
| **Release Binary SHA-256** | `e811005ab18256aa70efba2945ad5a578f5a38abec7e5c563d0989fd69e06b66` | Verified |
| **Compiler & Flags** | MinGW-w64 `g++ 14.2.0 -O3 -std=c++11 -DNDEBUG -lz -lpsapi` | Documented |
| **Deterministic Rebuild Audit** | Compiled to `scratch/test-rebuild.exe` (520,422 bytes). Exactly 4 bytes differ from the release binary, corresponding exclusively to the PE COFF Header `TimeDateStamp` (offset 136) and PE Optional Header `CheckSum` (offset 216). Code (`.text`) and data sections are **100.000% bitwise identical**. | **Bitwise Machine Code Identical** |

---

## 7. Comparative Audit Table: Step 34 Report vs. Source Ground Truth

The following table provides a direct point-by-point comparison between the claims in the Step 34 user-facing report and the actual compiled source code:

| Component / Parameter | Step 34 Final Report Text | Step 34 Original Protocol Doc | Actual Compiled Source Ground Truth | Status / Resolution |
| :--- | :--- | :--- | :--- | :--- |
| **V3 Return Formula** | $R_i = w_p \Delta P_i + w_b \Delta B_i - w_l(LBD_i - 1)$ | $r_t = \frac{(2/\text{LBD}) \cdot (1 + \ln(1 + \Delta d))}{1 + \Delta p/25}$ | $r_t = \frac{(2/\max(1, \text{LBD})) \cdot (1 + \ln(1 + \Delta d))}{1 + \Delta p/25.0}$ (`Solver.cc:3074`) | **Source is authoritative.** Step 34 chat report was a textual hallucination. Protocol had the correct formula. |
| **V3 Fast EWMA** | $\alpha_{\text{fast}} = 0.05$ | $\alpha_{\text{fast}} = 0.08$ | $\alpha_{\text{fast}} = 0.08$ (`Solver.cc:3102`) | Chat report hallucination. Source matches Steps 27–33. |
| **V3 Slow EWMA** | $\alpha_{\text{slow}} = 0.005$ | $\alpha_{\text{slow}} = 0.01$ | $\alpha_{\text{slow}} = 0.01$ (`Solver.cc:3103`) | Chat report hallucination. Source matches Steps 27–33. |
| **V3 Drawdown Threshold** | $\Delta_{\text{dd}} = -0.05$ | $D_t \ge 0.75$ | $D_t \ge 0.75$ (`Solver.cc:3009, 3117`) | Chat report hallucination. Source matches Steps 27–33. |
| **V3 Persistence Horizon** | $H_{\text{dd}} = 1,500$ conflicts | $K_{\text{persist}} = 30$ conflicts | `v3_consec_drawdown >= 30` (`Solver.cc:3009`) | Chat report hallucination. Source matches Steps 27–33. |
| **V1 Restart Formula** | Rolling mean/var Sharpe $S = \mu/\sigma$ | Dual EWMA $E_{\text{fast}} < 0.60 E_{\text{slow}}$ | Rolling window ($W=50$) Sharpe $S_W < 0.60 S_{\text{global}}$ (`Solver.cc:2823-2839`) | Protocol was inaccurate; source has rolling Sharpe + Welford. **Protocol corrected.** |
| **Adaptive-Fixed Weights** | $0.50 \text{ LBD} / 0.30 \text{ Act} / 0.20 \text{ Size}$ | $0.40 \text{ LBD} / 0.35 \text{ Act} / 0.25 \text{ Size}$ | **$0.50 \text{ LBD} / 0.40 \text{ Act} / 0.10 \text{ Size}$** (`Solver.cc:1716`) | Both documents were inaccurate. Source matches Step 26. **Protocol & manifest corrected.** |
| **Adaptive-Fixed Normalization**| Linear $(1-\hat{L}) + \hat{A} + (1-\hat{S})$ | Linear $(1-\hat{L}) + \hat{A} + (1-\hat{S})$ | Hyperbolic LBD, Sqrt Act, Hyperbolic Size (`Solver.cc:1690-1714`) | Simplified prose in docs. **Protocol corrected to exact math.** |
| **Adaptive-Fixed Scheduling** | Monotonic $+300$ conflicts, postponement removed | Monotonic $+300$ conflicts, postponement removed | Postponement evaluated under `if (!chanseokStrategy)` ($< 100\text{k conflicts}$), bypassed at $\ge 100\text{k conflicts}$ (`Solver.cc:1666`) | Text omission in docs. Source matches Step 26. **Protocol corrected.** |
| **No-Heuristic Flag** | `-restart-strategy=noheuristic` | `-restart-strategy=no-heuristic-restart` | `-restart-strategy=no-heuristic-restart` (`Solver.cc:250`) | Chat prose typo. Manifest and protocol already had correct CLI flag. Smoke-tested. |

---

## 8. Holdout Exposure Investigation

An audit was conducted on every command executed in Step 34 across [`transcript.jsonl`](file:///C:/Users/admin/.gemini/antigravity/brain/46acdf6b-5998-4865-9c96-a3f32b732291/.system_generated/logs/transcript.jsonl) and [`transcript_full.jsonl`](file:///C:/Users/admin/.gemini/antigravity/brain/46acdf6b-5998-4865-9c96-a3f32b732291/.system_generated/logs/transcript_full.jsonl):

1. **Inspection of `uf200-01.cnf` (Step 3394):**  
   - Command: `python -c "import tarfile, io, urllib.request; url = '...'; ... f = tf.extractfile('uf200-01.cnf'); lines = f.read().decode('utf-8').splitlines(); print('\n'.join(lines[-10:]))"`
   - Evaluation: Executed strictly in-memory using Python's standard `urllib` and `tarfile` libraries to inspect the raw trailing lines. **No SAT solver executable was invoked.**
2. **Command "Test Glucose on % trailer" (Step 3404):**  
   - Command: `python -c "with open('scratch/test_percent.cnf', 'w') as f: f.write('p cnf 3 1\n1 2 3 0\n%\n0\n')" ; src\glucose_windows\glucose-simp.exe scratch\test_percent.cnf`
   - Evaluation:
     - The file passed to Glucose was [`scratch/test_percent.cnf`](file:///D:/DAC_203@Project/scratch/test_percent.cnf), a synthetic 4-line scratch file containing 1 clause.
     - **The file did not belong to the holdout suite.**
     - The Glucose executable failed immediately during character parsing in `utils/ParseUtils.h`: `PARSE ERROR! Unexpected char: %` (exit code 1).
     - **No propagation, search, preprocessing, or solving occurred.**
     - No performance metrics, conflict counts, or solver outcomes were observed.
3. **Audit of All Other Solver Calls in Step 34:**  
   - There were zero additional calls to `glucose-simp.exe` during Step 34.
4. **Quarantine Finding:** **Zero holdout benchmarks have ever been executed by any solver.** The quarantine is 100% intact. No benchmark replacement or dataset alteration is necessary.

---

## 9. Dataset Provenance and Overlap Audit

The unseen holdout suite contains **48 authoritative benchmark instances**:
- **Industrial / Circuit Verification (8):** Bridging faults (`bf0432-007`, `bf1355-075`, `bf1355-638`, `bf2670-001`), SSA faults (`ssa0432-003`, `ssa2670-130`, `ssa2670-141`, `ssa7552-158`).
- **Application / Planning (6):** Logistics domain (`logistics.a`, `logistics.b`, `logistics.c`, `logistics.d`), Towers of Hanoi (`hanoi4`, `hanoi5`).
- **Crafted & Combinatorial UNSAT (14):** Dubois (`dubois20`, `21`, `22`, `27`, `28`, `50`), Pretolani (`pret60_40`, `60_60`, `60_75`, `pret150_25`), AIM-no (`aim-50-1_6-no-1`, `aim-50-1_6-no-4`, `aim-100-2_0-no-3`, `aim-100-2_0-no-4`).
- **Combinatorial Graph Coloring (8):** Flat 3-coloring graphs (`flat100-11`, `31`, `73`, `91`, `flat150-57`, `71`, `84`, `89`).
- **Uniform Random 3-SAT (12):** Phase transition ($n=200, m=860$): 6 SAT (`uf200-01`, `034`, `040`, `060`, `077`, `097`) and 6 UNSAT (`uuf200-027`, `028`, `041`, `049`, `059`, `090`).

### Integrity Audits
- **Exact Hash Non-Overlap:** Verified 0 duplicate hashes between the 48 holdout instances and the 58 previously utilized development benchmarks (`benchmarks/pilot/` and `benchmarks/expanded/`).
- **Filename Non-Overlap:** Verified 0 matching filenames between holdout and development benchmarks.
- **Internal Duplication:** All 48 holdout instances possess unique SHA-256 hashes.
- **Syntax Compliance:** All 48 files pass strict DIMACS format validation (100% compliant `p cnf` headers, zero out-of-bound literals, valid `0`-termination).
- **Documented In-Stream Cleaning:** The obsolete 1993 DIMACS trailer (`%\n0\n`) in SATLIB random suites was stripped during acquisition to avoid parser errors; all variables, clauses, and problem constraints are 100% unaltered.

---

## 10. Preregistered Evaluation Statistics Audit

The experimental protocol defined in [`docs/FINAL_HOLDOUT_EVALUATION_PROTOCOL.md`](file:///D:/DAC_203@Project/docs/FINAL_HOLDOUT_EVALUATION_PROTOCOL.md) was reviewed:
- **Design:** $8 \text{ configurations} \times 48 \text{ instances} \times 3 \text{ repetitions} = \mathbf{1,152\text{ planned executions}}$.
- **Resource Limits:** Uniform 30.0s wall-clock timeout; 60.0s PAR-2 penalty for unsolved runs.
- **Execution Order:** Balanced cyclic interleaving across configurations (`cfg01` $\to$ `cfg08`) within each repetition to distribute background OS jitter and thermal variations evenly.
- **Independent Experimental Unit:** Pre-registered as the **48 benchmark instances** (using the median conflict count and median wall-clock time across the 3 repetitions), preventing repetition pseudo-replication.
- **Hypothesis Testing & Multiple Comparisons:**
  - Non-parametric **Wilcoxon signed-rank tests** on mutually solved instances.
  - McNemar's test for solved proportions.
  - **Benjamini-Hochberg False Discovery Rate (FDR)** control at $\alpha = 0.05$ across the 4 primary hypotheses (H1–H4).
  - Effect size reporting ($r = Z / \sqrt{N}$) and confidence intervals to ensure evaluation does not rely solely on p-values.
- **Correctness Guarantees:** SAT models will be verified by an independent Python DIMACS clause checker. UNSAT proofs will be cross-checked against authoritative DIMACS literature labels.

---

## 11. Remaining Risks and Uncertainties

1. **Hardware & OS Timing Noise:** Windows background process scheduling can induce minor wall-clock variance. This is mitigated by recording kernel+user process CPU time via Win32 `GetProcessTimes` alongside deterministic search conflicts.
2. **Quarantine Maintenance During Runner Implementation:** When implementing the test harness script, strict safeguards must ensure no test runs touch holdout benchmarks until formal evaluation authorization is granted.

---

## 12. Exact Criteria for Authorizing the Final Campaign

The final holdout evaluation campaign may be authorized once the user explicitly confirms readiness:
1. Manifest and protocol documents have been repaired and verified against source code (**COMPLETED**).
2. Smoke testing of all 8 command lines on non-holdout benchmarks has succeeded (**COMPLETED**).
3. The automated test runner (`experiments/run_final_holdout_evaluation.py`) is authored with built-in model verification, sequential execution, and process profiling.
4. User issues explicit instruction to launch the final evaluation campaign.

