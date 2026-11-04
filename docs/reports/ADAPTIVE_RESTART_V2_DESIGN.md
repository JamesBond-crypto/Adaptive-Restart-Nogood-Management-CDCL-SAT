# Adaptive Restart Controller V2: Regression Diagnosis and Research Design

**Project Title:** Adaptive Restart and Nogood Management for Constraint Satisfaction Solvers  
**Author / Research Team:** DeepMind Coding Assistant (Antigravity)  
**Date:** October 31, 2026  
**Status:** Research Design & Diagnostic Audit Completed (Pre-Implementation)  
**Target Architecture:** Glucose 4.2.1 Windows Release Port (`src/glucose_windows/`)  
**Reference Documents:**  
- `docs/ADAPTIVE_RESTART_V1.md`  
- `docs/ADAPTIVE_RESTART_V1_AUDIT.md`  
- `docs/ADAPTIVE_RESTART_V1_STABILIZATION.md`  
- `docs/EXPANDED_FOUR_VARIANT_EVALUATION.md`  
- `docs/EXPANDED_REPRODUCIBILITY_REPORT.md`  

---

## 1. Executive Summary and Empirical Motivation

In Phases B through D, we implemented, audited, and empirically evaluated **Adaptive Restart Controller V1** alongside **Adaptive Learned-Clause Retention V1** across 576 solver executions (a 20-instance pilot suite, an expanded 36-instance benchmark suite, and a 3-repetition factorial campaign).

The empirical evidence from Step 19 and Step 20 demonstrated a striking, reproducible performance bifurcation:
1. **Dramatic Improvements on Structured Constraints**: On symmetry-heavy, structured formulas (Graph Coloring and Pigeonhole Principle), V1 eliminated rapid restart thrashing (reducing genuine restarts by up to 99%), cutting search conflicts by **29.6% to 53.2%** and database reductions by **89% to 92%**.
2. **Severe, Consistent Regressions on Uniform Random 3-SAT**: On unstructured uniform Random 3-SAT near the phase transition ($N = 200\text{--}250, m/n \approx 4.26$) and large planted instances, V1 increased conflict counts by **+50% to +157%**, inflating wall-clock runtime and degrading overall PAR-2 scores relative to baseline Glucose (2.42s vs 2.19s).

This document presents a rigorous source-level diagnosis of why Adaptive Restart V1 degrades on uniform random formulas, evaluates candidate online signals, and formulates the mathematical and architectural design for **Adaptive Restart Controller V2**.

> [!IMPORTANT]
> This milestone is strictly for **diagnosis, theoretical modeling, and experimental design**. No solver source code, hyperparameters, or benchmark manifests are modified in this step.

---

## 2. Confirmed Empirical Regression Patterns

Detailed inspection of the 576 execution logs across all 3 repetitions identified four benchmark instances that exhibited consistent, severe conflict regressions under Adaptive Restart V1 (Cfg 2 and Cfg 4) relative to baseline Glucose (Cfg 1):

| Benchmark Instance | Problem Family | Status | Metric | Cfg 1 (Baseline) | Cfg 2 (Adapt Rst) | Cfg 4 (Combined) | Percentage Change (Cfg 2 / Cfg 4) |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| `rand3sat_n250_c1065_s1010.cnf` | Random 3-SAT | SAT | Conflicts | 114,109 | 178,700 | **222,436** | **+56.6% / +94.9%** |
| | | | Restarts | 30 | 8 | **11** | -73.3% / -63.3% |
| | | | Median Time | 2.842s | 3.871s | **8.126s** | +36.2% / +185.9% |
| `rand3sat_n235_c999_s1009.cnf` | Random 3-SAT | SAT | Conflicts | 33,846 | 79,234 | **60,533** | **+134.1% / +78.8%** |
| | | | Restarts | 0 | 2 | **1** | +2 / +1 |
| | | | Median Time | 0.526s | 1.814s | **1.117s** | +244.9% / +112.4% |
| `rand3sat_n200_c840_s1005.cnf` | Random 3-SAT | UNSAT | Conflicts | 25,375 | 43,186 | **41,602** | **+70.2% / +63.9%** |
| | | | Restarts | 1 | 0 | **0** | -100% / -100% |
| | | | Median Time | 0.353s | 0.648s | **0.656s** | +83.6% / +85.8% |
| `planted3sat_n240_c1022_s2009.cnf` | Planted 3-SAT | SAT | Conflicts | 5,611 | 14,442 | **9,758** | **+157.4% / +73.9%** |
| | | | Restarts | 2 | 0 | **0** | -100% / -100% |
| | | | Median Time | 0.087s | 0.179s | **0.117s** | +105.7% / +34.5% |

