# Presentation Notes: Adaptive Restart and Nogood Management for Constraint Satisfaction Solvers

**Course:** DAC - 203: Artificial Intelligence  
**Faculty Advisor:** Prof. Manoj Kumar  
**Presenters:** Manav Garg (25125026), Kugashiya Bhavy (25125024)  
**Implementation Testbed:** Glucose 4.2.1 C++, Native Windows 64-bit (MinGW-w64 GCC 14.2.0)  
**Primary Reference:** `PPT_VERIFICATION_REPORT.md`  

---

## Slide 1: Title Slide
- **Visual Overview:** Dark navy academic theme with cyan glowing geometric network, project title, course details, presenter credentials, advisor name, and three key technical badges (V3 Drawdown, Adaptive-Fixed Retention, 100% C++ Model Verification).
- **Speaker Script:**  
  "Good morning, respected Professor Manoj Kumar and members of the evaluation committee. Today, we present our research thesis: *Adaptive Restart and Nogood Management for Constraint Satisfaction Solvers*. Our work explores a novel, quantitative finance-inspired approach to search control in Conflict-Driven Clause Learning (CDCL) SAT solvers, implemented directly within the state-of-the-art Glucose 4.2.1 C++ codebase. We will walk you through our theoretical motivation, mathematical models, Windows 64-bit engineering testbed, and rigorously verified empirical findings across 3,000+ benchmark executions."
- **Examiner Tip:** Emphasize that every result is backed by frozen C++ code and mathematical verification of raw CNF models.

---

## Slide 2: Executive Summary & Research Overview
- **Visual Overview:** Three-column card layout dividing the research into (1) The Core Challenge, (2) Quantitative Architectures, and (3) Verified Empirical Results.
- **Speaker Script:**  
  "To summarize our thesis upfront: Modern CDCL SAT solvers are plagued by heavy-tailed execution runtimes due to rigid restart schedules and exponential learned-clause database bloat. We hypothesized that combinatorial search progress can be modeled as an asset return stream with dynamic volatility, high-water marks, drawdowns, and tail-risk shocks. We designed four quantitative architectures: the V3 Maximum Drawdown controller, Adaptive-Fixed multi-attribute retention, the Quantitative Risk Engine (QRE), and a duration-aware Portfolio-MAB. Across rigorous evaluation, our V3 Drawdown + Adaptive-Fixed solver won the 36-benchmark development suite (PAR-2 2.5381s vs 2.7463s baseline, with a 15.5% reduction in solved conflicts), while Native Glucose + Adaptive-Fixed won the 48-benchmark holdout suite (PAR-2 0.1107s; 144/144 solved). On complex planning benchmarks like Hanoi-5, V3 achieved an 80.0% speedup over the no-heuristic baseline."

---

## Slide 3: Introduction to CSP and Boolean Satisfiability
- **Visual Overview:** Side-by-side comparison diagram showing General Constraint Satisfaction Problem (CSP) graph vs Boolean Satisfiability (CNF SAT) clause formula.
- **Speaker Script:**  
  "Constraint Satisfaction Problems represent a fundamental paradigm in Artificial Intelligence, formalized as finding an assignment to variables over finite domains that satisfies all constraints. Boolean SAT is the canonical discrete CSP where variables are binary and constraints are expressed as a conjunction of disjunctive clauses. Beyond its foundational role as Cook and Levin's first NP-complete problem, SAT solvers are the computational engines powering modern industrial automated planning, hardware formal verification at companies like Intel and AMD, cryptographic analysis, and software model checking. However, because SAT is NP-complete, naive exhaustive search fails exponentially; modern industrial solving depends entirely on intelligent search heuristics."

---

