"""Chronological model selection, held-out evaluation and final retraining."""
from pathlib import Path
import math

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, mean_absolute_error,
                             r2_score, roc_auc_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURES


def classification_metrics(y, p):
    y, p = np.asarray(y), np.asarray(p)
    k = max(1, math.ceil(len(y) * .2))
    top = np.argsort(-p, kind="stable")[:k]
    precision = float(y[top].mean())
    prevalence = float(y.mean())
    return dict(n=len(y), prevalence=prevalence,
                average_precision=float(average_precision_score(y, p)),
                roc_auc=float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else None,
                brier=float(brier_score_loss(y, p)), precision_at_20pct=precision,
                lift_at_20pct=precision / prevalence if prevalence else None)


def regression_metrics(y, p):
    y, p = np.asarray(y), np.asarray(p)
    denominator = np.abs(y).sum()
    return dict(n=len(y), mae=float(mean_absolute_error(y, p)),
                wape=float(np.abs(y - p).sum() / denominator) if denominator else None,
                r2=float(r2_score(y, p)), actual_sum=float(y.sum()), predicted_sum=float(p.sum()))


def fit_evaluate(train, validation, test, scoring, model_dir: Path, seed=42):
    for name, part in [("train", train), ("validation", validation), ("test", test)]:
        if part.inactive_next90.nunique() != 2:
            raise ValueError(f"{name} needs both label classes; increase sample size or history.")
        if len(part) < 30:
            raise ValueError(f"Too few customers in {name}.")
    candidates = {
        "prior_baseline": DummyClassifier(strategy="prior"),
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1500, random_state=seed)),
        "hist_gradient_boosting": HistGradientBoostingClassifier(max_iter=120, max_leaf_nodes=15,
                                                                 min_samples_leaf=35, l2_regularization=10,
                                                                 learning_rate=.05, random_state=seed),
    }
    regressors = {
        "mean_baseline": DummyRegressor(strategy="mean"),
        "hist_gradient_boosting": HistGradientBoostingRegressor(max_iter=120, max_leaf_nodes=15,
                                                                min_samples_leaf=35, l2_regularization=10,
                                                                learning_rate=.05, random_state=seed),
    }
    validation_c, validation_r = {}, {}
    for name, model in candidates.items():
        model.fit(train[FEATURES], train.inactive_next90)
        validation_c[name] = classification_metrics(validation.inactive_next90, model.predict_proba(validation[FEATURES])[:, 1])
    for name, model in regressors.items():
        model.fit(train[FEATURES], train.margin_next90)
        validation_r[name] = regression_metrics(validation.margin_next90, model.predict(validation[FEATURES]))
    best_c = max(validation_c, key=lambda n: validation_c[n]["average_precision"])
    best_r = min(validation_r, key=lambda n: validation_r[n]["mae"])
    # Validation labels end before test begins. Refit the already selected models.
    development = pd.concat([train, validation], ignore_index=True)
    classifier, regressor = candidates[best_c], regressors[best_r]
    classifier.fit(development[FEATURES], development.inactive_next90)
    regressor.fit(development[FEATURES], development.margin_next90)
    test_p = classifier.predict_proba(test[FEATURES])[:, 1]
    test_v = regressor.predict(test[FEATURES])
    cbase = DummyClassifier(strategy="prior").fit(development[FEATURES], development.inactive_next90)
    rbase = DummyRegressor(strategy="mean").fit(development[FEATURES], development.margin_next90)
    # A simple recency ranking is an additional, non-probabilistic baseline.
    recency = test.recency_days.to_numpy()
    recency_top = np.argsort(-recency, kind="stable")[:max(1, math.ceil(len(test) * .2))]
    recency_precision = float(test.inactive_next90.to_numpy()[recency_top].mean())
    metrics = dict(
        source="synthetic", target="No sale in next 90 days; eligible if last sale <=180 days ago",
        evaluation_population="Existing customers across time; not an unseen-customer holdout",
        selected_classifier=best_c, selected_value_model=best_r,
        validation_classification=validation_c, validation_value=validation_r,
        test_classification=classification_metrics(test.inactive_next90, test_p),
        test_classification_baseline=classification_metrics(test.inactive_next90, cbase.predict_proba(test[FEATURES])[:, 1]),
        test_recency_ranking=dict(average_precision=float(average_precision_score(test.inactive_next90, recency)),
                                 precision_at_20pct=recency_precision,
                                 lift_at_20pct=recency_precision / float(test.inactive_next90.mean())),
        test_value=regression_metrics(test.margin_next90, test_v),
        test_value_baseline=regression_metrics(test.margin_next90, rbase.predict(test[FEATURES])),
        feature_names=FEATURES,
        split_counts={"train_rows":len(train), "validation_rows":len(validation), "test_rows":len(test)},
        evaluation_note="Test used once for reporting; no hyperparameter or threshold tuning on test. Synthetic metrics do not estimate real business impact.")
    importance = permutation_importance(classifier, test[FEATURES], test.inactive_next90,
                                        scoring="average_precision", n_repeats=3, random_state=seed)
    importance_df = pd.DataFrame(dict(feature=FEATURES, average_precision_drop=importance.importances_mean,
                                      std=importance.importances_std)).sort_values("average_precision_drop", ascending=False)
    predictions = test[["customer_id", "snapshot_date", "inactive_next90", "margin_next90"]].copy()
    predictions["predicted_risk"] = test_p
    predictions["predicted_margin90"] = test_v
    # Final model sees all completed historical labels, never the scoring horizon.
    all_labeled = pd.concat([train, validation, test], ignore_index=True)
    classifier.fit(all_labeled[FEATURES], all_labeled.inactive_next90)
    regressor.fit(all_labeled[FEATURES], all_labeled.margin_next90)
    result = scoring.copy()
    result["inactive_risk90"] = classifier.predict_proba(scoring[FEATURES])[:, 1]
    result["expected_margin90"] = regressor.predict(scoring[FEATURES])
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(dict(classifier=classifier, value_model=regressor, features=FEATURES,
                     score_cutoff=scoring.snapshot_date.iloc[0], source="synthetic"), model_dir / "models.joblib")
    return result, metrics, importance_df, predictions
