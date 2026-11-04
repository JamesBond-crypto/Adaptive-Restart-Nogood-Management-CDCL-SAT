# Experimental Design: Adaptive Restarts and Learned-Clause (Nogood) Management

**Project Title:** Adaptive Restart and Nogood Management for Constraint Satisfaction Solvers  
**Document:** Experimental Protocol, Hypothesis Formulation, and Evaluation Methodology  
**Baseline Engine:** Glucose 4.2.1 (Windows MinGW-w64 Port)  
**Status:** Pre-Implementation Specification  

---

## 1. Research Questions & Hypotheses

This research investigates online adaptive decision-making inside Conflict-Driven Clause Learning (CDCL) Boolean Constraint Satisfaction Solvers. We structure our investigation around three core research questions:

### RQ1: Adaptive Restart Performance
> *Does an online adaptive restart policy based on search efficiency and conflict-volatility metrics improve solver performance over unmodified Glucose 4.2.1?*

- **Null Hypothesis ($H_{0,1}$):** A search-efficiency-guided restart policy (e.g., Sharpe-inspired progress-to-volatility ratio or percentile conflict-risk tracking) exhibits no statistically significant difference in solved instances or PAR-2 runtime compared to Glucose 4.2.1's moving-average LBD restart policy.
- **Alternative Hypothesis ($H_{1,1}$):** Monitoring conflict depth volatility and propagation rate allows the solver to exit unproductive search subspaces earlier without prematurely abandoning productive deep descents, reducing total conflicts and runtime on structured problem instances.

### RQ2: Adaptive Learned-Clause (Nogood) Retention Performance
> *Does a multi-criteria learned-clause retention policy incorporating clause usefulness, activity, age, and LBD improve solver performance over Glucose 4.2.1's baseline reduction policy?*

- **Null Hypothesis ($H_{0,2}$):** Augmenting Glucose's LBD-dominated clause purging policy with clause usage frequency and age decay yields no statistically significant improvement in memory efficiency or search progress.
- **Alternative Hypothesis ($H_{1,2}$):** Static LBD thresholding occasionally purges high-LBD clauses that participate frequently in recent unit propagations; a multi-attribute utility retention policy preserves high-utility reasoning paths while aggressively pruning inactive clauses.

### RQ3: Synergistic Interaction (Combined Effects)
> *Does combining adaptive restarts with adaptive learned-clause retention provide complementary or compound performance benefits?*

- **Null Hypothesis ($H_{0,3}$):** Combining both mechanisms produces additive or conflicting effects without synergistic performance gains.
- **Alternative Hypothesis ($H_{1,3}$):** Frequent restarts alter the distribution of learned clause LBDs; an adaptive clause database manager dynamically stabilizes the database across frequent restarts, producing compound reductions in overall search effort.

---

## 2. Baseline and Experimental Variants

To scientifically isolate each architectural modification, we define a $2 \times 2$ factorial experimental matrix comprising four distinct solver configurations:

```
                          Learned-Clause (Nogood) Retention
                          Standard Glucose       Adaptive Utility
                        +----------------------+----------------------+
      Standard Glucose  |       BASELINE       |      VARIANT B       |
Restart                 | (Glucose 4.2.1 Stock)| (Adaptive Retention) |
Policy                  +----------------------+----------------------+
      Adaptive Restart  |      VARIANT A       |      VARIANT C       |
                        |  (Adaptive Restarts) |  (Full Combined)     |
                        +----------------------+----------------------+
```

### 1. Baseline: Unmodified Glucose 4.2.1
- **Restart Policy:** Glucose's dual-queue dynamic restart scheme:
  - Bounded LBD queue size: $50$ conflicts (`sizeLBDQueue`).
  - Restart condition: $\text{avg}(\text{LBD}_{\text{short}}) \times K > \text{avg}(\text{LBD}_{\text{long}})$, with $K = 0.8$.
  - Blocked restarts: If $\text{trail.size}() > R \times \text{avg}(\text{trailQueue})$ with $R = 1.4$.