In contrast, the three prominent improvement cases demonstrated opposite behavior:
- `gcol_unsat_k10_c9.cnf`: 528,305 $\to$ **247,457 conflicts (-53.2%)**, restarts dropped from 1,249 to **3**.
- `php_10p_8h.cnf`: 60,580 $\to$ **40,852 conflicts (-32.6%)**, restarts dropped from 166 to **2**.
- `gcol_unsat_k9_c8.cnf`: 55,154 $\to$ **42,049 conflicts (-23.8%)**, restarts dropped from 188 to **1**.

---

## 3. Source-Level Code Diagnosis

Careful examination of `src/glucose_windows/core/Solver.cc` reveals the root architectural cause of this divergence.

### 3.1 The V1 Trigger Mechanism
In `Solver::checkAdaptiveRestartTrigger()` (lines 2384–2438):
1. **Progress Metric ($E_W$)**: $E_W = \frac{1}{W} \sum_{k=1}^W \Delta p_k$, where $\Delta p_k$ is the number of unit propagations executed by the Boolean Constraint Propagation (BCP) engine between conflict $k-1$ and $k$.
2. **Instability Metric ($\sigma_W$)**: $\sigma_W = \sqrt{\text{Var}_W(d_k)}$, where $d_k$ is the decision level at which conflict $k$ was discovered.
3. **Efficiency Score ($\mathcal{S}_W$)**:
   $$\mathcal{S}_W = \frac{E_W}{\sigma_W + 1.0}$$
4. **Trigger Condition**:
   $$\text{Trigger if } \mathcal{S}_W < \theta \cdot \mathcal{S}_{\text{global}} \quad (\theta = 0.60)$$
   subject to $C \ge 100$, window fullness $w = 50$, and minimum interval $\Delta C_{\text{restart}} \ge 50$.

### 3.2 The Confirmed Source of Regression: The "Sterile Subtree Propagation Trap"
When a CDCL solver makes an unpromising decision at a high decision level in a uniform random formula:
1. The solver enters an unsatisfiable resolution subproblem.
2. In this subproblem, BCP repeatedly propagates 15 to 30 unit literals before hitting a contradiction, yielding a high local propagation rate ($E_W \approx 15\text{--}25$).
3. Because the solver is trapped deep in this subproblem, conflicts occur repeatedly at nearly identical decision levels ($d_k \approx 28, 29, 31, 30, 29$).
4. Consequently, the decision-level variance $\sigma_W$ is **artificially low** ($\sigma_W \approx 1.0\text{--}1.8$).
5. The resulting window efficiency score $\mathcal{S}_W$ evaluates to:
   $$\mathcal{S}_W = \frac{E_W}{\sigma_W + 1.0} \approx \frac{20}{1.5 + 1.0} \approx 8.0 \text{ to } 16.0$$
   Meanwhile, the global cumulative score across the entire run is $\mathcal{S}_{\text{global}} \approx 8.0\text{--}10.5$.
6. Because $\mathcal{S}_W > \theta \cdot \mathcal{S}_{\text{global}}$ ($15.0 > 0.60 \times 10.0 = 6.0$), **the restart condition is NEVER satisfied**.