## Slide 4: Inside Modern CDCL Solvers
- **Visual Overview:** CDCL solver flowchart showing Decision (VSIDS), BCP (2-Watched Literals), Implication Graph Conflict Analysis (1-UIP), Learned Clause Asserting & Backjumping, and Periodic Search Control.
- **Speaker Script:**  
  "To appreciate our contributions, we must examine the five pillars of Conflict-Driven Clause Learning (CDCL):
  1. *VSIDS Branching:* Bumps activities of variables involved in conflicts to focus search on contentious subtrees.
  2. *Two-Watched Literals:* BCP inspects clauses only when one of two watched literals is set to false, enabling tens of millions of propagations per second.
  3. *Conflict Analysis & 1-UIP:* Traces the implication graph back to the First Unique Implication Point, producing an asserting learned nogood.
  4. *Non-Chronological Backjumping:* Bypasses whole subtrees to jump directly to the decision level where the learned clause forces propagation.
  5. *Restarts and Clause Reductions:* Periodically unassigns variables to escape dead ends while retaining learned lemmas."

---

## Slide 5: Problem Statement: The Dual Search-Control Dilemmas
- **Visual Overview:** Heavy-tailed trap diagram contrasting standard backtracking trapped in fruitless subtrees with CDCL restarts pruning bad paths while preserving nogoods.
- **Speaker Script:**  
  "Despite the sophistication of CDCL, solvers face two chronic, interrelated search-control dilemmas:
  *First, The Restart Dilemma:* Gomes and Selman established that backtrack search runtimes follow heavy-tailed Pareto distributions. Restarting too frequently creates search thrashing, where the solver clears variable assignments before deep implications can be derived. Conversely, restarting too late traps the solver in massive, unsatisfiable subtrees for millions of futile conflicts.
  *Second, The Clause Bloat Dilemma:* Adding a learned nogood at every single conflict rapidly inflates clause databases past working memory capacity. Bloated databases degrade Two-Watched Literal traversal, collapsing BCP throughput by up to 300%. Yet deleting clauses too aggressively discards critical lemmas, forcing the solver to rediscover identical conflict subtrees."

---

## Slide 6: Literature Review: Four Foundational Pillars
- **Visual Overview:** Four research cards summarizing the foundational papers: Audemard & Simon (Glucose / LBD), Biere & Fröhlich (CaDiCaL), Liang et al. (MAB in SAT), and Tolpin & Shimony / Koriche et al. (Value of Information & Tournaments).
- **Speaker Script:**  
  "Our research builds upon four foundational pillars in combinatorial search literature:
  1. *Audemard & Simon (2009, 2012):* Introduced Glucose and the Literal Block Distance (LBD) metric, establishing that clauses with LBD <= 2 ('Glue clauses') are exceptionally powerful and must never be deleted.
  2. *Biere & Fröhlich (2018):* Introduced CaDiCaL, demonstrating the vital balance between inprocessing, chronological backtracking, and disciplined learned-clause garbage collection.
  3. *Liang, Cherif, and Li (2016, 2026):* Pioneered Multi-Armed Bandit learning for SAT branching heuristics, proving that reward signals must align with the temporal scale of search decisions.
  4. *Tolpin & Shimony (2011) and Koriche et al. (2022):* Formally modeled the computational Value of Information and adaptive tournaments to eliminate weak search policies early."

---

## Slide 7: Research Objectives & Technical Hypotheses
- **Visual Overview:** Research roadmap timeline across six evolutionary phases with explicit statements for RQ1, RQ2, and RQ3.
- **Speaker Script:**  
  "We translated our research questions into three concrete technical hypotheses:
  *RQ1 (Adaptive Restarting):* We hypothesized that tracking search progress as a quality-adjusted return and monitoring drawdown collapse (Dt >= 0.75 for 30 consecutive conflicts) would dynamically prune futile subtrees better than static Luby sequences.
  *RQ2 (Adaptive Retention):* We hypothesized that a composite multi-attribute scoring function combining LBD, variable activity, and clause size, integrated with Glucose's decoupled cadence (2000+300n), would eliminate clause bloat without suffering legacy reduction deferral bugs.
  *RQ3 (Online Portfolio Selection):* We hypothesized that an Exp3 / Discounted-UCB bandit could dynamically toggle between aggressive restarts and bounded descent."

