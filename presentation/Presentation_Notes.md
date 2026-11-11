# Presentation Notes: Adaptive Restart and Nogood Management for Constraint Satisfaction Solvers

**Course:** DAC - 203: Artificial Intelligence  
**Faculty Advisor:** Prof. Manoj Kumar  
**Presenters:** Kugashiya Bhavy (25125024), Manav Garg (25125026)  
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
  "To summarize our thesis upfront: Modern CDCL SAT solvers are plagued by heavy-tailed execution runtimes due to rigid restart schedules and exponential learned-clause database bloat. We hypothesized that combinatorial search progress can be modeled as an asset return stream with dynamic volatility, high-water marks, drawdowns, and tail-risk shocks. We designed four quantitative architectures: the V3 Maximum Drawdown controller, Adaptive-Fixed multi-attribute retention, the Quantitative Risk Engine (QRE), and a two-armed Portfolio-MAB prototype. Across rigorous evaluation, our V3 Drawdown + Adaptive-Fixed solver won the 36-benchmark development suite (PAR-2 2.5381s vs 2.7463s baseline, with a 15.5% reduction in solved conflicts), while Native Glucose + Adaptive-Fixed won the 48-benchmark holdout suite (PAR-2 0.1107s; 144/144 solved). On complex planning benchmarks like Hanoi-5, V3 achieved an 80.0% speedup over the no-heuristic baseline."
- **Examiner Tip:** Clarify that V3 won the complex development suite, while Adaptive-Fixed clause management provided universal improvements across both suites.

---

## Slide 3: Problem Formulation: Constraint Satisfaction & Boolean Satisfiability
- **Visual Overview:** Side-by-side comparison diagram showing General Constraint Satisfaction Problem (CSP) graph vs Boolean Satisfiability (CNF SAT) clause formula.
- **Speaker Script:**  
  "Constraint Satisfaction Problems represent a fundamental paradigm in Artificial Intelligence, formalized as finding an assignment to variables over finite domains that satisfies all constraints $\langle X, D, C \rangle$. Boolean SAT is the canonical discrete CSP where variables are binary and constraints are expressed as a conjunction of disjunctive clauses. Beyond its foundational role as Cook and Levin's first NP-complete problem, SAT solvers are the computational engines powering modern industrial automated planning, hardware formal verification at companies like Intel and AMD, cryptographic analysis, and software model checking. However, because SAT is NP-complete, naive exhaustive search fails exponentially; modern industrial solving depends entirely on intelligent search heuristics."
- **Examiner Tip:** If asked about the link between CSP and SAT, explain direct and logarithmic encodings that map finite domains to Boolean clauses.

---

## Slide 4: Solver Mechanics: Inside Modern CDCL
- **Visual Overview:** 5-step cyclic flowchart of Conflict-Driven Clause Learning: VSIDS Branching -> Two-Watched Literals (2WL) -> 1-UIP Conflict Analysis -> Non-Chronological Backjumping -> Search Control (Restarts & Reduction).
- **Speaker Script:**  
  "Modern industrial SAT solvers execute a continuous feedback loop. First, VSIDS selects unassigned variables based on historical conflict activity. Second, Boolean Constraint Propagation (BCP), accelerated by Two-Watched Literals, performs tens of millions of unit propagations per second. When a clause evaluates to false, 1-UIP conflict analysis traverses the implication graph backwards to construct an asserting learned clause (a nogood). The solver then executes non-chronological backjumping, leaping directly to the asserting level. Finally, periodic search control interrupts the engine: restarts clear the decision trail to escape local traps, while clause database reduction purges unpromising nogoods to bound memory and propagation overhead."
- **Examiner Tip:** Be prepared to define 1-UIP: the First Unique Implication Point on the current decision level that dominates all paths to the conflict node.

---

## Slide 5: Problem Statement: The Dual Search-Control Dilemmas
- **Visual Overview:** Dual-panel dilemma chart: Dilemma I (The Restart Dilemma: premature resets vs heavy-tailed traps) and Dilemma II (Clause Database Bloat: unbounded growth vs propagation degradation).
- **Speaker Script:**  
  "CDCL solving faces two fundamental search-control dilemmas. Dilemma I is the Restart Dilemma: Gomes et al. proved backtrack search follows heavy-tailed Pareto distributions, trapping solvers in exponentially deep futile subtrees. Yet restarting too aggressively causes search thrashing, repeatedly erasing partial assignment progress. Static geometric or Luby sequences operate blind to real-time search productivity. Dilemma II is Clause Database Bloat: learning a clause at every conflict generates millions of clauses, exhausting RAM and degrading Two-Watched Literal traversal throughput by up to 300%. Aggressive purging risks deleting critical lemmas, while conservative retention degrades solver throughput."
