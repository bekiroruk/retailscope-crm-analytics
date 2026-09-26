"""Explainable candidate ranking and prospective randomized experiment plan."""
import numpy as np
import pandas as pd


def ltv_scenario(expected_margin90, retention=.7, quarterly_discount=.025, quarters=12, acquisition_cost=0.):
    if not (0 <= retention <= 1) or quarterly_discount < 0 or quarters < 1:
        raise ValueError("Invalid scenario parameters.")
    factor = sum(retention ** k / (1 + quarterly_discount) ** (k + 1) for k in range(quarters))
    return np.asarray(expected_margin90) * factor - acquisition_cost


def campaign_candidates(scores, capacity=150, control_fraction=.2, seed=42):
    if capacity < 1 or not 0 < control_fraction < 1:
        raise ValueError("Invalid campaign capacity or control fraction.")
    s = scores.copy()
    s["priority_score"] = s.inactive_risk90 * s.expected_margin90.clip(lower=0)
    # Current consent is an eligibility signal only, never a historical model feature.
    eligible = (s.marketing_consent & ~s.identity_review_required & (s.expected_margin90 > 0)
                & (s.recency_days >= 30) & (s.inactive_risk90 >= .5))
    chosen = s.loc[eligible].sort_values(["priority_score", "customer_id"], ascending=[False, True]).head(capacity).copy()
    if len(chosen) < 2:
        chosen["experiment_group"] = "insufficient_sample"
    else:
        rng = np.random.default_rng(seed)
        n_control = min(len(chosen) - 1, max(1, round(len(chosen) * control_fraction)))
        control = set(rng.choice(chosen.customer_id.to_numpy(), size=n_control, replace=False))
        chosen["experiment_group"] = np.where(chosen.customer_id.isin(control), "control", "treatment")
    chosen["business_reason"] = "30+ gündür alışveriş yok; 90 günlük risk >= %50; tahmini brüt kâr pozitif"
    chosen["suggested_action"] = "Tercih edilen kategori için geri kazanım teklifini kontrollü dene"
    columns = ["customer_id", "snapshot_date", "segment", "city", "top_category", "top_brand",
               "recency_days", "inactive_risk90", "expected_margin90", "priority_score",
               "experiment_group", "business_reason", "suggested_action"]
    return chosen[columns].reset_index(drop=True)


def cohort_retention(events, cutoff):
    sales = events.loc[events.event_type.eq("sale") & (events.event_time < pd.Timestamp(cutoff))].copy()
    sales["month"] = sales.event_time.dt.to_period("M")
    first = sales.groupby("customer_id").month.min()
    sales["cohort"] = sales.customer_id.map(first)
    sales["month_index"] = [(m.year - c.year) * 12 + m.month - c.month for m, c in zip(sales.month, sales.cohort)]
    counts = sales.groupby(["cohort", "month_index"]).customer_id.nunique()
    size = first.value_counts()
    # Only complete months have a denominator: unseen future cells are absent, not zero.
    last_complete = (pd.Timestamp(cutoff).to_period("M") - 1)
    rows = []
    for cohort in sorted(first.unique()):
        max_age = (last_complete.year - cohort.year) * 12 + last_complete.month - cohort.month
        for age in range(max_age + 1):
            active = int(counts.get((cohort, age), 0))
            rows.append(dict(cohort=str(cohort), month_index=age, cohort_size=int(size[cohort]),
                             active_customers=active, retention_rate=active / int(size[cohort])))
    return pd.DataFrame(rows)


def customer_affinity(events, cutoff):
    cutoff = pd.Timestamp(cutoff)
    sales = events.loc[events.event_type.eq("sale") & (events.event_time < cutoff)
                       & (events.event_time >= cutoff - pd.Timedelta(days=365))]
    result = None
    for column in ["category", "brand", "product_id"]:
        grouped = sales.groupby(["customer_id", column], as_index=False).net_revenue.sum()
        top = grouped.sort_values(["customer_id", "net_revenue", column], ascending=[True, False, True]).drop_duplicates("customer_id")
        top = top[["customer_id", column]].rename(columns={column:"top_" + column})
        result = top if result is None else result.merge(top, on="customer_id", validate="one_to_one")
    return result
