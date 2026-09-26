"""Create a one-row relational fixture for the live SQL Server CI smoke test."""
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "outputs" / "real" / "marts"

ROWS = {
    "dim_customer": [{"customer_id": "UCI-1", "country": "United Kingdom"}],
    "dim_product": [{"product_id": "P1", "product_name": "Test product"}],
    "dim_date": [{"date": "2011-12-09", "year": 2011, "month": 12, "year_month": "2011-12"}],
    "fact_sales": [{"event_id": "UCI-SMOKE-1", "order_id": "I1", "customer_id": "UCI-1",
                    "product_id": "P1", "event_type": "sale", "signed_quantity": 2,
                    "unit_price": 10.5, "net_revenue": 21, "event_date": "2011-12-09"}],
    "customer_scores": [{"customer_id": "UCI-1", "snapshot_date": "2011-12-10",
                         "segment": "Champions", "rfm_score": "555", "r_score": 5,
                         "f_score": 5, "m_score": 5, "recency_days": 1,
                         "frequency_365": 1, "net_revenue_365": 21,
                         "inactive_risk90": 0.25, "expected_revenue90": 20,
                         "top_product_id": "P1", "top_product_name": "Test product",
                         "activation_eligible": False,
                         "activation_exclusion_reason": "Consent and contact data are unavailable in the public dataset",
                         "analysis_priority": 5}],
}


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, rows in ROWS.items():
        with (TARGET / f"{name}.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(f"Created SQL smoke-test marts in {TARGET}")


if __name__ == "__main__":
    main()
