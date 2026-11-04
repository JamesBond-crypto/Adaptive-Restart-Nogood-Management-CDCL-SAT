# Adaptive Nogood Retention: Source Audit and Mathematical Design

**Project Title:** Adaptive Restart and Nogood Management for Constraint Satisfaction Solvers  
**Document Type:** Source Inspection, Architectural Analysis, and Algorithm Design Specification  
**Milestone:** Step 13 (Design Milestone — No solver source code modified)  
**Target Engine:** Glucose 4.2.1 (`src/glucose_windows/`)  
**Status:** Complete Architectural & Mathematical Specification  

---

## 1. Executive Summary & Milestone Scope

Following the successful implementation, empirical audit, and stabilization of the Adaptive Restart Controller (Variant A, Steps 10–12), this milestone addresses the second major research contribution of our project: **Adaptive Learned-Clause (Nogood) Retention (Variant B and Variant C)**.

In Conflict-Driven Clause Learning (CDCL) SAT solvers, the learned clause database grows aggressively with each conflict. Because propagating across hundreds of thousands of redundant clauses severely degrades Boolean Constraint Propagation (BCP) speed and inflates memory usage, solvers must periodically purge low-utility learned clauses. Stock Glucose 4.2.1 revolutionized clause database reduction (`reduceDB()`) by sorting learned clauses primarily by their **Literal Block Distance (LBD)**, preserving "glue clauses" ($\text{LBD} \le 2$) permanently.

However, a detailed inspection of the Glucose 4.2.1 codebase reveals fundamental limitations in stock clause reduction:
1. **Coarse LBD Dominance:** In stock Glucose, any clause with $\text{LBD} = 4$ strictly dominates and survives over any clause with $\text{LBD} = 5$, even if the $\text{LBD} = 4$ clause has been completely inactive for 100,000 conflicts while the $\text{LBD} = 5$ clause is actively participating in current unit propagations.
2. **Blunt Activity Integration:** Clause activity is incorporated solely as a rigid 10% hard cut-off (marking the top 10% highest activity clauses as temporarily protected) and as a secondary tie-breaker when two clauses share identical LBDs.
3. **Absence of Propagation Utility:** Clause activity is incremented exclusively during conflict analysis resolution steps, completely ignoring the clause's frequency of generating unit propagations during BCP.
4. **Redundant Sorting Overhead:** Stock Glucose executes *two full vector sorts* of the learned clause database during every reduction call (an activity sort followed by an LBD sort), incurring unnecessary CPU overhead.

> [!IMPORTANT]
> **Milestone Boundary:** Per project instructions, this document constitutes **SOURCE INSPECTION AND ALGORITHM DESIGN ONLY**. No solver source files, build scripts, or evaluation runners have been altered during this step. Implementation will proceed only after formal design review.

---

## 2. Comprehensive Source Code Audit of Glucose 4.2.1 Clause Management

A rigorous audit of the Glucose 4.2.1 source code under `src/glucose_windows/core/` was performed to identify the exact mechanisms governing clause representation, allocation, scoring, reduction, and memory reclamation.

```
+--------------------------------------------------------------------------------------------------+
|                                    GLUCOSE CLAUSE LIFECYCLE                                      |
|                                                                                                  |
|   [Conflict Analysis]                                                                            |
|          │                                                                                       |
|          ▼                                                                                       |
|   1-UIP Derivation ────────► Compute LBD ───► ca.alloc() ───► learnts.push(cr)                   |
|          │                                        │                                              |
|          ▼                                        ▼                                              |
|   claBumpActivity()                       Header (8 bytes) + data[]                              |
|   c.setLBD(nblevels)                      [mark, learnt, canbedel, seen, lbd, size, act]         |
|                                                   │                                              |
|                                                   ▼                                              |
|   [Search & BCP] ◄────────────────────────────────┘                                              |
|          │                                                                                       |
|          ▼                                                                                       |
|   Every Conflict: claDecayActivity() [cla_inc *= 1/0.999]                                        |
|          │                                                                                       |
|          ▼                                                                                       |
|   Periodic Trigger: conflicts >= curRestart * nbclausesbeforereduce                              |
|          │                                                                                       |
|          ▼                                                                                       |
|   reduceDB() ──────────────► Sort 1: reduceDBAct_lt (Protect Top 10% Active)                     |
|          │             ───► Sort 2: reduceDB_lt    (LBD Ascending, Ties by Act)                  |
|          ▼                                                                                       |
|   Purge Loop ──────────────► Delete Worst 50% (Excluding LBD<=2, Size<=2, !canBeDel, locked)     |
|          │                                                                                       |
|          ▼                                                                                       |
|   checkGarbage() ──────────► Relocate Surviving Clauses to Compact Arena                         |
+--------------------------------------------------------------------------------------------------+
```

### 2.1 Clause Representation and Memory Layout

In `src/glucose_windows/core/SolverTypes.h` (lines 160–282), each clause is represented by the `Clause` class:

```cpp
class Clause {
    struct {
      unsigned mark       : 2;
      unsigned learnt     : 1;
      unsigned canbedel   : 1;
      unsigned extra_size : 2; // extra size (end of 32bits) 0..3       
      unsigned seen       : 1;
      unsigned reloced    : 1;
      unsigned exported   : 2; // Values to keep track of the clause status for exportations
      unsigned oneWatched : 1;
      unsigned simplified : 1;
      unsigned lbd        : BITS_LBD; // 19 bits (max LBD = 524,287)
      unsigned size       : BITS_REALSIZE; // 32 bits
    } header;

    union { Lit lit; float act; uint32_t abs; CRef rel; } data[0];
...
```

