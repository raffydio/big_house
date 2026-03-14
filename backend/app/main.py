"""
main.py — Big House AI
Entry point. Nessuna business logic — solo configurazione app, middleware e routing.

FIX: billing importato correttamente PRIMA di app = FastAPI(), 
     e include_router chiamato DOPO la definizione di app.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.database import init_db
from app.routers import auth, users, features, storage, billing   # ← TUTTI qui in un unico import

# ─────────────────────────────────────────
# Logging
# ─────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# Lifespan (startup / shutdown)
# ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Avvio {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    init_db()
    logger.info("Database pronto.")
    yield
    logger.info("Shutdown applicazione.")


# ─────────────────────────────────────────
# App  ← DEVE essere definita PRIMA di ogni include_router
# ─────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Piattaforma AI per analisi investimenti immobiliari",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Router ──  ← include_router DOPO app = FastAPI(...)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(features.router)
app.include_router(storage.router)
app.include_router(billing.router)


# ─────────────────────────────────────────
# Health check
# ─────────────────────────────────────────
@app.get("/health", tags=["System"], include_in_schema=False)
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}