---

## Slide 8: Glucose 4.2.1 Architecture & Research Implementation
- **Visual Overview:** Comprehensive architecture block diagram showing Core CDCL Engine (`Solver.cc`), Clause DB Management (`ReduceDB`), Search Control, Win32 Telemetry (`utils/System.cc`), and Simplification (`SimpSolver.cc`).
- **Speaker Script:**  
  "To conduct these experiments with industrial fidelity, we ported Glucose 4.2.1 directly to native Windows 64-bit C++. The implementation spans ~4,800 lines of modified C++ across `Solver.h` and `Solver.cc`. We engineered `utils/System.cc` using Win32 API calls (`QueryPerformanceCounter` and `GetProcessMemoryInfo`) for sub-millisecond telemetry. All executables were compiled under MinGW-w64 GCC 14.2.0 with `-O3 -std=c++11 -DNDEBUG`. We produced three cryptographically frozen binaries: `glucose-simp.exe` for baseline and V3, `glucose-qre-gated.exe` for risk-gated search, and `glucose-portfolio-mab.exe` supporting all project configurations."

---

## Slide 9: Baseline Algorithms in Glucose 4.2.1
- **Visual Overview:** Four-quadrant card overview of VSIDS variable branching, Two-Watched Literals, Glucose dynamic LBD restarts, and baseline ReduceDB clause deletion.
- **Speaker Script:**  
  "To ensure scientific rigor, all our novel controllers are benchmarked against unmodified Glucose 4.2.1 baselines:
  - *VSIDS:* Increments variable scores by 1.0 upon conflict involvement, decayed by 0.95 at every conflict step.
  - *2WL:* Maintains two watching pointers per clause, triggering checks only when a watched literal becomes false.
  - *Dynamic LBD Restarts:* Maintains a circular buffer of the last 50 LBD values; when the short-term moving average multiplied by 0.80 exceeds the global cumulative LBD average, an immediate restart is triggered.
  - *ReduceDB Baseline:* At scheduled intervals (2000, 2300, 2600...), permanently preserves LBD <= 2 glue clauses and purges the lowest 50% of remaining clauses based strictly on VSIDS activity."

---

## Slide 10: Adaptive Restart V1 and V2: Signal-Based Policies
- **Visual Overview:** Technical card breakdown of Adaptive V1 (Search Efficiency Ratio SW/S0) and Adaptive V2 (Anti-Starvation Ceiling and LBD Fallback).
- **Speaker Script:**  
  "Our initial adaptive attempts implemented signal-based monitoring:
  - *Adaptive V1:* We calculated a window efficiency ratio SW over a 50-conflict circular buffer: mean propagations divided by level standard deviation plus 1.0. A restart was triggered when SW fell below 60% of the global baseline S0. However, V1 suffered from an unexpected 'Starvation Trap': on certain structured formulas, SW remained permanently above threshold, allowing the solver to run for over 50,000 conflicts without restarting.
  - *Adaptive V2:* To fix this, we introduced an anti-starvation ceiling (`opt_v2_max_conflicts = 2500`) that unconditionally forces a restart, alongside an LBD quality fallback trigger. While V2 prevented search runaway, it was purely reactive and lacked knowledge of historic peak performance."

---

