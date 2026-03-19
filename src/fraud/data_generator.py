"""
Synthetic fraud transaction data generator for FinTechCo Fraud Detection.

Generates realistic payment transactions with labeled fraud indicators.
Fraud patterns mirror real-world fintech attack vectors: new-account abuse,
off-hours velocity spikes, cross-border high-risk IP transactions, and
amount anomalies relative to historical baselines.

Usage:
    from src.fraud.data_generator import generate_transactions, get_fraud_summary

    df = generate_transactions(10000)
    summary = get_fraud_summary(df)
"""

import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.rails.data import RAIL_IDS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEED = 42

COUNTRIES = [
    "US", "US", "US", "US", "US",  # domestic-heavy weighting
    "GB", "CA", "DE", "NG", "IN", "BR", "CN", "RU", "PH", "MX",
]
"""Country pool weighted toward US (domestic majority)."""

HIGH_RISK_COUNTRIES = {"NG", "RU", "CN"}

DEVICE_TYPES = ["mobile", "desktop", "tablet", "api"]
DEVICE_WEIGHTS = [0.52, 0.30, 0.10, 0.08]

# Rail selection weights for legitimate vs fraudulent transactions
LEGIT_RAIL_WEIGHTS = {
    "zelle": 0.31, "ach": 0.28, "rtp": 0.10, "fednow": 0.08,
    "venmo": 0.07, "paypal": 0.06, "same_day_ach": 0.04,
    "card_push": 0.03, "wire": 0.02, "swift": 0.01,
}

