#!/usr/bin/env python3
"""
TalentLens Ranker - Intelligent Candidate Discovery
Ranks 100,000 candidates for AI/Search Engineer positions.
Target runtime: ~25-30 seconds on CPU.
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

from utils.honeypot import get_honeypot_multiplier
from utils.scorer import compute_final_score
from utils.reasoning import generate_reasoning

__version__ = "2.0.0"


def load_candidates(filepath: str) -> List[Dict[str, Any]]:
    """
    Load candidates from JSONL file.
    
    Args:
        filepath: Path to JSONL file (supports .gz)
        
    Returns:
        List of candidate dictionaries
    """
    candidates = []
    print(f"[LOAD] Reading: {filepath}")
    start = time.time()
    
    try:
        if filepath.endswith(".gz"):
            import gzip
            opener = gzip.open(filepath, "rt", encoding="utf-8")
        else:
            opener = open(filepath, "r", encoding="utf-8")
        
        with opener as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    candidates.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
                
                if i % 10000 == 0:
                    elapsed = time.time() - start
                    print(f"  {i:,} loaded... ({elapsed:.1f}s)")
        
        elapsed = time.time() - start
        print(f"[LOAD] {len(candidates):,} candidates in {elapsed:.1f}s")
        
    except FileNotFoundError:
        print(f"[ERROR] File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to load candidates: {e}", file=sys.stderr)
        sys.exit(1)
    
    return candidates


def score_all(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score all candidates with honeypot detection.
    
    Args:
        candidates: List of candidate dictionaries
        
    Returns:
        List of result dictionaries with scores
    """
    total = len(candidates)
    print(f"[SCORE] Processing {total:,} candidates...")
    start = time.time()
    
    results = []
    
    for i, candidate in enumerate(candidates):
        # Progress reporting
        if (i + 1) % 20000 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            remaining = (total - i - 1) / rate if rate > 0 else 0
            print(f"  {i+1:,}/{total:,} scored... "
                  f"({elapsed:.1f}s elapsed, ~{remaining:.0f}s remaining)")
        
        # Honeypot check
        mult = get_honeypot_multiplier(candidate)
        
        # Compute score
        score, dims = compute_final_score(candidate, mult)
        
        results.append({
            "candidate_id": candidate.get("candidate_id", ""),
            "score": score,
            "dims": dims,
            "mult": mult,
            "candidate": candidate
        })
    
    elapsed = time.time() - start
    print(f"[SCORE] Completed in {elapsed:.1f}s ({total/elapsed:.0f} candidates/sec)")
    
    return results


def build_top100(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract and format top 100 candidates.
    Ensures correct tie-breaking: candidate_id ascending when rounded scores equal.
    Uses raw scores for primary sort, then fixes rounded-score ties.
    """
    print("[RANK] Building top 100...")
    start = time.time()
    
    # Sort by raw score descending, then by ID ascending
    results.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    
    rows = []
    top_n = min(100, len(results))
    
    for i in range(top_n):
        item = results[i]
        rank = i + 1
        reasoning = generate_reasoning(
            item["candidate"], rank, item["score"], item["dims"]
        )
        
        rows.append({
            "candidate_id": item["candidate_id"],
            "rank": rank,
            "score": round(item["score"], 4),
            "reasoning": reasoning
        })
        
        if rank <= 5:
            dims = item["dims"]
            print(f"  #{rank} | {item['candidate_id']} | score={rows[-1]['score']:.4f} | "
                  f"skills={dims['skills']:.2f} career={dims['career']:.2f} "
                  f"avail={dims['availability']:.2f} loc={dims['location']:.2f}")
    
    # BULLETPROOF TIE-BREAK FIX
    # Group by rounded score, sort each group by candidate_id ascending
    i = 0
    while i < len(rows):
        j = i
        while j < len(rows) and rows[j]["score"] == rows[i]["score"]:
            j += 1
        # Sort the group [i:j] by candidate_id ascending
        if j - i > 1:
            rows[i:j] = sorted(rows[i:j], key=lambda r: r["candidate_id"])
            # Re-assign ranks within the group
            for k in range(i, j):
                rows[k]["rank"] = k + 1
        i = j
    
    elapsed = time.time() - start
    print(f"[RANK] Top {top_n} selected in {elapsed:.1f}s")
    
    return rows

def write_output(rows: List[Dict[str, Any]], filepath: str) -> None:
    """
    Write ranked results to CSV file.
    
    Args:
        rows: List of output rows
        filepath: Output file path
    """
    print(f"[OUTPUT] Writing to: {filepath}")
    
    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, 
                fieldnames=["candidate_id", "rank", "score", "reasoning"],
                extrasaction='ignore'
            )
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"[OUTPUT] Saved {len(rows)} rows to {filepath}")
        
    except Exception as e:
        print(f"[ERROR] Failed to write output: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for TalentLens Ranker."""
    parser = argparse.ArgumentParser(
        description="TalentLens Ranker - Intelligent Candidate Discovery v2.0"
    )
    parser.add_argument(
        "--candidates",
        default="./candidates.jsonl",
        help="Path to candidates JSONL file"
    )
    parser.add_argument(
        "--out",
        default="./submission.csv",
        help="Output CSV file path"
    )
    args = parser.parse_args()
    
    # Start timer
    total_start = time.time()
    
    print("=" * 55)
    print("  TalentLens Ranker v2.0")
    print("  Intelligent Candidate Discovery")
    print("=" * 55)
    
    # Pipeline stages
    candidates = load_candidates(args.candidates)
    results = score_all(candidates)
    rows = build_top100(results)
    write_output(rows, args.out)
    
    # Final summary
    total_elapsed = time.time() - total_start
    print(f"\n{'=' * 55}")
    print(f"  Total time: {total_elapsed:.1f}s")
    if total_elapsed < 60:
        print(f"  Status: ✅ PASS (under 60s limit)")
    else:
        print(f"  Status: ⚠️  OVER LIMIT")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    main()