#!/usr/bin/env python3
"""
generate_pilot.py - Reproducible Pilot Benchmark Generator & Manifest Builder

Generates a curated collection of 20 nontrivial DIMACS CNF benchmarks across
three structural families to evaluate CDCL solver search behavior:
1. Uniform Random 3-SAT at the phase transition ratio (~4.26).
2. Planted Satisfiable 3-SAT with mathematically certified ground-truth assignments.
3. Structured Pigeonhole Principle (PHP) formulas with guaranteed UNSAT status.

Outputs:
- CNF files saved in: benchmarks/pilot/
- CSV manifest saved in: benchmarks/pilot_manifest.csv
"""

import os
import csv
import random
from pathlib import Path
from typing import List, Tuple, Dict, Any


def generate_random_3sat(num_vars: int, num_clauses: int, seed: int) -> List[List[int]]:
    """
    Generates a uniform random 3-SAT formula with fixed seed.
    Each clause contains 3 distinct variables with random polarities.
    """
    rng = random.Random(seed)
    clauses: List[List[int]] = []
    clause_set = set()

    attempts = 0
    max_attempts = num_clauses * 100

    while len(clauses) < num_clauses and attempts < max_attempts:
        attempts += 1
        vars_chosen = rng.sample(range(1, num_vars + 1), 3)
        lits = tuple(sorted([v if rng.choice([True, False]) else -v for v in vars_chosen], key=abs))
        if lits not in clause_set:
            clause_set.add(lits)
            clauses.append(list(lits))

    if len(clauses) < num_clauses:
        raise RuntimeError(f"Could not generate {num_clauses} distinct clauses without duplicates.")

    return clauses


def generate_planted_3sat(num_vars: int, num_clauses: int, seed: int) -> Tuple[List[List[int]], Dict[int, bool]]:
    """
    Generates a planted satisfiable 3-SAT formula.
    First chooses a satisfying assignment sigma.
    Ensures that every generated clause has at least one literal satisfied by sigma.
    """
    rng = random.Random(seed)
    # Plant a random truth assignment: {1: True/False, 2: True/False, ...}
    planted_model = {v: rng.choice([True, False]) for v in range(1, num_vars + 1)}

    clauses: List[List[int]] = []
    clause_set = set()

    attempts = 0
    max_attempts = num_clauses * 100

    while len(clauses) < num_clauses and attempts < max_attempts:
        attempts += 1
        vars_chosen = rng.sample(range(1, num_vars + 1), 3)

        # Generate polarities such that at least one literal evaluates to True under planted_model
        while True:
            polarities = [rng.choice([True, False]) for _ in range(3)]
            lits = [vars_chosen[i] if polarities[i] else -vars_chosen[i] for i in range(3)]
            # Check if at least one literal is satisfied
            is_sat = any(
                (lit > 0 and planted_model[abs(lit)]) or (lit < 0 and not planted_model[abs(lit)])
                for lit in lits
            )
            if is_sat:
                break

        canonical = tuple(sorted(lits, key=abs))
        if canonical not in clause_set:
            clause_set.add(canonical)
            clauses.append(list(canonical))

    if len(clauses) < num_clauses:
        raise RuntimeError(f"Could not generate {num_clauses} planted clauses without duplicates.")

    return clauses, planted_model


def generate_php(num_pigeons: int, num_holes: int) -> List[List[int]]:
    """
    Encodes the Pigeonhole Principle PHP(num_pigeons, num_holes).
    Variables: x_{i,j} = pigeon i is in hole j.
    Mapping: var(i, j) = (i - 1) * num_holes + j.
    """
    def var_idx(pigeon: int, hole: int) -> int:
        return (pigeon - 1) * num_holes + hole

    clauses: List[List[int]] = []

    # 1. Each pigeon must be in at least one hole:
    for i in range(1, num_pigeons + 1):
        clause = [var_idx(i, j) for j in range(1, num_holes + 1)]
        clauses.append(clause)

    # 2. No hole can hold two pigeons:
    for j in range(1, num_holes + 1):
        for i1 in range(1, num_pigeons + 1):
            for i2 in range(i1 + 1, num_pigeons + 1):
                clauses.append([-var_idx(i1, j), -var_idx(i2, j)])

    return clauses


