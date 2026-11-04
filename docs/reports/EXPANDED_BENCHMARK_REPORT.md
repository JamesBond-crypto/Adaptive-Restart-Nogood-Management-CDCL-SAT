# Expanded SAT Benchmark Suite: Baseline Characterization Report (Phase D, Part 1)

**Date**: October 30, 2026  
**Environment**: Windows 11 x64, MinGW-w64 GCC 14.2.0, Python 3.13  
**Solver**: Glucose 4.2.1 Windows Port (`src/glucose_windows/glucose-simp.exe`)  
**Baseline Mode**: `-restart-strategy=baseline -reduce-strategy=baseline`  
**External Timeout Limit**: 15.00 seconds per instance  
**Artifact Directory**: `benchmarks/expanded/`  
**Manifest Path**: `benchmarks/expanded_manifest.csv`  
**Characterization Results**: `experiments/results/expanded_baseline_characterization.csv`  

---

## 1. Executive Summary

This report documents the design, deterministic generation, mathematical validation, and baseline empirical characterization of an expanded 36-instance SAT benchmark suite. The suite is constructed to overcome the limitations of small smoke/pilot tests by providing substantial search workloads that actively exercise CDCL conflict analysis, genuine restart mechanisms, and multi-attribute learned-clause database reductions.

### Peak Characterization Highlights:
- **Total Instances Evaluated**: 36
- **Solved Instances**: 33 (91.7%) — 21 SAT (all independently verified) and 12 UNSAT
- **Timeout Instances (15.0s cutoff)**: 3 (8.3%) — zero crashes, zero memory faults, zero verification failures
- **Errors / Correctness Anomalies**: 0 (100% clean termination)
- **Maximum Conflicts Observed**: **438,461** (`php_10p_9h.cnf`)
- **Maximum Genuine Restarts**: **933** (`php_10p_9h.cnf`)
- **Maximum Clause Reductions (`nb ReduceDB`)**: **177** (`php_10p_9h.cnf`)
- **Maximum Learned Clauses Removed**: **388,747** (`php_10p_9h.cnf`)
- **Difficulty Classification**:
  - **Too Easy** (minimal search, <100 conflicts): 10 instances (27.8%)
  - **Moderate** (meaningful search, 100–5,000 conflicts): 8 instances (22.2%)
  - **Challenging** (repeated restarts / reductions, $\ge 5,000$ conflicts): 15 instances (41.7%)
  - **Timeout** ($\ge 15.0\text{s}$ ceiling): 3 instances (8.3%)

---

## 2. Benchmark Families and Instance Counts

The expanded benchmark suite consists of 36 distinct CNF instances structured across four problem families. No instance overlaps with or modifies any of the 20 pilot benchmarks in `benchmarks/pilot/`.

