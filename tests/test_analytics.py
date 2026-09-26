import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from retailscope.crm import campaign_candidates, cohort_retention, ltv_scenario
from retailscope.features import attach_labels, snapshot
from retailscope.identity import resolve
from retailscope.pipeline import validate_config
from retailscope.quality import clean_events
from retailscope.uci import (
    _model_metrics_mart,
    _quality_metrics_mart,
    attach_real_labels,
    real_segment,
    real_snapshot,
)


def customer(record, email="a@example.invalid", phone="SYNTH-1", loyalty="", consent=True):
    return dict(record_id=record, source="web", loyalty_id=loyalty, loyalty_verified=bool(loyalty),
                email=email, email_verified=True, phone=phone, phone_verified=True,
                city="İstanbul", marketing_consent=consent)


def event(eid, date, kind="sale", origin="", qty=1):
    sign = {"sale":1, "return":-1, "cancelled":0}[kind]
    return dict(event_id=eid, order_id="O"+eid, customer_record_id="R1", customer_id="C1",
                product_id="P1", category="Bakım", brand="Kurgu", event_time=pd.Timestamp(date),
                event_type=kind, quantity=qty, unit_price=100., discount_rate=0., unit_cost=60.,
                channel="online", origin_event_id=origin, signed_quantity=sign*qty,
                net_revenue=sign*qty*100., gross_margin=sign*qty*40.)


class IdentityTests(unittest.TestCase):
    def test_single_shared_phone_does_not_merge(self):
        dim, _ = resolve(pd.DataFrame([customer("R1"), customer("R2", email="b@example.invalid")]))
        self.assertEqual(len(dim), 2)

    def test_verified_pair_merges_and_opt_out_wins(self):
        dim, audit = resolve(pd.DataFrame([customer("R1"), customer("R2", email=" A@EXAMPLE.INVALID ", consent=False)]))
        self.assertEqual(len(dim), 1)
        self.assertFalse(dim.marketing_consent.iloc[0])
        self.assertEqual(audit.customer_id.nunique(), 1)

    def test_conflicting_loyalty_ids_remain_distinct_and_flagged(self):
        dim, audit = resolve(pd.DataFrame([customer("R1", loyalty="L1"), customer("R2", loyalty="L2"), customer("R3")]))
        self.assertEqual(len(dim), 3)
        self.assertTrue(audit.identity_review_required.all())

    def test_keys_independent_of_input_order(self):
        raw = pd.DataFrame([customer("R1", loyalty="L1"), customer("R2", email="b@example.invalid", phone="SYNTH-2")])
        _, a = resolve(raw)
        _, b = resolve(raw.iloc[::-1])
        self.assertEqual(a.set_index("record_id").customer_id.to_dict(), b.set_index("record_id").customer_id.to_dict())


class TimeAndAccountingTests(unittest.TestCase):
    def setUp(self):
        self.history = pd.DataFrame([event("S1", "2024-12-15"), event("S2", "2025-02-01")])

    def test_future_purchases_cannot_change_features(self):
        before = snapshot(self.history, "2025-03-01")
        future = pd.concat([self.history, pd.DataFrame([event("FUTURE", "2025-03-02", qty=999)])], ignore_index=True)
        assert_frame_equal(before, snapshot(future, "2025-03-01"))

    def test_cutoff_belongs_to_label_not_features(self):
        events = pd.concat([self.history, pd.DataFrame([event("BOUNDARY", "2025-03-01")])], ignore_index=True)
        features = snapshot(events, "2025-03-01")
        self.assertEqual(features.frequency_365.iloc[0], 2)
        labeled = attach_labels(features, events, "2025-03-01", "2025-06-01")
        self.assertEqual(labeled.inactive_next90.iloc[0], 0)

    def test_future_return_is_not_repeat_purchase_and_can_make_negative_value(self):
        ret = event("RET", "2025-03-03", "return", "S2")
        events = pd.concat([self.history, pd.DataFrame([ret])], ignore_index=True)
        labeled = attach_labels(snapshot(events, "2025-03-01"), events, "2025-03-01", "2025-06-01")
        self.assertEqual(labeled.inactive_next90.iloc[0], 1)
        self.assertEqual(labeled.margin_next90.iloc[0], -40.)

    def test_incomplete_followup_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Right-censored"):
            attach_labels(snapshot(self.history, "2025-03-01"), self.history, "2025-03-01", "2025-04-01")

    def test_cohort_future_month_is_absent(self):
        cohorts = cohort_retention(self.history, "2025-03-01")
        self.assertEqual(cohorts.month_index.max(), 2)
        self.assertEqual(cohorts.loc[cohorts.month_index.eq(1), "retention_rate"].iloc[0], 0)

    def test_return_and_duplicate_accounting_reconcile(self):
        sale = event("S1", "2025-01-01", qty=2)
        ret = dict(event("R1", "2025-01-02", "return", "S1"), order_id=sale["order_id"])
        bad = dict(sale, event_id="BAD", product_id="UNKNOWN")
        raw = pd.DataFrame([sale, sale, ret, bad]).drop(columns=["customer_id", "category", "brand", "signed_quantity", "net_revenue", "gross_margin"])
        products = pd.DataFrame([dict(product_id="P1", category="Bakım", brand="Kurgu")])
        mapping = pd.DataFrame([dict(record_id="R1", customer_id="C1")])
        cleaned, quarantine, report = clean_events(raw, products, mapping, "2025-02-01")
        self.assertEqual(cleaned.net_revenue.sum(), 100.)
        self.assertEqual(cleaned.gross_margin.sum(), 40.)
        self.assertEqual(report["exact_duplicates_removed"], 1)
        self.assertEqual(len(quarantine), 1)
        self.assertTrue(report["reconciled"])

    def test_conflicting_event_id_fails_closed(self):
        raw = pd.DataFrame([event("S1", "2025-01-01"), event("S1", "2025-01-01", qty=2)])
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            clean_events(raw, pd.DataFrame(), pd.DataFrame(), "2025-02-01")

    def test_overlapping_model_periods_rejected(self):
        c = dict(history_days=365, horizon_days=90, active_days=180,
                 train_cutoffs=["2025-01-01"], validation_cutoff="2025-02-01",
                 test_cutoff="2025-06-01", score_cutoff="2025-09-01")
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            validate_config(c, {})


