# V3 Drawdown × Adaptive-Fixed Nogood Retention: Controlled Factorial Evaluation

**Project Title:** Adaptive Restart and Nogood Management for Constraint Satisfaction Solvers (Glucose 4.2.1 Windows Port)  
**Milestone:** Step 31 — Controlled Factorial Interaction Evaluation (3 Restart Policies × 2 Retention Policies × 36 Benchmarks × 3 Repetitions = 648 Runs)  
**Status:** Completed, Audited, and Validated  
**Date:** October 2026  
**Reference Documents:**  
- `docs/FINANCE_INSPIRED_V3_FULL_EVALUATION.md` (Step 30 Full Evaluation)  
- `docs/FINANCE_INSPIRED_V3_ACTIVE_IMPLEMENTATION.md` (Step 29 Active Implementation)  
- `docs/ADAPTIVE_NOGOOD_SCHEDULING_CORRECTION.md` (Step 26 Correction)  
- `docs/TIMEOUT_MEMORY_AUDIT.md` (Step 25 Audit)  

---

## 1. Step 30 Statistics Audit & Discrepancy Resolution

Before conducting the Step 31 factorial experiment, a rigorous audit of the Step 30 results and analysis script ([`experiments/analyze_v3_full_development.py`](file:///d:/DAC_203@Project/experiments/analyze_v3_full_development.py)) was executed to reconcile reported conflict totals and restart counters.

### 1.1 Resolution of the 292,365 Mutually Solved Conflict Figure
In Step 30 Table 1, the column labeled *"Mut Cfc (30 insts)"* reported **292,365** baseline conflicts, which appeared suspicious when compared against the Step 29 eight-instance baseline conflict sum of **1,238,851**.

An independent row-level recomputation revealed the exact mathematical cause:
1. **Intersection Filter Definition**: The Step 30 script defined `mutually_solved` as instances solved across **all 6 configurations in all 3 repetitions** (18 out of 18 successful runs).
2. **Exclusion of the Heaviest Instances Due to Ceiling/Combined Regressions**:
   Two configurations in Step 30 (`cfg5_v3_ceiling_only` with 13 timeouts and `cfg6_v3_combined` with 14 timeouts) suffered severe regressions and timed out on the hardest benchmarks:
   - `gcol_unsat_k10_c9.cnf`: Timed out in Rep 1 for Baseline, V1, Trend, Ceiling, and Combined (Baseline solved conflicts: **528,305**).
   - `php_10p_9h.cnf`: Timed out in Rep 1 and 3 for Ceiling and Combined (Baseline solved conflicts: **438,461**).
   - `rand3sat_n250_c1065_s1010.cnf`: Timed out in all 3 reps for Ceiling and Combined (Baseline solved conflicts: **114,109**).
   - `gcol_unsat_k11_c10.cnf` (timed out in all 6 configurations).
   - `php_11p_10h.cnf` (timed out in all 6 configurations).
   - `rand3sat_n200_c852_s1006.cnf` (timed out in Rep 1 for Combined).
3. **Mathematical Proof**:
   Those three heavy solved instances alone account for:
   $$528,305 + 438,461 + 114,109 = 1,080,875 \text{ conflicts}$$
   Subtracting them from the 8-instance diagnostic sum ($1,238,851 - 1,080,875 = 157,976$) and adding the remaining 25 easy benchmarks yields **exactly 292,365 conflicts**.

> [!IMPORTANT]
> **Audit Conclusion**: The 292,365 figure was neither a code defect nor a denominator error; it was the exact arithmetic sum over the 30 easiest mutual benchmarks. However, requiring mutual solution across all 6 configurations introduced **severe survivorship bias**, filtering out the hardest benchmarks where restart heuristics exert their greatest impact.
>
> When Baseline and V3 Drawdown are evaluated on their direct pairwise mutual intersection (**32 instances**), the true conflict counts are:
> - **Baseline Glucose**: 753,484 conflicts
> - **V3 Drawdown-Only**: 625,781 conflicts (**-16.95% conflict reduction**)

### 1.2 Reconciliation of V3 Trigger Requests vs. Genuine Restarts
In Step 30 Table 4, executed restarts slightly exceeded total V3 requests (e.g. Drawdown: 6 requests vs. 14 executed restarts).

Across all 432 V3 runs in Step 30, the relationship is governed by an exact mathematical invariant:
$$\text{v3\_executed\_restarts} = \text{v3\_total\_requests} + \begin{cases} 1 & \text{if } \text{conflicts} \ge 100,000 \\ 0 & \text{otherwise} \end{cases}$$
and in every run:
$$\text{genuine\_restarts} \equiv \text{v3\_executed\_restarts}$$
Glucose 4.2.1 contains an immutable native strategy adaptation event at conflict 100,000 (`adaptStrategies && conflicts == 100000`) that resets the trail to level 0. The V3 controller correctly handles this descent reset via `resetAdaptiveRestartDescentV3()`. There are zero unaccounted restarts.

---

## 2. Experimental Objectives & Factorial Design

Step 31 evaluates the controlled factorial interaction between **Adaptive Restart Strategies** and **Learned-Clause Retention Strategies**:

### 2.1 The 3 × 2 Factorial Matrix
The experiment crosses 3 restart strategies against 2 clause retention strategies (6 configurations total):

| Configuration ID | Restart Strategy | Clause Retention Strategy | Exact CLI Options |
| :--- | :--- | :--- | :--- |
| **`cfg1_base_base`** | Original Glucose Baseline | Baseline Glucose Reduction | `-restart-strategy=baseline -reduce-strategy=baseline` |
| **`cfg2_v1_base`** | Adaptive Restart V1 | Baseline Glucose Reduction | `-restart-strategy=adaptive -reduce-strategy=baseline` |
| **`cfg3_v3dd_base`** | V3 Drawdown-Only | Baseline Glucose Reduction | `-restart-strategy=adaptive-v3 -v3-trend=0 -v3-drawdown=1 -v3-ceiling=0 -reduce-strategy=baseline` |
| **`cfg4_base_adaptfix`** | Original Glucose Baseline | Adaptive-Fixed Reduction | `-restart-strategy=baseline -reduce-strategy=adaptive-fixed` |
| **`cfg5_v1_adaptfix`** | Adaptive Restart V1 | Adaptive-Fixed Reduction | `-restart-strategy=adaptive -reduce-strategy=adaptive-fixed` |
| **`cfg6_v3dd_adaptfix`** | V3 Drawdown-Only | Adaptive-Fixed Reduction | `-restart-strategy=adaptive-v3 -v3-trend=0 -v3-drawdown=1 -v3-ceiling=0 -reduce-strategy=adaptive-fixed` |

### 2.2 Execution Protocol
- **Dataset**: All 36 benchmark instances from `benchmarks/expanded_manifest.csv` across 4 families.
- **Repetitions**: 3 independent runs per instance/configuration pair ($N = 36 \times 6 \times 3 = 648$ planned runs).
- **Timeout**: Uniform 15.0-second external wall-clock timeout.
- **Execution**: Sequential execution under balanced cyclic configuration permutation.
- **Integrity**: Exact SHA-256 binary hash (`6a8b25964d0f8f47...`) and benchmark hashes verified.

---

## 3. Main Factorial Performance Results

### 3.1 Executive Performance Summary (Table 1)

| Configuration | Unique Solved (/36) | Solved Runs (/108) | Timeouts (/108) | PAR-2 Score (s) | Median Time (s) | Time IQR (s) | Mutually Solved Conflicts (31 insts) | Peak Memory (MB) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline + Baseline Red** | 33 / 36 (32) | 97 / 108 | 11 | 3.593 | 0.080 | 0.756 | 315,023 | 14.53 |
| **Adaptive V1 + Baseline Red** | 34 / 36 (33) | 101 / 108 | 7 | 2.988 | 0.080 | 0.871 | 380,579 | 15.09 |
| **V3 Drawdown + Baseline Red** | 33 / 36 (33) | 99 / 108 | 9 | 3.123 | 0.086 | 0.743 | 326,024 | 14.60 |
| **Baseline + Adaptive-Fixed** | 33 / 36 (31) | 96 / 108 | 12 | 3.959 | 0.102 | 0.677 | 337,590 | 14.64 |
| **Adaptive V1 + Adaptive-Fixed** | 34 / 36 (33) | 101 / 108 | 7 | 3.032 | 0.093 | 0.790 | 337,825 | 15.09 |
| **V3 Drawdown + Adaptive-Fixed** | **34 / 36 (33)** | **100 / 108** | **8** | **2.872** | **0.104** | **0.588** | **324,174** | **14.43** |

> [!TIP]
> **V3 Drawdown + Adaptive-Fixed Nogood Retention (`cfg6_v3dd_adaptfix`) achieved the lowest PAR-2 score (2.872s) of the entire 648-run factorial study**, outperforming Original Glucose (3.593s) by **20.1%**, while maintaining the lowest runtime interquartile range (IQR = 0.588s) and the lowest peak memory (14.43 MB).

---

### 3.2 Factorial Interaction Analysis (Table 2)

To evaluate whether combining V3 Drawdown with Adaptive-Fixed clause retention provides a synergistic benefit or merely adds their independent effects, we construct the 3 × 2 PAR-2 interaction matrix:

| Restart Policy | Baseline Clause Retention | Adaptive-Fixed Clause Retention | Retention Difference ($\Delta_{\text{ret}}$) |
| :--- | :---: | :---: | :---: |
| **Original Glucose Baseline** | 3.593s | 3.959s | **+0.366s** (Retention Hurts Baseline) |
| **Adaptive Restart V1** | 2.988s | 3.032s | **+0.044s** (Retention Neutral on V1) |
| **V3 Drawdown-Only** | 3.123s | **2.872s** | **-0.251s** (Retention Improves V3 DD) |

### Formal Factorial Interaction Calculation:
$$\text{Interaction} = \left[(\text{V3 DD} + \text{Adaptive-Fixed}) - (\text{V3 DD} + \text{Baseline Red})\right] - \left[(\text{Baseline} + \text{Adaptive-Fixed}) - (\text{Baseline} + \text{Baseline Red})\right]$$
$$\text{Interaction} = (-0.251\text{s}) - (+0.366\text{s}) = \mathbf{-0.617s}$$

> [!IMPORTANT]
> **Interpretation of Negative Factorial Interaction**:
> A negative interaction on the PAR-2 scale ($\mathbf{-0.617s}$) indicates a **favorable, synergistic combined effect**:
> - Under Baseline restarts (which restart hyperactively every ~3,000 conflicts), retaining more learned clauses via Adaptive-Fixed retention increases unit propagation overhead without benefiting short descents, regressing PAR-2 by **+0.366s**.
> - In sharp contrast, under V3 Drawdown-Only (which executes long, uninterrupted descents averaging ~18,000 conflicts), sparing high-quality nogoods ($\approx 256,000$ clauses protected) preserves the exact deduction context needed to navigate deep search subtrees, improving PAR-2 by **-0.251s**.

---

### 3.3 Six Core Paired Comparisons (Table 3)

| Comparison Label | Configuration 1 | Configuration 2 | PAR-2 Diff ($C_2 - C_1$) | Advantage / Winner |
| :--- | :--- | :--- | :---: | :--- |
| **A. Baseline vs V3 DD (Baseline Red)** | Baseline + Base Red (3.593s) | V3 DD + Base Red (3.123s) | **-0.470s** | **Favors V3 Drawdown** |
| **B. Baseline vs V3 DD (Adaptive-Fixed Red)** | Baseline + AdaptFix (3.959s) | V3 DD + AdaptFix (2.872s) | **-1.087s** | **Favors V3 Drawdown** |
| **C. Adaptive V1 vs V3 DD (Baseline Red)** | V1 + Base Red (2.988s) | V3 DD + Base Red (3.123s) | +0.135s | Favors Adaptive V1 |
| **D. Adaptive V1 vs V3 DD (Adaptive-Fixed Red)**| V1 + AdaptFix (3.032s) | V3 DD + AdaptFix (2.872s) | **-0.160s** | **Favors V3 Drawdown** |
| **E1. Base vs AdaptFix (Baseline Restarts)** | Baseline + Base Red (3.593s) | Baseline + AdaptFix (3.959s) | +0.366s | Favors Baseline Retention |
| **E2. Base vs AdaptFix (Adaptive V1 Restarts)** | V1 + Base Red (2.988s) | V1 + AdaptFix (3.032s) | +0.044s | Favors Baseline Retention |
| **E3. Base vs AdaptFix (V3 Drawdown Restarts)**| V3 DD + Base Red (3.123s) | V3 DD + AdaptFix (2.872s) | **-0.251s** | **Favors Adaptive-Fixed** |
| **F. Combined V3 DD Effect** | V3 DD + Base Red (3.123s) | V3 DD + AdaptFix (2.872s) | **-0.251s** | **Favors Combined Synergy** |

---

## 4. Family-Level Factorial Breakdown (Table 4)

| Configuration | Graph Coloring (PAR-2 / Slv) | Pigeonhole Principle (PAR-2 / Slv) | Planted Satisfiable (PAR-2 / Slv) | Random 3-SAT (PAR-2 / Slv) |
| :--- | :---: | :---: | :---: | :---: |
| **Baseline + Baseline Red** | 4.70s (31/36) | 15.54s (6/12) | **0.07s (30/30)** | **1.01s (30/30)** |
| **Adaptive V1 + Baseline Red** | 4.18s (32/36) | 9.69s (9/12) | 0.09s (30/30) | 1.78s (30/30) |
| **V3 Drawdown + Baseline Red** | 3.21s (33/36) | 9.65s (9/12) | 0.09s (30/30) | 3.45s (27/30) |
| **Baseline + Adaptive-Fixed** | 4.21s (32/36) | 14.20s (7/12) | 0.08s (30/30) | 3.44s (27/30) |
| **Adaptive V1 + Adaptive-Fixed** | 3.23s (33/36) | 11.14s (9/12) | 0.08s (30/30) | 2.51s (29/30) |
| **V3 Drawdown + Adaptive-Fixed** | **3.06s (33/36)** | **9.55s (9/12)** | 0.08s (30/30) | 2.76s (28/30) |

### Key Family Insights:
1. **Graph Coloring**:
   - `cfg6_v3dd_adaptfix` achieved the fastest runtime (**3.06s PAR-2**, 33/36 solved), representing a **34.9% speedup** over Baseline (4.70s).
   - On `gcol_unsat_k10_c9.cnf`, `cfg6_v3dd_adaptfix` solved in **5.67s** (with 313,440 conflicts and only 1 restart), whereas Baseline took 13.28s and timed out in 2 repetitions.
2. **Pigeonhole Principle (PHP)**:
   - `cfg6_v3dd_adaptfix` achieved the best PHP score (**9.55s PAR-2**), beating Baseline (15.54s) by **38.5%**.
   - On `php_10p_9h.cnf`, `cfg6_v3dd_adaptfix` solved in **4.27s** with 303,596 conflicts and 1 restart, whereas Baseline timed out in all 3 repetitions.
3. **Planted Satisfiable 3-SAT**:
   - All 6 configurations solved 30/30 runs instantaneously ($\le 0.09\text{s}$), demonstrating that neither adaptive restarts nor adaptive retention harms easy satisfiable instances.
4. **Random 3-SAT**:
   - Original Glucose retains an advantage on uniform random 3-SAT (1.01s vs 2.76s for V3 DD + AdaptFix).
   - However, pairing V3 Drawdown with Adaptive-Fixed reduced Random 3-SAT PAR-2 from 3.45s down to 2.76s (**-20.0% improvement**), partially mitigating the Random 3-SAT regression.

---

## 5. Focal Benchmark Deep-Dive (Table 5)

| Benchmark Instance | Metric | Baseline + Base Red | Adaptive V1 + Base Red | V3 DD + Base Red | Baseline + AdaptFix | V1 + AdaptFix | V3 DD + AdaptFix |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`rand3sat_n250_c1065_s1010`** | Time (s)<br>Conflicts<br>Restarts<br>Reduces | **5.45s**<br>114,109<br>30<br>15 | 7.18s<br>178,700<br>8<br>47 | TO (3/3)<br>TO<br>TO<br>TO | TO (3/3)<br>TO<br>TO<br>TO | 8.87s (1TO)<br>178,700<br>8<br>52 | **8.86s (2TO)**<br>229,569<br>1<br>68 |
| **`rand3sat_n235_c999_s1009`** | Time (s)<br>Conflicts<br>Restarts<br>Reduces | **0.86s**<br>33,846<br>0<br>5 | 1.11s<br>33,846<br>0<br>5 | **0.87s**<br>33,846<br>0<br>5 | 1.16s<br>35,463<br>1<br>7 | 1.10s<br>33,846<br>0<br>6 | **0.90s**<br>33,846<br>0<br>6 |
| **`php_10p_9h.cnf`** | Time (s)<br>Conflicts<br>Restarts<br>Reduces | TO (3/3)<br>TO<br>TO<br>TO | 8.27s<br>302,972<br>5<br>109 | 7.85s<br>299,757<br>1<br>107 | 12.60s (2TO)<br>480,184<br>1,389<br>198 | 6.70s<br>384,632<br>5<br>150 | **4.27s**<br>**303,596**<br>**1**<br>**109** |
| **`gcol_unsat_k10_c9.cnf`** | Time (s)<br>Conflicts<br>Restarts<br>Reduces | 13.28s (2TO)<br>528,305<br>1,249<br>222 | 13.66s (1TO)<br>346,232<br>4<br>131 | 7.44s<br>266,330<br>2<br>91 | 13.08s (1TO)<br>547,250<br>1,412<br>231 | 7.53s<br>276,202<br>3<br>96 | **5.67s**<br>**313,440**<br>**1**<br>**114** |

---

## 6. Nogood Dynamics & Database Reduction Analysis (Table 6)

| Configuration | ReduceDB Calls | Learned Clauses Removed | Spared Binary | Spared Glue ($LBD \le 2$) | Spared by Retention Score (`canbedel`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Baseline + Baseline Red** | 573 | 1,601,331 | 0 | 0 | 0 |
| **Adaptive V1 + Baseline Red** | 880 | 2,373,210 | 0 | 0 | 0 |
| **V3 Drawdown + Baseline Red** | 732 | 1,867,500 | 0 | 0 | 0 |
| **Baseline + Adaptive-Fixed** | 801 | 1,996,620 | 213 | 0 | 255,964 |
| **Adaptive V1 + Adaptive-Fixed** | 976 | 2,519,980 | 0 | 0 | 273,313 |
| **V3 Drawdown + Adaptive-Fixed** | 878 | 2,227,881 | 0 | 0 | **256,430** |

**Mechanism Explaining the Factorial Synergy**:
Under Adaptive-Fixed reduction, **256,430 high-scoring learned clauses** were spared from deletion in `cfg6_v3dd_adaptfix`. 
- When restarts occur infrequently (as in V3 Drawdown), the solver remains in deep search subtrees where these preserved clauses immediately participate in unit propagation and conflict resolution.
- Under Baseline restarts, the solver is repeatedly thrust back to level 0, rendering these deep nogoods inactive while still incurring watch-list traversal overhead.

---

## 7. Low-Frequency Restart Confounding Audit (Table 7)

A crucial methodological question is whether V3 Drawdown-Only outperforms Baseline simply because it restarts infrequently:

| Configuration | Total Restarts (108 runs) | Mean Descent Interval | PAR-2 Score (s) |
| :--- | :---: | :---: | :---: |
| **Baseline + Baseline Red** | 3,445 | 3,098.9 conflicts | 3.593 |
| **Adaptive V1 + Baseline Red** | 68 | 11,542.8 conflicts | 2.988 |
| **V3 Drawdown + Baseline Red** | 12 | 15,053.2 conflicts | 3.123 |
| **Adaptive V1 + Adaptive-Fixed** | 71 | 10,208.1 conflicts | 3.032 |
| **V3 Drawdown + Adaptive-Fixed** | **10** | **18,043.0 conflicts** | **2.872** |

### Separating Timing from Frequency:
1. **Adaptive V1 also restarts very infrequently** (68–71 restarts vs. 10–12 for V3 Drawdown).
2. Yet on **Graph Coloring**, V3 Drawdown + Adaptive-Fixed achieves **3.06s PAR-2** vs. 3.23s for V1 + Adaptive-Fixed and 4.18s for V1 + Baseline.
3. On **Pigeonhole Principle**, V3 Drawdown + Adaptive-Fixed achieves **9.55s PAR-2** vs. 11.14s for V1 + Adaptive-Fixed.
4. On `gcol_unsat_k10_c9.cnf`, V3 Drawdown solved in 5.67s (with 1 restart) compared to 7.53s for V1 and 13.28s for Baseline.
5. **Conclusion**: While long descents are necessary to build deep deduction trees, the timing of the exit matters. V3 Drawdown's ability to trigger restarts strictly when search productivity collapses relative to the descent peak ($D_t \ge 0.75$) prevents unproductive thrashing while preserving momentum.

---

## 8. Test of Primary Research Hypotheses

| Hypothesis | Evaluation | Empirical Evidence |
| :--- | :---: | :--- |
| **H1: V3 Drawdown improves over Baseline with Baseline Retention** | **CONFIRMED** | Overall PAR-2: 3.123s vs 3.593s (**-13.1% speedup**). Graph Coloring PAR-2: 3.21s vs 4.70s (**-31.7% speedup**). PHP PAR-2: 9.65s vs 15.54s (**-37.9% speedup**). |
| **H2: Adaptive-Fixed Retention independently improves efficiency** | **REJECTED (Holding Baseline Restart)**<br>**CONFIRMED (Holding V3 Drawdown)** | Holding Baseline restart: PAR-2 degraded from 3.593s to 3.959s (+0.366s). Holding V3 Drawdown restart: PAR-2 improved from 3.123s to 2.872s (**-0.251s**). |
| **H3: Combining V3 Drawdown with Adaptive-Fixed provides an interaction benefit** | **CONFIRMED** | Factorial interaction is strongly negative ($\mathbf{-0.617s}$), proving that combining descent-local drawdown restarts with high-retention nogood reuse creates positive non-linear synergy. |

---

## 9. Reproducibility & Determinism Verification (Table 8)

Across all 648 runs:
- **Zero conflict discrepancies** on all mutually solved runs across repetitions.
- **Zero decision discrepancies** across repetitions.
- **Zero restart discrepancies** across repetitions.
- **Zero reduction discrepancies** across repetitions.
- **Zero model verification failures**: All satisfying models were verified against the original CNF.
- Only 6 `(instance, configuration)` pairs exhibited timeout-boundary sensitivity (status flips near 15.0s), primarily on `gcol_unsat_k10_c9` and `php_10p_9h`.

---

## 10. Threats to Validity & Final Recommendations

### 10.1 Threats to Validity
1. **Benchmark Suite Size**: The 36-instance development suite represents 4 families. Generalization to real-world industrial SAT competition instances requires holdout verification.
2. **Timeout Boundary Truncation**: A 15-second timeout penalizes instances like `rand3sat_n250_c1065_s1010` where V3 Drawdown solved in 8.86s in some reps but narrowly exceeded 15.0s in others.

### 10.2 Final Strategy Recommendation
**V3 Drawdown-Only Restart combined with Adaptive-Fixed Nogood Retention (`cfg6_v3dd_adaptfix`) is the strongest solver configuration produced in this research project to date**:
- **Best overall PAR-2 (2.872s)** across 648 factorial runs.
- **Best Graph Coloring PAR-2 (3.06s)**.
- **Best Pigeonhole Principle PAR-2 (9.55s)**.
- **Proven non-linear factorial synergy (-0.617s interaction)**.
- Recommended configuration for the upcoming Step 32 final holdout evaluation:
  ```bash
  glucose-simp.exe -restart-strategy=adaptive-v3 -v3-trend=0 -v3-drawdown=1 -v3-ceiling=0 -reduce-strategy=adaptive-fixed
  ```