| Family | Instance Count | Variable Range ($N$) | Clause Range ($M$) | Expected Status Distribution |
| :--- | :---: | :---: | :---: | :--- |
| **Family A: Random 3-SAT** | 10 | 150 – 250 | 639 – 1,065 | Unknown ground truth (uniform sampling near phase transition $m/n \approx 4.20\text{–}4.30$) |
| **Family B: Planted Satisfiable 3-SAT** | 10 | 160 – 260 | 682 – 1,108 | 10 SAT (mathematically guaranteed via planted assignment) |
| **Family C: Pigeonhole Principle (PHP)** | 4 | 63 – 110 | 261 – 561 | 4 UNSAT (mathematically guaranteed via Dirichlet's box principle) |
| **Family D: Graph Coloring ($K$-Coloring)** | 12 | 33 – 160 | 104 – 1,398 | 6 SAT (planted partition) + 6 UNSAT (chromatic lower bounds) |
| **Total** | **36** | **33 – 260** | **104 – 1,398** | **16 Known SAT, 10 Known UNSAT, 10 Unknown** |

---

## 3. Generation Method and Reproducibility

Benchmark generation is implemented in [`benchmarks/generate_expanded.py`](file:///d:/DAC_203@Project/benchmarks/generate_expanded.py) using deterministic pseudo-random seeds and exact mathematical constructions.

### Family A: Uniform Random 3-SAT
- **Generation Mechanism**: Variables $V = \{1, \dots, N\}$. Clauses are formed by uniformly sampling 3 distinct variables without replacement, with independent Bernoulli($p=0.5$) boolean polarities.
- **Ratios**: Clause-to-variable ratios vary slightly around the canonical phase transition threshold ($\alpha \approx 4.20, 4.25, 4.26, 4.30$) across sizes $N \in \{150, 175, 200, 215, 225, 235, 250\}$.
- **Determinism**: Seeded explicitly using seeds `1001` through `1010`. No tautological literals or duplicate clauses are permitted.

### Family B: Planted Satisfiable 3-SAT
- **Generation Mechanism**: First, a global ground-truth truth assignment $\sigma \in \{0, 1\}^N$ is sampled uniformly at random.
- **Filtering**: Candidate 3-literal clauses are randomly generated; a clause is retained if and only if at least one literal is satisfied under $\sigma$.
- **Determinism**: Seeded explicitly using seeds `2001` through `2010` across sizes $N \in \{160, 180, 200, 220, 240, 260\}$.

### Family C: Pigeonhole Principle (PHP)
- **Construction**: Encodes Dirichlet's principle mapping $P$ pigeons into $H$ holes ($P > H$).
- **Variables**: $x_{i, j} = 1$ iff pigeon $i \in \{1, \dots, P\}$ occupies hole $j \in \{1, \dots, H\}$. Total variables: $P \times H$.
- **Clauses**:
  1. Pigeon assignment ($\ge 1$ hole per pigeon): $\bigvee_{j=1}^H x_{i, j}$ for each $i \in \{1, \dots, P\}$ ($P$ clauses of size $H$).
  2. Hole exclusivity ($\le 1$ pigeon per hole): $(\neg x_{i_1, j} \lor \neg x_{i_2, j})$ for each hole $j$ and pairs $1 \le i_1 < i_2 \le P$ ($H \times \binom{P}{2}$ binary clauses).
- **Instances**: PHP(9,7), PHP(10,8), PHP(10,9), and PHP(11,10).

### Family D: Graph Coloring ($K$-Coloring)
- **CNF Encoding**: Given undirected graph $G = (V, E)$ with $N$ vertices and $K$ colors:
  1. **At-Least-One (ALO)**: $\bigvee_{c=1}^K x_{v, c}$ for each $v \in V$ ($N$ clauses of size $K$).
  2. **At-Most-One (AMO)**: $(\neg x_{v, c_1} \lor \neg x_{v, c_2})$ for each $v \in V, 1 \le c_1 < c_2 \le K$ ($N \binom{K}{2}$ binary clauses).
  3. **Edge Conflict**: $(\neg x_{u, c} \lor \neg x_{v, c})$ for each $\{u, v\} \in E, c \in \{1, \dots, K\}$ ($|E| \times K$ binary clauses).
- **Subfamily D1 (SAT)**: Vertices partitioned into $K$ balanced subsets $S_1, \dots, S_K$. Edges sampled strictly between different color partitions ($u \in S_i, v \in S_j, i \ne j$). By construction, assigning color $c$ to vertex $v \in S_c$ satisfies all ALO, AMO, and edge clauses.
- **Subfamily D2 (UNSAT)**:
  1. *Complete graphs $K_n$ with $K = n - 1$ colors* ($K_8, K_9, K_{10}, K_{11}$): By definition $\chi(K_n) = n > n - 1$.
  2. *Grötzsch graph with $K = 3$ colors*: The Mycielskian of $C_5$, known to be triangle-free with $\chi(G) = \chi(C_5) + 1 = 4 > 3$.
  3. *Clique-augmented graph with $K = 5$ colors*: A 30-vertex random graph containing an embedded $K_6$ clique; since $\chi(G) \ge \omega(G) \ge 6 > 5$, 5-coloring is mathematically impossible.

---

## 4. SAT/UNSAT Ground-Truth Policy

To prevent unsound experimental assumptions, ground-truth labels follow strict epistemological boundaries:

1. **Planted Satisfiable Benchmarks (Planted 3-SAT & Graph Coloring SAT)**:
   - Expected status: `SAT`.
   - Certified at generation time by evaluating the exact planted model against the CNF file using independent verifier [`experiments/verify_model.py`](file:///d:/DAC_203@Project/experiments/verify_model.py).
   - In all 16 cases, verification passed unconditionally.

2. **Mathematically Justified Unsatisfiable Benchmarks (PHP & Graph Coloring UNSAT)**:
   - Expected status: `UNSAT`.
   - Certified by combinatorial graph theory and Dirichlet's theorem:
     - Pigeonhole principle: $P > H$ entails non-existence of injective functions $[P] \to [H]$.
     - Complete graph cliques: $\chi(K_n) = n$, so $K_{n-1}$ coloring is impossible.
     - Mycielski theorem: $\chi(M(G)) = \chi(G) + 1$, guaranteeing $\chi(\text{Grötzsch}) = 4 > 3$.
     - Clique embedding: $\chi(G) \ge \omega(G) = 6 > 5$.

3. **Random 3-SAT Benchmarks**:
   - Expected status: `UNKNOWN`.
   - Never assigned an a priori status label.
   - Solved status is reported empirically only when certified: SAT models must pass independent evaluation; UNSAT results require conflict refutation proofs.

---

## 5. Manifest and Structural Validation Results

Automated validator [`benchmarks/validate_expanded.py`](file:///d:/DAC_203@Project/benchmarks/validate_expanded.py) performed a full-coverage audit of all 36 instances:

- **Instance Count**: 36 unique files declared and present.
- **No Overlap with Pilot**: Exactly 0 filenames or hashes shared with the 20 pilot instances in `benchmarks/pilot/`.
- **SHA-256 Hash Integrity**: Every file hash matches the manifest entry bit-for-bit.
- **DIMACS Format Compliance**:
  - Problem header `p cnf <vars> <clauses>` matches actual variable and clause counts in 100% of files.
  - Zero out-of-range literals (all literals satisfy $1 \le |L| \le N_{\text{declared}}$).
  - 100% of clause lines end with the standard `0` delimiter.
  - Exactly 0 duplicate clauses within any single formula.
- **Ground-Truth Cross-Check**:
  - 16 SAT instances: Planted models validated successfully against CNF clauses.
  - 10 UNSAT instances: Constructive proofs mathematically verified.
  - 10 UNKNOWN instances: Uniform random generation verified.

---

## 6. Baseline Solved, Timeout, and Error Counts

All 36 instances were executed using Glucose 4.2.1 under `-restart-strategy=baseline -reduce-strategy=baseline` with an external timeout of 15.0 seconds.

| Metric | Count | Percentage |
| :--- | :---: | :---: |
| **Total Instances Evaluated** | 36 | 100.0% |
| **Solved SAT** | 21 | 58.3% |
| **Solved UNSAT** | 12 | 33.3% |
| **Total Solved** | **33** | **91.7%** |
| **Timed Out ($\ge 15.0\text{s}$)** | 3 | 8.3% |
| **Crashes / Errors / Signal Aborts** | 0 | 0.0% |
| **SAT Model Verification Rate** | 21 / 21 | **100.0%** |

### Ground-Truth Conformance:
- **Planted 3-SAT**: 10/10 solved SAT (100% match with known ground truth).
- **Graph Coloring SAT**: 6/6 solved SAT (100% match with known ground truth).
- **Pigeonhole Principle**: 3/4 solved UNSAT; 1/4 timed out (`php_11p_10h.cnf`). Zero false SAT reported.
- **Graph Coloring UNSAT**: 4/6 solved UNSAT; 2/6 timed out (`gcol_unsat_k10_c9.cnf`, `gcol_unsat_k11_c10.cnf`). Zero false SAT reported.
- **Random 3-SAT**: 5 SAT, 5 UNSAT, 0 timeouts. All 5 SAT models verified by `verify_model.py`. This empirical 50/50 split cleanly reflects phase-transition behavior.

---

## 7. Search Statistics by Benchmark Family

The table below summarizes the search telemetry captured by the automated runner across all four benchmark families under baseline Glucose execution:

| Family | Instances | Solved (SAT / UNSAT) | Timeouts | Mean Conflicts | Max Conflicts | Mean Restarts | Max Restarts | Mean Reductions | Max Reductions | Total Wall Time (s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Random 3-SAT** | 10 | 5 SAT / 5 UNSAT | 0 | 27,682.6 | 114,109 | 4.0 | 30 | 3.9 | 15 | 7.289 |
| **Planted 3-SAT** | 10 | 10 SAT / 0 UNSAT | 0 | 2,313.4 | 11,256 | 0.3 | 2 | 0.4 | 2 | 0.543 |
| **Pigeonhole Principle** | 4 | 0 SAT / 3 UNSAT | 1 | 168,675.0 | 438,461 | 371.3 | 933 | 61.7 | 177 | 23.409 |
| **Graph Coloring** | 12 | 6 SAT / 4 UNSAT | 2 | 6,160.8 | 55,154 | 19.7 | 188 | 0.7 | 6 | 31.943 |
| **Total / Global** | **36** | **21 SAT / 12 UNSAT** | **3** | **31,733.8** | **438,461** | **52.2** | **933** | **9.1** | **177** | **63.184** |

### Key Observations:
1. **Pigeonhole Principle is Heavily CDCL-Intensive**: PHP formulas generated massive numbers of conflicts and triggered heavy restart and clause-reduction activity. `php_10p_9h.cnf` required 438,461 conflicts, 933 genuine restarts, and 177 database reductions (removing 388,747 clauses).
2. **Random 3-SAT Provides Consistent Search Workloads**: Across $N=150$ to $N=250$, conflicts scaled from 367 up to 114,109, with an average of 27,682 conflicts and 3.9 clause reductions per instance.
3. **Graph Coloring Demonstrates Bimodal Complexity**: The planted SAT instances solve rapidly (<0.15s) because unit propagation quickly identifies valid partition assignments. In contrast, the UNSAT complete graphs scale factorially: $K_8$ solves in 0.08s, $K_9$ solves in 1.23s (55,154 conflicts, 188 restarts), while $K_{10}$ and $K_{11}$ cleanly hit the 15-second timeout boundary.
4. **Planted 3-SAT Validates Fast Solvability with Occasional Hard Clusters**: Most planted instances solve under 0.05s, but instances with $N=200$ and $N=240$ generated 11,256 and 5,611 conflicts respectively.

---

## 8. Most Demanding Instances

The table below lists the 10 most demanding instances by wall-clock runtime:

| Rank | Benchmark Instance | Family | Status | Wall Time (s) | Conflicts | Genuine Restarts | Reductions (`nb ReduceDB`) | Clauses Removed |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `gcol_unsat_k10_c9.cnf` | Graph Coloring | **TIMEOUT** | 15.041 | — | — | — | — |
| 2 | `php_11p_10h.cnf` | Pigeonhole Principle | **TIMEOUT** | 15.025 | — | — | — | — |
| 3 | `gcol_unsat_k11_c10.cnf` | Graph Coloring | **TIMEOUT** | 15.023 | — | — | — | — |
| 4 | `php_10p_9h.cnf` | Pigeonhole Principle | UNSAT | 6.516 | 438,461 | 933 | 177 | 388,747 |
| 5 | `rand3sat_n250_c1065_s1010.cnf` | Random 3-SAT | SAT | 4.119 | 114,109 | 30 | 15 | 82,542 |
| 6 | `php_10p_8h.cnf` | Pigeonhole Principle | UNSAT | 1.778 | 60,580 | 166 | 6 | 36,991 |
| 7 | `gcol_unsat_k9_c8.cnf` | Graph Coloring | UNSAT | 1.226 | 55,154 | 188 | 6 | 37,387 |
| 8 | `rand3sat_n235_c999_s1009.cnf` | Random 3-SAT | SAT | 0.693 | 33,846 | 0 | 4 | 14,028 |
| 9 | `rand3sat_n225_c958_s1008.cnf` | Random 3-SAT | SAT | 0.632 | 26,501 | 2 | 4 | 13,873 |
| 10 | `rand3sat_n215_c915_s1007.cnf` | Random 3-SAT | UNSAT | 0.560 | 28,867 | 2 | 4 | 15,317 |

---

## 9. Instance Difficulty Classification

Following the experimental design protocol, all 36 instances were classified based on baseline search activity:

```
Difficulty Breakdown:
├── Too Easy (27.8%, 10 instances): < 100 conflicts, 0 restarts, 0 reductions
├── Moderate (22.2%, 8 instances): 100 - 5,000 conflicts, limited restarts/reductions
├── Challenging (41.7%, 15 instances): >= 5,000 conflicts OR >= 2 restarts/reductions
└── Timeout (8.3%, 3 instances): >= 15.0s evaluation limit
```

### Detailed Distribution by Category:
- **Too Easy (10 instances)**:
  - 6 Graph Coloring SAT: `gcol_sat_n30_k3_m90_s3001.cnf`, `gcol_sat_n35_k3_m115_s3002.cnf`, `gcol_sat_n40_k3_m140_s3003.cnf`, `gcol_sat_n40_k4_m180_s3006.cnf`, `gcol_sat_n45_k3_m165_s3004.cnf`, `gcol_sat_n50_k3_m190_s3005.cnf`
  - 1 Graph Coloring UNSAT: `gcol_unsat_grotzsch_k3.cnf` (24 conflicts)
  - 3 Planted 3-SAT: `planted3sat_n160_c688_s2002.cnf`, `planted3sat_n180_c756_s2003.cnf`, `planted3sat_n180_c767_s2004.cnf`
- **Moderate (8 instances)**:
  - 1 Graph Coloring UNSAT: `gcol_unsat_clique_embed_n30_k5_s3101.cnf` (306 conflicts)
  - 5 Planted 3-SAT: `planted3sat_n160_c682_s2001.cnf` (456 conflicts), `planted3sat_n200_c860_s2006.cnf` (345 conflicts), `planted3sat_n220_c937_s2007.cnf` (3,053 conflicts), `planted3sat_n220_c946_s2008.cnf` (1,284 conflicts), `planted3sat_n260_c1108_s2010.cnf` (957 conflicts)
  - 2 Random 3-SAT: `rand3sat_n150_c645_s1002.cnf` (367 conflicts), `rand3sat_n175_c735_s1003.cnf` (3,916 conflicts)
- **Challenging (15 instances)**:
  - 8 Random 3-SAT: `rand3sat_n150_c639_s1001.cnf` (5,637 cfc), `rand3sat_n175_c745_s1004.cnf` (15,550 cfc), `rand3sat_n200_c840_s1005.cnf` (25,375 cfc), `rand3sat_n200_c852_s1006.cnf` (22,658 cfc), `rand3sat_n215_c915_s1007.cnf` (28,867 cfc), `rand3sat_n225_c958_s1008.cnf` (26,501 cfc), `rand3sat_n235_c999_s1009.cnf` (33,846 cfc), `rand3sat_n250_c1065_s1010.cnf` (114,109 cfc)
  - 2 Planted 3-SAT: `planted3sat_n200_c852_s2005.cnf` (11,256 cfc), `planted3sat_n240_c1022_s2009.cnf` (5,611 cfc)
  - 3 Pigeonhole Principle: `php_9p_7h.cnf` (6,984 cfc), `php_10p_8h.cnf` (60,580 cfc), `php_10p_9h.cnf` (438,461 cfc)
  - 2 Graph Coloring UNSAT: `gcol_unsat_k8_c7.cnf` (6,105 cfc), `gcol_unsat_k9_c8.cnf` (55,154 cfc)
- **Timeout (3 instances)**:
  - `gcol_unsat_k10_c9.cnf`, `gcol_unsat_k11_c10.cnf`, `php_11p_10h.cnf`

---

## 10. Correctness and Diagnostic Verification

Throughout the entire expanded characterization run:
1. **Zero Solver Crashes**: Glucose 4.2.1 executed without segmentation faults, assertion failures, or unhandled exceptions under Windows 11.
2. **Zero Contradictions of Known Labels**: No known SAT instance was declared UNSAT, and no known UNSAT instance was declared SAT.
3. **100% Model Verification**: Every SAT outcome (21 instances) had its variable assignment parsed and validated by `verify_model.py`. In every case, 100% of the clauses were satisfied.
4. **Clean Timeout Recovery**: All 3 timed-out processes were terminated cleanly by the external Python harness without orphaned background tasks or log truncation.

---

## 11. Known Limitations of Synthetic Benchmarks

While this expanded suite provides rigorous stress-testing for restart frequency and learned-clause retention, synthetic benchmarks have known limitations:
- **Absence of Real-World Industrial Structure**: Synthetic random formulas lack the modular community structure, nested horn clauses, and variable backbones characteristic of bounded model checking, cryptographic circuit equivalence, or software verification instances.
- **Extreme Exponential Scaling of PHP**: Resolution-based CDCL solvers have proven exponential worst-case lower bounds on PHP ($2^{\Omega(n)}$). While excellent for stressing restart and reduction engines, they do not represent typical SAT solver use cases where backdoors or short refutations exist.
- **Triviality of Low-Density Planted Partitions**: Planted graph colorings with moderate edge densities are readily solved by unit propagation. In future work, harder graph coloring instances can be generated near the chromatic threshold where local minima and symmetry traps proliferate.

---

## 12. Recommendation for the Next Four-Configuration Evaluation (Phase D, Part 2)

Based on the baseline characterization results:

1. **Suite Readiness**: The 36 instances provide a well-balanced experimental testbed:
   - 10 instances serve as low-overhead smoke checks ("Too Easy").
   - 8 instances measure moderate search improvement ("Moderate").
   - 15 instances directly evaluate adaptive restart triggers and multi-attribute clause retention under heavy conflict loads ("Challenging").
   - 3 instances provide strict timeout challenge problems to determine if adaptive configurations can achieve superior par-2 scores or complete proofs within the 15-second cutoff.
2. **Recommended Timeout**: A timeout of **15.0 seconds** remains optimal. It bounds the total four-configuration experiment (4 configurations $\times$ 36 instances = 144 runs) to approximately 4–6 minutes while giving challenging instances adequate time to perform multiple restarts and clause reductions.
3. **Target Configurations**:
   - `C1`: Baseline Restart + Baseline Reduction (`-restart-strategy=baseline -reduce-strategy=baseline`)
   - `C2`: Adaptive Restart + Baseline Reduction (`-restart-strategy=adaptive -reduce-strategy=baseline`)
   - `C3`: Baseline Restart + Adaptive Reduction (`-restart-strategy=baseline -reduce-strategy=adaptive`)
   - `C4`: Adaptive Restart + Adaptive Reduction (`-restart-strategy=adaptive -reduce-strategy=adaptive`)

The expanded benchmark suite is fully validated and ready for full four-configuration comparative analysis.

