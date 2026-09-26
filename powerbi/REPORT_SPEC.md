# RetailScope report specification

Use a 16:9 canvas, 24 px outer margins, and a consistent 12-column grid. Keep
page backgrounds off-white (`#F6F7F3`), use deep teal for primary marks, and
reserve coral for exceptions or comparison—not decoration. Titles should state
the metric and time frame without acronyms where space permits.

## 1 — Executive Overview

**Question:** What happened in the business, and how large is the customer base?

| Zone | Visual | Binding |
|---|---|---|
| Top row | Four cards | Net Revenue; Sale Orders; Purchasing Customers; Return Value Rate |
| Main left | Line chart | `dim_date[year_month]` × Net Revenue |
| Main right | Horizontal bar | `customer_scores[segment]` × Scored Customers |
| Footer | Text note | Source, GBP currency, scoring cutoff, and activation limitation |

Sort `year_month` ascending and segments by customer count descending. Cards use
large values with compact supporting labels; no gauge visuals.

## 2 — Customer Portfolio

**Question:** Which customers and segments show the strongest risk/value signal?

| Zone | Visual | Binding |
|---|---|---|
| Header | Single-select slicer | `customer_scores[snapshot_date]` |
| Left | Segment bar chart | Segment × Scored Customers |
| Center | Scatter plot | Recency × 365-day net revenue; risk as color; customer ID as detail |
| Bottom | Detail table | Customer, segment, recency, frequency, revenue, inactivity risk |

Use risk as a continuous color scale with accessible contrast. Do not label this
page as a campaign audience: source data lacks consent and contact fields.

## 3 — Risk & Value

**Question:** How useful are the scores, and where is analytical priority highest?

| Zone | Visual | Binding |
|---|---|---|
| Top row | Four cards | Average 90D Inactivity Risk; Expected 90D Revenue; Held-out Top-20% Lift; Revenue MAE Improvement |
| Main | Scatter plot | Inactivity risk × expected revenue; analytical priority as size; customer ID as detail |
| Side | Metrics table | `model_metrics[label]`, value, baseline |

Add a visible subtitle: “Prioritization score; not campaign uplift.” Keep model
and baseline values side by side so accuracy is never presented without a
reference point.

## 4 — Cohorts & Quality

**Question:** How does retention evolve, and can the source totals be trusted?

| Zone | Visual | Binding |
|---|---|---|
| Main left | Matrix heatmap | Cohort rows; month-index columns; maximum retention rate |
| Top right | Three cards | Accepted rows; Quarantined rows; Row reconciliation |
| Bottom right | Horizontal bar | Quality metric label × value |

Turn off matrix subtotals. Format retention as a percentage and leave
unobserved future cells blank. Color the reconciliation card teal only when its
value is `1`.

## Formatting and accessibility

- Minimum body text: 11 pt; minimum card label: 10 pt.
- Use sentence case and no rotated labels.
- Provide alt text for every non-decorative visual.
- Do not rely on color alone for pass/fail or model/baseline comparisons.
- Keep decimal precision intentional: revenue to 0–2 decimals, rates to 1–2
  points, AP/ROC-AUC to three decimals, lift to two decimals.
- Verify tab order and keyboard focus after the final layout pass.

## Desktop acceptance pass

1. Refresh all eight queries with no errors.
2. Confirm the four active relationships and the marked date table.
3. Check all cards against `outputs/real/reports/metrics.json` and
   `data_quality.json`.
4. Test the snapshot, date, country, and segment interactions.
5. Review at 100% zoom and at a narrow laptop width.
6. Save the final `.pbix` and, if desired, a PBIP copy for source control.
