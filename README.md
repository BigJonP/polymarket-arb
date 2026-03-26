# polymarket-arb

MVP full-stack app for detecting Polymarket cross-market inconsistencies and relative-value opportunities.

## Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Frontend: React, TypeScript, Vite, Tailwind CSS
- Data pipeline: Polymarket ingestion, heuristic candidate generation, hybrid relation analysis, opportunity scoring

## What it does

- Fetches active Polymarket markets and stores raw market payloads
- Generates likely related market pairs without brute-forcing every combination
- Uses rule-based logic first, then an LLM for stricter relation detection
- Classifies relationships as `exclusive`, `implies`, `subset`, `negative_correlation`, and other supported types
- Scores three opportunity classes:
  - `hard_arb`
  - `structural_mispricing`
  - `soft_dislocation`
- Exposes a dashboard and detail view for the active opportunity set

## Project layout

```text
backend/
  app/
    api/
    services/
    config.py
    db.py
    main.py
    models.py
    schemas.py
frontend/
  src/
    api/
    components/
    pages/
    types/
docker-compose.yml
```

## Environment

Copy `.env.example` to `.env` and adjust values if needed.

Important values:

- `DATABASE_URL`: should point to the Dockerized Postgres instance on `localhost:5432`
- `MARKET_SCAN_LIMIT`: number of fetched markets to analyze per refresh, default `50`
- `OPENAI_API_KEY`: optional; if unset, the app falls back to rule-only relation detection
- `OPENAI_BATCH_SIZE`: number of candidate pairs grouped into each OpenAI relation-analysis request
- `VITE_API_BASE_URL`: frontend API base

## Local run

Shortcut with `make`:

```bash
make install
make dev
```

### 1. Start PostgreSQL

The database is Docker-only in this project. Start it with:

```bash
make db
```

or:

```bash
docker compose up db -d
```

### 2. Run the backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

or:

```bash
make backend
```

Backend endpoints:

- `GET /health`
- `GET /markets`
- `GET /markets/{id}`
- `GET /opportunities`
- `GET /opportunities/{id}`
- `POST /admin/refresh`

### 3. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

or:

```bash
make frontend
```

Open `http://localhost:5173`.

## Docker run

Build and run the full stack:

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Postgres: Docker container published on `localhost:5432`

## Refresh workflow

The manual refresh endpoint runs the full MVP pipeline:

1. Fetch active markets from Polymarket
2. Upsert market data into Postgres
3. Analyze only the first `MARKET_SCAN_LIMIT` markets from the latest fetch
4. Generate candidate market pairs using simple heuristics
5. Analyze relations with rule-based logic and batched optional LLM confirmation
6. Score and store active opportunities

The dashboard refresh button calls `POST /admin/refresh`.

## Notes

- The app is conservative by design and does not label every mismatch as arbitrage.
- `hard_arb` is reserved for stronger logical inconsistencies.
- `negative_correlation` only produces `soft_dislocation`, not hard arb.
- The only supported database setup is the Postgres container from `docker compose`.
- No auth, trading, notifications, websockets, or backtesting are included in this MVP.
