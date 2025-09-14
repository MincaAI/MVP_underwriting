#!/usr/bin/env python3
"""
Evaluate codifier accuracy using labeled test data.

This script tests the codifier pipeline against labeled vehicle data to measure
accuracy, auto-accept rates, and precision metrics.
"""

import csv
import argparse
import sys
import pathlib

# Add packages to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "packages" / "db" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "packages" / "ml" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "services" / "worker-codifier" / "src"))

from app.ml.normalize import normalize_text
from worker_codifier.main import build_label, top_k
from worker_codifier.rerank import rerank
from worker_codifier.policy import decision_for

def eval_file(path: str, t_high: float = 0.90, t_low: float = 0.70, k: int = 25):
    """
    Evaluate codifier performance on labeled test file.
    
    Args:
        path: Path to CSV file with labeled test data
        t_high: High threshold for auto-acceptance
        t_low: Low threshold for review requirement  
        k: Number of candidates to retrieve
    """
    n = 0
    top1 = 0
    auto = 0
    needs = 0
    miss = 0
    auto_correct = 0
    
    print(f"Evaluating codifier with thresholds: t_high={t_high}, t_low={t_low}")
    print(f"Using top-{k} candidates")
    print("-" * 60)
    
    try:
        with open(path, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                n += 1
                
                # Build label for query
                year_val = None
                if row.get("year"):
                    try:
                        year_val = int(row["year"])
                        if year_val == 0:
                            year_val = None
                    except (ValueError, TypeError):
                        year_val = None
                
                qlabel = build_label(
                    row.get("brand"), 
                    row.get("model"), 
                    year_val,
                    row.get("body"), 
                    row.get("use"), 
                    row.get("description")
                )
                
                # Get candidates
                cands = top_k(
                    row.get("brand", ""), 
                    row.get("model", ""), 
                    year_val,
                    row.get("body"), 
                    row.get("use"), 
                    row.get("description"), 
                    k=k
                )
                
                # Rerank candidates
                ranked = rerank(qlabel, cands)
                
                # Get prediction and decision
                pred = ranked[0][0] if ranked else None
                score = ranked[0][1] if ranked else 0.0
                dec = decision_for(score, t_high, t_low)
                
                # Update metrics
                true_cvegs = row.get("cvegs_true", "")
                top1 += int(pred == true_cvegs)
                auto += int(dec == "auto_accept")
                needs += int(dec == "needs_review") 
                miss += int(dec == "no_match")
                auto_correct += int(dec == "auto_accept" and pred == true_cvegs)
                
                # Print progress every 10 rows
                if n % 10 == 0:
                    print(f"Processed {n} rows...")
    
    except FileNotFoundError:
        print(f"Error: File {path} not found")
        return
    except Exception as e:
        print(f"Error processing file: {e}")
        return
    
    # Print final results
    print("\\n" + "=" * 60)
    print("CODIFIER EVALUATION RESULTS")
    print("=" * 60)
    print(f"Total rows evaluated: {n}")
    print(f"Top-1 accuracy: {top1/n:.3f} ({top1}/{n})")
    print()
    print("Decision Distribution:")
    print(f"  Auto-accept: {auto/n:.3f} ({auto}/{n})")
    print(f"  Needs review: {needs/n:.3f} ({needs}/{n})")
    print(f"  No match: {miss/n:.3f} ({miss}/{n})")
    print()
    print("Auto-Accept Quality:")
    auto_precision = auto_correct/max(auto, 1)
    print(f"  Auto-accept precision: {auto_precision:.3f} ({auto_correct}/{auto})")
    print()
    print("Threshold Analysis:")
    print(f"  t_high = {t_high} (auto-accept threshold)")
    print(f"  t_low = {t_low} (review threshold)")
    
    # Recommendations
    print("\\nRECOMMENDATIONS:")
    if auto_precision < 0.98:
        print(f"⚠️  Auto-accept precision ({auto_precision:.3f}) is below 0.98")
        print(f"   → Consider raising t_high from {t_high} to {t_high + 0.05:.2f}")
    else:
        print(f"✅ Auto-accept precision ({auto_precision:.3f}) meets target ≥ 0.98")
    
    if auto/n < 0.5:
        print(f"⚠️  Auto-accept rate ({auto/n:.3f}) is low")
        print("   → Consider enriching alias dictionaries")
        print("   → Consider lowering t_high if precision allows")
    else:
        print(f"✅ Auto-accept rate ({auto/n:.3f}) is acceptable")
    
    if miss/n > 0.2:
        print(f"⚠️  No-match rate ({miss/n:.3f}) is high")
        print("   → Consider lowering t_low threshold")
        print("   → Review AMIS catalogue coverage")
    else:
        print(f"✅ No-match rate ({miss/n:.3f}) is acceptable")

def main():
    parser = argparse.ArgumentParser(description="Evaluate codifier accuracy")
    parser.add_argument("--file", required=True, help="Path to labeled CSV file")
    parser.add_argument("--t_high", type=float, default=0.90, 
                       help="High threshold for auto-accept (default: 0.90)")
    parser.add_argument("--t_low", type=float, default=0.70,
                       help="Low threshold for review (default: 0.70)")
    parser.add_argument("--k", type=int, default=25,
                       help="Number of candidates to retrieve (default: 25)")
    
    args = parser.parse_args()
    
    eval_file(args.file, args.t_high, args.t_low, args.k)

if __name__ == "__main__":
    main()