# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Hersheys-Maqgarra**: A FastAPI web application with MongoDB integration and an NFC-e (Nota Fiscal de Consumidor Eletrônica) web scraper utility. The app includes page templates and API endpoints for page rendering.

- **Framework**: FastAPI 0.115.0
- **Database**: MongoDB (async via Motor)
- **Python**: 3.11+
- **Key Dependencies**: Uvicorn, Pydantic, BeautifulSoup4 (for scraping)

## Architecture Overview

```
src/
├── main.py               # FastAPI app factory and middleware setup
├── core/
│   └── config.py        # Settings management (Pydantic BaseSettings)
├── api/
│   └── pages.py         # API routes (GET /pages/)
├── db/
│   └── utils.py         # MongoDB connection helper (async)
├── util/
│   ├── nfce_scrapper/   # NFC-e document scraper (see below)
│   └── translators/     # Data format translators
└── static/
    ├── templates/       # Jinja2 templates
    └── ...
```

### Key Components

**FastAPI App (main.py)**
- Creates app with CORS middleware (all origins allowed)
- Includes session middleware
- Routes requests to registered routers
- Mounts static files at `/src/static`

**Settings (core/config.py)**
- Uses Pydantic BaseSettings with .env file support
- Required vars: `MONGO_URI`, `OPENAI_API_KEY`, `OPENAI_MODEL`
- Optional vars: `ENV`, `HOST`, `PORT`, `MONGO_DB`, `MONGO_DEBUG`

**Database (db/utils.py)**
- Lazy-initializes single `AsyncIOMotorClient` connection
- Returns async MongoDB database instance via `get_db()`
- Connection is reused across requests

**NFC-e Scraper (util/nfce_scrapper/)**
- Independent utility for parsing SEFAZ SP (São Paulo tax authority) NFC-e public consultation pages
- Core classes:
  - `NfceScrapper`: Main orchestrator (URL validation, HTML fetch, JSON persistence)
  - `NfceParser`: HTML extraction using BeautifulSoup with multi-layered fallbacks
  - `NfceData` & related models: Pydantic models for type safety
- Extracts: seller, buyer, items, payments, totals, metadata, status flags
- URL format: `https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/...?p=<44-digit-key>|segments...`
- All errors caught gracefully; `scrape()` returns `(data_dict, "OK")` or `({}, error_msg)`

**Data Translators (util/translators/)**
- Format converters for NFC-e data between different API schemas
- `NfceToWebmaniaTranslator`: Converts NFC-e scraper output to Webmania API format
  - Handles field mapping with type conversions (e.g., `series` to int, UUIDs generation)
  - Conditional fields (e.g., `consumidor` omitted if buyer has no CPF/CNPJ)
  - Parses address strings with smart fallback handling
  - CLI interface: `python src/util/translators/nfce_to_webmania.py <json_file>`

## Setup & Running

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Environment Setup
Copy `.env.example` to `.env` and fill in required values:
```bash
cp .env.example .env
# Edit .env with MONGO_URI, OPENAI_API_KEY, OPENAI_MODEL
```

### Run Locally
```bash
# Via Uvicorn directly (auto-reload)
PYTHONPATH=src uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using Python module
PYTHONPATH=src python -m uvicorn main:app --reload
```

### Run via Docker
```bash
docker-compose up --build
```
The PYTHONPATH environment variable is set to `/app/src` in the container.

**Note**: The `docker-compose.yml` references `build: .`, which requires a Dockerfile in the project root. If building Docker images, ensure a Dockerfile exists (or provide one).

### Run Tests

**Pytest Suite (recommended)**
Comprehensive test suite with 54 tests covering NfceScrapper and NfceToWebmaniaTranslator:
```bash
# Install test dependencies
pip install pytest pytest-mock responses

# Run all tests
PYTHONPATH=src pytest tests/ -v

# Run specific test file
PYTHONPATH=src pytest tests/test_scrapper.py -v
PYTHONPATH=src pytest tests/test_translator.py -v

# Run single test class or function
PYTHONPATH=src pytest tests/test_scrapper.py::TestNfceScrapperUrlValidation -v
```

