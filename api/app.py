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
