"""
FinTechCo Money Movement Hub API
"""

import json
import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from src.payments.generator import (
    generate_metrics,
    generate_payments,
    generate_model_health,
    generate_chart_data,
    generate_rails,
)
from src.routing.runner import run_sync_pipeline
from src.fraud.data_generator import generate_transactions, get_fraud_summary, get_recent_transactions
from src.fraud.model import get_model_metrics, predict_fraud, get_risk_distribution


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **({"exc_info": self.formatException(record.exc_info)} if record.exc_info else {}),
        })

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_JsonFormatter())
logging.root.handlers = [_handler]
logging.root.setLevel(logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(title="FinTechCo Money Movement Hub API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(Path(__file__).parent.parent / "dashboard.html")


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/metrics")
def get_metrics():
    return generate_metrics()


@app.get("/api/rails")
def get_rails():
    return {"rails": generate_rails()}


@app.get("/api/payments")
def get_payments():
    return {"payments": generate_payments(count=20)}


@app.get("/api/model-health")
def get_model_health():
    return generate_model_health()


@app.get("/api/chart-data")
def get_chart_data():
    return generate_chart_data()


@app.get("/fraud", include_in_schema=False)
def fraud_dashboard():
    return FileResponse(Path(__file__).parent.parent / "fraud_dashboard.html")


@app.get("/api/fraud/metrics")
def get_fraud_metrics():
    df = generate_transactions(n=10000)
    summary = get_fraud_summary(df)
    metrics = get_model_metrics()
    return {
        "transactions_24h": summary["total_transactions"],
        "fraud_detection_rate": round(metrics["champion"]["recall"] * 100, 1),
        "false_positive_rate": round((1 - metrics["champion"]["precision"]) * 100, 1),
        "amount_saved": round(summary["total_fraud_amount"] * metrics["champion"]["recall"], 2),
        "model_accuracy": round(metrics["champion"]["accuracy"] * 100, 1),
        "avg_detection_time_ms": 12,
    }


@app.get("/api/fraud/transactions")
def get_fraud_transactions():
    recent = get_recent_transactions(n=30)
    scored = predict_fraud(recent)
    flagged = [t for t in scored if t["fraud_score"] > 0.3]
    flagged.sort(key=lambda x: x["fraud_score"], reverse=True)
    return {"transactions": flagged[:20]}


@app.get("/api/fraud/model-performance")
def get_fraud_model_performance():
    return get_model_metrics()


@app.get("/api/fraud/risk-distribution")
def get_fraud_risk_distribution():
    return get_risk_distribution()


@app.get("/api/fraud/chart-data")
def get_fraud_chart_data():
    df = generate_transactions(n=5000)
    df["hour"] = df["hour_of_day"]
    hourly = df.groupby("hour").agg(
        total=("is_fraud", "count"),
        fraud=("is_fraud", "sum"),
    ).reset_index()
    rail_fraud = df.groupby("payment_rail").agg(
        total=("is_fraud", "count"),
        fraud=("is_fraud", "sum"),
    ).reset_index()
    rail_fraud["fraud_rate"] = round(rail_fraud["fraud"] / rail_fraud["total"] * 100, 2)
    return {
        "hourly": {
            "labels": hourly["hour"].tolist(),
            "legitimate": (hourly["total"] - hourly["fraud"]).tolist(),
            "fraud": hourly["fraud"].tolist(),
        },
        "by_rail": {
            "labels": rail_fraud["payment_rail"].tolist(),
            "fraud_rates": rail_fraud["fraud_rate"].tolist(),
            "fraud_counts": rail_fraud["fraud"].tolist(),
        },
    }


@app.post("/api/sync-routing-model")
def sync_routing_model():
    """
    Sync the routing model — runs the 3-step pipeline:
    1. Pull payment batch
    2. Recompute rail weights
    3. Recalibrate thresholds
    """
    logger.info("sync_routing_model: pipeline initiated")
    result = run_sync_pipeline()
    logger.info("sync_routing_model: pipeline complete in %dms", result["total_duration_ms"])
    return result
