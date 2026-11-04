# Executive Results Summary

**Project:** Adaptive Restart and Nogood Management for Constraint Satisfaction Solvers  
**Authors:** Manav Garg (25125026) & Kugashiya Bhavy (25125024)  
**Advisor:** Prof. Manoj Kumar  

---

## 1. Overview of Experimental Campaign

The empirical evaluation of our adaptive search-control architectures spanned two rigorous, pre-registered testing environments:

1. **Development Suite (`benchmarks/expanded/`):** 36 combinatorial instances (Graph Coloring, Pigeonhole, Random 3-SAT, Planted 3-SAT) evaluated across 6 factorial configurations with 3 random repetitions (**648 total runs**, uniform 15.0 s timeout, PAR-2 penalty 30.0 s).
2. **Unseen Final Holdout Suite (`benchmarks/final_holdout/`):** 48 quarantined benchmark instances across 7 diverse problem families (AIM, Dubois, Pretolani, Flat Graph Coloring, Logistics Planning, Towers of Hanoi, Bridging Faults) evaluated across 8 factorial configurations with 3 repetitions (**1,152 total runs**, uniform 30.0 s timeout, PAR-2 penalty 60.0 s).
3. **Statistical Certification:** Every SAT result was independently certified using a standalone truth-assignment verifier ([`verify_model.py`](./experiments/verify_model.py)). Every UNSAT result was verified against authoritative ground-truth labels. Zero invalid claims or silent corruptions occurred.

---

## 2. Development Benchmark Results (Step 41 Full Development Evaluation)

The development benchmark suite evaluates solver performance on hard, conflict-dense combinatorial problem structures.

**Authoritative Record:** [`experiments/results/qre_gated_full_development/master_results.csv`](./experiments/results/qre_gated_full_development/master_results.csv) (648 runs: 36 instances × 6 configurations × 3 repetitions).

### Strategy Performance Ranking (Development Suite — 36 Instances, 648 Runs)

| Configuration Identifier | Evaluated Configuration | Solved / Total | Timeouts | PAR-2 Score (s) | Solved Wall Mean (s) | Solved Mean Conflicts | PAR-2 Relative Change |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`cfg_v3dd_adaptfix`** | **V3 Drawdown + Adaptive-Fixed** | **102 / 108** | **6** | **2.5381 s** | **0.9227 s** | **34,690.7** | **+7.58% faster (Winner)** |
| `cfg01_baseline_base` | Baseline Glucose 4.2.1 | 102 / 108 | 6 | 2.7463 s | 1.1432 s | 41,055.8 | Baseline (0.0%) |
| `cfg_active_adaptfix` | Active QRE + Adaptive-Fixed | 100 / 108 | 8 | 3.1960 s | 1.0517 s | 42,929.6 | -16.37% (over-restarts) |
| `cfg_gated_adaptfix` | Stagnation-Gated QRE + AdaptFix | 98 / 108 | 10 | 3.4716 s | 0.7646 s | 35,097.9 | -26.41% |
| `cfg05_baseline_adaptfix` | Glucose Baseline + AdaptFix | 98 / 108 | 10 | 3.5892 s | 0.8943 s | 35,578.1 | -30.69% |
| `cfg_gated_base` | Stagnation-Gated QRE + Base Red | 97 / 108 | 11 | 3.5915 s | 0.5967 s | 27,524.8 | -30.78% |

### Key Development Insights:
- **Drawdown Restarts (V3):** By tracking rolling search productivity against an exponentially decaying High-Water Mark ($0.999 \times \text{HWM}$ with exact relative drawdown $D_t = \frac{\text{HWM}_t - \text{EWMA}_{\text{fast}, t}}{\text{HWM}_t + 0.05}$), V3 cuts stagnant search branches early, reducing solved mean conflicts by **15.5%** (34,690.7 vs 41,055.8) and improving PAR-2 runtime by **7.58% (~7.6%)**.
- **Fair Common Solved Subset (31 Benchmarks / 93 Runs per Config):** On the instances solved by all 6 configurations without timeout, `cfg_v3dd_adaptfix` achieved the fastest solved wall mean time (**0.2981 s** vs. 0.3291 s for baseline Glucose).

---

## 3. Unseen Final Holdout Results (Step 36 Quarantined Suite)

The holdout suite tests generalizability on 48 completely unseen instances across 7 benchmark families under strict quarantine.