## Slide 11: V3 Maximum Drawdown: Concept & Financial Analogy
- **Visual Overview:** Complete V3 decision flowchart with Conflict Event, Return Calculation, Dual EWMAs, Decaying HWM, and Trigger Evaluation alongside the financial mapping card.
- **Speaker Script:**  
  "This motivated our flagship search-control policy: *V3 Maximum Drawdown*. In quantitative finance, Maximum Drawdown measures the peak-to-trough percentage decline of a portfolio. We mapped these market concepts directly into CDCL search state:
  - The portfolio asset return rt corresponds to propagation efficiency and backjump depth per conflict.
  - Short-term market movement corresponds to our Fast EWMA (alpha = 0.08, ~12 conflict memory).
  - Long-term market trend corresponds to our Slow EWMA (alpha = 0.01, ~100 conflict memory).
  - The asset's historic all-time high corresponds to our decaying High-Water Mark (HWM).
  - A stop-loss execution corresponds to a CDCL restart: when search efficiency collapses 75% below its recent peak for 30 consecutive conflicts, the solver cuts its search losses and restarts."

---

## Slide 12: V3 Mathematical Model & Verified Parameters
- **Visual Overview:** High-resolution dual-panel plot showing V3 Fast/Slow EWMA and decaying High-Water Mark (top) and relative Drawdown Dt with trigger line (bottom), beside verified formulas from `Solver.cc`.
- **Speaker Script:**  
  "Let us review the exact, verified mathematical model implemented in `Solver.cc`:
  1. *Quality-Adjusted Return:* $r_t = \frac{2.0}{\max(1, LBD)} \cdot \frac{1.0 + \ln(1.0 + \Delta D)}{1.0 + \Delta P / 25.0}$. Note that the C++ code uses a logarithmic backjump boost and a linear propagation cost.
  2. *Dual EWMAs:* Fast EWMA uses $\alpha_{fast} = 0.08$ (coefficient 0.92 / 0.08); Slow EWMA uses $\alpha_{slow} = 0.01$ (coefficient 0.99 / 0.01).
  3. *Decayed High-Water Mark:* $HWM_t = \max(0.999 \times HWM_{t-1}, EWMA_{fast, t})$, decaying by 0.1% per conflict to prevent stale peaks from locking the solver.
  4. *Relative Drawdown:* $D_t = \frac{HWM_t - EWMA_{fast, t}}{HWM_t + 0.05}$.
  5. *Trigger:* A restart is triggered when $D_t \ge 0.75$ persists for **30 consecutive conflicts**, with a 100-conflict warmup and 50-conflict cooldown."

---

## Slide 13: Learned-Clause Management & The Reduction Bug
- **Visual Overview:** Dual-panel timeline comparing the buggy clause database bloat (top) with the clean sawtooth cadence of Adaptive-Fixed retention (bottom).
- **Speaker Script:**  
  "A critical scientific breakthrough occurred during our inspection of clause database management. In early experiments (Steps 32–34), our adaptive clause reduction tripled runtimes on Pigeonhole (PHP) formulas. Profiling revealed an insidious reduction deferral defect: the legacy algorithm used an over-conservative LBD variance condition that continually executed `nbclausesbeforereduce += 1000`. The database never underwent reduction, bloating past 100,000 clauses and crippling BCP throughput! By diagnosing this bug, we established that clause reduction scheduling must be decoupled from instantaneous restart noise, leading to our Adaptive-Fixed architecture."

---

## Slide 14: Adaptive-Fixed Retention Architecture
- **Visual Overview:** Component score curves for $S_{LBD}$, $S_{act}$, and $S_{size}$ beside the composite scoring equation and protection classes.
- **Speaker Script:**  
  "Our *Adaptive-Fixed Retention* architecture pairs Glucose's decoupled cadence (`firstReduceDB = 2000`, `incReduceDB = 300`) with continuous multi-attribute clause utility scoring:
  $R(c) = 0.50 \cdot S_{LBD} + 0.40 \cdot S_{act} + 0.10 \cdot S_{size}$
  - *LBD Score (50% weight):* $S_{LBD} = \frac{1.0}{1.0 + 0.50 \max(0, LBD - 2)}$. LBD 2 receives 1.0; LBD 6 drops to 0.33.
  - *Activity Score (40% weight):* Square-root mapped normalized VSIDS activity gives fair credit to moderately active clauses.
  - *Size Score (10% weight):* Penalizes large clauses ($S_{size} = \frac{1.0}{1.0 + 0.05 \max(0, size - 2)}$).
  - *Strict Protection:* Binary clauses ($size \le 2$), Glue clauses ($LBD \le 2$), locked reason clauses, and immune clauses are never deleted.
  This architecture proved decisive, winning the 48-instance holdout suite."