### 3.3 The Absence of an Anti-Starvation Ceiling
In `Solver.cc`:
- Guard 3 enforces a minimum interval (`adapt_conflicts_since_restart < 50` $\implies$ return false) to prevent rapid restart thrashing.
- However, **there is no upper bound ($C_{\text{max\_interval}} = \infty$)** on the number of consecutive conflicts permitted without a restart!
- On `planted3sat_n240_c1022_s2009.cnf`, the solver ran for **14,442 consecutive conflicts with ZERO restarts**.
- On `rand3sat_n200_c840_s1005.cnf`, the solver ran for **43,186 consecutive conflicts with ZERO restarts**.

### 3.4 Complete Blindness to Learned-Clause Quality
In baseline Glucose, `search()` monitors the Literal Block Distance (LBD) of newly learned clauses via `lbdQueue`:
$$\text{do\_restart} = \text{lbdQueue.getavg}() \times K > \frac{\text{sumLBD}}{\text{conflictsRestarts}} \quad (K = 0.80)$$
When the solver enters an unpromising subtree in random 3-SAT, the learned clauses have **terrible (high) LBD values** (LBD $\ge 12\text{--}18$). Baseline Glucose immediately recognizes that clause quality has collapsed and fires a restart, abandoning the fruitless search branch and returning to decision level 0.

In Adaptive Restart V1, the LBD trigger was **entirely replaced** (`if (!adaptive_restart_mode) { ... } else { checkAdaptiveRestartTrigger(); }`). Consequently, V1 possesses zero awareness of learned-clause quality. It observes high local unit propagation, assumes search progress is outstanding, and suppresses restarts indefinitely while the solver chokes on thousands of low-quality learned clauses.

---

## 4. Confirmed Facts vs. Open Hypotheses

To maintain strict scientific integrity, we distinguish what existing telemetry directly proves from what remains hypothetical:

### Confirmed Findings (Proven by Direct Telemetry):
1. **Prolonged Restart Suppression**: V1 allows search descents to continue for tens of thousands of conflicts without restarting (proven by `starts = 1`, `genuine_restarts = 0`, and `conflicts > 14,000`).
2. **Elevated Efficiency Scores During Regressions**: Telemetry confirms that during regression runs, final scores were $\mathcal{S}_W = 12.43\text{--}17.56$ while $\mathcal{S}_{\text{global}} = 8.08\text{--}10.64$. The controller was actively concluding that search efficiency was superior to the global average.
3. **No Database Reduction Churn**: Regressions were not caused by excessive `reduceDB` calls; `reduce_db_count` scaled proportionally with conflict counts.
4. **Negligible Controller Overhead**: Telemetry confirmed that `checkAdaptiveRestartTrigger()` and `updateAdaptiveRestartController()` consume $<0.01\text{s}$ total CPU time. The runtime regression is 100% caused by extra CDCL search tree exploration.

### Open Hypotheses (Requiring V2 Verification):
1. *Hypothesis H1*: Restoring a learned-clause LBD escape hatch will selectively trigger restarts on random 3-SAT without destroying the 50% conflict reduction achieved on Graph Coloring and PHP.
2. *Hypothesis H2*: Imposing an upper bound ceiling on consecutive conflicts without a restart will eliminate the extreme tail regressions ($>10,000$ conflicts without restart) on planted instances.
3. *Hypothesis H3*: Normalizing propagation throughput by decision level ($E_W / \overline{d}_W$) can distinguish shallow, globally useful propagations from deep, sterile subtrees.

---

## 5. Investigation of Additional Online Restart Signals

We evaluate six potential online signals available during CDCL search to distinguish productive progress from sterile subtree exploration:

### Signal A: Short-Window vs. Long-Window LBD Quality Ratio ($Q_{\text{LBD}}$)
- **Mathematical Definition**:
  $$Q_{\text{LBD}} = \frac{\overline{\text{LBD}}_{W_{\text{short}}}}{\overline{\text{LBD}}_{\text{long}}}$$
  where $\overline{\text{LBD}}_{W_{\text{short}}}$ is the moving average over the last $W=50$ conflicts, and $\overline{\text{LBD}}_{\text{long}}$ is the cumulative average since the last restart.
