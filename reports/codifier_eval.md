# Codifier Evaluation Report

## Overview
This report contains the evaluation results for the vehicle codifier system using labeled test data.

## Test Configuration
- **Test Dataset**: `data/samples/labeled_100.csv`
- **Test Size**: 50 labeled vehicle records
- **Evaluation Metrics**: Top-1 accuracy, auto-accept rate, auto-accept precision
- **Candidate Pool**: Top-25 similar vehicles from AMIS catalogue

## Baseline Thresholds
- **t_high = 0.90**: Auto-accept threshold
- **t_low = 0.70**: Review requirement threshold

## Expected Results Structure

```
CODIFIER EVALUATION RESULTS
============================================================
Total rows evaluated: 50
Top-1 accuracy: 0.XXX (XX/50)

Decision Distribution:
  Auto-accept: 0.XXX (XX/50)  
  Needs review: 0.XXX (XX/50)
  No match: 0.XXX (XX/50)

Auto-Accept Quality:
  Auto-accept precision: 0.XXX (XX/XX)

Threshold Analysis:
  t_high = 0.90 (auto-accept threshold)
  t_low = 0.70 (review threshold)
```

## Evaluation Instructions

To run the evaluation:

```bash
# Ensure development environment is running
make dev

# Load AMIS catalogue if not already loaded
./tools/load_amis.py --file data/amis_sample.xlsx

# Build embeddings for semantic search
./tools/build_embeddings.py --batch-size 32

# Run codifier evaluation
./tools/eval_codifier.py --file data/samples/labeled_100.csv --t_high 0.90 --t_low 0.70
```

## Target Metrics

### Quality Targets
- **Auto-accept precision**: ≥ 0.98 (98% of auto-accepted predictions must be correct)
- **Top-1 accuracy**: ≥ 0.85 (85% of top predictions should be correct)

### Throughput Targets  
- **Auto-accept rate**: ≥ 0.50 (50% of cases should be auto-processed)
- **No-match rate**: ≤ 0.20 (Less than 20% should be unmatched)

## Threshold Tuning Guidelines

### If Auto-Accept Precision < 0.98
- **Action**: Increase t_high threshold
- **Increment**: +0.05 steps (0.90 → 0.95 → 0.97, etc.)
- **Trade-off**: Higher precision, lower auto-accept rate

### If Auto-Accept Rate < 0.50  
- **Action**: Enrich alias dictionaries
- **Files**: `configs/aliases/brands.yaml`, `models.yaml`, `bodies.yaml`
- **Alternative**: Lower t_high if precision allows

### If No-Match Rate > 0.20
- **Action**: Lower t_low threshold  
- **Increment**: -0.05 steps (0.70 → 0.65 → 0.60)
- **Check**: Ensure AMIS catalogue coverage is adequate

## Production Recommendations

Based on evaluation results, the recommended production thresholds will be:

- **t_high**: [To be determined from evaluation]
- **t_low**: [To be determined from evaluation]

## Notes
- This evaluation assumes the AMIS catalogue contains the ground truth CVEGS codes
- Real-world performance may vary based on data quality and coverage
- Regular re-evaluation is recommended as the system processes more data