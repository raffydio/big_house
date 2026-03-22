"""
backend/app/core/job_store.py
SPRINT 4 — Gestione stato job in Redis.

Ogni job è un hash Redis con TTL di 2 ore.

Struttura job:
    job_id        str   — UUID v4
    user_id       int
    plan          str   — free | basic | pro | plus
    feature       str   — deepresearch | calcola
    status        str   — queued | running | completed | failed
    progress      int   — 0-100
    current_step  str   — descrizione step corrente (per il frontend)
    step_num      int   — numero step corrente (1-based)
    total_steps   int   — numero totale step
    result        str|None  — JSON del risultato (solo se completed)
    error         str|None  — messaggio errore (solo se failed)
    created_at    str   — ISO datetime
    started_at    str|None
    completed_at  str|None

Fallback: se Redis non è disponibile usa un dict in-memoria (dev locale).
         Il fallback non supporta multi-processo, è solo per sviluppo.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── TTL job in Redis ──────────────────────────────────────────────────────────
JOB_TTL_SECONDS = 7200  # 2 ore

# ── Step labels per feature ───────────────────────────────────────────────────
DEEP_RESEARCH_STEPS = [
    "Analisi mercato locale",        # task 1 — Market Scout
    "Valutazione immobili",          # task 2 — Property Analyst
    "Analisi rischi e opportunità",  # task 3 — Risk Assessor
    "Raccomandazione finale",        # task 4 — Investment Strategist
]

CALCOLA_ROI_STEPS = [
    "Valutazione prezzi di mercato",  # task 1 — Property Valuator
    "Calcolo metriche finanziarie",   # task 2 — Financial Analyst
    "Confronto e raccomandazione",    # task 3 — Comparator
]


# ── Redis client (lazy init) ──────────────────────────────────────────────────

_redis_client = None
_fallback_store: dict = {}   # usato solo se Redis non è disponibile


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis
        client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
        client.ping()                     # verifica connessione
        _redis_client = client
        logger.info(f"[job_store] Redis connesso: {redis_url}")
        return _redis_client
    except Exception as e:
        logger.warning(
            f"[job_store] Redis non disponibile ({e}). "
            f"Uso fallback in-memory (solo per sviluppo locale)."
        )
        return None


def _redis_available() -> bool:
    return _get_redis() is not None


# ── CRUD job ──────────────────────────────────────────────────────────────────

def create_job(
    user_id: int,
    plan: str,
    feature: str,
) -> str:
    """
    Crea un nuovo job e lo salva in Redis (o fallback).
    Restituisce il job_id generato.
    """
    job_id = str(uuid.uuid4())
    total_steps = len(DEEP_RESEARCH_STEPS) if feature == "deepresearch" else len(CALCOLA_ROI_STEPS)

    job = {
        "job_id":       job_id,
        "user_id":      user_id,
        "plan":         plan,
        "feature":      feature,
        "status":       "queued",
        "progress":     0,
        "current_step": "In coda...",
        "step_num":     0,
        "total_steps":  total_steps,
        "result":       None,
        "error":        None,
        "created_at":   datetime.utcnow().isoformat(),
        "started_at":   None,
        "completed_at": None,
    }

    _save_job(job_id, job)
    logger.info(f"[job_store] Job creato: {job_id} | user={user_id} | plan={plan} | feature={feature}")
    return job_id


def get_job(job_id: str) -> Optional[dict]:
    """Restituisce il job o None se non trovato / scaduto."""
    r = _get_redis()
    if r:
        raw = r.get(f"job:{job_id}")
        return json.loads(raw) if raw else None
    else:
        return _fallback_store.get(job_id)


def update_job(job_id: str, **fields) -> None:
    """
    Aggiorna uno o più campi del job.
    Esempi:
        update_job(job_id, status="running", started_at=now)
        update_job(job_id, progress=50, current_step="Valutazione immobili", step_num=2)
        update_job(job_id, status="completed", result=json_str, completed_at=now, progress=100)
        update_job(job_id, status="failed", error="Gemini rate limit", completed_at=now)
    """
    job = get_job(job_id)
    if job is None:
        logger.warning(f"[job_store] update_job: job {job_id} non trovato")
        return

    job.update(fields)
    _save_job(job_id, job)


def mark_running(job_id: str) -> None:
    update_job(
        job_id,
        status="running",
        progress=5,
        current_step="Avvio analisi...",
        started_at=datetime.utcnow().isoformat(),
    )


def mark_step(job_id: str, step_num: int, total_steps: int, step_label: str) -> None:
    """Chiamato dal Celery task dopo ogni task CrewAI completato."""
    # Progresso: da 10% a 90% distribuito sui task
    progress = 10 + int((step_num / total_steps) * 80)
    update_job(
        job_id,
        progress=progress,
        current_step=step_label,
        step_num=step_num,
        total_steps=total_steps,
    )
    logger.info(f"[job_store] {job_id} — step {step_num}/{total_steps}: {step_label} ({progress}%)")


def mark_completed(job_id: str, result: dict) -> None:
    update_job(
        job_id,
        status="completed",
        progress=100,
        current_step="Analisi completata",
        result=json.dumps(result, ensure_ascii=False),
        completed_at=datetime.utcnow().isoformat(),
    )
    logger.info(f"[job_store] {job_id} — COMPLETED")


def mark_failed(job_id: str, error: str) -> None:
    update_job(
        job_id,
        status="failed",
        current_step="Errore durante l'analisi",
        error=error,
        completed_at=datetime.utcnow().isoformat(),
    )
    logger.error(f"[job_store] {job_id} — FAILED: {error}")


def get_result(job_id: str) -> Optional[dict]:
    """Restituisce il risultato deserializzato se il job è completato."""
    job = get_job(job_id)
    if job and job.get("status") == "completed" and job.get("result"):
        try:
            return json.loads(job["result"])
        except Exception:
            return None
    return None


# ── Private ───────────────────────────────────────────────────────────────────

def _save_job(job_id: str, job: dict) -> None:
    r = _get_redis()
    if r:
        r.setex(f"job:{job_id}", JOB_TTL_SECONDS, json.dumps(job, ensure_ascii=False))
    else:
        _fallback_store[job_id] = job