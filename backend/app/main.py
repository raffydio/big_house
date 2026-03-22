# backend/app/main.py
# SPRINT 4 — Aggiunto router jobs per il polling dei job asincroni

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, features, billing, storage, users
from app.routers.jobs import router as jobs_router
from app.core.database import init_db
from app.core.storage_manager import ensure_storage_schema, run_full_cleanup

logger = logging.getLogger(__name__)


async def periodic_cleanup():
    while True:
        await asyncio.sleep(24 * 60 * 60)
        try:
            logger.info("Background cleanup avviato")
            run_full_cleanup()
        except Exception as e:
            logger.error(f"Periodic cleanup error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Big House AI — avvio...")
    init_db()
    ensure_storage_schema()
    run_full_cleanup()
    task = asyncio.create_task(periodic_cleanup())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Big House AI — shutdown.")


app = FastAPI(
    title="Big House AI",
    description="Analisi immobiliare con AI — FastAPI + CrewAI + Gemini",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,     tags=["Authentication"])
app.include_router(users.router,    tags=["Users"])
app.include_router(features.router, tags=["AI Features"])
app.include_router(jobs_router,     tags=["Jobs"])          # ← SPRINT 4
app.include_router(billing.router,  tags=["Billing"])
app.include_router(storage.router,  tags=["Storage"])


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "Big House AI"}