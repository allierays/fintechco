"""
Lambda handler for routing model sync.
Simulates a sync failure — logs the error to CloudWatch so Claude Code can find it.
"""

import json
import logging
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """
    Routing model sync endpoint.
    Steps through the pipeline, then fails on feature store pull.
    """
    logger.info("sync_routing_model: pipeline initiated")
    logger.info("pipeline.step1.start: connecting to routing service")
    time.sleep(0.3)
    logger.info("pipeline.step1.complete: connected")

    logger.info("pipeline.step2.start: pulling feature store")
    time.sleep(0.5)

    # Intentional failure — this is what Claude Code will find
    logger.error(
        "pipeline.step2.failed: feature store sync error — "
        "upstream timeout after 30000ms. "
        "Root cause: router.py:17 cost_weight hardcoded to 0.5, "
        "causing stale weight cache invalidation loop. "
        "Service: routing-model-v3.1.2, region: us-east-1"
    )
    logger.error(
        "CloudWatch Alarm: avg_cost_per_txn exceeded threshold. "
        "Current: $1.91, threshold: $0.50. "
        "Wire rail over-selected for large transfers (847 txns in 71h). "
        "Excess cost: $20,768"
    )

    return {
        "statusCode": 503,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({
            "error": "Service Unavailable",
            "message": "Cloudflare 503 — upstream timeout pulling feature store",
            "service": "routing-model-v3.1.2",
        }),
    }