**Manual Testing**
For manual scraper testing:
```bash
# Run legacy smoke test
PYTHONPATH=src python src/util/test_nfce_scrapper.py

# Test with your own NFC-e URL
PYTHONPATH=src python -c "
from util.nfce_scrapper import NfceScrapper
scraper = NfceScrapper(output_dir='output/nfce')
data, status = scraper.scrape('<your_nfce_url>')
print(f'Status: {status}')
print(f'Seller: {data.get(\"seller\", {}).get(\"name\")}')"
```

## Test Suite

The project includes a comprehensive pytest-based test suite with 54 tests organized into two main modules:

### Test Structure
```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── test_scrapper.py               # 21 tests for NfceScrapper class
├── test_translator.py             # 33 tests for NfceToWebmaniaTranslator class
└── fixtures/
    ├── valid_nfce.html            # Sample SEFAZ HTML for parsing tests
    └── valid_nfce.json            # Expected scraper output for comparison
```

### NfceScrapper Tests (21 tests)
- **URL Validation** (6 tests): Missing scheme/host, missing `p=` param, single segment, non-44-digit first segment
- **HTTP Error Handling** (4 tests): HTTP 404/500, connection errors, timeouts (all mocked with `responses` library)
- **Successful Scraping** (9 tests): Valid HTML parsing, seller/items extraction, numeric field validation, file I/O, totals verification
- **Status Flags** (2 tests): Cancelled and denied invoice handling

### NfceToWebmaniaTranslator Tests (33 tests)
- **Status Conversion** (4 tests): Cancelled, denied, approved status with precedence rules
- **Address Parsing** (3 tests): Full 6-part addresses, partial addresses, empty addresses
- **Buyer Field Building** (5 tests): CPF-only, CNPJ-only, both, none, missing both
- **Unit Parsing** (4 tests): With/without "UN: " prefix, empty values, None handling
- **Products** (4 tests): Items with/without codes, 1-indexed numbering, empty lists
- **Schema Translation** (6 tests): Dict input, UUID validation, serie as int, required fields, field preservation
- **File Loading** (4 tests): Path objects, string paths, equivalence with dict input, FileNotFoundError
- **Payment Building** (3 tests): Single/multiple payments, empty payment lists

### Key Testing Features
- **No Network Calls**: All scraper tests use `responses` mock library for HTTP requests
- **Offline Testing**: Translator tests use pure dict inputs, no filesystem I/O
- **Fixture-Based**: Real SEFAZ HTML structure with corresponding expected JSON output
- **Fast Execution**: All 54 tests run in <1 second
- **Mocked Sessions**: `pytest-mock` for clean HTTP mocking

### Running the Tests
```bash
# All tests with verbose output
PYTHONPATH=src pytest tests/ -v

# Quiet mode (progress bar only)
PYTHONPATH=src pytest tests/ -q

# With coverage
PYTHONPATH=src pytest tests/ --cov=src/util --cov-report=term-missing

# Stop on first failure
PYTHONPATH=src pytest tests/ -x

# Show print statements (no capture)
PYTHONPATH=src pytest tests/ -s
```

### Test Dependencies
Added to `requirements.txt`:
- `pytest==7.4.4` — Testing framework
- `pytest-mock==3.12.0` — Mocking plugin
- `responses==0.24.1` — HTTP request mocking

## Common Development Tasks

### Add API Route
1. Create handler in `src/api/` (e.g., `src/api/nfce.py`)
2. Include router in `main.py`: `app.include_router(router_nfce, prefix="/nfce")`
3. Use `get_db()` for database access if needed

### Enhance NFC-e Scraper
- Parsing logic: `src/util/nfce_scrapper/parser.py` (multi-layered field extraction)
- Data models: `src/util/nfce_scrapper/models.py` (update for new fields)
- Custom exceptions: `src/util/nfce_scrapper/exceptions.py`
- Always return gracefully from `scrape()` (never raise to caller)

### Add Data Format Translator
1. Create new translator in `src/util/translators/` (e.g., `nfce_to_custom_format.py`)
2. Implement a class with a `translate(source)` method
3. Support loading from dict, file path (str or Path), or JSON string
4. Update `src/util/translators/__init__.py` to export the new class
5. Add CLI interface with `if __name__ == "__main__":` block for testing