- **Clause Reduction Policy:**
  - Invocation interval: Triggered periodically when $\text{conflicts} \ge \text{curRestart} \times \text{nbclausesbeforereduce}$.
  - Retention criteria: Permanent preservation of glue clauses ($\text{LBD} \le 2$), binary clauses ($\text{size} \le 2$), and the top $10\%$ most active clauses; median-based pruning of remaining clauses.
- **Source Integrity:** Executed directly from `src/glucose_windows/` with default command-line parameters.

### 2. Variant A: Adaptive Restart Policy Only
- **Restart Policy:** Controlled by our proposed adaptive restart controller (monitoring search progress rate, conflict depth volatility, or Sharpe-inspired search efficiency).
- **Clause Reduction Policy:** Identical to Baseline (unmodified Glucose reduction).
- **Purpose:** Exclusively isolates the impact of the restart mechanism on search descent duration and backtrack frequency.

### 3. Variant B: Adaptive Learned-Clause Retention Only
- **Restart Policy:** Identical to Baseline (unmodified Glucose dual-queue LBD restarts).
- **Clause Reduction Policy:** Controlled by our multi-attribute learned-clause retention algorithm (incorporating propagation count, clause age, activity decay, and LBD).
- **Purpose:** Exclusively isolates the impact of database pruning on memory overhead, propagation speed, and retention of critical reasoning paths.

### 4. Variant C: Full Adaptive Solver (Combined)
- **Restart Policy:** Proposed adaptive restart controller enabled.
- **Clause Reduction Policy:** Proposed multi-attribute clause retention policy enabled.
- **Purpose:** Evaluates compounding interactions and potential cross-mechanism synergies.

---

## 3. Candidate Measurements & Metrics

Relying solely on wall-clock runtime in solver research is fundamentally insufficient due to operating system scheduling jitter, CPU frequency scaling, background cache contention, and Windows timer quantization (~$10\text{--}15.6\text{ ms}$). 

Therefore, our evaluation framework records three distinct tiers of metrics:

```
+-----------------------------------------------------------------------------------+
|                              Candidate Measurements                               |
|                                                                                   |
|  [Deterministic Search Effort]      [Database Telemetry]      [System Resources]  |
|  - Conflicts                        - Learnt Clauses Added    - Process CPU Time  |
|  - Decisions                        - Learnt Clauses Purged   - Wall-Clock Time   |
|  - Unit Propagations                - Glue Clauses (LBD <= 2) - Peak RSS Memory   |
|  - Total Restarts                   - Average Learnt LBD      - Timeout Status    |
|  - Blocked Restarts                 - Clause DB Reductions    - Solved Count      |
+-----------------------------------------------------------------------------------+
```

### Tier 1: Hardware-Independent Deterministic Search Effort
These integer counters reflect the true algorithmic progress of the CDCL engine and are 100% immune to machine speed or system load:
- **Conflicts (`solver.conflicts`):** Number of backtrack-inducing dead ends encountered. Primary indicator of whether a policy prunes useless search spaces.
- **Decisions (`solver.decisions`):** Total free branch choices made.
- **Unit Propagations (`solver.propagations`):** Total literal implications deduced via two-watched-literal lists. Measures Boolean Constraint Propagation (BCP) work.
- **Restarts (`solver.starts`):** Number of times the solver reset its search tree to level zero.
- **Blocked Restarts (`solver.stats[nbstopsrestarts]`):** Number of times restart conditions were overridden due to rapid assignment growth.

### Tier 2: Learned-Clause Database Telemetry
- **Clause Database Reductions (`solver.stats[nbReduceDB]`):** Frequency of database purge cycles.
- **Removed Clauses (`solver.stats[nbRemovedClauses]`):** Absolute count of discarded learned nogoods.
- **Glue Clauses Preserved (`solver.stats[nbDL2]`):** Number of high-quality clauses ($\text{LBD} \le 2$) retained.
- **Average Learned Clause Size & LBD:** Structural compactness of generated lemmas.

