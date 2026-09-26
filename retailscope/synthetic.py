"""Entirely fictional data. Latent generator attributes are never model inputs."""
from pathlib import Path
import json

import numpy as np
import pandas as pd


def generate(root: Path, config: dict) -> dict:
    rng = np.random.default_rng(config["seed"])
    start = pd.Timestamp(config["start"])
    end = pd.Timestamp(config["observed_until_exclusive"])
    span = (end - start).days
    raw = root / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    categories = ["Bez ve bakım", "Beslenme", "Giyim", "Oyuncak", "Bebek araç gereç"]
    bases = [280, 420, 550, 380, 1800]
    products = []
    for k, category in enumerate(categories):
        for j in range(12):
            price = round(bases[k] * rng.uniform(.55, 1.8), 2)
            products.append(dict(product_id=f"P{k * 12 + j:03}",
                                 product_name=f"{category} Ürün {j + 1}",
                                 category=category, brand=f"Kurgu Marka {j % 4 + 1}",
                                 list_price=price, unit_cost=round(price * rng.uniform(.48, .7), 2)))
    customers, events = [], []
    eid = 0
    for i in range(config["customers"]):
        loyalty = f"L{i:06}"
        email = f"customer{i:06}@example.invalid"
        # Non-routable synthetic token, deliberately not a real telephone number.
        phone = f"SYNTH-{i:06}"
        city = str(rng.choice(["İstanbul", "Ankara", "İzmir", "Bursa", "Kocaeli"]))
        consent = bool(rng.random() < .76)
        no_loyalty = rng.random() < .12
        ids = [f"WEB{i:06}"]
        if rng.random() < .28:
            ids.append(f"POS{i:06}")
        for source_id in ids:
            customers.append(dict(record_id=source_id, source="web" if source_id.startswith("WEB") else "store",
                                  loyalty_id="" if no_loyalty else loyalty,
                                  loyalty_verified=not no_loyalty,
                                  email=email if source_id.startswith("WEB") else " " + email.upper() + " ",
                                  email_verified=True, phone=phone, phone_verified=True,
                                  city=city, marketing_consent=consent))
        # Staggered acquisition, heterogeneous shopping rates and natural exits.
        acquired = int(rng.integers(0, max(1, span - 120)))
        rate = float(rng.uniform(.45, 3.0))
        exit_day = acquired + int(rng.integers(75, 780))
        if rng.random() < .4:
            exit_day = span + 1
        category_pref = rng.dirichlet([3, 1.5, 1.6, 1.2, .6])
        channel_prob = float(rng.uniform(.1, .9))
        t = float(acquired)
        while t < min(span, exit_day):
            event_time = start + pd.Timedelta(days=int(t), hours=int(rng.integers(8, 22)))
            channel = "online" if rng.random() < channel_prob else "store"
            record_id = ids[0] if channel == "online" else ids[-1]
            order_id = f"O{eid:08}"
            cancelled = rng.random() < .035
            for _ in range(int(rng.integers(1, 4))):
                cat = int(rng.choice(len(categories), p=category_pref))
                product = products[cat * 12 + int(rng.integers(0, 12))]
                qty = int(rng.integers(1, 4))
                discount = float(rng.choice([0, .05, .1, .2], p=[.45, .15, .3, .1]))
                row = dict(event_id=f"E{eid:09}", order_id=order_id,
                           customer_record_id=record_id, product_id=product["product_id"],
                           event_time=event_time.isoformat(), event_type="cancelled" if cancelled else "sale",
                           quantity=qty, unit_price=product["list_price"], discount_rate=discount,
                           unit_cost=product["unit_cost"], channel=channel, origin_event_id="")
                events.append(row)
                eid += 1
                if not cancelled and rng.random() < .065:
                    returned_at = event_time + pd.Timedelta(days=int(rng.integers(1, 31)))
                    if returned_at < end:
                        events.append(dict(row, event_id=f"E{eid:09}", event_type="return",
                                           quantity=int(rng.integers(1, qty + 1)),
                                           event_time=returned_at.isoformat(), origin_event_id=row["event_id"]))
                        eid += 1
            # Lower purchase frequency in late lifecycle, without exposing lifecycle state.
            slowdown = 1.8 if exit_day - t < 90 else 1.0
            t += max(1., rng.exponential(30. / rate) * slowdown)
    frame = pd.DataFrame(events)
    # Deliberate, documented quality defects exercise the quarantine path.
    duplicate_count = min(35, len(frame))
    frame = pd.concat([frame, frame.head(duplicate_count)], ignore_index=True)
    bad = dict(events[0], event_id="BAD_CUSTOMER", customer_record_id="UNKNOWN", event_type="sale")
    bad2 = dict(events[0], event_id="BAD_QUANTITY", quantity=0, event_type="sale")
    frame = pd.concat([frame, pd.DataFrame([bad, bad2])], ignore_index=True)
    pd.DataFrame(customers).to_csv(raw / "customers.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(products).to_csv(raw / "products.csv", index=False, encoding="utf-8-sig")
    frame.to_csv(raw / "events.csv", index=False, encoding="utf-8-sig")
    metadata = dict(source="synthetic", currency="TRY", seed=config["seed"],
                    observed_until_exclusive=end.date().isoformat(),
                    statement="All customers, brands, prices and transactions are fictional; no ebebek data.",
                    customer_records=len(customers), source_customers=config["customers"],
                    raw_events=len(frame), deliberate_exact_duplicates=duplicate_count)
    (raw / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return metadata
