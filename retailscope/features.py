"""Features only see [cutoff-history, cutoff); labels see [cutoff, cutoff+horizon)."""
import numpy as np
import pandas as pd

FEATURES = ["recency_days", "tenure_days", "frequency_365", "frequency_90", "frequency_previous90",
            "net_revenue_365", "net_revenue_90", "gross_margin_365", "average_order_value",
            "category_count", "brand_count", "online_share", "discount_share", "return_unit_rate", "order_trend"]


def snapshot(events, cutoff, history_days=365, active_days=180):
    cutoff = pd.Timestamp(cutoff)
    prior = events.loc[events.event_time < cutoff]
    history = prior.loc[prior.event_time >= cutoff - pd.Timedelta(days=history_days)]
    sales = history.loc[history.event_type.eq("sale")]
    if sales.empty:
        raise ValueError(f"No sales history before {cutoff.date()}")
    group = sales.groupby("customer_id")
    f = group.agg(last_purchase=("event_time", "max"), frequency_365=("order_id", "nunique"),
                  gross_sales=("net_revenue", "sum"), category_count=("category", "nunique"),
                  brand_count=("brand", "nunique"), sold_units=("quantity", "sum"))
    # Floor full days; eligibility boundary is explicitly defined in docs.
    f["recency_days"] = (cutoff - f.last_purchase).dt.total_seconds() / 86400
    first = prior.loc[prior.event_type.eq("sale")].groupby("customer_id").event_time.min()
    f["tenure_days"] = (cutoff - first).dt.total_seconds() / 86400
    money = history.groupby("customer_id")[["net_revenue", "gross_margin"]].sum()
    f["net_revenue_365"] = money.net_revenue
    f["gross_margin_365"] = money.gross_margin
    recent = history.loc[history.event_time >= cutoff - pd.Timedelta(days=90)]
    prev = sales.loc[(sales.event_time >= cutoff - pd.Timedelta(days=180)) & (sales.event_time < cutoff - pd.Timedelta(days=90))]
    f["frequency_90"] = recent.loc[recent.event_type.eq("sale")].groupby("customer_id").order_id.nunique()
    f["frequency_previous90"] = prev.groupby("customer_id").order_id.nunique()
    f["net_revenue_90"] = recent.groupby("customer_id").net_revenue.sum()
    f["average_order_value"] = f.gross_sales / f.frequency_365
    f["online_share"] = sales.assign(online=sales.channel.eq("online")).groupby("customer_id").online.mean()
    f["discount_share"] = sales.assign(discounted=sales.discount_rate.gt(0)).groupby("customer_id").discounted.mean()
    returned = history.loc[history.event_type.eq("return")].groupby("customer_id").quantity.sum()
    f["return_unit_rate"] = returned / f.sold_units
    f = f.fillna(0)
    f["order_trend"] = (f.frequency_90 + 1) / (f.frequency_previous90 + 1)
    f = f.loc[f.recency_days <= active_days, FEATURES].copy()
    f["snapshot_date"] = cutoff.date().isoformat()
    return f.reset_index()


def attach_labels(features, events, cutoff, observed_until, horizon_days=90):
    cutoff = pd.Timestamp(cutoff)
    end = cutoff + pd.Timedelta(days=horizon_days)
    if end > pd.Timestamp(observed_until):
        raise ValueError("Right-censored labels: complete follow-up is not available.")
    future = events.loc[(events.event_time >= cutoff) & (events.event_time < end)]
    buyers = set(future.loc[future.event_type.eq("sale"), "customer_id"])
    f = features.copy()
    f["inactive_next90"] = (~f.customer_id.isin(buyers)).astype(int)
    margin = future.groupby("customer_id").gross_margin.sum()
    f["margin_next90"] = f.customer_id.map(margin).fillna(0)
    return f


def segment(features):
    f = features.copy()
    # Fixed business thresholds support consistent interpretation across runs.
    f["r_score"] = np.select([f.recency_days <= 15, f.recency_days <= 30, f.recency_days <= 60, f.recency_days <= 90], [5, 4, 3, 2], default=1)
    f["f_score"] = np.select([f.frequency_365 >= 18, f.frequency_365 >= 10, f.frequency_365 >= 5, f.frequency_365 >= 2], [5, 4, 3, 2], default=1)
    f["m_score"] = np.select([f.net_revenue_365 >= 25000, f.net_revenue_365 >= 12000, f.net_revenue_365 >= 6000, f.net_revenue_365 >= 1500], [5, 4, 3, 2], default=1)
    f["rfm_score"] = f.r_score.astype(str) + f.f_score.astype(str) + f.m_score.astype(str)
    f["segment"] = np.select([
        (f.r_score >= 4) & (f.f_score >= 4) & (f.m_score >= 4),
        (f.recency_days > 90) & (f.f_score >= 3),
        (f.tenure_days <= 60) & (f.frequency_365 <= 2),
        (f.f_score >= 4) & (f.recency_days <= 90),
        f.recency_days > 60],
        ["Şampiyon", "Geri kazanım adayı", "Yeni müşteri", "Sadık müşteri", "İlgi gerekiyor"],
        default="Gelişen müşteri")
    return f