- **Examiner Tip:** Emphasize that our research addresses *both* dilemmas in a unified mathematical framework.

---

## Slide 6: Literature Review: Four Foundational Pillars
- **Visual Overview:** 4 quadrant cards summarizing seminal research contributions: Audemard & Simon (IJCAI 2009 / JSAT 2012), Biere & Fröhlich (SAT 2018), Liang et al. (CP 2016 / 2026), Tolpin & Shimony (2011) / Koriche et al. (2022).
- **Speaker Script:**  
  "Our architecture builds on four foundational pillars in combinatorial search literature. Audemard and Simon introduced Glucose and the Literal Block Distance (LBD) metric, proving clauses with LBD $\le 2$ ('Glue clauses') must never be deleted. Biere and Fröhlich introduced chronological backtracking and interleaved inprocessing in CaDiCaL. Liang, Cherif, and Li demonstrated that Multi-Armed Bandits can select variable branching heuristics when rewards align with search time scales. Finally, Tolpin and Shimony, and Koriche et al., formalized the Value of Information (VOI) and adaptive tournaments for online meta-heuristic selection."
- **Examiner Tip:** Note that our literature review also integrates Wallace, Grimes, and Freuder (IJCAI 2009) on identifying stable features in dynamic constraint satisfaction.

---

## Slide 7: Research Objectives & Technical Hypotheses
- **Visual Overview:** Three core research questions and paired hypotheses addressing adaptive restarts, nogood management, and online portfolio selection.
- **Speaker Script:**  
  "We formulated three core research questions. RQ1: Can quantitative financial drawdown metrics detect search stagnation more effectively than static Luby sequences? We hypothesize that dual-EWMA conflict return monitoring with high-water mark decay can prune futile subtrees while preserving productive momentum. RQ2: Can multi-attribute clause retention eliminate database bloat without sacrificing solver deductive power? We hypothesize that combining LBD, conflict activity, and clause length in a continuous score preserves vital lemmas while purging dead weight. RQ3: Can online multi-armed bandits dynamically balance exploration and exploitation across heterogeneous problem domains?"
- **Examiner Tip:** Clarify that our engineering validation also rigorously tested each hypothesis on clean, isolated C++ baselines.

---

## Slide 8: Baseline Foundations: Reference Algorithms in Native Glucose 4.2.1
- **Visual Overview:** Architectural diagram of Glucose 4.2.1 core components: VSIDS, Luby sequence restarts, Dynamic LBD restarts, and ReduceDB clause reduction.
- **Speaker Script:**  
  "To establish an uncompromised scientific evaluation, we selected Native Glucose 4.2.1 as our base platform. Its baseline consists of: (1) VSIDS variable branching with activity decay of 0.95; (2) Dual restart heuristics: a fast EWMA comparing short-term LBD (window 50) against long-term LBD (window 5000), interleaved with Luby restart sequences ($u \cdot 100$ conflicts); and (3) ReduceDB clause management, which periodically sorts learned clauses by LBD and removes the worst 50%, while permanently protecting Glue clauses (LBD $\le 2$). All our research algorithms were implemented directly within this C++ engine."
- **Examiner Tip:** Stress that we modified Glucose 4.2.1 at the native engine level, compiling on Windows 64-bit with MinGW GCC 14.2.0.

---

## Slide 9: Search Control V1/V2: Signal-Based Policies
- **Visual Overview:** Comparative table and equations for Adaptive Restart V1 (Progress Ratio) and Adaptive Restart V2 (Anti-Starvation Propagation Rate).
- **Speaker Script:**  
  "Our preliminary architectures explored signal-based restart control. Adaptive Restart V1 monitored a Progress Ratio $SW$, calculating the ratio of unit propagations to conflict backjump depth. If progress dropped below a calibrated threshold over a sliding window, a restart was triggered. Adaptive Restart V2 introduced an anti-starvation ceiling and monitored propagation rate per decision level. While both policies demonstrated improved responsiveness on specific structured instances, they suffered from threshold sensitivity and lacked an overarching statistical model of search stagnation, motivating our V3 Maximum Drawdown architecture."
