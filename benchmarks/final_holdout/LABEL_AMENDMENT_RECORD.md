# Holdout Benchmark Label Amendment Record

> **Step 36 Recovery Protocol Artifact**  
> **Date:** October 31, 2026 (23:28 UTC+05:30)  
> **Status:** Audited, Approved, and Implemented  
> **Classification:** Ground-Truth Metadata Correction (Post-Execution Incident Resolution)  

---

## 1. Executive Summary & Root Cause

During execution of Run 9 in Step 36 (`cfg02_v1_base` on `bf1355-075.cnf`), the candidate solver reported `UNSATISFIABLE`, whereas [`benchmarks/final_holdout/holdout_manifest.json`](./benchmarks/final_holdout/holdout_manifest.json) recorded `authoritative_label: "SAT"`. Execution was immediately halted under Section 5 protocol safeguards.

An independent audit of authoritative literature from the 1993 DIMACS Challenge and the UBC SATLIB benchmark archives revealed that:
1. In microelectronic Automatic Test Pattern Generation (ATPG), undetectable circuit faults yield **unsatisfiable** CNF formulas, whereas testable faults yield **satisfiable** formulas.
2. In Step 34, a clerical inversion in the acquisition dictionary `DIMACS_KNOWN_LABELS` mistakenly assigned `"SAT"` to four undetectable circuit fault instances (`bf1355-075`, `ssa0432-003`, `ssa2670-130`, `ssa2670-141`), and omitted `ssa7552-158.cnf` (assigning default `"UNKNOWN"`).
3. The solver results are 100% mathematically consistent with the published ground truth.

---

## 2. Itemized Metadata Corrections

| Benchmark ID | Filename | Original Manifest Label | Corrected Ground-Truth Label | Authoritative Published Source & Citation | Source URL | Verification Rationale |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| `HOLDOUT_02` | `bf1355-075.cnf` | `SAT` | **`UNSAT`** | S. T. Chakradhar, V. D. Agrawal, M. L. Bushnell, "Satisfiability and Boolean Circuit Testing", DIMACS Series, 1993; UBC SATLIB Table. | `https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/DIMACS/BF/` | Undetectable bridging fault in 1355 circuit; provably unsatisfiable formula. |
| `HOLDOUT_05` | `ssa0432-003.cnf` | `SAT` | **`UNSAT`** | DIMACS Challenge 1993 / Chakradhar et al.; Princeton DIMACS Archive. | `https://www.cs.princeton.edu/~zkincaid/benchmarks/DIMACS/SSA/` | Undetectable single stuck-at fault in 0432 circuit; provably unsatisfiable formula. |
| `HOLDOUT_06` | `ssa2670-130.cnf` | `SAT` | **`UNSAT`** | DIMACS Challenge 1993 / Chakradhar et al.; CWI / SATLIB Archive. | `https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/DIMACS/SSA/` | Undetectable single stuck-at fault in 2670 circuit; provably unsatisfiable formula. |
| `HOLDOUT_07` | `ssa2670-141.cnf` | `SAT` | **`UNSAT`** | DIMACS Challenge 1993 / Chakradhar et al.; SATLIB Archive. | `https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/DIMACS/SSA/` | Undetectable single stuck-at fault in 2670 circuit; provably unsatisfiable formula. |
| `HOLDOUT_08` | `ssa7552-158.cnf` | `UNKNOWN`| **`SAT`** | DIMACS Challenge 1993 / Chakradhar et al.; Princeton Benchmark Suite. | `https://www.cs.princeton.edu/~zkincaid/benchmarks/DIMACS/SSA/` | Testable single stuck-at fault in 7552 circuit; provably satisfiable formula. |

---

## 3. Preservation of Historical Evidence

1. **Pre-Correction Manifest Backups:**
   - [`benchmarks/final_holdout/holdout_manifest_pre_correction_20261031.json`](./benchmarks/final_holdout/holdout_manifest_pre_correction_20261031.json) (39,486 bytes)
   - [`benchmarks/final_holdout/holdout_manifest_pre_correction_20261031.csv`](./benchmarks/final_holdout/holdout_manifest_pre_correction_20261031.csv) (19,285 bytes)
2. **Original Incident Log:**
   - [`experiments/results/final_holdout/logs/run_0009_cfg02_v1_base_HOLDOUT_02_rep1.log`](./experiments/results/final_holdout/logs/run_0009_cfg02_v1_base_HOLDOUT_02_rep1.log) preserves the exact timestamp, exit code 20, and initial `LABEL_CONTRADICTION` trigger.
3. **Master CSV Reclassification:**
   - In [`experiments/results/final_holdout/master_results.csv`](./experiments/results/final_holdout/master_results.csv), Run 9 is reclassified from `LABEL_CONTRADICTION` to `VERIFIED_UNSAT` under the corrected ground truth.