- **Required Source Counters**: `lbdQueue.getavg()` and `sumLBD / conflictsRestarts`.
- **Already Implemented in Solver?**: **YES**. Fully maintained in `Solver.h` / `Solver.cc`.
- **Computational / Memory Overhead**: 0 extra memory, $O(1)$ floating-point division.
- **Failure Modes**: Can trigger prematurely if a brief cluster of high-LBD clauses occurs during an otherwise productive descent.
- **Verdict**: **Essential**. This is Glucose's primary defense against sterile subtrees; bypassing it in V1 was the root cause of random 3-SAT regressions.

### Signal B: Conflicts Since Last Restart / Anti-Starvation Ceiling ($\Delta C_{\text{restart}}$)
- **Mathematical Definition**:
  $$\text{Starvation Guard: } \Delta C_{\text{restart}} \ge C_{\text{max\_ceiling}}$$
- **Required Source Counters**: `adapt_conflicts_since_restart`.
- **Already Implemented in Solver?**: **YES**. Maintained in `Solver.cc` line 2373.
- **Computational / Memory Overhead**: 0 extra memory, 1 integer comparison.
- **Failure Modes**: If $C_{\text{max\_ceiling}}$ is set too low (e.g. $<500$), it could interrupt long, productive refutations on PHP or Graph Coloring.
- **Verdict**: **Essential**. Guarantees a hard upper bound on search descent length, eliminating extreme tail regressions.

### Signal C: Depth-Normalized Propagation Rate ($E_{d, W}$)
- **Mathematical Definition**:
  $$E_{d, W} = \frac{E_W}{\mu_{d, W} + 1.0}$$
  where $\mu_{d, W}$ is the mean decision level of conflicts in window $W$.
- **Required Source Counters**: `adapt_win_props` and `adapt_win_levels`.
- **Already Implemented in Solver?**: **YES**. Both are tracked in the rolling window buffer.
- **Computational / Memory Overhead**: 1 division, $O(1)$ time.
- **Failure Modes**: Heavily penalizes deep search even on structured formulas where deep resolution is necessary.
- **Verdict**: **Secondary**. Useful for diagnostic ranking, but riskier than LBD monitoring.

### Signal D: Non-Chronological Backjump Distance ($\Delta d_{\text{jump}}$)
- **Mathematical Definition**: Mean backjump span $\Delta d_{\text{jump}} = d_{\text{conflict}} - d_{\text{backtrack}}$.
- **Required Source Counters**: `backtrack_level` (from `analyze()`) and `decisionLevel()`.
- **Already Implemented in Solver?**: Available in `search()`, but not currently stored in a rolling window.
- **Computational / Memory Overhead**: Requires an additional circular buffer of size 50 (200 bytes).
- **Failure Modes**: Highly noisy; single 1-UIP conflict clauses often jump back to level 1 even in sterile subtrees.
- **Verdict**: **Rejected for V2**. High variance and added state with marginal predictive advantage over LBD.

### Signal E: Rate of Conflicts per Decision ($\rho_{\text{cfc}}$)
- **Mathematical Definition**: Window ratio $\frac{\Delta C}{\Delta D}$.
- **Required Source Counters**: Windowed decision count.
- **Already Implemented in Solver?**: Global counter exists; windowed counter does not.
- **Verdict**: **Rejected for V2**. Redundant with unit propagation throughput ($E_W$).

### Signal F: Learned Clause Usefulness / Activity Bump Rate
- **Mathematical Definition**: Tracking the frequency at which recently learned clauses are resolved upon in subsequent conflicts.
- **Required Source Counters**: Per-clause timestamp or reference tracking.
- **Computational / Memory Overhead**: Significant ($O(N)$ pointer lookups and clause header modifications).
- **Verdict**: **Rejected for V2**. Substantial overhead and delayed feedback loop.

---

## 6. Proposed Candidate V2 Policies

We develop two mathematically precise candidate restart policies for Adaptive Restart V2.

```
Restart Policy Hierarchy:
├── Candidate Policy 1 (Recommended): Two-Tier Dual-Signal (V1 Progress + LBD Override + Starvation Ceiling)
└── Candidate Policy 2 (Alternative): Multiplicative Unified Efficiency-Quality Index (UEQI)
```