---

## Slide 15: Quantitative Risk Engine (QRE)
- **Visual Overview:** Architectural gating diagram illustrating Signal 1 (Rolling Sharpe Ratio), Signal 2 (Non-parametric VaR95), the Conjunction requirement (8 consecutive conflicts), and the Stagnation Gating safeguards.
- **Speaker Script:**  
  "To handle sudden search turbulence, we designed the Quantitative Risk Engine (QRE) featuring two telemetry signals:
  1. *Rolling Sharpe Ratio:* $S_{branch} = \frac{SMA_{10}(R) - SMA_{50}(R)}{\max(0.75, \sigma_{D, 10})}$, where $R$ is propagations per decision and $\sigma_{D, 10}$ is depth volatility. A score below -0.35 alerts to negative search momentum.
  2. *Value-at-Risk ($VaR_{95}$):* Tracks conflict shock ($Shock_t = LBD_t / \max(1, \Delta decisions)$). Verified directly from `Solver.cc`: it uses a non-parametric nearest-rank maximum shock across a rolling 12-conflict window, alerting when $max \ge 3.2$ and $max \ge 1.6 \times median$.
  An emergency restart requires BOTH signals to be active for 8 consecutive conflicts."

---

## Slide 16: Stagnation-Gated QRE: Suppressing Restart Storms
- **Visual Overview:** Comparison cards showing the Active QRE pathology on random SAT vs the Stagnation-Gated stabilization mechanisms.
- **Speaker Script:**  
  "Scientific integrity demands presenting failure modes and how they were corrected. In our initial Active QRE implementation, uniform random 3-SAT instances (`rand3sat_n175_c735_s1003.cnf`) suffered a catastrophic **+192.6% conflict explosion**. In uniform random SAT, variable activity is homogeneous; local statistical fluctuations triggered false VaR alerts, setting off hyperactive restart storms that wiped the assignment trail before VSIDS could focus.
  To resolve this, we introduced *Stagnation-Gating*:
  - Expanded cooldown from 500 to **1,500 conflicts** since genuine restart.
  - Enforced a strict frequency budget: **maximum 2 QRE restarts per 10,000 conflicts**.
  This completely suppressed premature restart cascades while preserving emergency interventions on structured formulas."

---

## Slide 17: Portfolio-MAB: Duration-Aware Bandit Scheduler
- **Visual Overview:** Two-arm selection diagram showing Arm 0 (Native Glucose), Arm 1 (Bounded Descent up to 500 conflicts), the conflict-normalized reward formula, and pilot metrics.
- **Speaker Script:**  
  "In Step 44, we evaluated online meta-learning using an Exp3 / Discounted-UCB bandit ($\gamma = 0.95, c = 0.40$). The bandit toggled between Arm 0 (Native Glucose Luby restarts) and Arm 1 (Bounded Descent, postponing restarts up to 500 conflicts). The reward was conflict-normalized: $Reward = \text{clamp}\left(\frac{\Delta glue + 0.20 \Delta non\_glue}{\Delta c}, 0, 1\right)$.
  In a 16-instance pilot (240 runs), Portfolio-MAB achieved PAR-2 of 0.1243s vs 0.1390s for Glucose. However, on phase-transition instances, the bandit alternated erratically, increasing conflicts by +45.2%. Rather than hasty ad-hoc parameter retuning before our thesis deadline, we made a disciplined academic STOP decision, freezing V3 Drawdown and Adaptive-Fixed retention as our primary verified contributions."

---

