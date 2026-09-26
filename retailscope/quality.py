"""Clean signed transaction events; preserve returns and reconcile exclusions."""
import numpy as np
import pandas as pd


def clean_events(raw, products, mapping, observed_until):
    e = raw.copy().fillna({"origin_event_id": ""})
    original_count = len(e)
    e = e.drop_duplicates()
    removed = original_count - len(e)
    if e.event_id.duplicated().any():
        raise ValueError("Conflicting rows share an event_id; source reconciliation is required.")
    if products.product_id.duplicated().any():
        raise ValueError("product_id must be unique.")
    e["event_time"] = pd.to_datetime(e.event_time, errors="coerce")
    for c in ["quantity", "unit_price", "discount_rate", "unit_cost"]:
        e[c] = pd.to_numeric(e[c], errors="coerce")
    e["rejection_reason"] = ""
    checks = {
        "unknown_customer": ~e.customer_record_id.isin(mapping.record_id),
        "unknown_product": ~e.product_id.isin(products.product_id),
        "invalid_timestamp": e.event_time.isna(),
        "after_observation_end": e.event_time >= pd.Timestamp(observed_until),
        "invalid_type": ~e.event_type.isin(["sale", "return", "cancelled"]),
        "invalid_channel": ~e.channel.isin(["online", "store"]),
        "invalid_number": ~np.isfinite(e[["quantity", "unit_price", "discount_rate", "unit_cost"]]).all(axis=1),
        "invalid_quantity": (e.quantity <= 0) | (e.quantity % 1 != 0),
        "invalid_price_or_discount": (e.unit_price <= 0) | (e.unit_cost < 0) | ~e.discount_rate.between(0, 1),
    }
    for reason, mask in checks.items():
        e.loc[mask & e.rejection_reason.eq(""), "rejection_reason"] = reason
    # A return must refer to an earlier valid sale with the same commercial fields.
    sales = e.loc[e.event_type.eq("sale") & e.rejection_reason.eq("")].set_index("event_id")
    totals = {}
    for idx, row in e.loc[e.event_type.eq("return") & e.rejection_reason.eq("")].sort_values(["event_time", "event_id"]).iterrows():
        origin = row.origin_event_id
        valid = origin in sales.index
        if valid:
            sale = sales.loc[origin]
            valid = (row.event_time >= sale.event_time and
                     all(row[c] == sale[c] for c in ["customer_record_id", "product_id", "order_id", "unit_price", "unit_cost", "discount_rate"]) and
                     totals.get(origin, 0) + row.quantity <= sale.quantity)
        if not valid:
            e.loc[idx, "rejection_reason"] = "invalid_return_reference"
        else:
            totals[origin] = totals.get(origin, 0) + row.quantity
    quarantine = e.loc[e.rejection_reason.ne("")].copy()
    valid = e.loc[e.rejection_reason.eq("")].drop(columns="rejection_reason")
    valid = valid.merge(mapping[["record_id", "customer_id"]], left_on="customer_record_id", right_on="record_id", validate="many_to_one")
    valid = valid.merge(products[["product_id", "category", "brand"]], on="product_id", validate="many_to_one")
    sign = valid.event_type.map({"sale": 1, "return": -1, "cancelled": 0})
    valid["signed_quantity"] = (valid.quantity * sign).astype(int)
    valid["net_revenue"] = (valid.signed_quantity * valid.unit_price * (1 - valid.discount_rate)).round(2)
    valid["gross_margin"] = (valid.net_revenue - valid.signed_quantity * valid.unit_cost).round(2)
    valid = valid.sort_values(["event_time", "event_id"]).reset_index(drop=True)
    report = dict(raw_rows=original_count, exact_duplicates_removed=removed, quarantined_rows=len(quarantine),
                  accepted_rows=len(valid), rejection_counts=quarantine.rejection_reason.value_counts().to_dict(),
                  return_rows=int(valid.event_type.eq("return").sum()),
                  cancelled_rows=int(valid.event_type.eq("cancelled").sum()),
                  reconciled=original_count == removed + len(quarantine) + len(valid))
    assert report["reconciled"]
    return valid, quarantine, report
