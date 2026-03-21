# hersheys-maqgarra-fastapi

Backend for **Hershey's Máquina de Garra CAPIBARRA** — a promotional campaign where users scan purchase receipts (NFC-e) to earn plays on a claw machine game.

## What it does

- Validates receipts via QR code (NFC-e scraping) or camera image (OpenAI vision)
- Counts matching Hershey's products (chocolate bars) on each receipt
- Manages a game turn queue (join, next, play, skip, complete)
- Tracks participation through NFC/QR physical tags linked to sessions
- Prevents duplicate receipt submissions

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.135 |
| Database | MongoDB (async Motor) |
| Cache | Redis |
| Image parsing | OpenAI Vision |
| NFC-e scraping | BeautifulSoup4 + lxml (SEFAZ SP) |
| NFe emission | WebmaniaNFe API |
| Observability | structlog + LogCenter SDK + Sentry (optional) |
| Runtime | Python 3.11, Uvicorn |

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in `.env` — required variables:

```env
BASE_URL=              # Base URL for SMS links
MONGO_URI=             # MongoDB connection string
REDIS_URL=             # Redis connection string
JWT_SECRET=            # JWT signing secret
OPENAI_API_KEY=
OPENAI_MODEL=
API_KEY_HEADER=x-api-key
DEVICE_ID_HEADER=x-device-id
```

Optional: `SENTRY_DSN`, `LOG_API`, `LOG_API_KEY`, `LOG_PROJECT_ID`, `SMS_API_URL`, `SMS_API_KEY`, `NF_API_KEY`, `NF_BASE_API`.

### 3. Seed API keys

```bash
PYTHONPATH=src python src/scripts/seed_api_keys.py
```

## Running

**Local (auto-reload):**

```bash
PYTHONPATH=src uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Docker:**

```bash
docker-compose up --build
```

API docs available at `http://localhost:8000/docs`.

## Tests

```bash
# All tests
PYTHONPATH=src pytest tests/ -v

# Single file
PYTHONPATH=src pytest tests/test_scrapper.py -v

# With coverage
PYTHONPATH=src pytest tests/ --cov=src/util --cov-report=term-missing
```

## Project structure

```
src/
├── main.py               # App factory, middleware, routers
├── core/                 # Config, exceptions, Redis client
├── api/
│   ├── dependencies.py   # Dependency injection wiring
│   └── routes/           # receipts, tags, queue, sessions, products, health
├── services/             # Business logic (receipt validation, queue, tags, sessions...)
├── repositories/         # MongoDB data access
├── schemas/              # Pydantic request/response models
├── db/utils.py           # MongoDB connection helper
├── util/
│   ├── nfce_scrapper/    # SEFAZ SP NFC-e scraper
│   └── translators/      # NfceToWebmaniaTranslator
└── static/
    ├── templates/        # Frontend HTML pages (Vanilla JS)
    └── assets/           # CSS / JS / images
```
