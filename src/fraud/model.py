"""
Fraud detection model for FinTechCo payment system.

Provides a champion (RandomForest) and challenger (GradientBoosting) model
trained on synthetic transaction data. The module lazily trains on first use
and caches models at module level for subsequent calls.

Functions:
    train_model       -- Train both models on a DataFrame of labelled transactions.
    get_model_metrics -- Return accuracy, precision, recall, F1, AUC-ROC, and top features.
    predict_fraud     -- Score a list of transaction dicts for fraud probability.
    get_risk_distribution -- Histogram of fraud scores across risk buckets.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.fraud.data_generator import generate_transactions

# ---------------------------------------------------------------------------
# Feature definitions
# ---------------------------------------------------------------------------

NUMERIC_FEATURES = [
    "amount",
    "ip_risk_score",
    "account_age_days",
    "hour_of_day",
    "transaction_velocity_1h",
    "avg_amount_30d",
    "is_weekend",
    # derived numeric
    "amount_to_avg_ratio",
    "is_night",
    "is_new_account",
]

CATEGORICAL_FEATURES = [
    "payment_rail",
    "device_type",
    "sender_country",
    "receiver_country",
]

# ---------------------------------------------------------------------------
# Module-level model cache
# ---------------------------------------------------------------------------

_model_cache: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add engineered features to a copy of the DataFrame.

    Derived features:
        * ``amount_to_avg_ratio`` -- amount / avg_amount_30d
        * ``is_night``            -- 1 if hour_of_day in [0, 5]
        * ``is_new_account``      -- 1 if account_age_days < 30
    """
    df = df.copy()
    df["amount_to_avg_ratio"] = (
        df["amount"] / df["avg_amount_30d"].replace(0, np.nan)
    ).fillna(0.0)
    df["is_night"] = (df["hour_of_day"].between(0, 5)).astype(int)
    df["is_new_account"] = (df["account_age_days"] < 30).astype(int)
    return df


def _build_preprocessor() -> ColumnTransformer:
    """Build the sklearn ColumnTransformer for numeric + categorical features."""
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )


def _build_pipeline(estimator) -> Pipeline:
    """Wrap a preprocessor and estimator into a single sklearn Pipeline."""
    return Pipeline([
        ("preprocessor", _build_preprocessor()),
        ("classifier", estimator),
    ])


def _evaluate(pipeline: Pipeline, X: pd.DataFrame, y: pd.Series) -> dict:
    """Compute classification metrics for a fitted pipeline."""
    y_pred = pipeline.predict(X)
    y_proba = pipeline.predict_proba(X)[:, 1]

    cm = confusion_matrix(y, y_pred)

    return {
        "accuracy": round(float(accuracy_score(y, y_pred)), 4),
        "precision": round(float(precision_score(y, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y, y_pred, zero_division=0)), 4),
        "auc_roc": round(float(roc_auc_score(y, y_proba)), 4),
        "confusion_matrix": cm.tolist(),
    }


def _get_feature_names(pipeline: Pipeline) -> list[str]:
    """Extract final feature names from the fitted preprocessor."""
    preprocessor: ColumnTransformer = pipeline.named_steps["preprocessor"]
    names: list[str] = list(NUMERIC_FEATURES)
    cat_encoder: OneHotEncoder = preprocessor.named_transformers_["cat"]
    names.extend(cat_encoder.get_feature_names_out(CATEGORICAL_FEATURES).tolist())
    return names


