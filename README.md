# RetailScope

RetailScope is a reproducible retail CRM analytics project covering customer identity resolution, RFM segmentation, 90-day inactivity risk, customer value estimation, campaign targeting, SQL Server integration, and Power BI-ready data marts.

The project uses fully synthetic data. It contains no real customer records, company data, or measured campaign outcomes.

## What it delivers

| Capability | Output |
|---|---|
| Customer identity resolution | Conservative record linkage with match rules and review flags |
| Data quality | Duplicate control, quarantine reasons, return validation, row reconciliation |
| Customer analytics | RFM segments, channel behavior, category, brand, and product affinity |
| Risk modeling | Probability of no purchase in the next 90 days |
| Customer value | 90-day gross-margin forecast and an explicit three-year LTV scenario |
| CRM activation | Ranked candidates with deterministic treatment/control assignment |
| Reporting | Self-contained interactive HTML dashboard and Power BI-ready tables |
| Data platform | SQL Server schema, views, ad-hoc queries, and transactional loader |

## Analytics workflow

`Synthetic events → identity resolution → validation and quarantine → time-based features → model selection → held-out evaluation → CRM scores → reporting`

The feature window ends before the prediction cutoff. Training, validation, and test outcome windows do not overlap. Model selection uses validation data; the test period is reserved for final reporting.

## Validation snapshot

Results below come from the deterministic synthetic run with seed `42`.

| Metric | Result |
|---|---:|
| Source customer records | 2,266 |
| Unified customers | 1,800 |
| Accepted transaction events | 81,489 |
| Quarantined events | 2 |
| Scored customers | 1,368 |
| Automated tests | 14 passed |
| Test customers | 1,499 |
| Inactivity Average Precision | 0.7300 |
| Inactivity ROC-AUC | 0.8727 |
| Top-20% lift | 3.259× |
| 90-day value MAE | 1,706.12 TRY |

The value model has a WAPE of 73.93% and an aggregate positive bias of approximately 29.3%. It is therefore a portfolio baseline, not a production budgeting model. Full evidence and limitations are recorded in [`docs/VALIDATION.md`](docs/VALIDATION.md) and [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md).

## Quick start

Requirements: Python 3.12. GPU is not required.

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m retailscope all
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
Start-Process .\outputs\reports\dashboard.html
```

### Linux or macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m retailscope all
.venv/bin/python -m unittest discover -s tests -v
```

The pipeline writes generated source data to `data/` and derived artifacts to `outputs/`. Both directories are excluded from Git because they are reproducible.

## Repository structure

```text
retailscope/       Analytics package: generation, identity, quality, features, models, CRM, reports
tests/             Identity, accounting, temporal leakage, and targeting tests
sql/               SQL Server schema, views, and analysis queries
powerbi/           Data model instructions and DAX measures
templates/         Offline HTML dashboard template
scripts/           Windows runner and optional SQL Server loader
docs/              Data dictionary, model card, validation record, sources, and project plan
```

## SQL Server and Power BI

The Python pipeline is executable and tested. SQL Server and Power BI assets are implementation-ready but have not been executed in a live SQL Server instance or validated in Power BI Desktop.

- [`sql/schema.sql`](sql/schema.sql) defines the star-schema tables, keys, indexes, and views.
- [`scripts/load_sqlserver.py`](scripts/load_sqlserver.py) loads five empty target tables in a single transaction and refuses destructive overwrite.
- [`powerbi/README.md`](powerbi/README.md) documents relationships, data types, pages, and refresh behavior.
- [`powerbi/measures.dax`](powerbi/measures.dax) contains the report measures.

## Documentation

- [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) — table grains, field definitions, and accounting rules
- [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md) — population, temporal design, metrics, limitations, and LTV assumptions
- [`docs/VALIDATION.md`](docs/VALIDATION.md) — executed checks and measured synthetic results
- [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) — path from synthetic prototype to real-data validation
- [`docs/SOURCES.md`](docs/SOURCES.md) — data strategy and technical references

## Scope and responsible use

- The inactivity target means **no sale in the next 90 days**; it is not contractual churn or proven brand abandonment.
- Current consent is used only as a campaign eligibility rule, never as a model feature.
- High predicted risk does not imply positive campaign uplift. A randomized experiment is required to estimate incremental impact.
- The generated treatment/control split is an experiment plan. No communication is sent and no ROI is claimed.
- Identity hashes are not an anonymization guarantee. A production implementation needs governed identifiers, consent history, and merge lineage.
- Product prices, costs, customers, brands, and transactions are fictional and must not be interpreted as results from any retailer.

## Status

Version `0.1.0` is a tested synthetic reference implementation. The next milestone is a validated real-data adapter followed by repeated time-based backtests and a Power BI Desktop implementation.