class CRMTests(unittest.TestCase):
    def test_campaign_excludes_opt_out_conflict_and_negative_value(self):
        rows=[]
        for i in range(7):
            rows.append(dict(customer_id=f"C{i}", snapshot_date="2026-04-01", segment="Sadık müşteri", city="Bursa",
                             top_category="Bakım", top_brand="Kurgu", recency_days=60,
                             inactive_risk90=.8, expected_margin90=1000, marketing_consent=True,
                             identity_review_required=False))
        rows[0]["marketing_consent"]=False
        rows[1]["identity_review_required"]=True
        rows[2]["expected_margin90"]=-10
        rows[3]["recency_days"]=5
        result=campaign_candidates(pd.DataFrame(rows), capacity=3)
        self.assertEqual(set(result.customer_id), {"C4", "C5", "C6"})
        self.assertEqual(set(result.experiment_group), {"treatment", "control"})
        assert_frame_equal(result, campaign_candidates(pd.DataFrame(rows), capacity=3))

    def test_ltv_zero_retention_has_only_first_discounted_period(self):
        result=ltv_scenario([100], retention=0, quarterly_discount=.1, quarters=12)
        self.assertAlmostEqual(float(result[0]), 100/1.1)


class UCIAdapterTests(unittest.TestCase):
    def setUp(self):
        self.events = pd.DataFrame([
            dict(event_id="1", order_id="A", customer_id="UCI-1", product_id="P1", product_name="One",
                 country="United Kingdom", event_time=pd.Timestamp("2010-01-01"), event_type="sale",
                 signed_quantity=2, unit_price=10., net_revenue=20.),
            dict(event_id="2", order_id="B", customer_id="UCI-1", product_id="P2", product_name="Two",
                 country="United Kingdom", event_time=pd.Timestamp("2010-03-01"), event_type="sale",
                 signed_quantity=1, unit_price=15., net_revenue=15.),
            dict(event_id="3", order_id="C", customer_id="UCI-1", product_id="P2", product_name="Two",
                 country="United Kingdom", event_time=pd.Timestamp("2010-04-03"), event_type="return",
                 signed_quantity=-1, unit_price=15., net_revenue=-15.),
        ])

    def test_real_features_stop_at_cutoff(self):
        before = real_snapshot(self.events, "2010-04-01")
        future = pd.concat([self.events, pd.DataFrame([dict(self.events.iloc[0], event_id="4", order_id="D",
            event_time=pd.Timestamp("2010-04-02"), signed_quantity=99, net_revenue=990.)])], ignore_index=True)
        assert_frame_equal(before, real_snapshot(future, "2010-04-01"))

    def test_returns_reduce_revenue_but_not_inactivity(self):
        labeled = attach_real_labels(real_snapshot(self.events, "2010-04-01"), self.events,
                                     "2010-04-01", "2010-07-01")
        self.assertEqual(labeled.inactive_next90.iloc[0], 1)
        self.assertEqual(labeled.revenue_next90.iloc[0], -15.)

    def test_real_segmentation_outputs_valid_scores(self):
        frame = pd.DataFrame({"customer_id":[f"C{i}" for i in range(10)],
            "recency_days":range(10), "frequency_365":range(1,11),
            "net_revenue_365":range(100,1100,100), "tenure_days":[200]*10})
        result = real_segment(frame)
        self.assertTrue(result.rfm_score.str.fullmatch(r"[1-5]{3}").all())

    def test_powerbi_metric_marts_are_flat_and_complete(self):
        quality = {
            "raw_rows": 10, "exact_duplicates_removed": 1, "quarantined_rows": 2,
            "accepted_rows": 7, "known_customers": 3, "products": 4, "sale_orders": 5,
            "return_rows": 1, "zero_price_rows_accepted": 0, "reconciled": True,
            "quarantine_reasons": {"missing_customer_id": 2},
        }
        metrics = {
            "test_classification": {"average_precision": .7, "roc_auc": .8, "lift_at_20pct": 1.5},
            "test_classification_baseline": {"average_precision": .4, "roc_auc": .5, "lift_at_20pct": 1.0},
            "test_recency_ranking": {"lift_at_20pct": 1.2},
            "test_value": {"mae": 500.0}, "test_value_baseline": {"mae": 800.0},
        }
        quality_mart = _quality_metrics_mart(quality)
        model_mart = _model_metrics_mart(metrics)
        self.assertEqual(set(quality_mart.columns), {"metric", "label", "value", "unit", "status"})
        self.assertEqual(model_mart.metric.tolist(),
                         ["average_precision", "roc_auc", "lift_at_20pct", "revenue_mae"])
        self.assertEqual(model_mart.loc[model_mart.metric.eq("lift_at_20pct"), "baseline"].iloc[0], 1.2)
        self.assertTrue((model_mart.split == "held_out_test").all())


class PowerBIDeliveryTests(unittest.TestCase):
    def test_contract_validator_accepts_repository_package(self):
        from scripts.validate_powerbi_contract import validate_package

        root = Path(__file__).resolve().parents[1]
        errors = validate_package(root / "powerbi" / "model_contract.json", data_root=None)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