### Tier 3: System Performance & Outcome Metrics
- **Process CPU Time:** Measured via Win32 `GetProcessTimes()` (user + kernel CPU dedicated to the solver process).
- **Elapsed Wall-Clock Time:** High-resolution measurement via `std::chrono::steady_clock` (nanosecond resolution).
- **Peak Memory Usage:** Queried via `GetProcessMemoryInfo()` (`PeakWorkingSetSize` in megabytes).
- **Solved Instance Count ($S$):** Number of benchmarks decided within the cutoff time limit.
- **PAR-2 Score (Penalized Average Runtime):** Standard SAT competition metric penalizing timeouts:
  $$\text{PAR-2} = \frac{1}{N} \left( \sum_{i \in \text{Solved}} T_i + \sum_{j \in \text{Unsolved}} 2 \cdot T_{\text{limit}} \right)$$

---

## 4. Fair Experimental Protocol

To prevent experimental bias, data leakage, and invalid cross-benchmark conclusions, all tests must adhere to the following protocol:

### A. Problem Family Categorization
Solvers behave differently across different problem topologies. Benchmarks must be organized into clear families and reported independently:
1. **Application / Industrial:** Hardware verification, cryptographic circuit inversion, model checking (large, highly structured instances).
2. **Crafted / Combinatorial:** Graph coloring, pigeonhole variations, Latin squares (challenging mathematical structures).
3. **Random 3-SAT:** Uniform random instances at the satisfiability phase transition ($m/n \approx 4.267$) where structure is absent.

> [!WARNING]
> **Cross-Benchmark Contamination Warning:**  
> Performance metrics must **never** be aggregated across unrelated benchmark suites. A speedup on random formulas does not imply a speedup on industrial hardware circuits. Every table and plot must report results grouped by problem family.

### B. Standardized Execution Environment
- **Platform:** Single dedicated host to eliminate hardware variance.
- **Process Isolation:** One benchmark instance executed at a time (sequential execution; no competing parallel benchmarks).
- **Compiler Invariance:** All solver variants compiled using identical flags (`-O3 -std=c++11 -DNDEBUG -lz -lpsapi`) with the same GCC 14.2 toolchain.
- **Fixed Per-Instance Cutoff:** Strict timeout $T_{\text{limit}}$ enforced externally by our Python test runner (e.g., $300\text{ s}$ for exploratory sweeps; $1200\text{ s}$ or $5000\text{ s}$ for final evaluations).

### C. Statistical Reporting Standards
- **Median & Interquartile Range (IQR):** Standard arithmetic means are distorted by heavy-tailed runtime distributions. We will report Median and IQR alongside mean values.
- **Cactus Plots:** Sorted cumulative solved runtime curves to visualize solver dominance across each problem family.
- **Statistical Significance Tests:** Wilcoxon signed-rank test (paired non-parametric) to verify whether observed differences between Baseline and Variants are statistically significant ($p < 0.05$).

---

## 5. Ablation Study Methodology

An ablation study determines whether observed performance gains are caused by our algorithmic hypotheses rather than incidental side effects (e.g., altered memory footprint or random seed variations).

### Analytical Framework
Using our $2 \times 2$ factorial structure:

| Comparison | Isolated Variable | Measurement Objective |
| :--- | :--- | :--- |
| **Variant A vs. Baseline** | Adaptive Restart Policy | Quantifies the isolated effect of adaptive restarts while holding clause management constant. |
| **Variant B vs. Baseline** | Adaptive Clause Retention | Quantifies the isolated effect of multi-attribute nogood retention while holding restarts constant. |
| **Variant C vs. (A + B)** | Cross-Mechanism Interaction | Evaluates whether combining both features produces positive synergy, redundancy, or destructive interference: $\Delta_{\text{interaction}} = \Delta C - (\Delta A + \Delta B)$. |

### Micro-Ablation Checks
When analyzing Variant A:
- Disable conflict volatility scoring; evaluate only progress rate.
- Compare static Luby restarts vs. Glucose dynamic restarts vs. proposed adaptive controller.

When analyzing Variant B:
- Remove clause age decay; evaluate pure activity + LBD retention.
- Remove usage frequency counters; evaluate pure LBD retention.

---

## 6. Correctness & Soundness Verification Protocol

An experimental solver that runs quickly but returns incorrect results is scientifically worthless. Every run will be subjected to automated verification:

```
+-----------------------------------------------------------------------------------+
|                        Correctness Verification Flow                              |
|                                                                                   |
|  [Solver Output] ---> "s SATISFIABLE" ---> [Model Checker: verify_model.py]       |
|                                            - Substitute literals into CNF         |
|                                            - Check every clause evaluates True    |
|                                                                                   |
|                  ---> "s UNSATISFIABLE" -> [Cross-Verification Oracle]            |
|                                            - Compare against ground-truth labels  |
|                                            - Or check certified DRAT proof stream |
+-----------------------------------------------------------------------------------+
```

### 1. Satisfiable (SAT) Certification
- **Verification Rule:** When a variant outputs `s SATISFIABLE`, it prints the truth model `v l1 l2 ... ln 0`.
- **Automated Validation:** An independent Python validation script (`verify_model.py`) parses the original problem file (`.cnf`) and confirms:
  $$\forall C_j \in F, \quad \exists l \in C_j \text{ such that } \sigma(l) == \text{True}$$
- If even one clause evaluates to False, the run is flagged as **UNSOUND (CRITICAL BUG)**.

### 2. Unsatisfiable (UNSAT) Certification
- **Verification Rule:** When a variant outputs `s UNSATISFIABLE`, the claim must be checked because satisfying assignments do not exist to easily verify.
- **Oracle Comparison:** Benchmarks drawn from competition archives have certified ground-truth status (`SAT`, `UNSAT`, or `UNKNOWN`). Any variant classifying a known SAT formula as UNSAT or vice versa is immediately marked defective.
- **Proof Logging (DRUP/DRAT):** Glucose supports emitting proof traces via `-certified -certified-output=proof.drat`. For ambiguous instances, proofs will be validated via the certified proof checker `drat-trim`.

---

## 7. Implementation Overlap & Architectural Risks

Integrating new heuristics into a highly optimized solver like Glucose presents specific technical risks:

### Overlap with Existing Glucose Heuristics
1. **Glucose's Existing Dynamic Restarts:**  
   Glucose already incorporates an adaptive restart mechanism based on short-term vs. long-term LBD averages (`lbdQueue` vs. `sumLBD / conflictsRestarts`).  
   *Risk:* A proposed restart controller must explicitly replace or supersede this logic rather than running concurrently, or the two controllers will trigger conflicting restart signals.
2. **Blocked Restarts Interference:**  
   Glucose blocks restarts when the assignment trail is expanding rapidly (`trail.size() > R * trailQueue.getavg()`).  
   *Risk:* Overriding blocked restarts could degrade performance on satisfiable application instances by interrupting productive deep descents.
3. **Chanseok Strategy & Multi-Tier DBs:**  
   Glucose includes an alternate clause management mode (`chanseokStrategy`, line 216 of `Solver.h`) and vivification minimization (`useLCM`).  
   *Risk:* Any modified clause retention logic must cleanly integrate with standard 2-watched literal invariants. Deleting a clause that is currently "locked" as the reason for an active assignment on the trail causes immediate solver crash or memory corruption.
4. **Computational Overhead in Inner Search Loops:**  
   The CDCL conflict loop executes millions of times per second.  
   *Risk:* Calculating complex floating-point metrics (such as online standard deviations, percentiles, or decaying exponent sums) inside `search()` can drastically reduce propagation throughput, converting an algorithmic advantage into a net wall-clock slowdown.

> [!IMPORTANT]
> **Scientific Objectivity Commitment:**  
> Our proposed restart and nogood management heuristics are exploratory hypotheses. We do not assume they will outperform Glucose 4.2.1. Negative results (proving that a proposed score provides no benefit or introduces unacceptable overhead) are scientifically valid and will be documented with the same statistical rigor as positive outcomes.

---

## 8. Summary of Evaluation Roadmap

```
Step 1: Protocol Approval (This Document)
   │
Step 2: Automated Evaluation Harness (Python runner, timeout enforcement, model checker)
   │
Step 3: Baseline Data Acquisition (Run Glucose 4.2.1 across curated validation suite)
   │
Step 4: Implementation of Variant A (Adaptive Restarts) & Evaluation
   │
Step 5: Implementation of Variant B (Adaptive Clause Retention) & Evaluation
   │
Step 6: Implementation of Variant C (Combined) & Full Factorial Ablation Analysis
```

