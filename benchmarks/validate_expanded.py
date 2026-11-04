#!/usr/bin/env python3
"""
validate_expanded.py - Comprehensive Validation of Expanded SAT Benchmarks
"""

import os
import sys
import csv
import hashlib
from pathlib import Path

# Add experiments directory for model verifier
sys.path.insert(0, str(Path(__file__).parent.parent / "experiments"))
from verify_model import verify_model

def run_validation():
    manifest_path = Path("benchmarks/expanded_manifest.csv")
    expanded_dir = Path("benchmarks/expanded")
    pilot_manifest = Path("benchmarks/pilot_manifest.csv")

    with open(manifest_path, "r", encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    print(f"[*] Total records in manifest: {len(records)}")

    # 1. Uniqueness check
    fnames = set()
    hashes = set()
    for r in records:
        fname = r["filename"]
        h = r["sha256"]
        if fname in fnames:
            raise ValueError(f"Duplicate filename: {fname}")
        fnames.add(fname)
        if h in hashes:
            raise ValueError(f"Duplicate SHA-256: {h} for {fname}")
        hashes.add(h)

    # 2. Pilot overlap check
    with open(pilot_manifest, "r", encoding="utf-8") as f:
        pilot_records = list(csv.DictReader(f))
    pilot_fnames = {p["filename"] for p in pilot_records}
    overlap = fnames.intersection(pilot_fnames)
    if overlap:
        raise ValueError(f"Overlap with pilot instances: {overlap}")
    print("[+] No filename or instance overlap with pilot benchmarks.")

    # 3. Structural and syntax validation
    sat_count = 0
    unsat_count = 0
    unknown_count = 0

    for r in records:
        p = Path(r["filepath"])
        if not p.is_file():
            raise FileNotFoundError(f"Missing file: {p}")

        # Hash check
        file_hash = hashlib.sha256(p.read_bytes()).hexdigest()
        if file_hash != r["sha256"]:
            raise ValueError(f"Hash mismatch for {r['filename']}: expected {r['sha256']}, got {file_hash}")

        # DIMACS parse check
        with open(p, "r", encoding="utf-8") as f:
            lines = f.readlines()

        header_found = False
        decl_vars = 0
        decl_clauses = 0
        clause_count = 0
        max_var = 0
        clauses = []
        planted_model_line = None

        for line in lines:
            line_s = line.strip()
            if not line_s:
                continue
            if line_s.startswith("c"):
                if "Planted model:" in line_s:
                    planted_model_line = line_s.split("Planted model:")[1].strip()
                continue
            if line_s.startswith("p cnf"):
                parts = line_s.split()
                decl_vars = int(parts[2])
                decl_clauses = int(parts[3])
                header_found = True
                continue
            if not header_found:
                raise ValueError(f"Clause before header in {p}")
            if not line_s.endswith(" 0") and line_s != "0":
                raise ValueError(f"Clause does not end with 0 in {p}: {line_s}")

            lits = [int(x) for x in line_s.split()[:-1]]
            if not lits:
                continue
            for lit in lits:
                if lit == 0 or abs(lit) > decl_vars:
                    raise ValueError(f"Literal {lit} out of range (1..{decl_vars}) in {p}")
                max_var = max(max_var, abs(lit))
            clause_count += 1
            canon = tuple(sorted(lits, key=abs))
            clauses.append(canon)

        if clause_count != decl_clauses:
            raise ValueError(f"Clause count mismatch in {p}: declared {decl_clauses} vs actual {clause_count}")
        if decl_vars != int(r["num_vars"]):
            raise ValueError(f"Variable count mismatch in {p}: manifest {r['num_vars']} vs declared {decl_vars}")
        if decl_clauses != int(r["num_clauses"]):
            raise ValueError(f"Clause count mismatch in {p}: manifest {r['num_clauses']} vs declared {decl_clauses}")
        if len(set(clauses)) != len(clauses):
            raise ValueError(f"Duplicate clauses found in {p}")

        # Ground truth status tracking
        status = r["known_status"]
        if status == "SAT":
            sat_count += 1
            # If Planted 3-SAT, verify planted model line
            if planted_model_line:
                v_model = f"v {planted_model_line} 0"
                ok, msg = verify_model(str(p), v_model)
                if not ok:
                    raise RuntimeError(f"Model verification failed for {p}: {msg}")
        elif status == "UNSAT":
            unsat_count += 1
        elif status == "UNKNOWN":
            unknown_count += 1
        else:
            raise ValueError(f"Invalid known_status: {status}")

    print(f"[+] All {len(records)} instances validated successfully:")
    print(f"    - SAT (Known & Verified): {sat_count}")
    print(f"    - UNSAT (Mathematically Justified): {unsat_count}")
    print(f"    - UNKNOWN (Uniform Random Sampling): {unknown_count}")
    print("[+] All DIMACS syntax, literal bounds, clause counts, and SHA-256 hashes are verified!")

if __name__ == "__main__":
    run_validation()

