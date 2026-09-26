"""Adapter and leakage-safe modeling pipeline for UCI Online Retail II."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import platform

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from .crm import cohort_retention
from .models import classification_metrics, regression_metrics


REAL_FEATURES = [
    "recency_days", "tenure_days", "frequency_365", "frequency_90",
    "frequency_previous90", "net_revenue_365", "net_revenue_90",
    "average_order_value", "product_count", "units_365",
    "return_value_rate", "order_trend",
]


def _save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def load_uci_workbook(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Load both workbook sheets and return clean events, dimensions and quality evidence."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    parts = []
    workbook = pd.ExcelFile(path)
    for sheet in workbook.sheet_names:
        part = pd.read_excel(path, sheet_name=sheet)
        part["source_sheet"] = sheet
        part["source_row"] = np.arange(2, len(part) + 2)
        parts.append(part)
    raw = pd.concat(parts, ignore_index=True)
    required = {"Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"}
    missing = required.difference(raw.columns)
    if missing:
        raise ValueError(f"UCI workbook is missing columns: {sorted(missing)}")

    duplicate_columns = sorted(required)
    duplicate = raw.duplicated(subset=duplicate_columns, keep="first")
    work = raw.loc[~duplicate].copy()
    work["InvoiceDate"] = pd.to_datetime(work["InvoiceDate"], errors="coerce")
    work["Quantity"] = pd.to_numeric(work["Quantity"], errors="coerce")
    work["Price"] = pd.to_numeric(work["Price"], errors="coerce")
    work["Customer ID"] = pd.to_numeric(work["Customer ID"], errors="coerce")
    invoice = work["Invoice"].astype("string").str.strip()
    stock = work["StockCode"].astype("string").str.strip()
    reason = pd.Series("", index=work.index, dtype="string")
    checks = [
        (work["Customer ID"].isna(), "missing_customer_id"),
        (work["InvoiceDate"].isna(), "invalid_invoice_date"),
        (invoice.isna() | invoice.eq(""), "missing_invoice"),
        (stock.isna() | stock.eq(""), "missing_stock_code"),
        (work["Quantity"].isna() | work["Quantity"].eq(0), "invalid_quantity"),
        (work["Price"].isna() | work["Price"].lt(0), "invalid_price"),
        (invoice.str.upper().str.startswith("C", na=False) & work["Quantity"].gt(0), "positive_cancellation"),
    ]
    for mask, label in checks:
        reason = reason.mask(reason.eq("") & mask, label)
    quarantine = work.loc[reason.ne("")].copy()
    quarantine["quarantine_reason"] = reason.loc[reason.ne("")]
    accepted = work.loc[reason.eq("")].copy()

    accepted["event_type"] = np.where(accepted["Quantity"].lt(0), "return", "sale")
    accepted["customer_id"] = "UCI-" + accepted["Customer ID"].astype("int64").astype(str)
    accepted["order_id"] = accepted["Invoice"].astype("string").str.strip()
    accepted["product_id"] = accepted["StockCode"].astype("string").str.strip()
    accepted["product_name"] = accepted["Description"].fillna("Description unavailable").astype(str).str.strip()
    accepted["country"] = accepted["Country"].fillna("Unknown").astype(str).str.strip()
    accepted["event_time"] = accepted["InvoiceDate"]
    accepted["signed_quantity"] = accepted["Quantity"].astype("int64")
    accepted["unit_price"] = accepted["Price"].astype(float)
    accepted["net_revenue"] = accepted["signed_quantity"] * accepted["unit_price"]
    accepted["event_id"] = (
        "UCI-" + accepted["source_sheet"].str.extract(r"(\d{4}-\d{4})", expand=False).fillna("sheet")
        + "-" + accepted["source_row"].astype(str)
    )
    events = accepted[["event_id", "order_id", "customer_id", "product_id", "product_name", "country",
                       "event_time", "event_type", "signed_quantity", "unit_price", "net_revenue"]].copy()
    events = events.sort_values(["event_time", "event_id"]).reset_index(drop=True)

    customers = (events.sort_values("event_time").groupby("customer_id", as_index=False)
                 .agg(country=("country", lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[-1])))
    products = (events.sort_values("event_time").groupby("product_id", as_index=False)
                .agg(product_name=("product_name", lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[-1])))
    reason_counts = quarantine["quarantine_reason"].value_counts().sort_index().astype(int).to_dict()
    quality = {
        "source": "UCI Online Retail II",
        "raw_rows": int(len(raw)),
        "exact_duplicates_removed": int(duplicate.sum()),
        "quarantined_rows": int(len(quarantine)),
        "accepted_rows": int(len(events)),
        "quarantine_reasons": reason_counts,
        "known_customers": int(events.customer_id.nunique()),
        "products": int(events.product_id.nunique()),
        "sale_orders": int(events.loc[events.event_type.eq("sale"), "order_id"].nunique()),
        "return_rows": int(events.event_type.eq("return").sum()),
        "zero_price_rows_accepted": int(events.unit_price.eq(0).sum()),
        "reconciled": int(len(raw)) == int(duplicate.sum()) + int(len(quarantine)) + int(len(events)),
    }
    return events, customers, products, quality


def real_snapshot(events: pd.DataFrame, cutoff, history_days=365, active_days=180) -> pd.DataFrame:
    cutoff = pd.Timestamp(cutoff)
    prior = events.loc[events.event_time < cutoff]
    history = prior.loc[prior.event_time >= cutoff - pd.Timedelta(days=history_days)]
    sales = history.loc[history.event_type.eq("sale")]
    if sales.empty:
        raise ValueError(f"No sales history before {cutoff.date()}")
    group = sales.groupby("customer_id")
    features = group.agg(last_purchase=("event_time", "max"), frequency_365=("order_id", "nunique"),
                         gross_sales=("net_revenue", "sum"), product_count=("product_id", "nunique"),
                         units_365=("signed_quantity", "sum"))
    features["recency_days"] = (cutoff - features.last_purchase).dt.total_seconds() / 86400
    first = prior.loc[prior.event_type.eq("sale")].groupby("customer_id").event_time.min()
    features["tenure_days"] = (cutoff - first).dt.total_seconds() / 86400
    features["net_revenue_365"] = history.groupby("customer_id").net_revenue.sum()
    recent = history.loc[history.event_time >= cutoff - pd.Timedelta(days=90)]
    previous = sales.loc[(sales.event_time >= cutoff - pd.Timedelta(days=180))
                         & (sales.event_time < cutoff - pd.Timedelta(days=90))]
    features["frequency_90"] = recent.loc[recent.event_type.eq("sale")].groupby("customer_id").order_id.nunique()
    features["frequency_previous90"] = previous.groupby("customer_id").order_id.nunique()
    features["net_revenue_90"] = recent.groupby("customer_id").net_revenue.sum()
    features["average_order_value"] = features.gross_sales / features.frequency_365
    returned_value = -history.loc[history.event_type.eq("return")].groupby("customer_id").net_revenue.sum()
    features["return_value_rate"] = (returned_value / features.gross_sales.replace(0, np.nan)).clip(lower=0)
    features = features.fillna(0)
    features["order_trend"] = (features.frequency_90 + 1) / (features.frequency_previous90 + 1)
    features = features.loc[features.recency_days <= active_days, REAL_FEATURES].copy()
    features["snapshot_date"] = cutoff.date().isoformat()
    return features.reset_index()


def attach_real_labels(features: pd.DataFrame, events: pd.DataFrame, cutoff, observed_until,
                       horizon_days=90) -> pd.DataFrame:
    cutoff = pd.Timestamp(cutoff)
    end = cutoff + pd.Timedelta(days=horizon_days)
    if end > pd.Timestamp(observed_until):
        raise ValueError("Right-censored labels: complete follow-up is not available.")
    future = events.loc[(events.event_time >= cutoff) & (events.event_time < end)]
    buyers = set(future.loc[future.event_type.eq("sale"), "customer_id"])
    labeled = features.copy()
    labeled["inactive_next90"] = (~labeled.customer_id.isin(buyers)).astype(int)
    revenue = future.groupby("customer_id").net_revenue.sum()
    labeled["revenue_next90"] = labeled.customer_id.map(revenue).fillna(0)
    return labeled


def _quintile(values: pd.Series, reverse=False) -> pd.Series:
    if len(values) < 5:
        return pd.Series(3, index=values.index, dtype=int)
    score = pd.qcut(values.rank(method="first"), 5, labels=False).astype(int) + 1
    return 6 - score if reverse else score


def real_segment(features: pd.DataFrame) -> pd.DataFrame:
    result = features.copy()
    result["r_score"] = _quintile(result.recency_days, reverse=True)
    result["f_score"] = _quintile(result.frequency_365)
    result["m_score"] = _quintile(result.net_revenue_365)
    result["rfm_score"] = result.r_score.astype(str) + result.f_score.astype(str) + result.m_score.astype(str)
    result["segment"] = np.select([
        (result.r_score >= 4) & (result.f_score >= 4) & (result.m_score >= 4),
        (result.r_score <= 2) & (result.f_score >= 4),
        (result.tenure_days <= 90) & (result.frequency_365 <= 2),
        (result.f_score >= 4) & (result.r_score >= 3),
        result.r_score <= 2,
    ], ["Champions", "Win-back candidates", "New customers", "Loyal customers", "Needs attention"],
       default="Developing customers")
    return result


def _fit_real(train, validation, test, scoring, model_dir: Path, seed=42):
    for name, part in [("train", train), ("validation", validation), ("test", test)]:
        if part.inactive_next90.nunique() != 2 or len(part) < 30:
            raise ValueError(f"{name} does not contain an evaluable customer population.")
    classifiers = {
        "prior_baseline": DummyClassifier(strategy="prior"),
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1500, random_state=seed)),
        "hist_gradient_boosting": HistGradientBoostingClassifier(max_iter=160, max_leaf_nodes=15,
            min_samples_leaf=35, l2_regularization=10, learning_rate=.05, random_state=seed),
    }
    regressors = {
        "mean_baseline": DummyRegressor(strategy="mean"),
        "hist_gradient_boosting": HistGradientBoostingRegressor(max_iter=160, max_leaf_nodes=15,
            min_samples_leaf=35, l2_regularization=10, learning_rate=.05, random_state=seed),
    }
    validation_c, validation_r = {}, {}
    for name, model in classifiers.items():
        model.fit(train[REAL_FEATURES], train.inactive_next90)
        validation_c[name] = classification_metrics(validation.inactive_next90,
                                                     model.predict_proba(validation[REAL_FEATURES])[:, 1])
    for name, model in regressors.items():
        model.fit(train[REAL_FEATURES], train.revenue_next90)
        validation_r[name] = regression_metrics(validation.revenue_next90, model.predict(validation[REAL_FEATURES]))
    best_c = max(validation_c, key=lambda n: validation_c[n]["average_precision"])
    best_r = min(validation_r, key=lambda n: validation_r[n]["mae"])
    development = pd.concat([train, validation], ignore_index=True)
    classifier, regressor = classifiers[best_c], regressors[best_r]
    classifier.fit(development[REAL_FEATURES], development.inactive_next90)
    regressor.fit(development[REAL_FEATURES], development.revenue_next90)
    test_p = classifier.predict_proba(test[REAL_FEATURES])[:, 1]
    test_v = regressor.predict(test[REAL_FEATURES])
    cbase = DummyClassifier(strategy="prior").fit(development[REAL_FEATURES], development.inactive_next90)
    rbase = DummyRegressor(strategy="mean").fit(development[REAL_FEATURES], development.revenue_next90)
    recency = test.recency_days.to_numpy()
    top = np.argsort(-recency, kind="stable")[:max(1, math.ceil(len(test) * .2))]
    recency_precision = float(test.inactive_next90.to_numpy()[top].mean())
    metrics = {
        "source": "UCI Online Retail II",
        "currency": "GBP",
        "target": "No sale in next 90 days; eligible if last sale <=180 days ago",
        "value_target": "Net revenue in next 90 days; returns included",
        "selected_classifier": best_c,
        "selected_value_model": best_r,
        "validation_classification": validation_c,
        "validation_value": validation_r,
        "test_classification": classification_metrics(test.inactive_next90, test_p),
        "test_classification_baseline": classification_metrics(
            test.inactive_next90, cbase.predict_proba(test[REAL_FEATURES])[:, 1]),
        "test_recency_ranking": {
            "average_precision": float(average_precision_score(test.inactive_next90, recency)),
            "precision_at_20pct": recency_precision,
            "lift_at_20pct": recency_precision / float(test.inactive_next90.mean()),
        },
        "test_value": regression_metrics(test.revenue_next90, test_v),
        "test_value_baseline": regression_metrics(test.revenue_next90, rbase.predict(test[REAL_FEATURES])),
        "feature_names": REAL_FEATURES,
        "split_counts": {"train_rows": len(train), "validation_rows": len(validation), "test_rows": len(test)},
        "evaluation_note": "Chronological holdout. Test was used once for reporting; no campaign uplift is claimed.",
    }
    importance = permutation_importance(classifier, test[REAL_FEATURES], test.inactive_next90,
                                        scoring="average_precision", n_repeats=3, random_state=seed)
    importance_df = pd.DataFrame({"feature": REAL_FEATURES,
                                  "average_precision_drop": importance.importances_mean,
                                  "std": importance.importances_std}).sort_values("average_precision_drop", ascending=False)
    predictions = test[["customer_id", "snapshot_date", "inactive_next90", "revenue_next90"]].copy()
    predictions["predicted_risk"] = test_p
    predictions["predicted_revenue90"] = test_v
    all_labeled = pd.concat([train, validation, test], ignore_index=True)
    classifier.fit(all_labeled[REAL_FEATURES], all_labeled.inactive_next90)
    regressor.fit(all_labeled[REAL_FEATURES], all_labeled.revenue_next90)
    scores = scoring.copy()
    scores["inactive_risk90"] = classifier.predict_proba(scoring[REAL_FEATURES])[:, 1]
    scores["expected_revenue90"] = regressor.predict(scoring[REAL_FEATURES])
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"classifier": classifier, "value_model": regressor, "features": REAL_FEATURES,
                 "score_cutoff": scoring.snapshot_date.iloc[0], "source": "UCI Online Retail II"},
                model_dir / "uci_models.joblib")
    return scores, metrics, importance_df, predictions


def _top_product(events: pd.DataFrame, cutoff) -> pd.DataFrame:
    start = pd.Timestamp(cutoff) - pd.Timedelta(days=365)
    sales = events.loc[events.event_type.eq("sale") & (events.event_time >= start)
                       & (events.event_time < pd.Timestamp(cutoff))]
    grouped = sales.groupby(["customer_id", "product_id", "product_name"], as_index=False).net_revenue.sum()
    return (grouped.sort_values(["customer_id", "net_revenue", "product_id"], ascending=[True, False, True])
            .drop_duplicates("customer_id")[["customer_id", "product_id", "product_name"]]
            .rename(columns={"product_id": "top_product_id", "product_name": "top_product_name"}))


def _write_real_dashboard(path: Path, template: Path, events, scores, products, quality, metrics, config) -> None:
    monthly = (events.assign(month=events.event_time.dt.strftime("%Y-%m"))
               .groupby("month", as_index=False).net_revenue.sum())
    top_products = (events.groupby(["product_id", "product_name"], as_index=False).net_revenue.sum()
                    .sort_values("net_revenue", ascending=False).head(8))
    payload = {
        "config": config, "quality": quality, "metrics": metrics,
        "totals": {"net_revenue": float(events.net_revenue.sum()), "scored_customers": len(scores),
                   "sales_orders": int(events.loc[events.event_type.eq("sale"), "order_id"].nunique())},
        "monthly": monthly.round(2).to_dict("records"),
        "products": top_products.round(2).to_dict("records"),
        "customers": scores[["customer_id", "country", "segment", "recency_days", "frequency_365",
                             "net_revenue_365", "inactive_risk90", "expected_revenue90",
                             "top_product_name"]].round(4).to_dict("records"),
    }
    data = json.dumps(payload, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    path.write_text(template.read_text(encoding="utf-8").replace("__REPORT_DATA__", data), encoding="utf-8")


def _quality_metrics_mart(quality: dict) -> pd.DataFrame:
    """Return a flat, BI-friendly view of the data-quality evidence."""
    definitions = [
        ("raw_rows", "Raw transaction rows", "rows", "observed"),
        ("exact_duplicates_removed", "Exact duplicates removed", "rows", "observed"),
        ("quarantined_rows", "Quarantined rows", "rows", "observed"),
        ("accepted_rows", "Accepted transaction rows", "rows", "observed"),
        ("known_customers", "Identified customers", "customers", "observed"),
        ("products", "Distinct products", "products", "observed"),
        ("sale_orders", "Sale orders", "orders", "observed"),
        ("return_rows", "Return rows", "rows", "observed"),
        ("zero_price_rows_accepted", "Accepted zero-price rows", "rows", "review"),
        ("reconciled", "Row reconciliation", "boolean", "pass" if quality["reconciled"] else "fail"),
    ]
    rows = []
    for metric, label, unit, status in definitions:
        value = quality[metric]
        rows.append({"metric": metric, "label": label, "value": int(value), "unit": unit, "status": status})
    for reason, value in sorted(quality.get("quarantine_reasons", {}).items()):
        rows.append({
            "metric": f"quarantine_{reason}",
            "label": f"Quarantine: {reason.replace('_', ' ')}",
            "value": int(value),
            "unit": "rows",
            "status": "observed",
        })
    return pd.DataFrame(rows)


def _model_metrics_mart(metrics: dict) -> pd.DataFrame:
    """Return held-out metrics and their baselines for dashboard cards."""
    test_c = metrics["test_classification"]
    base_c = metrics["test_classification_baseline"]
    recency = metrics["test_recency_ranking"]
    test_v = metrics["test_value"]
    base_v = metrics["test_value_baseline"]
    rows = [
        ("average_precision", "Inactivity average precision", test_c["average_precision"],
         base_c["average_precision"], "ratio"),
        ("roc_auc", "Inactivity ROC-AUC", test_c["roc_auc"], base_c["roc_auc"], "ratio"),
        ("lift_at_20pct", "Top-20% lift", test_c["lift_at_20pct"], recency["lift_at_20pct"], "multiple"),
        ("revenue_mae", "90-day revenue MAE", test_v["mae"], base_v["mae"], "GBP"),
    ]
    return pd.DataFrame(rows, columns=["metric", "label", "value", "baseline", "unit"]).assign(
        split="held_out_test"
    )


def run_uci(root: Path, workbook: Path, config: dict) -> dict:
    output = root / "outputs" / "real"
    marts, reports = output / "marts", output / "reports"
    for directory in [marts, reports]:
        directory.mkdir(parents=True, exist_ok=True)
    events, customers, products, quality = load_uci_workbook(workbook)
    observed_until = pd.Timestamp(config["score_cutoff"])
    if events.event_time.max() >= observed_until:
        raise ValueError("score_cutoff must be after the latest event.")
    horizon = pd.Timedelta(days=config["horizon_days"])
    cutoffs = [pd.Timestamp(x) for x in config["train_cutoffs"]]
    validation, test, score = [pd.Timestamp(config[k]) for k in
                               ["validation_cutoff", "test_cutoff", "score_cutoff"]]
    if not (max(cutoffs) + horizon <= validation and validation + horizon <= test
            and test + horizon <= score):
        raise ValueError("Outcome windows overlap or are right-censored.")
    frames = {}
    for cutoff in config["train_cutoffs"] + [config["validation_cutoff"], config["test_cutoff"]]:
        frames[cutoff] = attach_real_labels(
            real_snapshot(events, cutoff, config["history_days"], config["active_days"]),
            events, cutoff, observed_until, config["horizon_days"])
    train = pd.concat([frames[c] for c in config["train_cutoffs"]], ignore_index=True)
    validation_frame, test_frame = frames[config["validation_cutoff"]], frames[config["test_cutoff"]]
    scoring = real_snapshot(events, config["score_cutoff"], config["history_days"], config["active_days"])
    with threadpool_limits(limits=2):
        scores, metrics, importance, predictions = _fit_real(
            train, validation_frame, test_frame, scoring, output / "models", config["seed"])
    scores = (real_segment(scores).merge(customers, on="customer_id", validate="one_to_one")
              .merge(_top_product(events, config["score_cutoff"]), on="customer_id", how="left", validate="one_to_one"))
    scores["activation_eligible"] = False
    scores["activation_exclusion_reason"] = "Consent and contact data are unavailable in the public dataset"
    scores["analysis_priority"] = scores.inactive_risk90 * scores.expected_revenue90.clip(lower=0)
    event_dates = events.event_time.dt.normalize()
    fact = events[["event_id", "order_id", "customer_id", "product_id", "event_type",
                   "signed_quantity", "unit_price", "net_revenue"]].copy()
    fact["event_date"] = event_dates.dt.strftime("%Y-%m-%d")
    calendar = pd.DataFrame({"date": pd.date_range(events.event_time.min().normalize(), score - pd.Timedelta(days=1))})
    calendar["year"], calendar["month"] = calendar.date.dt.year, calendar.date.dt.month
    calendar["year_month"] = calendar.date.dt.strftime("%Y-%m")
    calendar["date"] = calendar.date.dt.strftime("%Y-%m-%d")
    score_columns = ["customer_id", "snapshot_date", "segment", "rfm_score", "r_score", "f_score", "m_score",
                     "recency_days", "frequency_365", "net_revenue_365", "inactive_risk90",
                     "expected_revenue90", "top_product_id", "top_product_name", "activation_eligible",
                     "activation_exclusion_reason", "analysis_priority"]
    tables = {
        "dim_customer": customers,
        "dim_product": products,
        "dim_date": calendar,
        "fact_sales": fact,
        "customer_scores": scores[score_columns],
        "cohort_retention": cohort_retention(events, config["score_cutoff"]),
        "data_quality_metrics": _quality_metrics_mart(quality),
        "model_metrics": _model_metrics_mart(metrics),
    }
    for name, table in tables.items():
        table.to_csv(marts / f"{name}.csv", index=False, encoding="utf-8-sig")
    pd.concat(frames.values(), ignore_index=True).to_csv(marts / "labeled_snapshots.csv", index=False, encoding="utf-8-sig")
    importance.to_csv(reports / "feature_importance.csv", index=False, encoding="utf-8-sig")
    predictions.to_csv(reports / "test_predictions.csv", index=False, encoding="utf-8-sig")
    metrics["split_dates"] = {k: config[k] for k in
                              ["train_cutoffs", "validation_cutoff", "test_cutoff", "score_cutoff"]}
    _save_json(reports / "metrics.json", metrics)
    _save_json(reports / "data_quality.json", quality)
    manifest = {
        "project": "RetailScope", "version": "0.2.0", "config": config,
        "source": {"name": "UCI Online Retail II", "doi": "10.24432/C5CG6D",
                   "license": "CC BY 4.0", "workbook_sha256": hashlib.sha256(Path(workbook).read_bytes()).hexdigest()},
        "python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
        "sklearn": sklearn.__version__,
    }
    _save_json(reports / "run_manifest.json", manifest)
    _write_real_dashboard(reports / "dashboard.html", root / "templates" / "real_dashboard.html",
                          events, scores, products, quality, metrics, config)
    return {
        "source": "UCI Online Retail II", "accepted_events": len(events), "known_customers": len(customers),
        "scored_customers": len(scores), "classifier": metrics["selected_classifier"],
        "test_average_precision": round(metrics["test_classification"]["average_precision"], 4),
        "test_roc_auc": round(metrics["test_classification"]["roc_auc"], 4),
        "test_lift_at_20pct": round(metrics["test_classification"]["lift_at_20pct"], 3),
        "test_value_mae_gbp": round(metrics["test_value"]["mae"], 2),
        "report": str(reports / "dashboard.html"),
    }