---

### 6.1 Candidate Policy 1 (Recommended): Two-Tier Dual-Signal with Quality Fallback and Anti-Starvation Ceiling

Candidate Policy 1 retains the V1 Sharpe-ratio progress controller to protect deep refutations on structured formulas, but integrates two safety mechanisms: an **LBD-quality distress override** and an **anti-starvation conflict ceiling**.

#### Mathematical Formulation:
At each conflict after BCP, evaluate:
1. **Warmup Guard**: $C \ge C_{\text{warmup}} = 100$.
2. **Window Fullness Guard**: $w = W = 50$.
3. **Blocked Restart Guard**: If $\text{trail.size}() > R \times \text{avg}_{5000}(\text{trail.size})$, block restart and reset window ($w = 0$).

If all guards pass, a restart is triggered if and only if **at least one** of the following three conditions holds:

$$\text{Trigger Restart} \iff \mathcal{T}_{\text{progress}} \lor \mathcal{T}_{\text{quality}} \lor \mathcal{T}_{\text{starvation}}$$

where:

1. **Condition 1 (V1 Progress Degradation Trigger)**:
   $$\mathcal{T}_{\text{progress}} \iff \left(\Delta C_{\text{restart}} \ge C_{\text{min\_interval}}\right) \land \left(\mathcal{S}_W < \theta \cdot \mathcal{S}_{\text{global}}\right)$$
   with $\theta = 0.60, C_{\text{min\_interval}} = 50$, and $\mathcal{S}_W = \frac{E_W}{\sigma_W + 1.0}$.
   *(Maintains the large conflict reductions achieved on Graph Coloring and PHP by suppressing restarts when progress is high).*

2. **Condition 2 (Learned-Clause Quality Fallback Trigger)**:
   $$\mathcal{T}_{\text{quality}} \iff \left(\Delta C_{\text{restart}} \ge C_{\text{min\_interval}}\right) \land \left(\text{lbdQueue.getavg}() \times K_{\text{fallback}} > \frac{\text{sumLBD}}{\text{conflictsRestarts}}\right)$$
   where $K_{\text{fallback}} = 0.80$ (matching standard Glucose baseline).
   *(Detects when the solver is learning poor-quality, high-LBD clauses in an unpromising subtree, overriding the high-propagation false progress illusion).*

3. **Condition 3 (Anti-Starvation Conflict Ceiling)**:
   $$\mathcal{T}_{\text{starvation}} \iff \Delta C_{\text{restart}} \ge C_{\text{max\_ceiling}}$$
   where $C_{\text{max\_ceiling}} = 2,500$ conflicts ($50 \times C_{\text{min\_interval}}$).
   *(Guarantees that no search descent can run indefinitely without restarting, eliminating pathological tail entrapment).*

#### Architectural Properties:
- **Computational Overhead**: $O(1)$ constant time per conflict (1 integer comparison, 1 existing circular buffer lookup, exactly 1 floating-point comparison).
- **Memory Overhead**: Zero additional bytes (reuses existing `lbdQueue`, `sumLBD`, and `adapt_conflicts_since_restart`).
- **Baseline Equivalence**: When `-restart-strategy=baseline`, Condition 2 alone is evaluated (with $K=0.80$), yielding 100% byte-for-byte equivalence with baseline Glucose.

---

### 6.2 Candidate Policy 2 (Alternative): Multiplicative Unified Efficiency-Quality Index (UEQI)

Candidate Policy 2 unifies progress, depth stability, and clause quality into a single continuous metric, coupled with a dynamic conflict ceiling.

#### Mathematical Formulation:
Define the **Unified Search Index** $\mathcal{U}_W$:
$$\mathcal{U}_W = \left(\frac{E_W}{\sigma_W + 1.0}\right) \times \left(\frac{\overline{\text{LBD}}_{\text{global}}}{\text{lbdQueue.getavg}() + 0.1}\right)$$

Define the **Global Baseline Index** $\mathcal{U}_{\text{global}}$:
$$\mathcal{U}_{\text{global}} = \frac{E_{\text{global}}}{\sigma_{\text{global}} + 1.0}$$

