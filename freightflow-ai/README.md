# FreightFlow AI

AI-powered automation middleware for freight brokers. Ingests unstructured
freight emails/documents, extracts structured load data, cross-references
historical lane rates to compute a recommended quote and margin, and
generates a client-ready email + PDF rate confirmation — all surfaced on a
live broker operations dashboard.

## Stack

- **Backend:** FastAPI + SQLAlchemy + SQLite, Pandas-based rate engine,
  pdfplumber for PDF text extraction, ReportLab for PDF generation, optional
  Claude (Anthropic) structured-output parsing.
- **Frontend:** React (Vite) + Tailwind CSS, polling-based live dashboard.

## Quick Start

The fastest way to run everything:

```bash
cd freightflow-ai
./run.sh
```

This creates a Python virtualenv, installs backend deps, installs frontend
deps (first run only), and starts both servers:

- Backend API: http://localhost:8000 (interactive docs at `/docs`)
- Dashboard: http://localhost:5173

Press `Ctrl+C` to stop both.

## Manual Setup

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

On first run the SQLite database (`backend/data/freightflow.db`) is created
and seeded automatically with sample historical lane rates, a fuel
surcharge, and target carrier margins by equipment type.

Optional: copy `backend/.env.example` to `backend/.env` and set
`ANTHROPIC_API_KEY` to use real LLM structured-output extraction instead of
the built-in offline mock parser. The app works fully without this.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Optional: copy `frontend/.env.example` to `frontend/.env` to point the
dashboard at a non-default backend URL (`VITE_API_URL`).

## How It Works

### 1. Inbound ingestion

- `POST /api/ingest/email` — simulates an inbound freight email/webhook.
  Accepts raw unstructured text (`raw_text`, optional `filename`).
- `POST /api/ingest/document` — accepts an uploaded PDF (rate confirmation,
  BOL, load tender). Text is extracted with `pdfplumber`.

Both create a `Tender` in `incoming` status containing the raw text.

### 2. AI parsing + rate engine

`POST /api/tenders/{id}/process` runs:

1. **Parsing** (`app/parser.py`) — extracts origin, destination, equipment
   type, weight, pickup date, and commodity into clean JSON. Uses Claude
   structured tool-output when `ANTHROPIC_API_KEY` is set, otherwise a
   deterministic regex/heuristic mock parser (no API key required).
2. **Rate engine** (`app/rate_engine.py`) — loads historical lane rates into
   a Pandas DataFrame, matches the parsed lane/equipment (falling back to
   equipment-type or national averages when no exact lane match exists),
   applies the current fuel surcharge, and computes carrier cost, a
   recommended customer rate, and estimated profit margin using each
   equipment type's target margin.
3. **Quote draft generation** (`app/quote_generator.py`) — immediately
   produces a client-ready email draft and an HTML + PDF rate confirmation
   sheet.

The tender moves to `parsed_quoted` status.

### 3. Broker decision

`POST /api/tenders/{id}/decision` with `{"action": "approve"}` accepts the
AI-recommended rate, or `{"action": "override", "override_rate": 2500}` to
set a custom rate. Either way the tender moves to `active` and the quote
documents are regenerated with the final rate.

### 4. Completion / audit

`POST /api/tenders/{id}/audit` marks an active load `audited` once its
document trail is complete.

### Dashboard

The React dashboard polls `GET /api/tenders` every few seconds and renders
a kanban board with four columns matching the lifecycle above: **Incoming
Tenders**, **AI Parsed & Quoted**, **Active Loads**, **Audited Documents**.
Each card exposes the relevant action (run AI parse & quote, approve/
override, mark audited) and a detail view with the full rate breakdown,
raw source text, AI-drafted email, and a PDF download link.

## Project Structure

```
freightflow-ai/
├── run.sh                   # one-command launcher for both services
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py          # FastAPI app, CORS, router registration
│   │   ├── database.py      # SQLAlchemy engine/session (SQLite)
│   │   ├── models.py        # Tender, Quote, LaneRate, FuelSurcharge, CarrierMargin
│   │   ├── schemas.py       # Pydantic request/response models
│   │   ├── parser.py        # mock + Anthropic structured-output extraction
│   │   ├── rate_engine.py   # Pandas-based margin/rate calculation
│   │   ├── quote_generator.py  # email draft + HTML/PDF rate confirmation
│   │   ├── seed_data.py     # sample historical lane rates & margins
│   │   ├── templates/rate_confirmation.html
│   │   └── routers/
│   │       ├── ingestion.py # POST /api/ingest/email, /api/ingest/document
│   │       ├── tenders.py   # list/process/decision/audit/quote/pdf endpoints
│   │       └── lanes.py     # GET /api/lanes
│   └── data/                # SQLite DB + generated PDFs (gitignored)
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── api.js            # axios client
    │   └── components/
    │       ├── KanbanBoard.jsx
    │       ├── TenderCard.jsx
    │       ├── TenderDetailModal.jsx
    │       ├── IngestModal.jsx
    │       └── StatusBadge.jsx
    └── ...
```

## API Reference

| Method | Path | Description |
|---|---|---|
| POST | `/api/ingest/email` | Ingest raw tender text |
| POST | `/api/ingest/document` | Ingest a PDF document |
| GET | `/api/tenders` | List tenders (optional `?status=`) |
| GET | `/api/tenders/{id}` | Get one tender |
| POST | `/api/tenders/{id}/process` | Run AI parse + rate engine + quote draft |
| POST | `/api/tenders/{id}/decision` | Approve or override the quote |
| POST | `/api/tenders/{id}/audit` | Mark an active load audited |
| GET | `/api/tenders/{id}/quote` | Latest email draft + HTML rate confirmation |
| GET | `/api/tenders/{id}/pdf` | Download the rate confirmation PDF |
| GET | `/api/lanes` | List historical lane rate data |

Full interactive documentation (Swagger UI) is available at
`http://localhost:8000/docs` while the backend is running.
