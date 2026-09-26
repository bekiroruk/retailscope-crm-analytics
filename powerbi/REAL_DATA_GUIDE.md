# Power BI — UCI real-data model

Use the CSV files in `outputs/real/marts/`. Import them as UTF-8 and use the
English (United States) locale for decimal parsing. Currency is GBP.

## Relationships

| One | Many | Direction |
|---|---|---|
| `dim_customer.customer_id` | `fact_sales.customer_id` | Single |
| `dim_product.product_id` | `fact_sales.product_id` | Single |
| `dim_date.date` | `fact_sales.event_date` | Single |
| `dim_customer.customer_id` | `customer_scores.customer_id` | Single |

Mark `dim_date[date]` as the date table. Do not connect `snapshot_date` to the
transaction date relationship. Use a single-select `snapshot_date` slicer for
score visuals. Add each expression in `real_measures.dax` as a separate measure.

## Suggested report pages

| Page | Visuals |
|---|---|
| Executive overview | Net revenue, orders, customers, monthly trend, return-value rate |
| Customer 360 | RFM segment, risk distribution, recency/frequency scatter, customer table |
| Revenue outlook | Expected 90-day revenue, risk-versus-value scatter, top products |
| Cohorts | `cohort_retention` matrix: cohort × month index, maximum retention rate |
| Data quality | Accepted/quarantined/duplicate rows from `data_quality.json` |

The public data does not contain cost, category, brand, contact, or marketing
consent fields. Do not label revenue as margin, calculate campaign ROI, or use
the score table as an activation audience. A `.pbix` must be created and
validated in Power BI Desktop on Windows; this repository does not claim that
Desktop validation occurred in the Linux build environment.