#### Detailed Memory Breakdown:
- **Header Structure:**
  - Word 0 (32 bits):
    - `mark` (2 bits): Used by garbage collection (mark = 1 denotes deleted clause scheduled for compaction).
    - `learnt` (1 bit): 1 for learned clauses, 0 for original problem clauses.
    - `canbedel` (1 bit): 1 if eligible for deletion; 0 if protected/frozen.
    - `extra_size` (2 bits): Number of 32-bit auxiliary fields allocated immediately after literals.
    - `seen` (1 bit): Utilized exclusively for original clauses in `Solver::simplify()`; **completely unused for learned clauses**.
    - `reloced` (1 bit): Flag utilized during garbage collection relocation.
    - `exported` (2 bits): Reserved for parallel portfolio sharing.
    - `oneWatched` (1 bit): Single-watch optimization flag.
    - `simplified` (1 bit): Flag indicating clause simplification status.
    - `lbd` (19 bits): Literal Block Distance ($\text{LBD} \in [0, 524287]$).
    - *Unallocated bit:* Exactly $2 + 1 + 1 + 2 + 1 + 1 + 2 + 1 + 1 + 19 = 31$ bits used; **1 bit remains free** in Word 0.
  - Word 1 (32 bits):
    - `size` (32 bits): Number of literals in the clause.
  - **Total Header Size:** Exactly 8 bytes (two 32-bit words).

- **Dynamic Data Array (`data[0]`):**
  - Literals: `data[0 .. size-1].lit` (each `Lit` is a 32-bit signed integer).
  - Auxiliary field: When `extra_size > 0` (which is unconditionally true for learned clauses: `extra_size = 1`), `data[size].act` stores the clause activity as a 32-bit IEEE 754 single-precision float (`float act`).
  - Total allocation for a learned clause of $S$ literals:
    $$\text{Words} = 2 + S + 1 = S + 3 \text{ words} \quad (4S + 12 \text{ bytes})$$

### 2.2 Clause Allocation and Memory Arena

