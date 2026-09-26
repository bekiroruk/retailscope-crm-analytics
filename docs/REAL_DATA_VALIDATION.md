# Real-data validation record

## Source and run

- Dataset: UCI Machine Learning Repository, **Online Retail II**
- DOI: `10.24432/C5CG6D`
- License: CC BY 4.0
- Observation period: 1 December 2009 through 9 December 2011
- Workbook SHA-256: `bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980`
- Runtime: Python 3.12, seed 42

## Data reconciliation

| Check | Result |
|---|---:|
| Raw rows | 1,067,371 |
| Exact duplicate rows removed | 34,335 |
| Rows quarantined after deduplication | 235,151 |
| Accepted events | 797,885 |
| Known customers | 5,942 |
| Products | 4,646 |
| Sale orders | 36,975 |
| Return rows | 18,390 |

Every quarantined row is missing `Customer ID`. The accounting identity
`raw = duplicate + quarantine + accepted` holds. Seventy zero-price rows are
retained because they can represent free items or operational adjustments.

## Temporal evaluation

Features use the 365 days strictly before each cutoff. Customers are eligible
when their last sale is at most 180 days before the cutoff. Labels cover the
following 90 days. Training, validation, and test outcome windows do not
overlap.

| Split | Cutoff(s) | Rows |
|---|---|---:|
| Train | 2010-12-01, 2011-03-01 | 6,828 |
| Validation | 2011-06-01 | 2,659 |
| Test | 2011-09-01 | 2,772 |
| Production-style score | 2011-12-10 | 3,478 |

## Held-out test results

| Metric | Model | Baseline |
|---|---:|---:|
| Inactivity Average Precision | 0.6534 | 0.3929 prior |
| Inactivity ROC-AUC | 0.7665 | 0.5000 prior |
| Top-20% lift | 1.784× | 1.573× recency ranking |
| Brier loss | 0.2148 | 0.2704 prior |
| 90-day net-revenue MAE | £588.67 | £845.93 mean |
| 90-day net-revenue WAPE | 69.04% | 99.21% mean |

The classifier and value model are both histogram gradient boosting, selected
only on the validation period. The value model underpredicts aggregate test
revenue and is not suitable for budgeting without further calibration.

## Responsible-use limits

- No cost field: revenue is not gross margin, LTV, profit, or ROI.
- No category or brand field: product descriptions are not converted into
  invented business taxonomies.
- No consent or contact data: every score is marked `activation_eligible=false`.
- No campaign outcome: high risk is not evidence of positive treatment uplift.
- A customer can appear in multiple time snapshots; this evaluates future
  scoring of existing customers, not unseen-customer generalization.
