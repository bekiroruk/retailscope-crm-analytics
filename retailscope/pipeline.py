from pathlib import Path
import hashlib
import json
import platform

import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits

from .crm import campaign_candidates, cohort_retention, customer_affinity, ltv_scenario
from .features import attach_labels, segment, snapshot
from .identity import resolve
from .models import fit_evaluate
from .quality import clean_events
from .report import write_report


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def validate_config(c, metadata):
    horizon = pd.Timedelta(days=c["horizon_days"])
    cutoffs = [pd.Timestamp(x) for x in c["train_cutoffs"]]
    validation, test, score = [pd.Timestamp(c[k]) for k in ["validation_cutoff", "test_cutoff", "score_cutoff"]]
    if (c["history_days"], c["horizon_days"], c["active_days"]) != (365, 90, 180):
        raise ValueError("v0.1 implements 365-day history, 90-day target, 180-day eligibility. Rename features and targets before changing these.")
    if not cutoffs or cutoffs != sorted(set(cutoffs)):
        raise ValueError("Training cutoffs must be distinct and sorted.")
    if not (max(cutoffs) + horizon <= validation and validation + horizon <= test and test + horizon <= score):
        raise ValueError("Overlapping outcome windows across train/validation/test/scoring.")
    end = pd.Timestamp(metadata["observed_until_exclusive"])
    if end != pd.Timestamp(c["observed_until_exclusive"]) or score != end:
        raise ValueError("Config and raw data must agree on the exclusive observation end / score cutoff.")
    if metadata["source"] != "synthetic":
        raise ValueError("Use a separately validated real-data adapter; v0.1 is a synthetic reference pipeline.")


def run(root: Path, config: dict):
    raw, output = root / "data" / "raw", root / "outputs"
    marts, reports = output / "marts", output / "reports"
    for directory in [marts, reports]:
        directory.mkdir(parents=True, exist_ok=True)
    metadata = json.loads((raw / "metadata.json").read_text(encoding="utf-8"))
    validate_config(config, metadata)
    customers = pd.read_csv(raw / "customers.csv", keep_default_na=False)
    products = pd.read_csv(raw / "products.csv", keep_default_na=False)
    raw_events = pd.read_csv(raw / "events.csv", keep_default_na=False)
    dim, mapping = resolve(customers)
    events, quarantine, quality = clean_events(raw_events, products, mapping, metadata["observed_until_exclusive"])
    quality.update(raw_customer_records=len(customers), unified_customers=len(dim),
                   collapsed_records=len(customers) - len(dim),
                   identity_review_customers=int(dim.identity_review_required.sum()))
    frames = {}
    all_cutoffs = config["train_cutoffs"] + [config["validation_cutoff"], config["test_cutoff"]]
    for cutoff in all_cutoffs:
        f = snapshot(events, cutoff)
        frames[cutoff] = attach_labels(f, events, cutoff, metadata["observed_until_exclusive"])
    train = pd.concat([frames[c] for c in config["train_cutoffs"]], ignore_index=True)
    validation, test = frames[config["validation_cutoff"]], frames[config["test_cutoff"]]
    scoring = snapshot(events, config["score_cutoff"])
    with threadpool_limits(limits=2):
        scores, metrics, importance, predictions = fit_evaluate(train, validation, test, scoring,
                                                               output / "models", config["seed"])
    scores = segment(scores).merge(dim, on="customer_id", validate="one_to_one")
    scores = scores.merge(customer_affinity(events, config["score_cutoff"]), on="customer_id", how="left", validate="one_to_one")
    scores["ltv_3year_scenario"] = ltv_scenario(scores.expected_margin90)
    campaign = campaign_candidates(scores, config["campaign_capacity"], config["control_fraction"], config["seed"])
    cohorts = cohort_retention(events, config["score_cutoff"])
    event_dates = pd.to_datetime(events.event_time).dt.normalize()
    fact = events[["event_id", "order_id", "customer_id", "product_id", "event_type", "channel", "signed_quantity", "net_revenue", "gross_margin"]].copy()
    fact["event_date"] = event_dates.dt.strftime("%Y-%m-%d")
    calendar = pd.DataFrame({"date":pd.date_range(config["start"], pd.Timestamp(config["score_cutoff"]) - pd.Timedelta(days=1))})
    calendar["year"] = calendar.date.dt.year
    calendar["month"] = calendar.date.dt.month
    calendar["year_month"] = calendar.date.dt.strftime("%Y-%m")
    calendar["date"] = calendar.date.dt.strftime("%Y-%m-%d")
    # Snapshot fields live in their own fact table; dimensions cover all observed customers.
    score_columns = ["customer_id", "snapshot_date", "segment", "rfm_score", "r_score", "f_score", "m_score",
                     "recency_days", "frequency_365", "net_revenue_365", "gross_margin_365", "inactive_risk90",
                     "expected_margin90", "ltv_3year_scenario", "top_category", "top_brand", "top_product_id"]
    tables = {"dim_customer": dim, "identity_audit": mapping, "dim_product": products, "dim_date": calendar,
              "fact_sales": fact, "customer_scores": scores[score_columns], "campaign_candidates":campaign,
              "cohort_retention":cohorts, "quarantine":quarantine}
    for name, table in tables.items():
        table.to_csv(marts / f"{name}.csv", index=False, encoding="utf-8-sig")
    pd.concat(frames.values(), ignore_index=True).to_csv(marts / "labeled_snapshots.csv", index=False, encoding="utf-8-sig")
    importance.to_csv(reports / "feature_importance.csv", index=False, encoding="utf-8-sig")
    predictions.to_csv(reports / "test_predictions.csv", index=False, encoding="utf-8-sig")
    metrics["split_dates"] = {k:config[k] for k in ["train_cutoffs", "validation_cutoff", "test_cutoff", "score_cutoff"]}
    save_json(reports / "metrics.json", metrics)
    save_json(reports / "data_quality.json", quality)
    manifest = dict(project="RetailScope", version="0.1.0", config=config, source=metadata,
                    python=platform.python_version(), pandas=pd.__version__, numpy=np.__version__, sklearn=sklearn.__version__,
                    inputs_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(raw.iterdir()) if p.is_file()})
    save_json(reports / "run_manifest.json", manifest)
    write_report(reports, root / "templates" / "dashboard.html", events, scores, campaign, cohorts, quality, metrics, config)
    return dict(customers=len(dim), scored_customers=len(scores), accepted_events=len(events),
                candidates=len(campaign), classifier=metrics["selected_classifier"],
                test_average_precision=round(metrics["test_classification"]["average_precision"], 4),
                report=str(reports / "dashboard.html"))
