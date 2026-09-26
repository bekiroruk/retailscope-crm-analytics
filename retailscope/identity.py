"""Conservative identity linkage with reproducible keys and an audit trail."""
import hashlib
import re

import pandas as pd


def truth(value) -> bool:
    return str(value).strip().lower() in {"true", "1"}


def clean(value) -> str:
    return "" if pd.isna(value) else str(value).strip().casefold()


def resolve(customers: pd.DataFrame):
    if customers.record_id.duplicated().any():
        raise ValueError("Duplicate customer record_id; reconcile source revisions before linkage.")
    records = []
    for row in customers.to_dict("records"):
        email = clean(row["email"]) if truth(row["email_verified"]) else ""
        phone = re.sub(r"[\s()+-]", "", clean(row["phone"])) if truth(row["phone_verified"]) else ""
        loyalty = clean(row["loyalty_id"]) if truth(row["loyalty_verified"]) else ""
        records.append(dict(row, norm_email=email, norm_phone=phone, norm_loyalty=loyalty))
    pairs = {}
    for r in records:
        pair = (r["norm_email"], r["norm_phone"])
        if all(pair):
            pairs.setdefault(pair, set())
            if r["norm_loyalty"]:
                pairs[pair].add(r["norm_loyalty"])
    resolved = []
    for r in records:
        pair = (r["norm_email"], r["norm_phone"])
        candidates = pairs.get(pair, set())
        conflict = len(candidates) > 1
        if r["norm_loyalty"]:
            key, rule = "loyalty:" + r["norm_loyalty"], "verified_loyalty"
        elif all(pair) and len(candidates) == 1:
            key, rule = "loyalty:" + next(iter(candidates)), "verified_pair_to_loyalty"
        elif all(pair) and not conflict:
            key, rule = "pair:" + repr(pair), "verified_email_and_phone"
        else:
            key, rule = "record:" + r["record_id"], "unmerged_record"
        cid = "C" + hashlib.sha256(key.encode()).hexdigest()[:16]
        resolved.append(dict(record_id=r["record_id"], customer_id=cid, match_rule=rule,
                             identity_review_required=conflict, city=r["city"],
                             marketing_consent=truth(r["marketing_consent"])))
    audit = pd.DataFrame(resolved)
    dim = audit.sort_values("record_id").groupby("customer_id", as_index=False).agg(
        city=("city", "first"), marketing_consent=("marketing_consent", "all"),
        identity_review_required=("identity_review_required", "any"), source_records=("record_id", "size"))
    return dim, audit