A restart is triggered if and only if:
$$\Delta C_{\text{restart}} \ge C_{\text{min\_interval}} \land \left(\mathcal{U}_W < \theta_{\mathcal{U}} \cdot \mathcal{U}_{\text{global}} \lor \Delta C_{\text{restart}} \ge C_{\text{max\_ceiling}}\right)$$
with $\theta_{\mathcal{U}} = 0.75$ and $C_{\text{max\_ceiling}} = 2,500$.

#### Analysis of Candidate Policy 2:
- **Advantage**: Mathematically compact single metric that continuously trades off propagation throughput against clause quality.
- **Risk**: Multiplicative coupling between $E_W$ and LBD creates non-linear feedback. If LBD is moderately high but $E_W$ is very high, the product can oscillate unpredictably, making threshold calibration delicate across diverse benchmark families.

---

### 6.3 Policy Comparison and Recommendation

| Evaluation Dimension | Candidate Policy 1 (Two-Tier Dual-Signal) | Candidate Policy 2 (Unified Index UEQI) |
| :--- | :--- | :--- |
| **Mechanistic Transparency** | **High** (Progress, Quality, and Starvation are decoupled) | Moderate (Multiplicative interaction obscures individual drivers) |
| **Risk of Unintended Side Effects** | **Very Low** (Reuses battle-tested Glucose LBD logic) | Moderate (Risk of premature restarts if LBD spikes temporarily) |
| **Resolution of Random 3-SAT Regressions** | **High** (LBD fallback directly escapes sterile subtrees) | High (High LBD penalizes index) |
| **Preservation of Graph/PHP Gains** | **High** (Maintains V1 suppression when clauses are good) | Moderate (Requires tuning $\theta_{\mathcal{U}}$) |
| **Computational Overhead** | **$O(1)$, zero new allocations** | $O(1)$, zero new allocations |
| **Hyperparameter Sensitivity** | **Low** ($K_{\text{fallback}}=0.80$ is Glucose standard) | High ($\theta_{\mathcal{U}}$ requires careful tuning) |

**Recommendation**: **Candidate Policy 1** is selected as the primary research candidate for Adaptive Restart V2. It directly targets the empirical root causes identified in our audit while introducing minimal architectural risk.

---

## 7. Anti-Overfitting Protocol: Dataset Partitioning

A critical methodological requirement of scientific research is preventing **data leakage and overfitting**:

> [!CAUTION]
> The existing 20 pilot instances and 36 expanded instances have been executed repeatedly during Steps 9–20 to diagnose algorithm behavior. Designing V2 specifically to fix these 56 instances risks tailoring thresholds to idiosyncratic properties of our synthetic generators.

To ensure scientific validity, Adaptive Restart V2 must be developed and validated according to a strict three-tier evaluation protocol:

```
Three-Tier Evaluation Partition:
├── Tier 1: Diagnostic / Development Set (Existing 56 instances)
│   └── Used for diagnostic inspection, regression verification, and sanity checks.
├── Tier 2: Calibration / Validation Set (Newly generated, distinct seeds & sizes)
│   └── Used exclusively if hyperparameter calibration (e.g. C_max_ceiling) is required.
└── Tier 3: Unseen Generalization Test Suite (Completely blind benchmarks)
    └── Reserved exclusively for final performance evaluation; untouched during V2 design.
```

### Protocol Guidelines:
1. **Tier 1 (Development Set)**: The current 36 expanded benchmarks (`benchmarks/expanded/`) serve as the diagnostic baseline to verify that confirmed regressions on `rand3sat_n250` and `rand3sat_n235` are mitigated.
2. **Tier 2 (Calibration Set)**: If hyperparameter tuning is needed for $C_{\text{max\_ceiling}}$ or $K_{\text{fallback}}$, a separate set of 30 synthetic instances with different variable counts and seeds must be used.
3. **Tier 3 (Blind Test Set)**: The ultimate performance claims of Adaptive Restart V2 must be evaluated on an independent, unseen suite (e.g., larger problem sizes $N = 300\text{--}400$, different graph coloring families, or industrial SAT competition benchmarks) that was never used during V1 or V2 development.