def write_cnf_file(path: Path, num_vars: int, clauses: List[List[int]], header_comment: str):
    """Writes clauses to a DIMACS CNF file format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"c {header_comment}\n")
        f.write(f"p cnf {num_vars} {len(clauses)}\n")
        for clause in clauses:
            f.write(f"{' '.join(map(str, clause))} 0\n")


def build_pilot_suite() -> List[Dict[str, Any]]:
    output_dir = Path("benchmarks/pilot")
    manifest_path = Path("benchmarks/pilot_manifest.csv")
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_records: List[Dict[str, Any]] = []

    # ==========================================
    # Family A: Random 3-SAT (Phase Transition ~4.26)
    # ==========================================
    random_configs = [
        (50, round(50 * 4.26), 101),
        (50, round(50 * 4.26), 102),
        (75, round(75 * 4.26), 201),
        (75, round(75 * 4.26), 202),
        (100, round(100 * 4.26), 301),
        (100, round(100 * 4.26), 302),
        (125, round(125 * 4.26), 401),
    ]

    for n_vars, n_clauses, seed in random_configs:
        fname = f"rand3sat_n{n_vars}_c{n_clauses}_s{seed}.cnf"
        fpath = output_dir / fname
        clauses = generate_random_3sat(n_vars, n_clauses, seed)
        write_cnf_file(
            fpath,
            n_vars,
            clauses,
            f"Random 3-SAT instance: n={n_vars}, m={n_clauses}, seed={seed}, ratio={n_clauses/n_vars:.2f}"
        )
        manifest_records.append({
            "filename": fname,
            "filepath": str(fpath),
            "family": "Random 3-SAT",
            "parameters": f"n={n_vars}, m={n_clauses}",
            "random_seed": seed,
            "num_vars": n_vars,
            "num_clauses": len(clauses),
            "known_status": "UNKNOWN",
            "status_reason": "Uniform random sampling at phase transition ratio (m/n ≈ 4.26); no ground-truth oracle applied."
        })

    # ==========================================
    # Family B: Planted Satisfiable 3-SAT
    # ==========================================
    planted_configs = [
        (60, round(60 * 4.26), 501),
        (60, round(60 * 4.26), 502),
        (90, round(90 * 4.26), 601),
        (90, round(90 * 4.26), 602),
        (120, round(120 * 4.26), 701),
        (120, round(120 * 4.26), 702),
        (150, round(150 * 4.26), 801),
    ]

    for n_vars, n_clauses, seed in planted_configs:
        fname = f"planted3sat_n{n_vars}_c{n_clauses}_s{seed}.cnf"
        fpath = output_dir / fname
        clauses, model = generate_planted_3sat(n_vars, n_clauses, seed)
        model_str = " ".join(f"{v if model[v] else -v}" for v in sorted(model.keys()))
        write_cnf_file(
            fpath,
            n_vars,
            clauses,
            f"Planted Satisfiable 3-SAT: n={n_vars}, m={n_clauses}, seed={seed}. Planted model: {model_str}"
        )
        manifest_records.append({
            "filename": fname,
            "filepath": str(fpath),
            "family": "Planted Satisfiable 3-SAT",
            "parameters": f"n={n_vars}, m={n_clauses}",
            "random_seed": seed,
            "num_vars": n_vars,
            "num_clauses": len(clauses),
            "known_status": "SAT",
            "status_reason": f"Mathematically guaranteed satisfiable by construction with planted assignment."
        })

    # ==========================================
    # Family C: Pigeonhole Principle (PHP)
    # ==========================================
    php_configs = [
        (4, 3),  # 4 pigeons, 3 holes -> 12 vars, 22 clauses
        (5, 4),  # 5 pigeons, 4 holes -> 20 vars, 45 clauses
        (6, 5),  # 6 pigeons, 5 holes -> 30 vars, 81 clauses
        (7, 6),  # 7 pigeons, 6 holes -> 42 vars, 133 clauses
        (8, 7),  # 8 pigeons, 7 holes -> 56 vars, 204 clauses
        (9, 8),  # 9 pigeons, 8 holes -> 72 vars, 297 clauses
    ]

    for pigeons, holes in php_configs:
        fname = f"php_{pigeons}p_{holes}h.cnf"
        fpath = output_dir / fname
        clauses = generate_php(pigeons, holes)
        n_vars = pigeons * holes
        write_cnf_file(
            fpath,
            n_vars,
            clauses,
            f"Pigeonhole Principle PHP({pigeons},{holes}): {pigeons} pigeons in {holes} holes."
        )
        manifest_records.append({
            "filename": fname,
            "filepath": str(fpath),
            "family": "Pigeonhole Principle (PHP)",
            "parameters": f"pigeons={pigeons}, holes={holes}",
            "random_seed": "N/A (deterministic)",
            "num_vars": n_vars,
            "num_clauses": len(clauses),
            "known_status": "UNSAT",
            "status_reason": f"Mathematically unsatisfiable by Dirichlet's box principle ({pigeons} pigeons cannot occupy {holes} distinct holes without collision)."
        })

    # Write manifest CSV
    fieldnames = [
        "filename",
        "filepath",
        "family",
        "parameters",
        "random_seed",
        "num_vars",
        "num_clauses",
        "known_status",
        "status_reason"
    ]

    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest_records)

    print(f"[+] Successfully generated {len(manifest_records)} pilot instances.")
    print(f"[+] Files stored in: {output_dir}")
    print(f"[+] Manifest created at: {manifest_path}")

    return manifest_records


if __name__ == "__main__":
    build_pilot_suite()

