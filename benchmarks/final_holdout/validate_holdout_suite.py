#!/usr/bin/env python3
"""
validate_holdout_suite.py - Independent Dataset Integrity & Overlap Verification

Verifies the integrity of the 48 unseen holdout SAT benchmark instances without
executing any candidate SAT solver:
1. Confirms file existence and exact SHA-256 integrity against manifest.
2. Confirms ZERO overlap with earlier development suites (pilot, expanded, smoke).
3. Verifies DIMACS syntax (header, literals <= vars, 0-termination).
4. Reports summary statistics across problem families and categories.
"""

import sys
import os
import csv
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Tuple

HOLDOUT_DIR = Path(__file__).resolve().parent
WORKSPACE = HOLDOUT_DIR.parent.parent
MANIFEST_CSV = HOLDOUT_DIR / "holdout_manifest.csv"
MANIFEST_JSON = HOLDOUT_DIR / "holdout_manifest.json"

def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def get_development_benchmark_hashes() -> Dict[str, str]:
    hashes = {}
    for p in WORKSPACE.glob("benchmarks/**/*.cnf"):
        if "final_holdout" in str(p):
            continue
        h = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        hashes[h.hexdigest()] = str(p.relative_to(WORKSPACE))
    return hashes

def validate_dimacs(path: Path) -> Tuple[bool, int, int, str]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    lines = text.splitlines()
    header_found = False
    decl_vars = 0
    decl_clauses = 0
    actual_clauses = 0
    current_clause = []

    for line_idx, line in enumerate(lines, 1):
        sline = line.strip()
        if not sline or sline.startswith("c"):
            continue
        if sline == "%":
            break
        if sline.startswith("p "):
            parts = sline.split()
            if len(parts) < 4 or parts[1] != "cnf":
                return False, 0, 0, f"Malformed header line {line_idx}"
            decl_vars = int(parts[2])
            decl_clauses = int(parts[3])
            header_found = True
            continue

        if not header_found:
            return False, 0, 0, f"Clause before header on line {line_idx}"

        tokens = sline.split()
        for tok in tokens:
            try:
                lit = int(tok)
            except ValueError:
                return False, 0, 0, f"Non-integer token '{tok}' on line {line_idx}"
            if lit == 0:
                actual_clauses += 1
                current_clause = []
            else:
                if abs(lit) > decl_vars:
                    return False, 0, 0, f"Literal {lit} exceeds declared vars {decl_vars} on line {line_idx}"
                current_clause.append(lit)

    if current_clause:
        return False, decl_vars, actual_clauses, "Final clause missing 0 terminator"
    if not header_found:
        return False, 0, 0, "Missing 'p cnf' header"

    note = "OK" if actual_clauses == decl_clauses else f"Clause count diff ({actual_clauses} vs {decl_clauses})"
    return True, decl_vars, actual_clauses, note

def main():
    print("=" * 80)
    print("INDEPENDENT HOLDOUT DATASET INTEGRITY & SYNTAX AUDIT")
    print("=" * 80)

    if not MANIFEST_CSV.exists() or not MANIFEST_JSON.exists():
        print("[!] ERROR: Holdout manifest not found!")
        sys.exit(1)

    with open(MANIFEST_CSV, "r", encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    print(f"[*] Total Manifest Entries: {len(records)}")
    assert len(records) == 48, f"Expected 48 instances, got {len(records)}"

    dev_hashes = get_development_benchmark_hashes()
    print(f"[*] Development Benchmarks Indexed: {len(dev_hashes)}")

    errors = 0
    holdout_hashes = set()
    category_counts = {}
    label_counts = {}

    for r in records:
        bid = r["benchmark_id"]
        fname = r["filename"]
        expected_sha = r["sha256_hash"]
        cat = r["category"]
        lbl = r["authoritative_label"]

        category_counts[cat] = category_counts.get(cat, 0) + 1
        label_counts[lbl] = label_counts.get(lbl, 0) + 1

        fpath = HOLDOUT_DIR / fname
        if not fpath.exists():
            print(f"[!] ERROR: File {fname} missing from disk!")
            errors += 1
            continue

        actual_sha = get_file_sha256(fpath)
        if actual_sha != expected_sha:
            print(f"[!] ERROR: Hash mismatch for {fname}: actual={actual_sha}, expected={expected_sha}")
            errors += 1

        if actual_sha in holdout_hashes:
            print(f"[!] ERROR: Duplicate holdout file detected: {fname}")
            errors += 1
        holdout_hashes.add(actual_sha)

        if actual_sha in dev_hashes:
            print(f"[!] CRITICAL: Overlap with development benchmark: {fname} == {dev_hashes[actual_sha]}")
            errors += 1

        is_valid, n_vars, n_clauses, val_note = validate_dimacs(fpath)
        if not is_valid:
            print(f"[!] ERROR: DIMACS validation failed for {fname}: {val_note}")
            errors += 1

    print("\n--- Category Breakdown ---")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat:<35}: {count} instances")

    print("\n--- Label Distribution ---")
    for lbl, count in sorted(label_counts.items()):
        print(f"  {lbl:<15}: {count} instances")

    print("\n" + "=" * 80)
    if errors == 0:
        print("[+] AUDIT PASSED: All 48 holdout instances are valid, unique, and strictly 0% overlap with development data.")
    else:
        print(f"[!] AUDIT FAILED with {errors} errors!")
        sys.exit(1)
    print("=" * 80)

if __name__ == "__main__":
    from typing import Tuple
    main()