## Slide 18: Experimental Setup & Rigorous Methodology
- **Visual Overview:** Dual-card summary comparing the Development Suite (36 benchmarks, 648 runs, 15s timeout) with the Quarantined Holdout Suite (48 benchmarks, 1,152 runs, 30s timeout, 0 timeouts).
- **Speaker Script:**  
  "Our experimental campaign was conducted under strict scientific protocols across two independent benchmark suites:
  - *Development Suite:* 36 expanded benchmarks across 3 repetitions and 6 configurations = 648 total runs with a 15.0s timeout (PAR-2 penalty = 30.0s). Used to evaluate and select algorithm candidates.
  - *Quarantined Holdout Suite:* 48 benchmarks across 3 repetitions and 8 configurations = 1,152 total runs with a 30.0s timeout (PAR-2 penalty = 60.0s). Quarantined under cryptographic SHA-256 manifests until algorithm code was frozen. All 1,152 runs solved without a single timeout. Notably, 67.0% of holdout runs finished in <= 0.05s, introducing high sensitivity to OS process scheduling noise."

---

## Slide 19: Development Results: V3 Drawdown Victory
- **Visual Overview:** Publication-quality bar chart showing PAR-2 scores across all 6 development configurations alongside the verified results summary table.
- **Speaker Script:**  
  "Here are the definitive results on the 36-instance development suite (648 runs):
  - **Winner:** *V3 Drawdown + Adaptive-Fixed* achieved the best overall performance, solving **102 out of 108 runs** with a PAR-2 score of **2.5381s** (compared to 2.7463s for native Glucose).
  - Crucially, V3 Drawdown reduced total solved conflicts by **15.5%** (3,538,449 vs 4,187,694 for Glucose), demonstrating that peak-drawdown tracking eliminates useless branching.
  - Active QRE scored PAR-2 3.1960s (100/108 solved), while Gated QRE scored 3.4716s (98/108 solved). This confirmed V3 Drawdown + Adaptive-Fixed as our strongest combined architecture."

---

## Slide 20: Holdout Results: Adaptive-Fixed Victory
- **Visual Overview:** Dual charts showing Holdout PAR-2 scores (top) and Total Conflicts (bottom) across all 8 configurations alongside the verified holdout table.
- **Speaker Script:**  
  "On the quarantined 48-instance holdout suite (1,152 runs, 0 timeouts):
  - **Winner:** *Native Glucose Restarts + Adaptive-Fixed Retention* achieved the lowest PAR-2 score (**0.1107s** vs 0.1208s for native Glucose) and the fewest total conflicts (**709,587** vs 778,158).
  - V3 Drawdown + Base Retention achieved PAR-2 0.1642s (946,539 conflicts).
  - Because 67% of holdout instances were easy (<0.05s), Glucose's rapid clearing was optimal, and Adaptive-Fixed retention provided an additional 8.8% conflict reduction by pruning non-essential lemmas."

---

## Slide 21: Deep-Dive Case Study: Towers of Hanoi Planning
- **Visual Overview:** Horizontal bar chart comparing mean wall-clock runtimes on `hanoi5.cnf` across 8 configurations with the verified per-run data card.
- **Speaker Script:**  
  "We conducted a deep-dive audit on `hanoi5.cnf` (HOLDOUT_14), a complex 5-disk planning problem. Across 24 verified runs:
  - Glucose + Adaptive-Fixed solved in **0.206s** (15.4k conflicts, 57 restarts).
  - Native Glucose solved in **0.289s** (17.2k conflicts, 58 restarts).
  - V3 Drawdown + Base solved in **3.064s** (81.3k conflicts, exactly 5 genuine restarts).
  - No-Heuristic baseline (`cfg04`) required **15.284s** (242.4k conflicts, 1 restart).
  *Authoritative Finding:* V3 Drawdown was **80.0% faster than the No-Heuristic control** with surgical 5 restarts. We explicitly clarify: V3 was NOT faster than Glucose on this benchmark, because Glucose's rapid LBD clearing was ideal for pruning planning dead ends."

