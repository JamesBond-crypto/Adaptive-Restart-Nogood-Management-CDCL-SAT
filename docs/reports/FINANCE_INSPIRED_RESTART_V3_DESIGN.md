# Finance-Inspired Adaptive Restart V3: Risk-Adjusted Search Progress Design

**Project Title:** Adaptive Restart and Nogood Management for Constraint Satisfaction Solvers (Glucose 4.2.1 Windows Port)  
**Document Type:** Research and Algorithmic Design Specification (Step 27)  
**Author / Research Team:** DeepMind Coding Assistant (Antigravity)  
**Date:** October 2026  
**Status:** Design Completed — Ready for Architectural Review  
**Target Codebase:** `src/glucose_windows/core/Solver.h`, `Solver.cc`, `simp/Main.cc`  

---

## 1. Executive Summary & Why Finance-Inspired Metrics Are Relevant

### 1.1 Context and Problem Formulation
In modern Conflict-Driven Clause Learning (CDCL) SAT solvers, search restarts serve a critical optimization purpose: they prevent the solver from remaining trapped in exponentially large, sterile subtrees caused by early suboptimal branching decisions. By unassigning all decision variables back to level 0 while preserving the learned clause database (nogoods) and variable activity scores, a restart re-roots search at the most globally constrained variable choices.

In Glucose 4.2.1, restarts are triggered by a moving average of Literal Block Distance (LBD):
$$\text{do\_restart} = \text{lbdQueue.getavg}() \times K > \frac{\text{sumLBD}}{\text{conflictsRestarts}} \quad (K = 0.80)$$
While highly successful, Glucose's restart heuristic is a scalar heuristic that monitors only recent clause quality relative to a cumulative average.

In Phases B through D of this project, we designed and stabilized **Adaptive Restart Controller V1**, inspired by the financial Sharpe ratio:
$$\mathcal{S}_W = \frac{E_W}{\sigma_W + 1.0} = \frac{\frac{1}{W}\sum \Delta p_k}{\sqrt{\text{Var}_W(d_k)} + 1.0}$$
V1 demonstrated remarkable success on structured problems (Graph Coloring and Pigeonhole Principle), cutting conflicts by up to **53.2%** and reductions by up to **92%**. However, V1 introduced severe regressions on uniform Random 3-SAT (conflict counts inflating by **+50% to +157%**), because it mistook high Boolean Constraint Propagation (BCP) activity in sterile subtrees for search progress.

Step 22 implemented **Adaptive Restart V2**, which patched this blind spot by overlaying an anti-starvation conflict ceiling ($\Delta C \ge 2500$) and an LBD distress fallback ($K = 0.80$). While V2 restored stability, it is an ad-hoc hybrid of three disjoint triggers with seven independent parameters.

### 1.2 The Financial Paradigm: Search Progress as Capital Allocation
The fundamental thesis of **Finance-Inspired Restart V3** is that CDCL search can be modeled rigorously as an online capital allocation problem:
- **Capital Expended**: CPU cycles, unit propagations ($\Delta p_t$), decisions made, and conflict resolution steps.
- **Search Return ($r_t$)**: The net informational value generated per unit of work, manifested through learned-clause quality (LBD), backjump depth ($\Delta d_t$), and formula contraction.
- **Search Risk**: The variance, downside stalling, and drawdown of return over time.
- **Restart Decision**: The disinvestment from a depreciating, sterile asset (the current search descent) to reallocate capital into the global root portfolio.

### 1.3 Where the Financial Analogy Holds vs. Where it Breaks
To avoid pseudo-scientific borrowing from financial literature, we establish strict formal boundaries:

| Dimension | Financial Portfolio Theory | CDCL SAT Solving | Algorithmic Implication |
| :--- | :--- | :--- | :--- |
| **Returns** | Continuous cash flow or price changes over discrete intervals. | Discrete, non-stationary informational events (conflicts, backjumps, learned clauses). | Return must be normalized per conflict event; cannot assume log-normal or Gaussian returns. |
| **Search Memory** | Cash balance accumulates; price history is exogenous. | Learned clauses permanently contract the state space (endogenous feedback). | A sequence of low-return conflicts may represent constructive proof generation. |
| **Risk / Volatility** | Symmetric variance ($\sigma^2$) penalizes upside price spikes as "risk." | High positive return spikes (glue clauses, deep backjumps) represent breakthroughs, not danger! | **Symmetric variance (Sharpe) is mathematically flawed for SAT search.** Downside deviation (Sortino) is required. |
| **Stationarity** | Financial regimes shift over months/years; ergodic assumptions fail. | Phase transitions occur as variables are assigned; BCP dynamics alter drastically. | Fast rolling windows or exponential decay are mandatory; long cumulative averages cause lag. |

---

## 2. Empirical & Theoretical Limitations of V1 and V2

### 2.1 The Core Flaw of V1: The "Sterile Subtree Propagation Trap"
In V1, progress is proxied solely by unit propagations: $E_W = \frac{1}{W}\sum_{k=1}^W \Delta p_k$.
When a solver makes a bad branching decision at a high decision level on an unstructured formula (e.g., Random 3-SAT near the phase transition $m/n \approx 4.26$):
1. The solver becomes trapped in an unsatisfiable subproblem.
2. BCP repeatedly propagates 15 to 30 variables before discovering a contradiction. Thus, $E_W \approx 20\text{--}25$ (exceptionally high).
3. Conflicts occur repeatedly at nearly identical decision levels ($d_k \approx 30, 29, 31, 30$). The decision-level variance is tiny: $\sigma_W \approx 1.2$.
4. The V1 Sharpe score evaluates to:
   $$\mathcal{S}_W = \frac{E_W}{\sigma_W + 1.0} \approx \frac{20}{1.2 + 1.0} \approx 9.09$$
   Meanwhile, the global cumulative score is $\mathcal{S}_{\text{global}} \approx 7.5$.