def _top_importances(pipeline: Pipeline, n: int = 10) -> list[dict]:
    """Return the top-n feature importances from a tree-based classifier."""
    feature_names = _get_feature_names(pipeline)
    importances = pipeline.named_steps["classifier"].feature_importances_
    indices = np.argsort(importances)[::-1][:n]
    return [
        {"feature": feature_names[i], "importance": round(float(importances[i]), 4)}
        for i in indices
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def train_model(df: pd.DataFrame) -> dict:
    """Train champion and challenger fraud-detection models.

    The champion is a ``RandomForestClassifier`` and the challenger is a
    ``GradientBoostingClassifier``, both with ``class_weight='balanced'``
    to handle the natural class imbalance in fraud data.

    Args:
        df: DataFrame of labelled transactions.  Must contain all raw feature
            columns listed in ``NUMERIC_FEATURES`` (minus derived ones) and
            ``CATEGORICAL_FEATURES``, plus an ``is_fraud`` label column.

    Returns:
        dict with keys:
            * ``champion``  -- fitted sklearn Pipeline (RandomForest)
            * ``challenger`` -- fitted sklearn Pipeline (GradientBoosting)
            * ``champion_metrics``  -- accuracy, precision, recall, f1, auc_roc,
              confusion_matrix, feature_importances
            * ``challenger_metrics`` -- same structure
            * ``X_test`` / ``y_test`` -- held-out test data for later scoring
    """
    global _model_cache

    df = _add_derived_features(df)

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df["is_fraud"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y,
    )

    # Champion: RandomForest
    champion_pipeline = _build_pipeline(
        RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            min_samples_leaf=4,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
    )

    # Challenger: GradientBoosting
    challenger_pipeline = _build_pipeline(
        GradientBoostingClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            min_samples_leaf=6,
            random_state=42,
        )
    )

    # GradientBoostingClassifier doesn't support class_weight, so we compute
    # sample weights manually to handle imbalance.
    fraud_count = int(y_train.sum())
    legit_count = len(y_train) - fraud_count
    weight_for_fraud = legit_count / max(fraud_count, 1)
    sample_weights = y_train.map({0: 1.0, 1: weight_for_fraud}).values

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        champion_pipeline.fit(X_train, y_train)
        challenger_pipeline.fit(X_train, y_train, classifier__sample_weight=sample_weights)

    champion_metrics = _evaluate(champion_pipeline, X_test, y_test)
    champion_metrics["feature_importances"] = _top_importances(champion_pipeline)

    challenger_metrics = _evaluate(challenger_pipeline, X_test, y_test)
    challenger_metrics["feature_importances"] = _top_importances(challenger_pipeline)

    _model_cache = {
        "champion": champion_pipeline,
        "challenger": challenger_pipeline,
        "champion_metrics": champion_metrics,
        "challenger_metrics": challenger_metrics,
        "X_test": X_test,
        "y_test": y_test,
    }

    return _model_cache


def _ensure_model() -> dict:
    """Lazily train models on first access using synthetic data.

    Generates 10 000 transactions via ``generate_transactions``, trains
    both champion and challenger models, and caches them at module level.
    Subsequent calls return the cached result immediately.

    Returns:
        The same dict produced by :func:`train_model`.
    """
    global _model_cache
    if _model_cache is None:
        df = generate_transactions(n=10000, seed=42)
        train_model(df)
    return _model_cache  # type: ignore[return-value]


def get_model_metrics() -> dict:
    """Return performance metrics for both champion and challenger models.

    Metrics include accuracy, precision, recall, F1, AUC-ROC, confusion
    matrix, and the top 10 feature importances (by Gini / gain).

    Returns:
        dict with ``champion`` and ``challenger`` sub-dicts, each containing
        accuracy, precision, recall, f1, auc_roc, confusion_matrix, and
        feature_importances.
    """
    cache = _ensure_model()
    return {
        "champion": cache["champion_metrics"],
        "challenger": cache["challenger_metrics"],
    }


def predict_fraud(transactions: list[dict]) -> list[dict]:
    """Score transactions for fraud using the champion model.

    Each input dict must contain the raw feature columns (amount,
    ip_risk_score, account_age_days, hour_of_day, transaction_velocity_1h,
    avg_amount_30d, is_weekend, payment_rail, device_type, sender_country,
    receiver_country).

    Args:
        transactions: List of transaction dicts with feature values.

    Returns:
        The same dicts, each augmented with:
            * ``fraud_score`` -- float in [0, 1] from the champion model
            * ``fraud_prediction`` -- bool, True if fraud_score >= 0.5
    """
    cache = _ensure_model()
    champion: Pipeline = cache["champion"]

    df = pd.DataFrame(transactions)
    df = _add_derived_features(df)
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]

    probas = champion.predict_proba(X)[:, 1]

    results = []
    for txn, score in zip(transactions, probas):
        enriched = dict(txn)
        enriched["fraud_score"] = round(float(score), 4)
        enriched["fraud_prediction"] = bool(score >= 0.5)
        results.append(enriched)

    return results


def get_risk_distribution() -> dict:
    """Return a histogram of fraud scores across risk buckets.

    Scores the held-out test set and buckets results into five ranges:
    0.0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0.

    Returns:
        dict with:
            * ``buckets`` -- list of bucket label strings
            * ``counts``  -- list of ints (total transactions per bucket)
            * ``fraud_counts`` -- list of ints (actual fraud per bucket)
    """
    cache = _ensure_model()
    champion: Pipeline = cache["champion"]
    X_test: pd.DataFrame = cache["X_test"]
    y_test = cache["y_test"]

    probas = champion.predict_proba(X_test)[:, 1]

    bucket_edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    bucket_labels = ["0.0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"]
    counts = []
    fraud_counts = []

    for lo, hi in zip(bucket_edges[:-1], bucket_edges[1:]):
        if hi < 1.0:
            mask = (probas >= lo) & (probas < hi)
        else:
            mask = (probas >= lo) & (probas <= hi)
        counts.append(int(mask.sum()))
        fraud_counts.append(int(y_test.values[mask].sum()))

    return {
        "buckets": bucket_labels,
        "counts": counts,
        "fraud_counts": fraud_counts,
    }