---

## Slide 22: Comparative Factorial & Statistical Analysis
- **Visual Overview:** Two-card presentation covering the Factorial Interaction Matrix (Restart vs Retention) and the Wilcoxon Signed-Rank Test audit.
- **Speaker Script:**  
  "Our 2x4 factorial design decoupled restart scheduling from clause retention:
  - *Retention:* Adaptive-Fixed proved universally beneficial across all restart engines by eliminating the scheduling deferral bug.
  - *Restart Domain-Specificity:* V3 Drawdown excels on difficult, structured instances with sustained conflict bursts, whereas Glucose Luby excels on shallow, rapidly solvable instances.
  - *Statistical Significance:* Direct Wilcoxon signed-rank testing on holdout benchmark means yielded $W^+ = 780, W^- = 396, Z = 1.9693, p = 0.0489$. However, after applying Benjamini-Hochberg False Discovery Rate (FDR) correction across all configurations, the differences do NOT reach statistical significance ($q > 0.05$). We report this with scientific transparency: holdout differences are practically meaningful but statistically exploratory."

---

## Slide 23: Engineering Contributions & Model Verification
- **Visual Overview:** Four-card overview of Windows 64-bit Porting, 100% Mathematical Verification, Open Science Manifests, and Diagnostic Shadow Telemetry.
- **Speaker Script:**  
  "Beyond algorithmic design, our engineering deliverables include:
  1. *Windows 64-bit Port:* Clean compilation of Glucose 4.2.1 under MinGW-w64 GCC 14.2.0 with native Win32 performance counters.
  2. *100% Mathematical Verification:* Every satisfying assignment across 3,000+ runs was independently verified against raw DIMACS CNF clauses (`scripts/verify_satisfying_assignments.py`) with zero assertion failures.
  3. *Open Science:* Immutable SHA-256 manifests and frozen binaries guarantee complete reproducibility.
  4. *Diagnostic Shadow Mode:* Built `-v3-shadow`, `-qre-shadow`, and `-portfolio-shadow` modes, proving zero behavioral deviation during telemetry tracking."

---

## Slide 24: Research Limitations & Future Horizons
- **Visual Overview:** Balanced side-by-side presentation of Honest Scientific Boundaries and Future Research Horizons.
- **Speaker Script:**  
  "We identify clear scientific boundaries and future opportunities:
  *Limitations:* Our 84 benchmarks, while diverse, require scaling to SAT Competition industrial suites (thousands of instances). Dynamic statistical triggers showed variance noise on uniform random 3-SAT, and multi-core portfolio sharing remains unexamined.
  *Future Work:*
  1. Integrating Adaptive-Fixed scoring into a 3-tier learned clause memory (Core, Tier-2, Local).
  2. Phase-transition entropy sensing to automatically disable heuristic restarts on uniform random formulas.
  3. Multi-objective Bayesian co-optimization of restart thresholds and clause utility weights."

---

## Slide 25: Final Conclusion & Q&A
- **Visual Overview:** Executive closing card with six verified bullet accomplishments and professional Thank You / Open Discussion banner.
- **Speaker Script:**  
  "In conclusion:
  - We demonstrated that quantitative finance principles—Maximum Drawdown, Rolling Sharpe, and Value-at-Risk—can be successfully adapted to CDCL search control.
  - V3 Drawdown + Adaptive-Fixed won the development suite (PAR-2 2.5381s vs 2.7463s, cutting conflicts by 15.5%).
  - Glucose + Adaptive-Fixed won the holdout suite (PAR-2 0.1107s), successfully resolving the legacy clause deferral defect.
  - On complex planning, V3 Drawdown achieved an 80.0% speedup over the no-heuristic baseline with surgical restart precision.
  - All models and assignments were 100% verified under Windows 64-bit.
  Thank you for your time and guidance. We welcome your questions."

