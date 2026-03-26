"""
backend/app/routers/jobs.py
SPRINT 4/5 — Polling e SSE per lo stato dei job asincroni.

Endpoints:
    GET  /jobs/{job_id}        → stato corrente (polling ogni 2-3s dal frontend)
    GET  /jobs/{job_id}/stream → SSE stream (opzionale, aggiornamenti push)

Il frontend deve:
    1. Ricevere job_id da POST /features/deep-research o /features/calculate
    2. Fare polling GET /jobs/{job_id} ogni 2-3 secondi
    3. Quando status="completed" → leggere result e renderizzare
    4. Quando status="failed"    → mostrare error

Struttura risposta GET /jobs/{job_id}:
    {
        "job_id":       "uuid",
        "status":       "queued" | "running" | "completed" | "failed",
        "progress":     0-100,
        "current_step": "Analisi mercato locale",
        "step_num":     1,
        "total_steps":  3,
        "result":       {...} | null,   # solo se completed
        "error":        "..." | null,   # solo se failed
        "created_at":   "ISO datetime",
        "started_at":   "ISO datetime" | null,
        "completed_at": "ISO datetime" | null,
    }
"""

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.security import get_current_user
from app.core.job_store import get_job, get_result

logger = logging.getLogger(__name__)

# Esportazione del router (Risolve l'ImportError in main.py)
router = APIRouter(prefix="/jobs", tags=["Jobs"])


# ── GET /jobs/{job_id} — Polling ──────────────────────────────────────────────

@router.get(
    "/{job_id}",
    summary="Stato job asincrono",
    description=(
        "Polling ogni 2-3 secondi. "
        "Quando status='completed' il campo result contiene il risultato completo."
    ),
)
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    job = get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' non trovato o scaduto (TTL 2 ore).",
        )

    # Sicurezza: l'utente può leggere solo i propri job
    if job.get("user_id") != current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Non autorizzato a leggere questo job.",
        )

    # Deserializza il risultato se presente (è salvato come stringa JSON)
    result = None
    if job.get("status") == "completed" and job.get("result"):
        try:
            result = json.loads(job["result"])
        except Exception:
            result = {"raw": job["result"]}

    return {
        "job_id":       job["job_id"],
        "status":       job["status"],
        "progress":     job.get("progress", 0),
        "current_step": job.get("current_step", ""),
        "step_num":     job.get("step_num", 0),
        "total_steps":  job.get("total_steps", 3), # Aggiornato a 3 per la nuova pipeline
        "result":       result,
        "error":        job.get("error"),
        "created_at":   job.get("created_at"),
        "started_at":   job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "feature":      job.get("feature"),
        "plan":         job.get("plan"),
    }


# ── GET /jobs/{job_id}/stream — SSE (opzionale, aggiornamenti push) ───────────

@router.get(
    "/{job_id}/stream",
    summary="SSE stream aggiornamenti job",
    description=(
        "Server-Sent Events: invia aggiornamenti al client senza polling. "
        "Il client si connette una volta e riceve eventi fino a completamento."
    ),
    response_class=StreamingResponse,
)
async def stream_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' non trovato.")
    if job.get("user_id") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Non autorizzato.")

    async def event_generator() -> AsyncGenerator[str, None]:
        """Invia eventi SSE ogni 2 secondi finché il job non è terminato."""
        terminal_states = {"completed", "failed"}
        max_polls = 200      # 200 × 2s = 400s max — oltre il timeout task (600s)
        polls = 0

        while polls < max_polls:
            current_job = get_job(job_id)
            if current_job is None:
                yield _sse_event({"error": "job_not_found"}, event="error")
                break

            # Costruisce payload evento
            result = None
            if current_job.get("status") == "completed" and current_job.get("result"):
                try:
                    result = json.loads(current_job["result"])
                except Exception:
                    result = None

            payload = {
                "job_id":       current_job["job_id"],
                "status":       current_job["status"],
                "progress":     current_job.get("progress", 0),
                "current_step": current_job.get("current_step", ""),
                "step_num":     current_job.get("step_num", 0),
                "total_steps":  current_job.get("total_steps", 3), # Aggiornato a 3
                "result":       result,
                "error":        current_job.get("error"),
            }

            event_type = "progress"
            if current_job["status"] == "completed":
                event_type = "completed"
            elif current_job["status"] == "failed":
                event_type = "failed"

            yield _sse_event(payload, event=event_type)

            if current_job["status"] in terminal_states:
                break

            await asyncio.sleep(2)
            polls += 1

        # Evento di chiusura
        yield _sse_event({"message": "stream_ended"}, event="close")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",    # necessario per Nginx/Render
        },
    )


def _sse_event(data: dict, event: str = "message") -> str:
    """Formatta un evento SSE."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"