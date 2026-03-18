# FinTechCo — Money Movement Hub

An AI-powered payment routing dashboard that demonstrates how machine learning optimizes transaction costs across multiple payment rails.

The dashboard visualizes a realistic payment routing system processing 4.3M daily transactions across five rails (Zelle, RTP, FedNow, ACH, Wire), with an AI routing engine that selects the cheapest available rail for each transaction.

![Dashboard Screenshot](https://img.shields.io/badge/status-demo-blue)

## What it does

- **AI routing engine** scores payment rails in real time based on cost, success rate, and transfer size
- **Cost optimization** reduces average routing cost from $0.74/tx (rule-based) to $0.22/tx (AI-routed)
- **Anomaly detection** surfaces cost-saving opportunities with estimated monthly impact
- **Sync simulation** models a routing model refresh pipeline with error states

## Architecture

```
dashboard.html     ← Single-page dashboard (vanilla HTML/JS/Chart.js)
api/app.py         ← FastAPI backend serving metrics and routing APIs
src/
  rails/data.py    ← Rail definitions (cost, latency, success rates)
  routing/
    router.py      ← AI scoring model (scores rails per transaction)
    runner.py      ← 3-step sync pipeline orchestration
    generator.py   ← Synthetic payment batch generation
  payments/
    generator.py   ← Dashboard data generators (KPIs, charts, feed)
```

## Getting started

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn api.app:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000)

## Payment rails

| Rail | Cost | Speed | Use case |
|------|------|-------|----------|
| Zelle | Free | <2s | Consumer P2P |
| RTP | $0.50 | <10s | Real-time payments |
| FedNow | $0.45 | <10s | Federal Reserve instant rail |
| ACH | $0.25 | Next day | Batch, high volume |
| Wire | $25.00 | 2–4h | High-value, last resort |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard |
| GET | `/health` | Health check |
| GET | `/api/metrics` | KPI summary |
| GET | `/api/rails` | Rail status |
| GET | `/api/payments` | Recent transactions |
| GET | `/api/model-health` | Routing model status |
| GET | `/api/chart-data` | Volume and cost chart data |
| POST | `/api/sync-routing-model` | Trigger routing model sync |

## Tech stack

- **Frontend**: HTML, CSS, Chart.js, Font Awesome
- **Backend**: Python, FastAPI, Uvicorn
- **Data**: Synthetic generation (no external dependencies)