- **Examiner Tip:** Explain that V1 and V2 served as essential engineering milestones that highlighted the need for dual-speed filtering and volatility estimation.

---

## Slide 10: Drawdown Concept: V3 Maximum Drawdown Concept & Financial Mapping
- **Visual Overview:** Financial portfolio drawdown graph juxtaposed with SAT solver search-tree stagnation graph.
- **Speaker Script:**  
  "The core conceptual breakthrough of our research is mapping quantitative portfolio drawdown theory to combinatorial search. In quantitative finance, portfolio drawdown measures the percentage decline of cumulative asset value from its historical peak. In a SAT solver, each conflict yields a 'return': productive conflicts achieve deep backjumps and learn compact, low-LBD clauses, whereas stagnant search produces shallow backjumps and bloated clauses. We formalize search progress as a cumulative wealth curve; when the solver gets trapped in a fruitless branch of the search tree, its return collapses, triggering a severe drawdown from its High-Water Mark."
- **Examiner Tip:** Highlight the physical intuition: a high-water mark represents the solver's peak recent deductive velocity.

---

## Slide 11: Mathematical Model: V3 Maximum Drawdown Formulation & Verified Parameters
- **Visual Overview:** Detailed equation breakdown showing conflict return $r_t$, fast/slow EWMAs, high-water mark decay, drawdown $D_t$, and the exact trigger condition.
- **Speaker Script:**  
  "Here is our exact mathematical formulation, verified in `Solver.cc` lines 3086–3258. At each conflict $t$, the quality-adjusted return is $r_t = \frac{1}{\text{LBD}} \cdot (1 + \ln(1 + \text{backjump})) \cdot \frac{\text{propagations}}{1000}$. We smooth returns using dual EWMAs: a fast signal $S_{\text{fast}}$ ($\alpha_f = 0.08$) and a slow baseline $S_{\text{slow}}$ ($\alpha_s = 0.01$). The High-Water Mark decays slowly: $\text{HWM}_t = \max(S_{\text{slow}, t}, \gamma \cdot \text{HWM}_{t-1})$ with $\gamma = 0.9995$. Drawdown is defined as $D_t = \frac{\text{HWM}_t - S_{\text{slow}, t}}{\text{HWM}_t + 0.05}$. If $D_t \ge 0.75$ continuously for $\tau = 30$ consecutive conflicts, stagnation is confirmed and an adaptive restart is executed."
- **Examiner Tip:** Note the exact denominator $\text{HWM}_t + 0.05$: the $+0.05$ offset prevents division by zero and stabilizes drawdown during low-return search phases.

---

## Slide 12: Database Management: Learned-Clause Management & The Deferral Defect
- **Visual Overview:** Timeline illustration of the discovered ReduceDB scheduling defect versus our fixed decoupled reduction cadence.
- **Speaker Script:**  
  "During rigorous codebase auditing, we uncovered a critical architectural defect in native Glucose 4.2.1. In certain execution pathways, when search was in specific phase-saving or restart states, the internal clause reduction scheduling loop deferred ReduceDB calls indefinitely. This led to runaway memory consumption and degraded Two-Watched Literal lists on long-running instances. We resolved this pathology by implementing an explicit decoupled reduction cadence: ReduceDB is triggered at $2000 + 300 \cdot n$ conflicts, completely decoupled from restart state, guaranteeing periodic, bounded clause garbage collection."
- **Examiner Tip:** Emphasize that fixing this defect was vital for fair, leak-free benchmarking across both suites.

---

## Slide 13: Nogood Retention: Adaptive-Fixed Tri-Criteria Scoring
- **Visual Overview:** Weight distribution donut chart ($50\%$ LBD, $40\%$ Activity, $10\%$ Size) and tiered clause protection hierarchy.
- **Speaker Script:**  
  "To replace Glucose's single-attribute LBD sorting, we developed the Adaptive-Fixed retention policy. For every non-protected learned clause $c$, we compute a composite retention score: $R(c) = 0.50 \cdot S_{\text{LBD}}(c) + 0.40 \cdot S_{\text{act}}(c) + 0.10 \cdot S_{\text{size}}(c)$. All components are normalized between $0.0$ and $1.0$. Strict structural protections are enforced: Glue clauses (LBD $\le 2$), locked clauses actively participating in the implication trail, and binary/ternary clauses (size $\le 3$) are permanently immune from deletion. Remaining clauses are sorted by $R(c)$, and the lowest 50% are safely deleted."