**Authoritative Record:** [`experiments/results/final_holdout/master_results.csv`](./experiments/results/final_holdout/master_results.csv) (1,152 runs: 48 instances × 8 configurations × 3 repetitions).

### Strategy Performance Ranking (Final Holdout Suite — 48 Instances, 1,152 Runs)

| Configuration ID | Evaluated Configuration | Solved / Total | Timeouts | PAR-2 Score (s) | Mean Wall Time (s) | Mean Conflicts | PAR-2 Relative Change |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`cfg05_baseline_adaptfix`** | **Glucose Baseline + Adaptive-Fixed** | **144 / 144** | **0** | **0.1107 s** | **0.1107 s** | **4,927.7** | **+8.36% faster (Winner)** |
| `cfg01_baseline_base` | Glucose Baseline (Default) | 144 / 144 | 0 | 0.1208 s | 0.1208 s | 5,403.9 | Baseline (0.0%) |
| `cfg03_v3dd_base` | V3 Drawdown + Baseline Red | 144 / 144 | 0 | 0.1642 s | 0.1642 s | 6,573.2 | -35.93% (locality overhead) |
| `cfg08_noheuristic_adaptfix` | No-Heuristic + Adaptive-Fixed | 144 / 144 | 0 | 0.2417 s | 0.2417 s | 7,847.0 | Ablation control |
| `cfg02_v1_base` | Adaptive V1 + Baseline Red | 144 / 144 | 0 | 0.2784 s | 0.2784 s | 8,052.4 | Frequent restarts hurt locality |
| `cfg07_v3dd_adaptfix` | V3 Drawdown + Adaptive-Fixed | 144 / 144 | 0 | 0.3443 s | 0.3443 s | 8,949.2 | Overhead on rapid instances |
| `cfg04_noheuristic_base` | No-Heuristic + Baseline Red | 144 / 144 | 0 | 0.4201 s | 0.4201 s | 9,928.9 | Ablation control |
| `cfg06_v1_adaptfix` | Adaptive V1 + Adaptive-Fixed | 144 / 144 | 0 | 0.4440 s | 0.4440 s | 9,779.6 | Cumulative overhead |

### Statistical Hypothesis Testing & Significance Boundaries:
- **Pairwise Wilcoxon Signed-Rank Test:** Comparing Glucose Baseline + Adaptive-Fixed vs. Default Baseline Glucose yields positive rank sum $W^+ = 780.0$, negative rank sum $W^- = 396.0$, asymptotic $Z = 1.9693$, and two-tailed unadjusted $p = 0.0489$.
- **Multiple-Comparison Correction:** Because 67.0% of holdout runs finished in $\le 0.05$ s, raw timing differences are near operating-system scheduling noise. Applying the Benjamini-Hochberg False Discovery Rate (FDR) correction across all 8 factorial configurations elevates the adjusted $p$-value above the $\alpha = 0.05$ significance threshold ($p_{\text{adj}} > 0.05$). Consequently, this performance difference is reported as an **empirical numerical improvement (+8.36%)** rather than a statistically confirmed universal superiority.

---

## 4. Scientific Synthesis & Algorithm Boundaries

Comparing development and holdout results yields key domain boundaries:

```text
[Combinatorial / Conflict-Dense Problems (Development Suite)]
  --> Trapped search branches with high conflict volatility
  --> V3 DRAWDOWN RESTARTS WIN (+7.58% PAR-2, -15.5% solved conflicts)
  --> Early exit from stagnant descents preserves solver throughput

[Rapid / Shallow Problems (Holdout Suite)]
  --> Low conflict density (67% solved in ≤ 0.05 s)
  --> Frequent adaptive restarts disrupt trail locality
  --> NATIVE GLUCOSE DUAL-EWMA RESTARTS WIN (0.1208 s vs 0.1642 s for V3)

[Clause Retention Policy Across Solvers]
  --> ADAPTIVE-FIXED RETENTION WINS ON HOLDOUT (0.1107 s vs 0.1208 s)
  --> Multi-attribute utility R(c) = 0.50 S_LBD + 0.40 S_act + 0.10 S_size
      protects active reasoning lemmas across database reductions.

[Unstructured / Phase-Transition Random 3-SAT]
  --> Dynamic statistical triggers (Active QRE and Portfolio-MAB) thrash
  --> Causes conflict explosions (+45% to +192%) without structural guidance
  --> Honest research boundary: adaptive heuristics require structural contention.
```
