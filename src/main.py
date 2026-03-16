from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

import logging
import structlog
from logcenter_sdk.config import LogCenterConfig
from logcenter_sdk.sender import LogCenterSender
from logcenter_sdk.middleware import LogCenterAuditMiddleware

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import settings
from api.routes.health import router as health_router
from api.routes.receipts import router as receipts_router
from api.routes.tags import router as tags_router
from api.pages import router as pages_router


logging.basicConfig(level=logging.INFO, format="%(message)s")

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

log = structlog.get_logger(__name__)

cfg = LogCenterConfig(
    base_url=settings.LOG_API.rstrip("/"),
    project_id=settings.LOG_PROJECT_ID,
    api_key=settings.LOG_API_KEY,
    enabled=True,
)

sender = LogCenterSender(cfg)

try:
    import sentry_sdk
    from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
    SENTRY_AVAILABLE = True
except Exception:
    SENTRY_AVAILABLE = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.log_sender = sender

    # === STARTUP ===
    async def _delayed_startup_log():
        await asyncio.sleep(0.3)
        await sender.send(
            level="INFO",
            message="Hershey's Capibarra startup",
            status="OK",
            tags=["startup"],
            data={"env": settings.ENV, "version": "0.1.0-dev"},
            spool_on_fail=False,
        )

    asyncio.create_task(_delayed_startup_log())

    yield

    # === SHUTDOWN ===
    try:
        await sender.send(
            level="INFO",
            message="Hershey's Capibarra shutdown",
            status="OK",
            tags=["shutdown"],
            data={"env": settings.ENV, "version": "0.1.0-dev"},
            spool_on_fail=False
        )
    finally:
        await sender.stop_background_flush()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = os.path.join(BASE_DIR, "static")

def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="0.1.0-dev", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(LogCenterAuditMiddleware, sender=sender)

    if settings.SENTRY_DSN and SENTRY_AVAILABLE:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.2)
        app.add_middleware(SentryAsgiMiddleware)

    app.mount("/src/static", StaticFiles(directory="src/static"), name="src-static")

    app.include_router(health_router)
    app.include_router(receipts_router)
    app.include_router(tags_router)
    app.include_router(pages_router)

    return app


app = create_app()