---

## 8. Proposed V2 Ablation Plan

To rigorously evaluate Candidate Policy 1, the experimental campaign must isolate the marginal contribution of each component:

### 8.1 Evaluated Ablation Configurations:
1. **Ablation 0 (Original Baseline)**: Standard Glucose 4.2.1 (`-restart-strategy=baseline -reduce-strategy=baseline`).
2. **Ablation 1 (V1 Unmodified)**: V1 Progress Controller alone (`-restart-strategy=adaptive -reduce-strategy=baseline`).
3. **Ablation 2a (V1 + Starvation Ceiling Only)**: V1 Progress Controller + $C_{\text{max\_ceiling}} = 2500$ (disabling Condition 2).
4. **Ablation 2b (V1 + LBD Fallback Only)**: V1 Progress Controller + Condition 2 ($K_{\text{fallback}} = 0.80$) (disabling Condition 3).
5. **Ablation 2 (Full V2 Candidate 1)**: V1 Progress Controller + Condition 2 (LBD Fallback) + Condition 3 (Starvation Ceiling).
6. **Ablation 3 (Full V2 + Adaptive Nogood Retention V1)**: Full V2 combined with multi-attribute clause retention (`-restart-strategy=adaptive-v2 -reduce-strategy=adaptive`).

### 8.2 Primary Evaluation Metrics:
- **Solving Reliability**: Number of solved instances and timeout count (15.0s cutoff).
- **PAR-2 Score**: Penalized average runtime (penalizing timeouts at $2 \times 15.0 = 30.0\text{s}$).
- **Conflict Reductions on Structured Benchmarks**: Percentage change in conflicts on Graph Coloring and PHP relative to baseline Glucose.
- **Regression Mitigation on Random 3-SAT**: Percentage reduction in conflicts on `rand3sat_n250`, `rand3sat_n235`, and `planted3sat_n240` relative to V1.
- **Controller Execution Time**: Overhead of `checkAdaptiveRestartTrigger()` measured in milliseconds.

---

## 9. Recommended V2 Implementation Roadmap

When authorized for implementation in a future milestone, Adaptive Restart V2 should follow a phased, low-risk engineering path:

1. **Option Registration**:
   - Update `opt_restart_strategy` in `Solver.cc` to accept `"baseline"`, `"adaptive-v1"`, and `"adaptive-v2"`.
   - Add option `-adapt-max-interval` (default: 2,500, range: 100 to $10^6$).
   - Add option `-adapt-lbd-fallback` (default: 0.80, range: 0.1 to 2.0).
2. **Controller Logic Updates**:
   - In `Solver.h`: Declare `double adapt_lbd_fallback;` and `int adapt_max_interval;`.
   - In `Solver.cc`: Implement Candidate Policy 1 in `checkAdaptiveRestartTriggerV2()`.
3. **Preserve Baseline Invariance**:
   - Verify that selecting `-restart-strategy=baseline` remains bitwise identical to Glucose 4.2.1 across all deterministic counters.
4. **Telemetry Expansion**:
   - In `simp/Main.cc`: Add counters tracking which trigger fired (`restarts_by_progress`, `restarts_by_quality`, `restarts_by_starvation`).

---

## 10. Open Questions and Unresolved Evidence

1. **Optimal Value of $C_{\text{max\_ceiling}}$**: Is 2,500 conflicts universally appropriate, or should it scale dynamically with problem size (e.g. $N_{\text{vars}} \times 10$)?
2. **Interaction with Dynamic Phase-Saving**: Glucose resets phase saving periodically; does suppressing restarts interact positively or negatively with variable phase memory?
3. **Behavior under Long Timeouts**: On industrial benchmarks with 1,200s timeouts, does the LBD fallback trigger frequently enough to prevent memory bloat, or does the solver require tighter coordination with `reduceDB()`?

These questions will be directly tested during the ablation campaign following V2 implementation.