5. The trigger condition $\mathcal{S}_W < \theta \cdot \mathcal{S}_{\text{global}}$ ($9.09 < 0.60 \times 7.5 = 4.5$) **evaluates to FALSE indefinitely**.
6. **Failure Mode**: The solver churns in a sterile branch for tens of thousands of conflicts (e.g., 43,186 conflicts with 0 restarts on `rand3sat_n200_c840_s1005.cnf`), learning thousands of worthless, high-LBD clauses ($LBD \ge 12\text{--}18$).

```
V1 Failure in Sterile Subtrees (Random 3-SAT)
┌────────────────────────────────────────────────────────────────────────┐
│  High BCP Churn (Δp ≈ 25) ───► High E_w (E_w ≈ 25)                     │
│                                                                        │
│  Flat Decision Levels (d ≈ 30) ───► Low σ_w (σ_w ≈ 1.2)                │
│                                                                        │
│  S_w = E_w / (σ_w + 1) = 25 / 2.2 = 11.36 > θ * S_global                │
│                                                                        │
│  Outcome: Restarts SUPPRESSED for 40,000+ conflicts!                   │
│  Learned Clause LBD: 14 - 22 (Catastrophic Clause Quality)             │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Why V1's Denominator Penalizes Search Breakthroughs
Because V1 uses total standard deviation $\sigma_W = \sqrt{\text{Var}_W(d_k)}$ in the denominator:
- If the solver experiences a **massive breakthrough**—for example, deriving a 1-UIP clause that backjumps from level 45 all the way to level 2—the decision level shifts violently ($d_k = 45 \to 2$).
- This causes $\sigma_W$ to spike to $\approx 15.0\text{--}20.0$.
- Consequently, $\mathcal{S}_W$ plummets: $\frac{E_W}{20.0 + 1.0} \approx 0.5$.
- V1 may trigger a restart immediately *after* the solver achieves a breakthrough, prematurely discarding the productive descent!

### 2.3 Limitations of V2's Multi-Trigger Architecture
In Step 22, V2 introduced two safeguards:
$$\mathcal{T}_{\text{V2}} = \mathcal{T}_{\text{progress}} \lor \mathcal{T}_{\text{quality}} \lor \mathcal{T}_{\text{ceiling}}$$
While V2 curbed extreme regressions, our independent Step 23 audit identified clear architectural limitations:
1. **Lack of Theoretical Cohesion**: V2 is a piecewise union of three independent mechanisms rather than a single unified progress metric.
2. **Hyperparameter Proliferation**: V2 requires tuning $\theta$ (0.60), $W$ (50), $C_{\text{min}}$ (50), $C_{\text{warmup}}$ (100), $C_{\text{max}}$ (2500), $K_{\text{fallback}}$ (0.80), and queue sizing.
3. **Redundancy with Baseline**: When $\mathcal{T}_{\text{quality}}$ fires, it simply replicates Glucose's native LBD queue check, rendering the "adaptive" progress component redundant on those instances.

---

## 3. Dimensionally Sound Quality-Adjusted Search Return ($r_t$)

To replace V1's flawed propagation count, V3 must define a per-conflict return $r_t$ that reflects true mathematical search progress.

### 3.1 Candidate Online Observables
At each conflict $t$, the CDCL engine yields four primary signals:
1. **Literal Block Distance ($\text{LBD}_t \ge 2$)**: Number of distinct decision levels in the learned asserting clause. Lower is exponentially better; LBD $\le 2$ clauses are "glue" clauses that permanently bridge resolution domains.
2. **Backjump Distance ($\Delta d_t = d_t - d_{t, \text{backjump}} \ge 0$)**: The number of decision levels eliminated by 1-UIP conflict analysis. Represents direct state-space pruning.
3. **Unit Propagations ($\Delta p_t \ge 0$)**: The number of variable assignments forced by BCP between conflict $t-1$ and conflict $t$.
4. **Learned Clause Size ($\text{size}_t \ge 2$)**: Total literals in the learned clause.

### 3.2 Formal Definition of $r_t$
We define the **Quality-Adjusted Search Return** $r_t$ as:

$$r_t = \frac{Q_t}{\text{Work}_t} = \frac{q_{\text{lbd}}(\text{LBD}_t) \cdot \left(1 + \ln(1 + \Delta d_t)\right)}{1 + \frac{\Delta p_t}{P_{\text{scale}}}}$$

where:
1. **LBD Quality Factor $q_{\text{lbd}}(\text{LBD}_t)$**:
   $$q_{\text{lbd}}(\text{LBD}_t) = \frac{2.0}{\text{LBD}_t}$$
   - For glue clauses ($\text{LBD} = 2$): $q_{\text{lbd}} = 1.0$.
   - For high-quality clauses ($\text{LBD} = 3$): $q_{\text{lbd}} = 0.67$.
   - For mediocre clauses ($\text{LBD} = 6$): $q_{\text{lbd}} = 0.33$.
   - For low-quality clauses ($\text{LBD} = 20$): $q_{\text{lbd}} = 0.10$.
   *(Note: This function is continuous, strictly monotonic, bounded in $(0, 1]$, and requires zero branching).*
2. **Pruning Boost $1 + \ln(1 + \Delta d_t)$**:
   - If backjump is minimal ($\Delta d_t = 0$): factor is $1 + \ln(1) = 1.0$.
   - If backjump is moderate ($\Delta d_t = 5$): factor is $1 + \ln(6) \approx 2.79$.
   - If backjump is massive ($\Delta d_t = 50$): factor is $1 + \ln(51) \approx 4.93$.
   - Logarithmic scaling rewards deep backjumps while preventing a single extreme jump from destabilizing moving averages.
3. **Normalized Computational Work Denominator**:
   $$\text{Work}_t = 1 + \frac{\Delta p_t}{P_{\text{scale}}} \quad (P_{\text{scale}} = 25.0)$$
   - When $\Delta p_t = 0$ (immediate conflict): $\text{Work}_t = 1.0$, preventing division by zero.
   - When $\Delta p_t = 25$ (typical propagation work): $\text{Work}_t = 2.0$.
   - When $\Delta p_t = 250$ (heavy sterile churn): $\text{Work}_t = 11.0$, severely penalizing unproductive propagation.

### 3.3 Dimensional Analysis and Numerical Properties
- **Dimensionality**: $r_t$ is a dimensionless progress-efficiency scalar.
- **Range**: For any valid search state, $r_t \in (0, 10.0]$.
  - Minimum theoretical value: As $\text{LBD} \to \infty$ and $\Delta p \to \infty$, $r_t \to 0$.
  - Typical productive conflict ($\text{LBD} = 3, \Delta d = 2, \Delta p = 15$):
    $$r_t = \frac{0.667 \times (1 + \ln 3)}{1 + \frac{15}{25}} = \frac{0.667 \times 2.098}{1.60} \approx 0.875$$
  - Sterile subtree conflict ($\text{LBD} = 16, \Delta d = 0, \Delta p = 50$):
    $$r_t = \frac{0.125 \times 1.0}{1 + \frac{50}{25}} = \frac{0.125}{3.00} \approx 0.042 \quad (\mathbf{21\times \text{ lower!}})$$
  - Breakthrough glue conflict ($\text{LBD} = 2, \Delta d = 10, \Delta p = 5$):
    $$r_t = \frac{1.0 \times (1 + \ln 11)}{1 + \frac{5}{25}} = \frac{3.398}{1.20} \approx 2.83 \quad (\mathbf{67\times \text{ higher!}})$$

---

## 4. Sharpe-Inspired Search Efficiency Formulation

With a well-defined return $r_t$, we first evaluate how a modernized Sharpe-style metric performs.

### 4.1 Formal Mathematical Model
Let $W = 50$ be the rolling conflict window. The Sharpe-inspired efficiency score $\mathcal{S}_W$ is defined as:

$$\mathcal{S}_W = \frac{\bar{r}_W - R_{\text{ref}}}{\sigma_{r, W} + \epsilon_{\text{sharpe}}}$$

where:
1. **Window Mean Return**:
   $$\bar{r}_W = \frac{1}{W} \sum_{k=1}^W r_{t-W+k}$$
2. **Window Volatility (Sample Standard Deviation)**:
   $$\sigma_{r, W} = \sqrt{\frac{1}{W-1} \sum_{k=1}^W (r_{t-W+k} - \bar{r}_W)^2}$$
3. **Reference Return ($R_{\text{ref}}$)**:
   In financial economics, $R_{\text{ref}}$ represents the risk-free rate. In CDCL, it represents the minimum acceptable progress threshold. We evaluate two options:
   - *Option A (Global Cumulative Return)*: $R_{\text{ref}} = \eta \cdot \bar{r}_{\text{global}}$, where $\bar{r}_{\text{global}}$ is the cumulative average return updated via Welford's algorithm across the entire solve.
   - *Option B (Fixed Baseline Progress Threshold)*: $R_{\text{ref}} = 0.20$ (the expected return of an LBD=10 clause with zero backjump).
4. **Numerical Epsilon**: $\epsilon_{\text{sharpe}} = 0.05$ prevents division by zero when all $W$ returns in a sterile descent are identical.

### 4.2 Critical Theoretical Weakness of Sharpe for SAT
Despite correcting the return definition $r_t$, the Sharpe formulation suffers from an unavoidable mathematical pathology:
- **Symmetric Variance Penalty**: The term $\sigma_{r, W}$ treats high positive returns ($r_t \gg \bar{r}$) identically to near-zero stalls ($r_t \ll \bar{r}$).
- **Example Scenario**: Suppose a solver in a difficult descent discovers two exceptional glue clauses ($r = 3.0$) amidst several normal conflicts ($r = 0.5$). The mean $\bar{r}_W$ rises from $0.50$ to $0.65$, but sample variance $\sigma_{r, W}$ explodes from $0.05$ to $0.85$.
- As a consequence:
  $$\mathcal{S}_W = \frac{0.65 - 0.20}{0.85 + 0.05} = \frac{0.45}{0.90} = 0.50$$
  The Sharpe score **drops by 70%** precisely when the solver discovers high-quality proof structure!
- **Conclusion**: Symmetric volatility penalization is fundamentally misaligned with satisfiability search.

---

## 5. Sortino-Inspired Downside Risk Formulation

To resolve the symmetric volatility flaw, we adopt the financial **Sortino ratio** (Sortino & van der Meer, 1991), which measures return relative to a target while penalizing **only downside risk**.

```
Sharpe (Symmetric) vs. Sortino (Downside Only) Risk Profiling
┌────────────────────────────────────────────────────────────────────────┐
│  Return (r_t)                                                          │
│     ▲                                                                  │
│     │        ★ (Breakthrough Glue Clause: r = 3.2)                     │
│     │                                                                  │
│  τ  ├── ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ (Target Return)       │
│     │      •                                                           │
│     │    •   •                                                         │
│     │            ▼   ▼   ▼ (Sterile Subtree Stalls: r ≈ 0.04)          │
│  0  └────────────────────────────────────────────────────────► Time    │
│                                                                        │
│  Sharpe:  Penalizes BOTH ★ and ▼! (High σ lowers score).               │
│  Sortino: Rewards ★ (boosts numerator); Penalizes ONLY ▼!               │
└────────────────────────────────────────────────────────────────────────┘
```

### 5.1 Formal Mathematical Definition
Let $\tau > 0$ be the **Target Return Threshold** (Minimum Acceptable Progress).
At each conflict $k$, the **downside deviation** $d_k$ is:

$$d_k = \min(0, r_k - \tau)$$

The **Downside Semi-Variance** ($\text{DD}_W^2$) and **Downside Deviation** ($\sigma_{D, W}$) over window $W$ are:

$$\text{DD}_W^2 = \frac{1}{W} \sum_{k=1}^W \left(\min(0, r_k - \tau)\right)^2$$
$$\sigma_{D, W} = \sqrt{\text{DD}_W^2}$$

The **Sortino Efficiency Score** $\mathcal{S}_{\text{Sortino}}$ is defined as:

$$\mathcal{S}_{\text{Sortino}} = \frac{\bar{r}_W - \tau}{\sigma_{D, W} + \epsilon_{\text{sortino}}}$$

where $\epsilon_{\text{sortino}} = 0.05$.

### 5.2 Behavioral Characteristics and Advantages
1. **Immunity to Breakthrough Penalization**:
   If a conflict yields $r_k \ge \tau$, the downside deviation is identically zero ($d_k = 0$). Breakthrough glue clauses increase $\bar{r}_W$ without inflating $\sigma_{D, W}$, driving the Sortino score upward as desired.
2. **Rapid Stalling Sensitivity**:
   If the solver enters a sterile subtree, every conflict produces $r_k \approx 0.04 \ll \tau$.
   - The numerator $(\bar{r}_W - \tau)$ turns negative.
   - The denominator $\sigma_{D, W} = \sqrt{\frac{1}{W}\sum (\tau - 0.04)^2} \to \tau - 0.04$.
   - The Sortino score plunges sharply into negative territory:
     $$\mathcal{S}_{\text{Sortino}} \approx \frac{0.04 - 0.25}{0.21 + 0.05} = \frac{-0.21}{0.26} \approx -0.80$$
3. **Threshold Calibration**:
   A restart is triggered when recent progress falls into persistent downside distress:
   $$\text{Trigger if } \mathcal{S}_{\text{Sortino}} < \theta_{\text{sortino}} \quad (\theta_{\text{sortino}} \approx -0.20)$$

---

## 6. Drawdown-Based Restart Protection

In quantitative trading, **Maximum Drawdown (MDD)** measures the peak-to-trough decline of portfolio equity:
$$D_t = \frac{\text{Peak}_t - X_t}{\text{Peak}_t}$$
In CDCL search, drawdown offers an intuitive, scale-invariant signal: **how far has current search productivity collapsed relative to the peak productivity established during this descent?**

### 6.1 Avoiding the "Ghost Peak" Distortion
If peak efficiency is measured cumulatively across the entire solve, an early "lucky" descent will establish an irrecoverable High-Water Mark (HWM), causing all subsequent descents to perceive perpetual 80% drawdowns.

To ensure robustness, search drawdown must be **descent-local and exponential**:
1. **Descent Reset**: At every restart (descent initiation), the high-water mark resets:
   $$\text{HWM}_0 = 0.0$$
2. **Current Smoothed Return ($R_t$)**:
   To prevent single-conflict jitter from creating artificial peaks, drawdown operates on a short exponential moving average of return ($\alpha_{\text{fast}} = 0.10$):
   $$R_t = (1 - \alpha_{\text{fast}}) R_{t-1} + \alpha_{\text{fast}} r_t$$
3. **Decaying High-Water Mark ($\text{HWM}_t$)**:
   $$\text{HWM}_t = \max\left(R_t, (1 - \lambda) \text{HWM}_{t-1}\right) \quad (\lambda = 0.002)$$
   The decay rate $\lambda$ ensures that a peak achieved 500 conflicts ago naturally attenuates, preventing old bursts from permanently blocking future comparisons.

### 6.2 Relative Search Drawdown Metric
The rolling search drawdown $D_t$ is defined as:

$$D_t = \frac{\text{HWM}_t - R_t}{\text{HWM}_t + \epsilon_D} \quad (\epsilon_D = 0.10)$$

- $D_t \in [0.0, 1.0]$.
- $D_t \approx 0.0$: Search is operating at or near its peak descent productivity.
- $D_t \ge 0.70$: Search productivity has collapsed by $70\%$ from its recent peak.

### 6.3 Sustained Drawdown Condition
A restart should never fire on a single transient dip. A drawdown restart requires **sustained persistence**:
$$\text{Trigger if } D_t \ge \theta_{\text{DD}} \quad \text{for } K_{\text{persist}} \text{ consecutive conflicts}$$
Default parameters: $\theta_{\text{DD}} = 0.75$, $K_{\text{persist}} = 30$ conflicts.

---

## 7. EWMA & Tail-Risk (VaR / CVaR) Feasibility Assessment

### 7.1 Exponentially Weighted Moving Averages (EWMA)
EWMA recursively updates tracking statistics without requiring circular buffer arrays:
$$\mu_t = (1 - \alpha) \mu_{t-1} + \alpha x_t$$
$$\sigma_t^2 = (1 - \alpha) \sigma_{t-1}^2 + \alpha (x_t - \mu_t)^2$$

**Feasibility Analysis**:
- **Complexity**: Exactly 3 additions, 4 multiplications per conflict ($O(1)$).
- **Storage**: 2 `double` variables (16 bytes). Zero array allocation.
- **Verdict**: **Highly Feasible and Desirable.** Replaces circular buffers with continuous exponential memory.

### 7.2 Financial Tail-Risk Metrics: Value at Risk (VaR) & Expected Shortfall (CVaR)
- **Value at Risk ($\text{VaR}_\alpha$)**: The $(1 - \alpha)$ empirical quantile of the return distribution.
- **Expected Shortfall ($\text{CVaR}_\alpha$)**: $\mathbb{E}[r_t \mid r_t \le \text{VaR}_\alpha]$.

**Feasibility Analysis**:
1. **Computational Overhead**: Computing an exact quantile requires maintaining a sorted buffer of recent returns ($O(\log W)$ insertion via binary heap or balanced tree at every single conflict).
2. **Parametric Assumptions Fail**: Approximating VaR via $\mu - z_\alpha \sigma$ assumes a Gaussian distribution. In SAT search, returns are violently bimodal (clustered near 0 with rare positive spikes).
3. **Interpretability**: A restart heuristic based on 95% CVaR is opaque and difficult to debug during execution tracing.
4. **Verdict**: **Rejected.** CVaR introduces high computational complexity and fragile distributional assumptions without offering any empirical advantage over the Sortino semi-variance.

---

## 8. Specification of the Two Candidate V3 Controllers

We formulate two distinct, mathematically precise candidate controllers.

```
Candidate Controller Architectural Comparison
┌───────────────────────────────────┬───────────────────────────────────┐
│ Candidate 1: SASP-V3              │ Candidate 2: EWMA-DD-V3           │
│ (Sortino-Adjusted Search Progress)│ (Dual EWMA Quality-Drawdown)      │
├───────────────────────────────────┼───────────────────────────────────┤
│ • Structure: Sliding Window       │ • Structure: Sliding-Window-Free  │
│ • State: Circular Buffer (W=50)   │ • State: Dual EWMA + Decaying Peak│
│ • Primary Metric: Sortino Score   │ • Primary Metric: Dual-Horizon    │
│   (Mean vs. Downside Deviation)   │   Ratio (Fast / Slow EWMA)        │
│ • Protection: Conflict Ceiling    │ • Protection: Sustained Drawdown  │
│   (ΔC >= 2500 fallback)           │   (D_t >= 0.75 for 30 conflicts)  │
│ • Memory: ~800 bytes              │ • Memory: ~48 bytes               │
│ • Philosophy: Downside Risk       │ • Philosophy: Momentum & Drawdown │
└───────────────────────────────────┴───────────────────────────────────┘
```

---

### Candidate 1: Sortino-Adjusted Search Progress Controller (SASP-V3)

#### Core Philosophy
Replaces V1's symmetric variance with a bounded sliding-window Sortino ratio over the quality-adjusted return $r_t$, backed by an anti-starvation conflict ceiling.

#### 1. State Variables & Storage
```cpp
// Solver.h - SASP-V3 State
static const int SASP_WIN_SIZE = 50;
float    sasp_win_r[SASP_WIN_SIZE];       // Quality returns in window (200 bytes)
float    sasp_win_down[SASP_WIN_SIZE];    // Downside deviations in window (200 bytes)
int      sasp_head;                       // Circular buffer index (4 bytes)
int      sasp_count;                      // Samples accumulated (4 bytes)
uint64_t sasp_conflicts_since_restart;    // Descent conflict counter (8 bytes)
double   sasp_target_tau;                 // Target minimum return τ = 0.25 (8 bytes)
double   sasp_theta;                      // Sortino threshold θ = -0.20 (8 bytes)
int      sasp_ceiling;                    // Anti-starvation ceiling = 2500 (4 bytes)
```
*Total Memory Overhead*: 436 bytes per solver instance.

#### 2. Per-Conflict Mathematical Update (`updateSASP(confl)`)
Executed at conflict quiescence after 1-UIP conflict analysis:
1. Extract observables: $\text{LBD}_t$, backjump distance $\Delta d_t = d_{\text{cur}} - d_{\text{backjump}}$, and $\Delta p_t = \text{props} - \text{last\_props}$.
2. Compute Quality-Adjusted Return:
   $$r_t = \frac{\frac{2.0}{\text{LBD}_t} \cdot \left(1.0 + \ln(1.0 + \Delta d_t)\right)}{1.0 + \frac{\Delta p_t}{25.0}}$$
3. Compute Downside Deviation against target $\tau = 0.25$:
   $$\delta_t = \min(0.0, r_t - \tau)$$
4. Store in circular buffer:
   $$\text{sasp\_win\_r}[\text{head}] = r_t, \quad \text{sasp\_win\_down}[\text{head}] = \delta_t^2$$
   $$\text{head} = (\text{head} + 1) \pmod W$$
   $$\text{count} = \min(W, \text{count} + 1)$$
   $$\text{sasp\_conflicts\_since\_restart}++$$

#### 3. Restart Decision Logic (`checkSASPRestart()`)
Evaluated in `search()`:
```cpp
bool Solver::checkSASPRestart() {
    // Guard 1: Anti-Starvation Ceiling (Immediate fire)
    if (sasp_conflicts_since_restart >= (uint64_t)sasp_ceiling)
        return true;

    // Guard 2: Warmup and Cooldown
    if (conflicts < 100 || sasp_conflicts_since_restart < 50 || sasp_count < SASP_WIN_SIZE)
        return false;

    // Compute Window Mean Return
    double sum_r = 0.0, sum_down_sq = 0.0;
    for (int i = 0; i < SASP_WIN_SIZE; i++) {
        sum_r += sasp_win_r[i];
        sum_down_sq += sasp_win_down[i];
    }
    double mean_r = sum_r / (double)SASP_WIN_SIZE;
    double downside_dev = sqrt(sum_down_sq / (double)SASP_WIN_SIZE);

    // Compute Sortino Score
    double sortino = (mean_r - sasp_target_tau) / (downside_dev + 0.05);

    // Trigger restart if recent downside distress exceeds threshold
    return (sortino < sasp_theta); // θ = -0.20
}
```

#### 4. Reset on Restart (`resetSASP()`)
- `sasp_conflicts_since_restart = 0`
- `sasp_head = 0, sasp_count = 0`
- `lbdQueue.fastclear()`

---

### Candidate 2: Dual-Horizon EWMA Quality-Drawdown Controller (EWMA-DD-V3)

#### Core Philosophy
Eliminates circular buffers entirely. Replaces sliding windows with dual-horizon exponential moving averages (Momentum) coupled with a continuous descent-local Drawdown Safeguard.

#### 1. State Variables & Storage
```cpp
// Solver.h - EWMA-DD-V3 State
double   ewma_fast;                       // Fast EWMA of return (α_fast = 0.08, ~12 conflicts) (8 bytes)
double   ewma_slow;                       // Slow EWMA of return (α_slow = 0.01, ~100 conflicts) (8 bytes)
double   ewma_hwm;                        // Descent High-Water Mark of ewma_fast (8 bytes)
uint32_t ewma_stall_conflicts;            // Consecutive conflicts in severe drawdown (4 bytes)
uint64_t ewma_conflicts_since_restart;    // Descent conflict counter (8 bytes)
double   ewma_ratio_threshold;            // Fast/Slow ratio threshold θ_ratio = 0.60 (8 bytes)
double   ewma_dd_threshold;               // Drawdown threshold θ_dd = 0.75 (8 bytes)
uint32_t ewma_max_stall;                  // Drawdown persistence limit = 30 conflicts (4 bytes)
```
*Total Memory Overhead*: 52 bytes per solver instance (Zero array allocation).

#### 2. Per-Conflict Mathematical Update (`updateEWMADD(confl)`)
1. Compute Quality Return $r_t$ as defined in Section 3.2.
2. Update Dual EWMAs:
   $$\bar{r}_{\text{fast}, t} = (1 - \alpha_{\text{fast}}) \bar{r}_{\text{fast}, t-1} + \alpha_{\text{fast}} r_t \quad (\alpha_{\text{fast}} = 0.08)$$
   $$\bar{r}_{\text{slow}, t} = (1 - \alpha_{\text{slow}}) \bar{r}_{\text{slow}, t-1} + \alpha_{\text{slow}} r_t \quad (\alpha_{\text{slow}} = 0.01)$$
3. Update Decaying High-Water Mark:
   $$\text{HWM}_t = \max\left(\bar{r}_{\text{fast}, t}, (1 - \lambda) \text{HWM}_{t-1}\right) \quad (\lambda = 0.001)$$
4. Compute Drawdown:
   $$D_t = \frac{\text{HWM}_t - \bar{r}_{\text{fast}, t}}{\text{HWM}_t + 0.05}$$
   If $D_t \ge \theta_{\text{dd}}$ (0.75), increment $\text{ewma\_stall\_conflicts}++$; else reset to 0.
5. Increment descent conflicts: $\text{ewma\_conflicts\_since\_restart}++$.

#### 3. Restart Decision Logic (`checkEWMADDRestart()`)
Evaluated in `search()`:
```cpp
bool Solver::checkEWMADDRestart() {
    // Guard 1: Absolute Conflict Ceiling (Safety Net)
    if (ewma_conflicts_since_restart >= 2500)
        return true;

    // Guard 2: Minimum Cooldown
    if (conflicts < 100 || ewma_conflicts_since_restart < 50)
        return false;

    // Trigger A: Sustained Peak Drawdown Collapse
    // (Search established high productivity, then completely stalled for 30 consecutive conflicts)
    if (ewma_stall_conflicts >= ewma_max_stall)
        return true;

    // Trigger B: Dual-Horizon Trend Exhaustion
    // (Recent fast progress has fallen to less than 60% of local background progress)
    if (ewma_fast < ewma_ratio_threshold * ewma_slow)
        return true;

    return false;
}
```

#### 4. Reset on Restart (`resetEWMADD()`)
- `ewma_conflicts_since_restart = 0`
- `ewma_stall_conflicts = 0`
- `ewma_hwm = 0.0`
- `ewma_fast = 0.50` (neutral initialization)
- `lbdQueue.fastclear()`

---

## 9. Source Counters, Data Structures, and Implementation Feasibility

### 9.1 Required Source Counters and Access Paths
Both candidate controllers rely exclusively on existing, sanctioned solver state in `Solver.h` and `Solver.cc`:
- **Current LBD**: Evaluated from the newly derived 1-UIP clause in `analyze()` (already stored in `lbdQueue`).
- **Backjump Distance**: Calculated directly at conflict resolution via `decisionLevel() - backtrack_level` before `cancelUntil()`.
- **Search Propagations**: Tracked via `propagations - last_props` (already implemented in V1/V2).
- **Quiescent Evaluation**: Evaluated inside `Solver::search()` at line 2070 inside the quiescent `else` branch of `if (confl != CRef_Undef)`, guaranteeing zero pending conflicts.

### 9.2 Zero New External Dependencies
Neither candidate requires:
- File I/O or external libraries.
- Dynamic heap allocations (`malloc`/`new`).
- String matching or benchmark classification.
Both controllers operate strictly on $O(1)$ scalar arithmetic.

---

## 10. Computational Complexity, Runtime, and Memory Overhead Estimates

| Metric | Baseline Glucose | Adaptive Restart V1 | Adaptive Restart V2 | Candidate 1 (SASP-V3) | Candidate 2 (EWMA-DD-V3) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Time per Conflict** | $O(1)$ (queue push) | $O(1)$ amortized ($O(W)$ on check) | $O(1)$ ($O(W)$ on check) | $O(1)$ ($O(W)$ on check) | **Strict $O(1)$ unconditionally** |
| **FLOPs per Conflict** | ~4 | ~8 + loop | ~12 + loop | ~14 + loop | **~12 (no loop!)** |
| **Memory per Instance** | ~400 bytes | ~840 bytes | ~880 bytes | ~850 bytes | **~460 bytes (minimal)** |
| **Circular Buffers** | 2 (`lbd`, `trail`) | 3 (`+adapt_win`) | 3 (`+adapt_win`) | 3 (`+sasp_win`) | **2 (Zero new buffers)** |
| **Impact on BCP Rate** | 0.0% | < 0.2% | < 0.2% | < 0.3% | **< 0.1%** |

Both candidates impose less than **0.3%** runtime overhead on the BCP conflict loop, which is completely imperceptible relative to formula solving times.

---

## 11. Risks, Failure Modes, and Mathematical Limitations

### 11.1 Potential Failure Modes of Candidate 1 (SASP-V3)
1. **Window Transition Lag**: A discrete sliding window of size $W=50$ carries a 50-conflict memory. If search enters a sterile subtree, the Sortino score cannot reflect full distress until 30 to 40 conflicts have accumulated inside the buffer.
2. **Buffer Traversal Overhead**: Iterating over 50 array elements in `checkSASPRestart()` consumes ~100 CPU cycles at every quiescent conflict. While small, this is executed millions of times.

### 11.2 Potential Failure Modes of Candidate 2 (EWMA-DD-V3)
1. **Cold-Start Bias**: Early in a descent, $\bar{r}_{\text{fast}}$ and $\bar{r}_{\text{slow}}$ depend on their initial seed values. A 50-conflict cooldown guard (`ewma_conflicts_since_restart < 50`) is mandatory to prevent spurious early restarts.
2. **Peak Decay Sensitivity**: If the decay rate $\lambda$ is too small ($\lambda < 0.0001$), the high-water mark will decay too slowly, causing over-frequent drawdown triggers. If $\lambda$ is too large ($\lambda > 0.01$), the peak will decay immediately, masking legitimate search stalls.

### 11.3 Mathematical Limitations of Both Candidates
- **Non-Convexity of SAT Search Spaces**: A low quality-adjusted return over 50 conflicts does not mathematically prove that the current descent will not discover a refutation on conflict 51. Restarts are inherently a heuristic gamble.
- **Random 3-SAT Sensitivity**: On uniform Random 3-SAT, backjump distances are naturally short ($\Delta d \le 2$) and clause LBDs are naturally elevated ($\text{LBD} \approx 8\text{--}14$). Setting the target $\tau$ too high would trigger excessive restart thrashing.

---

## 12. Recommended Candidate & Justification

### Recommendation: Candidate 2 (EWMA-DD-V3) — Dual-Horizon EWMA Quality-Drawdown Controller

### Detailed Technical Justification:
1. **Algorithmic Elegance and Zero-Buffer Architecture**:
   Candidate 2 completely eliminates array indexing and circular buffer maintenance. It operates in strict $O(1)$ time with zero loops and consumes only 52 bytes of memory.
2. **True Downside Protection via Descent-Local Drawdown**:
   The decaying High-Water Mark directly captures the natural rhythm of CDCL search: when a descent is fruitful, it establishes a high productivity baseline; the moment BCP stalls and enters a sterile subtree, the drawdown counter immediately catches the collapse.
3. **Dual-Horizon Trend Following**:
   The interaction of Fast EWMA ($\alpha = 0.08$) and Slow EWMA ($\alpha = 0.01$) mimics proven financial MACD (Moving Average Convergence Divergence) principles, detecting search exhaustion smoothly without hard window boundary artifacts.
4. **Clean Parameter Semantics**:
   All parameters have intuitive physical meanings: $\theta_{\text{ratio}} = 0.60$ (progress dropped to 60% of baseline), $\theta_{\text{dd}} = 0.75$ (75% collapse from peak), $K_{\text{stall}} = 30$ (sustained for 30 conflicts).

---

## 13. Component Ablation Experiment Plan

To scientifically validate V3, future empirical evaluations must execute a factorial ablation isolating each mechanism:

```
Component Ablation Matrix (5 Configurations)
┌────────┬──────────────────────────────────────────────────────────────────┐
│ Conf 1 │ Historical Baseline: Adaptive Restart V1 (Sharpe Baseline)       │
├────────┼──────────────────────────────────────────────────────────────────┤
│ Conf 2 │ Quality Return Only: EWMA of r_t (No Drawdown Safeguard)         │
├────────┼──────────────────────────────────────────────────────────────────┤
│ Conf 3 │ Sortino Window Only: SASP-V3 (Candidate 1)                       │
├────────┼──────────────────────────────────────────────────────────────────┤
│ Conf 4 │ Drawdown Alone: Descent HWM Drawdown (No Quality Return, raw p)  │
├────────┼──────────────────────────────────────────────────────────────────┤
│ Conf 5 │ Full Recommended V3: EWMA-DD-V3 (Candidate 2)                    │
└────────┴──────────────────────────────────────────────────────────────────┘
```

### Primary Evaluation Metrics:
1. **Solved Count ($N_{\text{solved}}$)**: Total instances solved within timeout cutoff.
2. **PAR-2 Runtime**: Penalized Average Runtime with $2\times$ timeout penalty.
3. **Paired Wall-Clock Speedup**: Median and geometric mean speedup on mutually solved instances.
4. **Genuine Restarts & Average Interval**: Explanatory metric verifying elimination of restart starvation.
5. **Peak Working Set Memory**: Ensuring memory parity with Glucose baseline.

---

## 14. Anti-Overfitting Benchmark Protocol & Experimental Validity

### 14.1 Development Data Quarantine
The existing **20 pilot benchmarks** and **36 expanded benchmarks** have been repeatedly evaluated during Steps 11–26 to diagnose algorithm behavior.
> [!IMPORTANT]
> The pilot and expanded benchmarks must now be strictly designated as **Development / Training Data**. Under no circumstances may final claims of general SAT improvement be based solely on these 56 instances.

### 14.2 The Unseen Holdout Evaluation Suite
For final validation of V3, an independent **Evaluation Test Suite** of 40–50 new instances must be generated or sampled from SAT Competition benchmarks (SAT Competitions 2022–2024 Anniversary Suites), ensuring:
1. **Zero Overlap**: No identical random seeds, graph structures, or CNF hashes.
2. **Diverse Application Domains**:
   - Cryptographic hashing (SHA-256 / MD5 preimage attacks).
   - Bounded Model Checking (hardware verification circuits).
   - Maximum Clique and Exact Vertex Cover.
   - Pseudo-random phase-transition 3-SAT (strictly held out).
3. **Pre-Registered Protocol**: Hyperparameters must be frozen *before* evaluating the holdout suite.

### 14.3 Retention Interaction Protocol
To isolate algorithm causality:
- Phase 1: Evaluate V3 against Baseline Restarts using **Baseline Reduction** (`-reduce-strategy=baseline`) to isolate restart policy mechanics.
- Phase 2: Factorially combine V3 with **Adaptive-Fixed Retention** (`-reduce-strategy=adaptive-fixed`) to verify whether the reduction scheduling fix synergistic with V3.

---

## 15. Summary of Deliverable Findings

1. **Proposed Quality-Adjusted Return**:
   $$r_t = \frac{\frac{2.0}{\text{LBD}_t} \cdot \left(1 + \ln(1 + \Delta d_t)\right)}{1 + \frac{\Delta p_t}{25.0}}$$
   Dimensionally sound, numerically stable, bounded in $(0, 10]$, and natively neutralizes the sterile subtree trap.
2. **Practical Finance Signals**:
   - *Sortino Downside Deviation*: Feasible and mathematically superior to Sharpe (rewards breakthroughs, penalizes stalls).
   - *Decaying High-Water Mark Drawdown*: Highly practical and scale-invariant.
   - *Dual EWMA*: Optimal $O(1)$ alternative to sliding windows.
   - *VaR / CVaR*: Impractical for CDCL search; rejected.
3. **Recommended Controller**: **EWMA-DD-V3 (Candidate 2)**. Operates in strict $O(1)$ time, requires zero buffer arrays, and adds under 52 bytes of memory.
4. **Anti-Overfitting Integrity**: Existing 56 benchmarks quarantined as development data; mandatory evaluation on an independent, pre-registered holdout suite.