FRAUD_RAIL_WEIGHTS = {
    "wire": 0.22, "swift": 0.18, "card_push": 0.15, "zelle": 0.12,
    "rtp": 0.10, "ach": 0.08, "same_day_ach": 0.05, "paypal": 0.04,
    "venmo": 0.03, "fednow": 0.03,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _weighted_choice(rng: np.random.Generator, options: list,
                     weights: list, size: int) -> np.ndarray:
    """Draw *size* samples from *options* according to *weights*."""
    probs = np.array(weights, dtype=float)
    probs /= probs.sum()
    return rng.choice(options, size=size, p=probs)


def _generate_base_transactions(rng: np.random.Generator, n: int,
                                now: datetime) -> pd.DataFrame:
    """Create a DataFrame of *n* transactions with neutral (non-fraud-biased) fields."""
    # Timestamps spread over the last 30 days
    offsets = rng.integers(0, 30 * 24 * 3600, size=n)
    timestamps = pd.to_datetime([now - timedelta(seconds=int(s)) for s in offsets])

    # Amounts follow a log-normal distribution (median ~$250, long tail past $50k)
    amounts = np.round(rng.lognormal(mean=5.5, sigma=1.4, size=n), 2)
    amounts = np.clip(amounts, 1.00, 500_000.00)

    # Account ages -- most accounts are established, some are brand new
    account_ages = rng.exponential(scale=365, size=n).astype(int)
    account_ages = np.clip(account_ages, 1, 3650)

    # Average amount over the last 30 days (correlated with current amount)
    avg_amount_30d = amounts * rng.uniform(0.6, 1.2, size=n)
    avg_amount_30d = np.round(avg_amount_30d, 2)

    df = pd.DataFrame({
        "transaction_id": [uuid.uuid4().hex[:16] for _ in range(n)],
        "timestamp": timestamps,
        "amount": amounts,
        "sender_id": [f"USR-{rng.integers(100000, 999999)}" for _ in range(n)],
        "receiver_id": [f"USR-{rng.integers(100000, 999999)}" for _ in range(n)],
        "payment_rail": _weighted_choice(
            rng, list(LEGIT_RAIL_WEIGHTS.keys()),
            list(LEGIT_RAIL_WEIGHTS.values()), n,
        ),
        "sender_country": rng.choice(COUNTRIES, size=n),
        "receiver_country": rng.choice(COUNTRIES, size=n),
        "device_type": _weighted_choice(rng, DEVICE_TYPES, DEVICE_WEIGHTS, n),
        "ip_risk_score": rng.integers(0, 35, size=n),
        "account_age_days": account_ages,
        "is_weekend": np.isin(timestamps.weekday, [5, 6]).astype(int),
        "hour_of_day": timestamps.hour,
        "transaction_velocity_1h": rng.poisson(lam=1.2, size=n),
        "avg_amount_30d": avg_amount_30d,
        "is_fraud": 0,
    })

    return df


def _inject_fraud(rng: np.random.Generator, df: pd.DataFrame,
                  fraud_rate: float = 0.03) -> pd.DataFrame:
    """Mark ~*fraud_rate* of rows as fraud and skew their features to match
    realistic attack patterns.

    Fraud patterns applied (each fraud row gets 1-3 overlapping signals):
        1. New-account abuse -- account_age_days < 30, elevated amount
        2. Off-hours velocity -- hour 2-5 AM, velocity > 5
        3. Cross-border + high IP risk -- different countries, ip_risk_score > 70
        4. Amount anomaly -- amount >> avg_amount_30d
        5. High-value rail preference -- wire / swift / card_push
    """
    n = len(df)
    n_fraud = int(n * fraud_rate)
    fraud_idx = rng.choice(n, size=n_fraud, replace=False)

    df.loc[fraud_idx, "is_fraud"] = 1

    for idx in fraud_idx:
        patterns = rng.choice(
            ["new_account", "off_hours", "cross_border",
             "amount_spike", "high_value_rail"],
            size=rng.integers(1, 4),
            replace=False,
        )

        for p in patterns:
            if p == "new_account":
                df.at[idx, "account_age_days"] = int(rng.integers(1, 30))
                df.at[idx, "amount"] = round(float(rng.uniform(2000, 50000)), 2)

            elif p == "off_hours":
                fraud_hour = int(rng.integers(2, 6))
                ts = df.at[idx, "timestamp"].replace(hour=fraud_hour)
                df.at[idx, "timestamp"] = ts
                df.at[idx, "hour_of_day"] = fraud_hour
                df.at[idx, "transaction_velocity_1h"] = int(rng.integers(5, 20))

            elif p == "cross_border":
                non_us = [c for c in COUNTRIES if c != "US"]
                df.at[idx, "sender_country"] = rng.choice(non_us)
                df.at[idx, "receiver_country"] = rng.choice(
                    list(HIGH_RISK_COUNTRIES),
                )
                df.at[idx, "ip_risk_score"] = int(rng.integers(70, 100))

            elif p == "amount_spike":
                baseline = float(df.at[idx, "avg_amount_30d"])
                multiplier = float(rng.uniform(5, 25))
                df.at[idx, "amount"] = round(baseline * multiplier, 2)

            elif p == "high_value_rail":
                rail_keys = list(FRAUD_RAIL_WEIGHTS.keys())
                rail_probs = list(FRAUD_RAIL_WEIGHTS.values())
                df.at[idx, "payment_rail"] = _weighted_choice(
                    rng, rail_keys, rail_probs, 1,
                )[0]

    # Clamp values to valid ranges
    df["ip_risk_score"] = df["ip_risk_score"].clip(0, 100).astype(int)
    df["amount"] = df["amount"].clip(1.00, 500_000.00).round(2)

    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_transactions(n: int = 10000, fraud_rate: float = 0.03) -> pd.DataFrame:
    """Generate *n* synthetic payment transactions with fraud labels.

    Uses a fixed random seed (42) for reproducibility across runs.

    Args:
        n: Number of transactions to generate.
        fraud_rate: Approximate fraction of transactions labeled as fraud
            (default 3%).

    Returns:
        A pandas DataFrame sorted by timestamp (most recent first) with columns:
        transaction_id, timestamp, amount, sender_id, receiver_id, payment_rail,
        sender_country, receiver_country, device_type, ip_risk_score,
        account_age_days, is_weekend, hour_of_day, transaction_velocity_1h,
        avg_amount_30d, is_fraud.

    Example:
        >>> df = generate_transactions(10000)
        >>> df.shape
        (10000, 16)
        >>> 0.02 < df["is_fraud"].mean() < 0.05
        True
    """
    rng = np.random.default_rng(SEED)
    now = datetime.utcnow()

    df = _generate_base_transactions(rng, n, now)
    df = _inject_fraud(rng, df, fraud_rate=fraud_rate)

    df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
    return df


def get_fraud_summary(df: pd.DataFrame) -> dict:
    """Compute summary statistics from a transaction DataFrame.

    Args:
        df: DataFrame produced by :func:`generate_transactions`.

    Returns:
        Dictionary with keys:
            total_transactions, fraud_count, legitimate_count, fraud_rate,
            avg_fraud_amount, avg_legit_amount, median_fraud_amount,
            top_fraud_rails, fraud_by_device, fraud_by_hour,
            high_risk_ip_fraud_pct, new_account_fraud_pct,
            cross_border_fraud_pct.
    """
    fraud = df[df["is_fraud"] == 1]
    legit = df[df["is_fraud"] == 0]
    n_fraud = len(fraud)

    # Top rails by fraud volume
    rail_fraud = (
        fraud.groupby("payment_rail")
        .size()
        .sort_values(ascending=False)
        .reset_index(name="fraud_count")
    )
    top_fraud_rails = rail_fraud.to_dict(orient="records")

    # Fraud by device type
    fraud_by_device = fraud["device_type"].value_counts().to_dict()

    # Fraud by hour of day
    fraud_by_hour = fraud["hour_of_day"].value_counts().sort_index().to_dict()
    fraud_by_hour = {int(k): int(v) for k, v in fraud_by_hour.items()}

    # Derived risk indicators
    high_risk_ip = int((fraud["ip_risk_score"] >= 70).sum())
    new_account = int((fraud["account_age_days"] < 30).sum())
    cross_border = int(
        (fraud["sender_country"] != fraud["receiver_country"]).sum()
    )

    return {
        "total_transactions": len(df),
        "fraud_count": n_fraud,
        "legitimate_count": len(legit),
        "fraud_rate": round(n_fraud / len(df), 4) if len(df) else 0.0,
        "avg_fraud_amount": round(float(fraud["amount"].mean()), 2) if n_fraud else 0.0,
        "avg_legit_amount": round(float(legit["amount"].mean()), 2) if len(legit) else 0.0,
        "median_fraud_amount": round(float(fraud["amount"].median()), 2) if n_fraud else 0.0,
        "top_fraud_rails": top_fraud_rails,
        "fraud_by_device": fraud_by_device,
        "fraud_by_hour": fraud_by_hour,
        "high_risk_ip_fraud_pct": round(high_risk_ip / n_fraud, 4) if n_fraud else 0.0,
        "new_account_fraud_pct": round(new_account / n_fraud, 4) if n_fraud else 0.0,
        "cross_border_fraud_pct": round(cross_border / n_fraud, 4) if n_fraud else 0.0,
    }


def get_recent_transactions(n: int = 20) -> list[dict]:
    """Generate and return the *n* most recent transactions as a list of dicts.

    Convenience wrapper for API endpoints that need JSON-serializable output.
    Timestamps are converted to ISO-8601 strings.

    Args:
        n: Number of recent transactions to return (default 20).

    Returns:
        List of transaction dicts, sorted by timestamp descending.
    """
    df = generate_transactions(n=max(n, 1000))
    recent = df.head(n).copy()
    recent["timestamp"] = recent["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return recent.to_dict(orient="records")
