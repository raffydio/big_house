# backend/app/main.py
# CORRETTO: aggiunti router users e storage (mancavano → 404 su /users/me e /storage/*)

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, features, billing, storage, users
from app.core.database import init_db
from app.core.storage_manager import ensure_storage_schema, run_full_cleanup

logger = logging.getLogger(__name__)


# ── Background cleanup task ───────────────────────────────────────────────────
async def periodic_cleanup():
    """Cleanup ogni 24 ore. Gira in background per tutta la vita del processo."""
    while True:
        await asyncio.sleep(24 * 60 * 60)
        try:
            logger.info("Background cleanup avviato")
            run_full_cleanup()
        except Exception as e:
            logger.error(f"Periodic cleanup error: {e}")


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    logger.info("Big House AI — avvio...")

    # Inizializza DB principale (tabella users, chat_sessions, ecc.)
    init_db()

    # Crea tabelle storage se non esistono (sessions, stored_files, user_storage)
    ensure_storage_schema()

    # Cleanup iniziale: sessioni scadute, file orfani, cache ricerche
    run_full_cleanup()

    # Avvia task periodico ogni 24h
    task = asyncio.create_task(periodic_cleanup())

    yield

    # SHUTDOWN
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Big House AI — shutdown.")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Big House AI",
    description="Analisi immobiliare con AI — FastAPI + CrewAI + Gemini",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # restringere in produzione al dominio Cloudflare Pages
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Router ────────────────────────────────────────────────────────────────────
app.include_router(auth.router,     tags=["Authentication"])   # prefisso /auth definito nel router
app.include_router(users.router,    tags=["Users"])             # /users/me, /users/me/limits
app.include_router(features.router, tags=["AI Features"])       # /features/deep-research, /features/calculate
app.include_router(billing.router,  tags=["Billing"])           # /billing/create-checkout-session, /billing/webhook
app.include_router(storage.router,  tags=["Storage"])           # /storage/info, /storage/sessions


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "Big House AI"}