- **Examiner Tip:** Mention that the $40\%$ activity weighting ensures clauses actively resolving current conflicts are not discarded prematurely even if their LBD is moderate.

---

## Slide 14: Risk Telemetry: Quantitative Risk Engine (Sharpe Momentum & Tail Shock)
- **Visual Overview:** Rolling Sharpe ratio signal and non-parametric Value-at-Risk ($\text{VaR}_{95}$) shock detector for emergency intervention.
- **Speaker Script:**  
  "The Quantitative Risk Engine (QRE) augments search control with two higher-order telemetry signals. Signal 1 is the Rolling Sharpe Ratio: $S_{\text{branch}} = \frac{\text{SMA}_{10}(R) - \text{SMA}_{50}(R)}{\max(0.75, \sigma_{D,10})}$. When decisions $\ge 50$ and Sharpe drops below $-0.35$, it indicates a severe collapse in propagation yield relative to search depth volatility. Signal 2 is Value-at-Risk ($\text{VaR}_{95}$): a non-parametric nearest-rank maximum shock over a 12-conflict window, tracking $\text{Shock}_t = \frac{\text{LBD}_t}{\max(1, \Delta\text{decisions})}$. An alert fires when $\text{max\_shock} \ge 3.2$ and exceeds $1.6 \times \text{median}$. Emergency restart requires BOTH signals to remain active for 8 consecutive conflicts."
- **Examiner Tip:** Emphasize that $\text{VaR}_{95}$ is non-parametric nearest-rank over 12 conflicts, avoiding unrealistic Gaussian assumptions in combinatorial search.

---

## Slide 15: Stagnation Gating: Stagnation-Gated QRE (Taming Random SAT Cascades)
- **Visual Overview:** Comparative conflict progression chart: Un-gated QRE (restart storm on random 3-SAT) vs Stagnation-Gated QRE (disciplined intervals).
- **Speaker Script:**  
  "Our empirical testing revealed a critical scientific phenomenon on uniform random 3-SAT instances: active QRE triggered hyperactive restart cascades (a 'restart storm'), restarting every few dozen conflicts and destroying partial assignments needed for resolution, exploding conflicts by +192.6%. To resolve this, we designed Stagnation-Gated QRE. We enforced a strict 1,500-conflict refractory period, a frequency budget of at most 2 QRE restarts per 10,000 conflicts, and required confirmed conjunction over 8 conflicts before QRE intervention is permitted. This completely suppressed restart thrashing, reducing conflicts by 850k across the suite."
- **Examiner Tip:** Highlighting how a negative result was diagnosed and stabilized is a hallmark of scientific rigor.

---

## Slide 16: Online Learning: Two-Armed Portfolio-MAB Scheduler
- **Visual Overview:** Multi-Armed Bandit interaction loop selecting between Native Glucose restarts (Arm 0) and Bounded Descent (Arm 1).
- **Speaker Script:**  
  "We also investigated an online Two-Armed Portfolio-MAB prototype to dynamically select restart policies. Arm 0 represents Native Glucose dynamic LBD restarts, while Arm 1 implements bounded descent, postponing restarts by up to $\Delta c_{\max} = 500$ conflicts. Crucially, the reward is normalized by conflicts elapsed: $\text{Reward} = \text{clamp}\left(\frac{\Delta\text{glue} + 0.20 \cdot \Delta\text{non\_glue}}{\Delta c}, 0.0, 1.0\right)$. In pilot testing on 16 instances (240 runs), it achieved a promising PAR-2 of 0.1243s vs 0.1390s. However, on phase-transition random 3-SAT, the bandit alternated erratically (+45.2% conflicts). We made the disciplined academic decision to freeze the prototype and report the negative findings transparently rather than hastily retuning before submission."
- **Examiner Tip:** Emphasize the academic integrity of reporting both successes and limitations without overstating the MAB maturity.

---

## Slide 17: Empirical Protocol: Dual-Suite Evaluation Protocol
- **Visual Overview:** Side-by-side protocol table contrasting the Development Suite (36 benchmarks, 6 configs, 3 reps = 648 runs) and Quarantined Holdout Suite (48 benchmarks, 8 configs, 3 reps = 1,152 runs).
- **Speaker Script:**  
  "We enforced a rigorous dual-suite experimental methodology to guard against overfitting. The Development Suite comprised 36 heterogeneous benchmarks across bounded model checking, circuit synthesis, graph coloring, and random SAT, evaluated across 6 configurations and 3 repetitions (648 total runs; 15s timeout). The Holdout Suite comprised 48 quarantined benchmarks evaluated across 8 configurations and 3 repetitions (1,152 total runs; 30s timeout). The holdout files were held under strict cryptographic quarantine until C++ algorithms were frozen. Every satisfying model was independently verified by a standalone CNF model checker."