### Database Operations
- Async operations only; use `await get_db()` to get database instance
- Motor provides AsyncIOMotorClient with pymongo-compatible API

### Async/Await Best Practices
- All database operations must use `await` since Motor is async
- Never mix sync and async code in route handlers
- Define all request handlers as `async def`
- Example route:
```python
@router.get("/invoke")
async def invoke_endpoint():
    db = await get_db()
    result = await db.collection.find_one()
    return result
```

### Import Patterns
When `PYTHONPATH=src`, imports are relative to the `src/` directory:
```python
# API routes
from api.pages import router

# Database
from db.utils import get_db

# NFC-e Scraper (commonly used)
from util.nfce_scrapper import NfceScrapper
from util.nfce_scrapper.models import NfceData, NfceSellerModel
from util.nfce_scrapper.exceptions import NfceInvalidUrlError

# Data Translators
from util.translators import NfceToWebmaniaTranslator
```

## Key Development Notes

**Path Context**
- When running via Uvicorn, set `PYTHONPATH=src` so imports work (e.g., `from api.pages import ...`)
- Docker already sets this correctly

**CORS**
- Currently allows all origins, methods, headers (development-friendly, but update for production)

**NFC-e Scraper Status**
- Core functionality implemented and working
- Multi-layered fallback parsing is resilient to HTML layout variations
- Enhanced parsing for items, metadata, and URL validation
- Saves JSON output with access_key or timestamp as filename
- Error handling is graceful (no exceptions raised to caller)

**Data Format Translation**
- `NfceToWebmaniaTranslator` converts scraper output to Webmania API schema
- Supports dict, file paths, or Path objects as input sources
- All numeric fields passed through as strings (dot decimal, e.g., `"48.00"`)
- CLI interface available: `PYTHONPATH=src python src/util/translators/nfce_to_webmania.py <file.json>`
- Tested with all sample NFC-e files in `src/util/nfce_scrapper/output/nfce/`

**Dependencies to Know**
- **FastAPI**: Web framework with auto-generated OpenAPI docs at `/docs`
- **Motor**: Async MongoDB driver (requires MongoDB running)
- **BeautifulSoup4 + lxml**: HTML parsing for scraper (lxml is more robust than default parser)
- **Pydantic**: Data validation and settings management
- **Uvicorn**: ASGI server

**Test Dependencies**
- **pytest**: Testing framework
- **pytest-mock**: Mocking plugin for pytest
- **responses**: HTTP request mocking library (no real network calls in tests)

## Troubleshooting

### ModuleNotFoundError / Import Issues
**Problem**: `ModuleNotFoundError: No module named 'api'` or similar
- Ensure `PYTHONPATH=src` is set when running commands
- Verify you're running from the project root directory
- Check import statements don't use absolute paths (should be relative to src/)

### MongoDB Connection Issues
**Problem**: Connection timeout or "not connected" errors
- Verify MongoDB is running (locally, Docker, or Atlas)
- Check `MONGO_URI` in `.env` is correct and accessible
- Confirm `MONGO_DB` is set in `.env` (defaults to 'hersheys_maqgarra' if unset)
- Test with: `PYTHONPATH=src python -c "from db.utils import get_db"`

### NFC-e Scraper Returns Empty Data
**Problem**: `scrape()` returns `({}, error_msg)` or missing fields
- Verify the NFC-e URL format: must contain 44-digit access key after `p=` parameter
- Check the SEFAZ SP website hasn't changed HTML structure
- Test with a known valid URL first
- Review returned error message for specifics (URL invalid, network error, parse error, etc.)

### Async/Await Errors
**Problem**: `RuntimeError: no running event loop` or `TypeError: object coroutine was never awaited`
- Ensure all database calls use `await` (e.g., `await get_db()`)
- All route handlers must be defined as `async def`, not `def`
- Don't call async functions without `await` in synchronous contexts

## See Also
- Project memory contains implementation phases and detailed scraper design
- OpenAI integration is configured but not yet used in routes