In `src/glucose_windows/core/SolverTypes.h` (lines 286–365), memory allocation is handled by `ClauseAllocator`, an instantiation of `RegionAllocator<uint32_t>`:
- Clauses are allocated contiguously into large memory regions (typically 4 MB chunks).
- A clause pointer is a `CRef` (an unsigned 32-bit integer representing the word offset into the allocator's backing store).
- Dereferencing is performed via `ca[cr]` or `ca.lea(cr)`.

### 2.3 Clause Categorization in Search

Glucose 4.2.1 categorizes clauses into four distinct operational classes:
1. **Unit Clauses ($S = 1$):**
   - In `Solver::search()` (`Solver.cc:1582-1586`): When conflict analysis yields a unit clause, it is **never allocated** in `ClauseAllocator`. Instead, it is immediately enqueued at decision level 0 via `uncheckedEnqueue(learnt_clause[0])` and recorded in `stats[nbUn]`.
   - Unit clauses become unconditional top-level truths and are never subject to reduction.
2. **Binary Clauses ($S = 2$):**
   - Allocated in `ClauseAllocator`, but attached to specialized binary watch lists: `watchesBin[~c[0]]` and `watchesBin[~c[1]]`.
   - In `reduceDB_lt` (`Solver.h:751-755`) and `reduceDBAct_lt` (`Solver.h:733-737`), binary clauses are unconditionally prioritized over all larger clauses:
     ```cpp
     if (ca[x].size() > 2 && ca[y].size() == 2) return 1;
     if (ca[y].size() > 2 && ca[x].size() == 2) return 0;
     ```
   - In `reduceDB()` (`Solver.cc:1279`), the deletion condition explicitly requires `c.size() > 2`. Thus, **binary clauses are never deleted**.
3. **Glue Clauses ($\text{LBD} \le 2$):**
   - Glucose defines a clause as a "Glue Clause" if its literals span at most two distinct decision levels.
   - In `reduceDB()` (`Solver.cc:1279`), the deletion condition explicitly requires `c.lbd() > 2`.
   - Therefore, all clauses with $\text{LBD} \le 2$ are **permanently retained** in stock Glucose.
4. **General Learned Clauses ($S > 2$ and $\text{LBD} > 2$):**
   - Appended to `vec<CRef> learnts`.
   - These constitute the sole target population pruned during `reduceDB()`.

### 2.4 LBD Calculation and Dynamic Updates

LBD represents the number of distinct decision levels among the literals of a clause. Glucose maintains and updates LBD dynamically:

1. **Initial Calculation at Creation:**
   In `Solver::analyze()` (`Solver.cc:675-710`), after deriving the 1-UIP conflict clause, `computeLBD(learnt_clause)` calculates the count of distinct decision levels.
2. **Dynamic LBD Minimization during Resolution ("Dynamic NBLEVEL Trick"):**
   In `Solver::analyze()` (`Solver.cc:764-782`), whenever a learned clause `c` is resolved during conflict analysis:
   ```cpp
   if(c.learnt() && c.lbd() > 2) {
       unsigned int nblevels = computeLBD(c);
       if(nblevels + 1 < c.lbd()) { // improve the LBD
           if(c.lbd() <= lbLBDFrozenClause) {
               // seems to be interesting : keep it for the next round
               c.setCanBeDel(false);
           }
           if(chanseokStrategy && nblevels <= coLBDBound) {
               ...
           } else {
               c.setLBD(nblevels); // Update it
           }
       }
   }
   ```
   If the number of unique decision levels in the current assignment is at least 2 levels lower than the clause's stored LBD, Glucose permanently tightens `c.lbd()` and, if `c.lbd() <= 30` (`lbLBDFrozenClause`), temporarily protects the clause from the upcoming reduction (`c.setCanBeDel(false)`).

### 2.5 Clause Activity Tracking and Geometric Decay

In `src/glucose_windows/core/Solver.h` and `Solver.cc`:
- **Global Clause Increment:** `double cla_inc` (initialized to $1.0$).
- **Geometric Decay (`Solver.h:555`):**
  At every conflict (`Solver.cc:1613`), `claDecayActivity()` is invoked:
  $$\text{cla\_inc} \leftarrow \text{cla\_inc} \times \left( \frac{1}{\text{clause\_decay}} \right)$$
  where default `clause_decay = 0.999`.
- **Activity Bumping (`Solver.h:556-561`):**
  When a learned clause participates in conflict derivation (`Solver.cc:756`), or is newly learned (`Solver.cc:1597`):
  ```cpp
  inline void Solver::claBumpActivity (Clause& c) {
      if ( (c.activity() += cla_inc) > 1e20 ) {
          // Rescale:
          for (int i = 0; i < learnts.size(); i++)
              ca[learnts[i]].activity() *= 1e-20;
          cla_inc *= 1e-20; 
      } 
  }
  ```
- **Equivalence to Exponential Moving Average:**
  Because `cla_inc` scales geometrically by $(1 / 0.999)^C$ at conflict $C$, dividing a clause's activity by $\text{cla\_inc}$ yields its normalized discounted hit count:
  $$\widetilde{\text{act}}(C) = \frac{\text{act}(C)}{\text{cla\_inc}} = \sum_{k \in \mathcal{H}(C)} \lambda^{C - k}$$
  where $\lambda = 0.999$ and $\mathcal{H}(C)$ is the set of conflict indices at which $C$ was resolved. The half-life of a clause's activity is:
  $$t_{1/2} = \frac{\ln 2}{1 - \lambda} \approx \frac{0.69315}{0.001} \approx 693 \text{ conflicts}$$

### 2.6 Clause Database Reduction Triggers and Scheduling

In `Solver::search()` (`Solver.cc:1653-1664`):
```cpp
if((chanseokStrategy && !glureduce && learnts.size() > firstReduceDB) ||
   (glureduce && conflicts >= ((unsigned int) curRestart * nbclausesbeforereduce))) {

    if(learnts.size() > 0) {
        curRestart = (conflicts / nbclausesbeforereduce) + 1;
        reduceDB();
        performLCM = 1;
        if(!panicModeIsEnabled())
            nbclausesbeforereduce += incReduceDB;
    }
}
```
- By default: `glureduce = true`, `chanseokStrategy = false`.
- Parameters:
  - `firstReduceDB`: Initial threshold ($2000$ conflicts).
  - `incReduceDB`: Arithmetic increment added after each reduction ($300$ conflicts).
  - `specialIncReduceDB`: Bonus increment ($1000$ conflicts) added inside `reduceDB()` if the median clause has $\text{LBD} \le 3$.

### 2.7 Sorting and Selection Mechanics in Stock Glucose

In `Solver::reduceDB()` (`Solver.cc:1248-1294`), stock Glucose executes three distinct phases:

```cpp
void Solver::reduceDB() {
    int i, j;
    stats[nbReduceDB]++;

    // Phase 1: Sort by activity to protect the top 10% most active clauses
    if (!chanseokStrategy) {
        sort(learnts, reduceDBAct_lt(ca));
        for(int i = learnts.size() * 90 / 100; i < learnts.size(); i++) {
            Clause &c = ca[learnts[i]];
            c.setCanBeDel(false);
        }
    }

    // Phase 2: Sort by LBD ascending (ties broken by activity)
    sort(learnts, reduceDB_lt(ca));

    if(ca[learnts[learnts.size() / RATIOREMOVECLAUSES]].lbd() <= 3) 
        nbclausesbeforereduce += specialIncReduceDB;

    // Phase 3: Purge loop (target limit = 50% of learnts)
    int limit = (learnts.size() / 2);

    for(i = j = 0; i < learnts.size(); i++) {
        Clause &c = ca[learnts[i]];
        if(c.lbd() > 2 && c.size() > 2 && c.canBeDel() && !locked(c) && (i < limit)) {
            removeClause(learnts[i]);
            stats[nbRemovedClauses]++;
        } else {
            if(!c.canBeDel()) limit++; // Compensate limit for protected clause
            c.setCanBeDel(true);       // Reset for next reduction round
            learnts[j++] = learnts[i];
        }
    }
    learnts.shrink(i - j);
    checkGarbage();
}
```

In `Solver.h:743-768`, `reduceDB_lt` defines the ordering:
```cpp
struct reduceDB_lt {
    ClauseAllocator& ca;
    reduceDB_lt(ClauseAllocator& ca_) : ca(ca_) {}
    bool operator()(CRef x, CRef y) {
        if (ca[x].size() > 2 && ca[y].size() == 2) return 1;
        if (ca[y].size() > 2 && ca[x].size() == 2) return 0;
        if (ca[x].size() == 2 && ca[y].size() == 2) return 0;

        // Primary criterion: LBD (larger LBD is worse, placed at lower indices)
        if (ca[x].lbd() > ca[y].lbd()) return 1;
        if (ca[x].lbd() < ca[y].lbd()) return 0;

        // Secondary criterion: Activity
        return ca[x].activity() < ca[y].activity();
    }
};
```
Because `sort()` places elements satisfying `reduceDB_lt(x, y) == true` at lower indices ($0, 1, 2, \dots$), clauses with **higher LBD (worse quality)** are placed at the beginning of the vector, where they are deleted by `i < limit`.

### 2.8 Garbage Collection, Compaction, and Pointer Relocation

When a clause is deleted:
1. `removeClause(cr)` (`Solver.cc:579-591`):
   - Detaches the clause from two-literal watch lists: `detachClause(cr)`.
   - Sets reason to undef if locked (failsafe): `if(locked(c)) vardata[var(c[0])].reason = CRef_Undef;`.
   - Marks clause as dead: `c.mark(1)`.
   - Frees word region: `ca.free(cr)`.
2. Compaction via `checkGarbage()` (`Solver.cc:1293`):
   - If the ratio of wasted words to total allocated words exceeds `garbage_frac` (default $0.20$), `garbageCollect()` (`Solver.cc:2030-2045`) is invoked.
   - `garbageCollect()` allocates a new compact `ClauseAllocator to`, iterates through all live watcher lists, trail reasons, and clause vectors (`clauses`, `learnts`), relocates surviving clauses via `ca.reloc(cr, to)`, updates all pointer references, and swaps `to` into `ca`.

---

## 3. Critical Correctness Invariants & Safety Constraints

Any learned-clause retention algorithm must strictly adhere to the following non-negotiable correctness invariants:

### 3.1 Locked Clause Preservation Invariant (Mandatory)
- **Definition:** A clause $C$ is *locked* if $C$ is the antecedent / implication reason for an assigned literal currently on the trail:
  $$\exists p \in \text{trail} : \text{reason}(\text{var}(p)) = CRef(C) \land \text{value}(p) = \text{l\_True}$$
- **Glucose Implementation (`Solver.h:575-582`):**
  ```cpp
  inline bool Solver::locked (const Clause& c) const {
      if(c.size() > 2)
          return value(c[0]) == l_True && reason(var(c[0])) != CRef_Undef && ca.lea(reason(var(c[0]))) == &c;
      return (value(c[0]) == l_True && reason(var(c[0])) != CRef_Undef && ca.lea(reason(var(c[0]))) == &c)
          || (value(c[1]) == l_True && reason(var(c[1])) != CRef_Undef && ca.lea(reason(var(c[1]))) == &c);
  }
  ```
- **Why Locked Clauses Must Never Be Deleted:**
  In CDCL, when a conflict is encountered at decision level $d$, `Solver::analyze()` walks backwards along the trail, inspecting `reason(var(p))` to resolve literals and deduce the 1-UIP conflict clause. If a locked clause were deleted and its memory reclaimed or overwritten, conflict analysis would dereference a dangling pointer, leading to:
  1. Segmentation faults and memory corruption.
  2. Corrupted resolution steps producing unsound conflict clauses.
  3. Spurious UNSAT derivations on satisfiable formulas or invalid SAT assignments.
- **Safety Guarantee:** The condition `!locked(c)` must guard every clause deletion in any proposed reduction policy.

### 3.2 Binary Clause Preservation Invariant
Binary clauses ($S = 2$) provide hyper-efficient two-literal propagation and form the backbone of the solver's 2-SAT reasoning engine. In Glucose, binary clauses are tracked in specialized `watchesBin` structures. Attempting to manage or delete binary clauses through `reduceDB()` introduces severe watcher-list corruption and performance regression. **Binary clauses must remain permanently protected.**

### 3.3 Unit Clause Immediacy Invariant
Unit clauses ($S = 1$) are root-level deductions. They are never placed in `learnts` or `ClauseAllocator` and must remain outside `reduceDB()`.

### 3.4 Glue Clause Preservation Baseline
In stock Glucose, clauses with $\text{LBD} \le 2$ are permanently retained. In our adaptive policy, a configurable CLI parameter (`-nogood-protect-glue=<int>`, default `2`) ensures that glue clauses can be protected unconditionally, preserving the core engine's fundamental reasoning power.

### 3.5 100% Deterministic Baseline Equivalence Invariant
When the solver is invoked with:
```bash
./glucose.exe -restart-strategy=baseline -reduce-strategy=baseline <instance.cnf>
```
the solver execution path, reduction timing, deleted clause sequence, conflict counts, decision counts, and generated models MUST BE BIT-FOR-BIT IDENTICAL to unmodified stock Glucose 4.2.1.

---

## 4. Limitations of Stock Glucose Learned-Clause Management

Our source code audit reveals four distinct architectural and algorithmic limitations in stock Glucose 4.2.1:

```
               LIMITATIONS OF STOCK GLUCOSE CLAUSE REDUCTION
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     Strict LBD Dominance        │       │      Stale Clause Trap          │
│ LBD=4 strictly beats LBD=5      │       │ Old LBD=3 clause inactive for   │
│ regardless of actual activity   │       │ 100k conflicts survives forever │
└────────────────┬────────────────┘       └────────────────┬────────────────┘
                 │                                         │
                 ▼                                         ▼
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     BCP Propagation Blindness   │       │     Redundant Dual Sorting      │
│ Propagations give ZERO credit;  │       │ Learnts sorted TWICE per call:  │
│ only conflict resolution bumped │       │ O(N log N) act + O(N log N) LBD │
└─────────────────────────────────┘       └─────────────────────────────────┘
```

### 4.1 Strict LBD Dominance and Discontinuous Bucketing
In `reduceDB_lt`, Glucose orders clauses by `ca[x].lbd() > ca[y].lbd()`. Because LBD is an integer, this creates rigid step-function priority tiers:
$$\forall C_1, C_2 : \text{LBD}(C_1) < \text{LBD}(C_2) \implies C_1 \text{ is strictly preferred over } C_2$$
Suppose Clause $A$ has $\text{LBD} = 4$, was learned $50,000$ conflicts ago, and has had zero activity since. Suppose Clause $B$ has $\text{LBD} = 5$, was learned $200$ conflicts ago, and has resolved in $30$ recent conflicts. Stock Glucose sorts Clause $B$ into the deletion half while preserving Clause $A$, purely because $4 < 5$.

### 4.2 The Stale Clause Trap
Because clauses with low LBD ($\text{LBD} \le 3$) are heavily protected, clauses that were critical in an early search subspace remain in the database indefinitely, even when search has moved to entirely disjoint regions of the variable space. These stale clauses bloat watcher lists and consume BCP traversal time.

### 4.3 Absence of Propagation Utility (BCP Blind Spot)
In CDCL SAT solvers, unit propagation accounts for over $85\text{--}90\%$ of total CPU time. A clause that frequently forces unit implications during BCP prevents the solver from descending into inconsistent subtrees. However, Glucose only bumps clause activity during *conflict resolution* (`Solver.cc:756`). A clause that acts as a unit propagation workhorse receives zero activity reward unless it happens to be resolved in a 1-UIP derivation.

### 4.4 Redundant Dual-Sort Performance Overhead
In `reduceDB()` (`Solver.cc:1254-1264`), Glucose sorts `learnts` twice:
1. `sort(learnts, reduceDBAct_lt)` over $N$ clauses to mark the top 10% active.
2. `sort(learnts, reduceDB_lt)` over $N$ clauses to order by LBD.
Each sort takes $O(N \log N)$ operations. For databases with $N = 50,000$ clauses, executing two independent sorts imposes measurable CPU cache thrashing and latency.

---

## 5. Mathematical Formulation of Adaptive Nogood Retention (Variant B & C)

To overcome these limitations, we propose a **Continuous Multi-Attribute Retention Utility Function** $\mathcal{R}(C) \in [0, 1]$. Rather than relying on discrete lexicographic bucketing or blunt 10% cutoffs, $\mathcal{R}(C)$ combines multiple orthogonal signals into a single unified retention score.

```
       ADAPTIVE MULTI-ATTRIBUTE RETENTION UTILITY SCORE R(C)
       
       R(C) = w_LBD * S_LBD(C)  +  w_act * S_act(C)  +  w_size * S_size(C)
                 │                         │                      │
                 ▼                         ▼                      ▼
        [LBD Locality]            [Recent Activity]         [Clause Size]
        Hyperbolic Decay          Relative Scaled           Compactness Bonus
        1 / (1 + α*(LBD-2))       (act / max_act)^γ         1 / (1 + β*(size-2))
```

### 5.1 Formal Definition of $\mathcal{R}(C)$

For each non-permanent, non-binary learned clause $C \in \mathcal{L}$, the retention utility $\mathcal{R}(C)$ is defined as:
$$\mathcal{R}(C) = w_{\text{LBD}} \cdot \mathcal{S}_{\text{LBD}}(C) + w_{\text{act}} \cdot \mathcal{S}_{\text{act}}(C) + w_{\text{size}} \cdot \mathcal{S}_{\text{size}}(C)$$

subject to the convex combination constraints:
$$w_{\text{LBD}} \ge 0, \quad w_{\text{act}} \ge 0, \quad w_{\text{size}} \ge 0, \quad w_{\text{LBD}} + w_{\text{act}} + w_{\text{size}} = 1.0$$

A clause with a higher $\mathcal{R}(C)$ represents greater utility to the ongoing search. During reduction, clauses with the lowest $\mathcal{R}(C)$ scores are pruned first.

---

### 5.2 Component 1: Non-Linear Normalized LBD Locality Score $\mathcal{S}_{\text{LBD}}(C)$

LBD measures decision-level locality. Smaller LBD implies greater likelihood of becoming unit or producing conflicts across multiple search levels. Rather than using raw LBD integers, we map $\text{LBD}(C) \in [2, \infty)$ onto $(0, 1]$ using a continuous hyperbolic decay:

$$\mathcal{S}_{\text{LBD}}(C) = \frac{1.0}{1.0 + \alpha \cdot (\text{LBD}(C) - 2)}$$

where $\alpha > 0$ is a curvature hyperparameter (default $\alpha = 0.50$).

#### Properties of $\mathcal{S}_{\text{LBD}}(C)$:
1. **Bounded:** For glue clauses ($\text{LBD} = 2$), $\mathcal{S}_{\text{LBD}}(C) = 1.0$.
2. **Strictly Monotonic:** $\frac{\partial \mathcal{S}_{\text{LBD}}}{\partial \text{LBD}} = -\frac{\alpha}{(1 + \alpha(\text{LBD}-2))^2} < 0$.
3. **Smooth Convex Decay:**
   - $\text{LBD} = 2 \implies \mathcal{S}_{\text{LBD}} = 1.000$
   - $\text{LBD} = 3 \implies \mathcal{S}_{\text{LBD}} = \frac{1}{1 + 0.5(1)} \approx 0.667$
   - $\text{LBD} = 4 \implies \mathcal{S}_{\text{LBD}} = \frac{1}{1 + 0.5(2)} = 0.500$
   - $\text{LBD} = 6 \implies \mathcal{S}_{\text{LBD}} = \frac{1}{1 + 0.5(4)} \approx 0.333$
   - $\text{LBD} = 10 \implies \mathcal{S}_{\text{LBD}} = \frac{1}{1 + 0.5(8)} = 0.200$
   - $\text{LBD} = 30 \implies \mathcal{S}_{\text{LBD}} = \frac{1}{1 + 0.5(28)} \approx 0.067$
4. **Integration with Dynamic LBD:** Whenever Glucose's dynamic LBD minimization improves `c.lbd()`, $\mathcal{S}_{\text{LBD}}(C)$ immediately reflects this improvement at zero extra cost.

---

### 5.3 Component 2: Relative Scaled Activity Score $\mathcal{S}_{\text{act}}(C)$

Clause activity in Glucose tracks recent conflict resolution participation with geometric decay. However, because raw `c.activity()` values span several orders of magnitude (from $0.0$ to $10^{20}$ before rescaling), raw activity cannot be linearly combined with LBD.

We normalize activity relative to the current population maximum in `learnts`:
$$\text{act}_{\max} = \max_{C' \in \mathcal{L}} \text{act}(C')$$

If $\text{act}_{\max} = 0$, $\mathcal{S}_{\text{act}}(C) = 0$. Otherwise:
$$\mathcal{S}_{\text{act}}(C) = \left( \frac{\text{act}(C)}{\text{act}_{\max}} \right)^\gamma$$

where $\gamma \in (0, 1]$ is a dynamic-range compression exponent (default $\gamma = 0.50$, square-root scaling).

#### Why Square-Root Scaling ($\gamma = 0.50$)?
In CDCL search, a small fraction of "super-active" clauses accumulate disproportionately large activities, creating an extreme heavy-tailed distribution. Under linear scaling ($\gamma = 1.0$), a single super-active clause compresses the activity scores of all moderately active clauses down to $\approx 0.001$. Square-root scaling expands the lower and middle percentiles:
- $\text{Relative Activity} = 0.01 \implies \mathcal{S}_{\text{act}} = \sqrt{0.01} = 0.10$
- $\text{Relative Activity} = 0.25 \implies \mathcal{S}_{\text{act}} = \sqrt{0.25} = 0.50$
- $\text{Relative Activity} = 1.00 \implies \mathcal{S}_{\text{act}} = 1.00$
This ensures that moderately active clauses retain a meaningful activity signal in the overall score.

---

### 5.4 Component 3: Clause Compactness / Size Score $\mathcal{S}_{\text{size}}(C)$

Shorter clauses are easier to satisfy, require fewer non-false literals to become unit, and take less time to traverse during watch-list propagation. We define a size compactness score:

$$\mathcal{S}_{\text{size}}(C) = \frac{1.0}{1.0 + \beta \cdot (\text{size}(C) - 2)}$$

where $\beta \ge 0$ is a mild size penalty factor (default $\beta = 0.05$).
- $\text{size} = 3 \implies \mathcal{S}_{\text{size}} = \frac{1}{1 + 0.05(1)} \approx 0.952$
- $\text{size} = 10 \implies \mathcal{S}_{\text{size}} = \frac{1}{1 + 0.05(8)} \approx 0.714$
- $\text{size} = 50 \implies \mathcal{S}_{\text{size}} = \frac{1}{1 + 0.05(48)} \approx 0.294$
This acts as a natural tie-breaker that disfavors bloated, non-compact learned clauses.

---

### 5.5 Default Hyperparameters and Sensitivity Bounds

The recommended default configuration balances structural quality (LBD), temporal relevance (activity), and clause compactness:

| Hyperparameter | Symbol | Default | Valid Range | Physical Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **LBD Weight** | $w_{\text{LBD}}$ | `0.50` | $[0.0, 1.0]$ | Relative importance of decision-level locality |
| **Activity Weight** | $w_{\text{act}}$ | `0.40` | $[0.0, 1.0]$ | Relative importance of recent conflict participation |
| **Size Weight** | $w_{\text{size}}$ | `0.10` | $[0.0, 1.0]$ | Preference for shorter, compact reasoning lemmas |
| **LBD Curvature** | $\alpha$ | `0.50` | $(0.0, 5.0]$ | Rate of score decay as LBD increases |
| **Activity Compression** | $\gamma$ | `0.50` | $(0.0, 1.0]$ | Dynamic-range compression exponent for activity |
| **Size Penalty** | $\beta$ | `0.05` | $[0.0, 1.0]$ | Rate of score decay as clause size increases |
| **Glue Protection Threshold** | $L_{\text{glue}}$ | `2` | $[0, 10]$ | Clauses with $\text{LBD} \le L_{\text{glue}}$ permanently immune |
| **Reduction Purge Fraction** | $\delta$ | `0.50` | $(0.0, 0.90)$ | Target fraction of unprotected learned clauses to purge |

#### Sensitivity and Edge Cases:
- If $w_{\text{act}} = 0$ and $w_{\text{size}} = 0$ ($w_{\text{LBD}} = 1.0$): Reduction degenerates to a pure continuous LBD sorting.
- If $w_{\text{LBD}} = 0$ and $w_{\text{size}} = 0$ ($w_{\text{act}} = 1.0$): Reduction degenerates to MiniSat-style activity-only reduction.
- All weights are bounded in $[0, 1]$ and normalized so $\sum w_i = 1.0$.

---

## 6. System Architecture for $2 \times 2$ Factorial Experimentation

To scientifically evaluate the individual and compounding effects of our research contributions, the system architecture supports four mutually exclusive, fully decoupled experimental variants:

```
                            LEARNED-CLAUSE (NOGOOD) RETENTION
                            Baseline (Glucose 4.2.1)      Adaptive Multi-Attribute
                          +-----------------------------+-----------------------------+
        Baseline          |          BASELINE           |          VARIANT B          |
        (Dual-Queue LBD)  |  -restart-strategy=baseline |  -restart-strategy=baseline |
RESTART                   |  -reduce-strategy=baseline  |  -reduce-strategy=adaptive  |
POLICY                    +-----------------------------+-----------------------------+
        Adaptive          |          VARIANT A          |          VARIANT C          |
        (Sharpe Progress/ |  -restart-strategy=adaptive |  -restart-strategy=adaptive |
        Volatility Ratio) |  -reduce-strategy=baseline  |  -reduce-strategy=adaptive  |
                          +-----------------------------+-----------------------------+
```

### 6.1 Command-Line Interface (CLI) Specification

Both restart and reduction strategies are controlled via distinct, validated CLI flags:

```bash
# Baseline stock Glucose 4.2.1:
./glucose.exe -restart-strategy=baseline -reduce-strategy=baseline input.cnf

# Variant A: Adaptive Restart Controller only:
./glucose.exe -restart-strategy=adaptive -reduce-strategy=baseline input.cnf

# Variant B: Adaptive Nogood Retention only:
./glucose.exe -restart-strategy=baseline -reduce-strategy=adaptive input.cnf

# Variant C: Combined Adaptive Engine:
./glucose.exe -restart-strategy=adaptive -reduce-strategy=adaptive input.cnf
```

#### Strict Fail-Fast Argument Validation
In `Solver::Solver()`:
```cpp
const char* red_strat = (const char*)opt_reduce_strategy;
if (red_strat == NULL || strcmp(red_strat, "baseline") == 0) {
    adaptive_reduce_mode = false;
} else if (strcmp(red_strat, "adaptive") == 0) {
    adaptive_reduce_mode = true;
} else {
    fprintf(stderr, "ERROR! Invalid reduce strategy '%s'. Valid options: baseline, adaptive\n", red_strat);
    exit(1);
}
```
If an invalid option string is passed, the solver aborts immediately with exit code 1, preventing silent fallbacks or contaminated experimental data.

---

### 6.2 High-Performance Single-Pass Scored Sorting Optimization

In stock Glucose, `reduceDB()` sorts the learned database twice ($2 \times O(N \log N)$), dereferencing `ca[x]` and `ca[y]` inside the comparator on every comparison.

In our adaptive implementation, we introduce a **Single-Pass Scored Struct Architecture**:

```cpp
struct ScoredClause {
    CRef  cr;
    float score;
};

struct ScoredClause_lt {
    bool operator()(const ScoredClause& a, const ScoredClause& b) const {
        return a.score < b.score; // Lower score = worse clause = purged first
    }
};
```

#### Optimized Reduction Algorithm in `Solver::reduceDBAdaptive()`:
```
Algorithm: Adaptive Clause Reduction (O(N log N) with Precomputed Scores)
Input: Database learnts of CRef, ClauseAllocator ca
Output: Pruned learnts with lowest scoring clauses removed

1. act_max <- 0.0
2. For each cr in learnts:
       if ca[cr].activity() > act_max then act_max <- ca[cr].activity()

3. Allocate temporary vector: vec<ScoredClause> scored(learnts.size())
4. For i = 0 to learnts.size() - 1:
       cr <- learnts[i]
       c  <- ca[cr]
       Compute S_LBD  <- 1.0 / (1.0 + α * (c.lbd() - 2))
       Compute S_act  <- (act_max > 0) ? pow(c.activity() / act_max, γ) : 0.0
       Compute S_size <- 1.0 / (1.0 + β * (c.size() - 2))
       score <- w_LBD * S_LBD + w_act * S_act + w_size * S_size
       scored[i] <- ScoredClause(cr, score)

5. sort(scored, ScoredClause_lt)  // Single fast scalar sort, zero ca[] dereferences

6. limit <- learnts.size() * opt_nogood_del_ratio
7. j <- 0
8. For i = 0 to scored.size() - 1:
       cr <- scored[i].cr
       c  <- ca[cr]
       if c.lbd() > opt_protect_glue and c.size() > 2 and c.canBeDel() and not locked(c) and i < limit:
           removeClause(cr)
           stats[nbRemovedClauses]++
       else:
           if not c.canBeDel(): limit <- limit + 1
           c.setCanBeDel(true)
           learnts[j++] <- cr

9. learnts.shrink(scored.size() - j)
10. checkGarbage()
```

#### Algorithmic and Hardware Benefits:
1. **Single Sort:** Eliminates Phase 1 entirely, reducing sorting overhead by $50\%$.
2. **No Comparator Cache Misses:** Comparator compares two contiguous `float` primitives (`a.score < b.score`). It never dereferences memory in `ClauseAllocator ca`, achieving maximum CPU L1 data cache efficiency and branch prediction accuracy.
3. **Precomputed Floating-Point Work:** Complex functions (`pow`, divisions) are evaluated exactly $N$ times during step 4, never $O(N \log N)$ times during comparisons.
4. **Memory Footprint:** For $N = 50,000$ clauses, `scored` requires only $50000 \times 8 \text{ bytes} = 400 \text{ KB}$, which fits comfortably within modern L2/L3 CPU caches.

---

## 7. Telemetry, Diagnostic Metrics, and Evaluation Protocol

### 7.1 Proposed Telemetry Outputs

To enable rigorous analysis of database dynamics, the solver and Python evaluation harness will record:

| Metric Name | Source / Type | Description |
| :--- | :---: | :--- |
| `reduce_strategy` | Solver CLI / String | Strategy mode: `"baseline"` or `"adaptive"` |
| `nb_reduce_db` | `stats[nbReduceDB]` / int | Total clause reductions executed |
| `nb_removed_clauses` | `stats[nbRemovedClauses]` / int | Cumulative learned clauses deleted |
| `adaptive_nogood_avg_lbd` | Telemetry / double | Mean LBD of surviving clauses at final reduction |
| `adaptive_nogood_avg_score` | Telemetry / double | Mean $\mathcal{R}(C)$ of surviving clauses at final reduction |
| `adaptive_nogood_purged_lbd` | Telemetry / double | Mean LBD of clauses pruned during final reduction |

### 7.2 Experimental Ablation Protocol

To validate each component of the retention score, we define four ablation experiments:
1. **Ablation 1 (LBD Dominant):** $w_{\text{LBD}} = 1.0, w_{\text{act}} = 0.0, w_{\text{size}} = 0.0$. Isolates the continuous LBD transformation from discrete bucketing.
2. **Ablation 2 (Activity Dominant):** $w_{\text{LBD}} = 0.0, w_{\text{act}} = 1.0, w_{\text{size}} = 0.0$. Measures the performance of pure activity-based pruning without LBD.
3. **Ablation 3 (LBD + Activity, No Size):** $w_{\text{LBD}} = 0.55, w_{\text{act}} = 0.45, w_{\text{size}} = 0.0$. Evaluates the core multi-attribute interaction.
4. **Ablation 4 (Full Multi-Attribute):** $w_{\text{LBD}} = 0.50, w_{\text{act}} = 0.40, w_{\text{size}} = 0.10$. Evaluates the complete model including compactness bonuses.

### 7.3 Risk Analysis and Mitigation Strategies

| Potential Failure Mode | Root Cause | Architectural Mitigation |
| :--- | :--- | :--- |
| **Solver Crash / Segfault** | Deleting a locked clause | Strict `!locked(c)` precondition retained before any `removeClause(cr)`. |
| **Formula Inconsistency** | Deleting unit or binary clauses | `c.size() > 2` check strictly enforced; units never enter `learnts`. |
| **Loss of High-Quality Reasoning** | Pruning glue clauses | Clauses with $\text{LBD} \le L_{\text{glue}}$ (default 2) permanently immune from deletion. |
| **Sorting Numerical Instability** | `NaN` or `Inf` in score calculation | $\text{act}_{\max}$ guarded with $\epsilon = 10^{-12}$; scores strictly clamped to $[0.0, 1.0]$. |
| **Baseline Divergence** | Code path leakage into baseline mode | Baseline mode uses stock `reduceDB()` logic with zero code modifications. |

---

## 8. Summary of Findings and Implementation Roadmap

### Key Findings:
1. **Clause Structure Compatibility:** Glucose's `Clause` struct already allocates and maintains `float act` for every learned clause. No memory layout modifications or struct size expansions are required.
2. **Safety Invariants Clearly Mapped:** Locked clause protection (`!locked(c)`), binary clause immunity (`c.size() > 2`), and glue clause preservation (`c.lbd() > 2`) are fully verified in the source code.
3. **Algorithmic Efficiency Gain:** The proposed single-pass scored sorting algorithm reduces clause database sorting from $2 \times O(N \log N)$ with memory dereferencing down to $1 \times O(N \log N)$ with contiguous scalar comparisons.
4. **Clean Decoupled Architecture:** The $2 \times 2$ factorial matrix (Baseline, Variant A, Variant B, Variant C) can be completely realized via orthogonal CLI flags (`-restart-strategy` and `-reduce-strategy`) with 100% baseline equivalence guaranteed.

### Transition to Implementation:
With this design specification complete and verified against `src/glucose_windows/`, the mathematical foundations, safety invariants, and architectural components are established. We now await review and authorization before proceeding with the implementation of Variant B and C in future milestones.