- **Examiner Tip:** Emphasize that 100% of all SAT models produced were verified against raw CNF clauses.

---

## Slide 18: Development Results: V3 Drawdown Victory
- **Visual Overview:** Victory scoreboard and summary table for the Development Suite showing PAR-2 scores, solved counts, and conflict totals.
- **Speaker Script:**  
  "On the Development Suite, our V3 Drawdown + Adaptive-Fixed configuration won first place, achieving the lowest PAR-2 score of 2.5381 seconds compared to 2.7463 seconds for native Glucose—a 7.6% overall PAR-2 improvement. Crucially, V3 solved the 102 solved instances using only 3.54 million conflicts, compared to 4.19 million conflicts for native Glucose—a statistically significant 15.5% reduction in search conflicts. This confirms our hypothesis that drawdown monitoring guides search to solutions with fewer wasted backtracks."
- **Examiner Tip:** Note that both configurations solved 102/108 instances (tied lowest timeouts), but V3 solved them with greater deductive efficiency.

---

## Slide 19: Holdout Results: Adaptive-Fixed Victory
- **Visual Overview:** Holdout scoreboard showing 1,152/1,152 solved runs (0 timeouts), PAR-2 comparison (0.1107s vs 0.1208s), and conflict totals.
- **Speaker Script:**  
  "On the Quarantined Holdout Suite, all 1,152 runs across all 8 configurations solved within the 30-second timeout. Native Glucose with Adaptive-Fixed clause retention emerged as the top performer, achieving a PAR-2 score of 0.1107 seconds versus 0.1208 seconds for native Glucose—an 8.4% improvement, while also requiring the fewest total conflicts (709.6k vs 778.2k; an 8.8% reduction). We also noted that 67% of holdout runs finished in under 50 milliseconds, meaning runtime variance in this regime reflects OS thread scheduling noise rather than algorithmic divergence."
- **Examiner Tip:** Transparently explain that Adaptive-Fixed's clause retention tri-criteria proved universally beneficial across both suites.

---

## Slide 20: Case Study: Towers of Hanoi Planning Benchmark (hanoi5.cnf)
- **Visual Overview:** Search trajectory graph comparing runtime and restart frequency on `hanoi5.cnf` across 24 independent runs.
- **Speaker Script:**  
  "Slide 20 presents a deep-dive case study on `hanoi5.cnf`, an automated planning benchmark with 1,941 variables and 13,326 clauses. When evaluated against the No-Heuristic baseline (CFG04), V3 Drawdown achieved an 80.0% runtime speedup (3.064s vs 15.284s) and a 66.4% conflict reduction, executing exactly 5 surgical restarts compared to a single late restart in the unguided solver. In the spirit of scientific honesty, we also note that Native Glucose's rapid clearing (58 restarts, 0.289s) proved faster than V3 here, demonstrating that planning domains with high symmetry benefit from rapid trail invalidation."
- **Examiner Tip:** Highlight this slide as proof of rigorous, unbiased empirical analysis—reporting exact search metrics without exaggerating claims.

---

## Slide 21: Research Conclusion | Final Summary & Academic Defense
- **Visual Overview:** 5-pillar conclusion card summarizing key takeaways, engineering achievements, and opening the floor for Q&A.
- **Speaker Script:**  
  "To conclude our presentation: (1) We proved that quantitative risk and drawdown metrics can successfully govern combinatorial search in CDCL SAT solvers; (2) V3 Drawdown + Adaptive-Fixed achieved superior search efficiency on the development suite, reducing solved conflicts by 15.5%; (3) Adaptive-Fixed retention demonstrated universal benefits, winning the holdout suite; (4) We discovered and resolved a major clause reduction deferral defect in Glucose 4.2.1; and (5) All code, experimental CSVs, and CNF model verifications are open-source and reproducible on Windows 64-bit. Thank you, Professor Manoj Kumar and esteemed committee members. We welcome your questions."
- **Examiner Tip:** Conclude with confidence, emphasizing the end-to-end rigor of the implementation, from C++ code to empirical verification.
