# backend/app/main.py
# AGGIORNATO: integra storage_manager per cleanup automatico
#   - All'avvio: ensure_storage_schema() + run_full_cleanup()
#   - Ogni 24h: background task AsyncIO

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, features, billing
from app.core.storage_manager import ensure_storage_schema, run_full_cleanup

logger = logging.getLogger(__name__)

# ── Background cleanup task ───────────────────────────────────────────────────
async def periodic_cleanup():
    """Cleanup ogni 24 ore. Gira in background per tutta la vita del processo."""
    while True:
        await asyncio.sleep(24 * 60 * 60)   # aspetta 24h
        try:
            logger.info("Background cleanup avviato")
            run_full_cleanup()
        except Exception as e:
            logger.error(f"Periodic cleanup error: {e}")

# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    logger.info("Big House AI avvio...")
    ensure_storage_schema()       # crea tabelle se non esistono
    run_full_cleanup()            # cleanup iniziale (scaduti, orfani, cache)

    # Avvia il task periodico
    task = asyncio.create_task(periodic_cleanup())

    yield

    # SHUTDOWN
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Big House AI shutdown.")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Big House AI",
    description="Analisi immobiliare con AI",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # restringere in produzione al dominio Cloudflare
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,     prefix="/auth",     tags=["auth"])
app.include_router(features.router, prefix="/features", tags=["features"])
app.include_router(billing.router,  prefix="/billing",  tags=["billing"])

@app.get("/health")
def health():
    return {"status": "ok"}