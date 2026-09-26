# Real-data model guide

## Grain and semantics

| Table | Grain | Primary analytical use |
|---|---|---|
| `fact_sales` | One accepted sale or return line | Revenue, orders, customers, products, returns |
| `dim_customer` | One identified customer | Country and customer filtering |
| `dim_product` | One product code | Product filtering and ranking |
| `dim_date` | One calendar date | Transaction time analysis |
| `customer_scores` | One customer at the 2011-12-10 cutoff | RFM segment, inactivity risk, expected revenue |
| `cohort_retention` | One acquisition cohort and month index | Retention matrix |
| `model_metrics` | One held-out evaluation metric | Model-versus-baseline evidence |
| `data_quality_metrics` | One quality or reconciliation metric | Pipeline control totals |

Currency is GBP. CSV files use UTF-8 with BOM, ISO dates, and a period as the
decimal separator. The supplied Power Query expressions apply the `en-US`
locale so decimal parsing does not depend on the workstation locale.

## Important calculation choices

- Net revenue includes returns. `Return Value` changes the sign of negative
  return rows for display.
- Sale orders count distinct sale invoice IDs. Do not use `COUNTROWS` as an
  order count.
- The customer score table contains analytical scores only. Its public source
  has neither contact details nor marketing consent, so
  `activation_eligible=false` for every row.
- “Inactivity” means no sale in the next 90 days among customers whose last sale
  was at most 180 days before the cutoff. It is not contractual churn.
- Expected revenue is a 90-day regression output. It is not margin, lifetime
  value, campaign uplift, or ROI.
- Cohort retention uses `MAX(retention_rate)` in each cohort/month cell. Future
  cells remain blank; they must not be filled with zero.

## Filter behavior

The date dimension filters transaction facts only. Score visuals use
`customer_scores[snapshot_date]` as a single-select slicer. Segment filters do
not intentionally back-filter historical transactions through a bidirectional
relationship; that would answer an ambiguous “current segment applied to past
sales” question. If that analysis is later required, implement a documented
`TREATAS` measure for the specific visual.

## Acceptance criteria

- `Net Revenue`, `Sale Orders`, and `Purchasing Customers` reconcile to the
  generated HTML dashboard for the unfiltered period.
- `Data Reconciliation Passed` equals `1`.
- The model metric cards show AP `0.6534`, ROC-AUC `0.7665`, top-20% lift
  `1.784×`, and revenue MAE `£588.67` for the delivered UCI run.
- Selecting a customer segment changes score visuals but does not silently
  reinterpret historic sales.
- No visual describes predicted revenue as profit, LTV, or incremental impact.
