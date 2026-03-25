"""
backend/app/tasks/ai_tasks.py
SPRINT 4 — Celery tasks per le due feature AI.

Ogni task:
  1. Aggiorna lo stato del job in Redis (running → step N → completed/failed)
  2. Chiama il service corrispondente con un progress_callback
  3. Il progress_callback viene passato ai Task CrewAI come `callback`
     così dopo ogni task dell'agente viene aggiornato il progresso in Redis

Dispatch dal router (features.py):
    from app.tasks.ai_tasks import run_deep_research_task
    run_deep_research_task.apply_async(
        args=[job_id, query, plan, user_id, language],
        queue=queue_for_plan(plan),
    )
"""

import json
import logging
from datetime import datetime
from typing import Optional

from app.worker import celery_app
from app.core.job_store import (
    mark_running, mark_step, mark_completed, mark_failed,
    DEEP_RESEARCH_STEPS, CALCOLA_ROI_STEPS,
)

logger = logging.getLogger(__name__)


# ── Task: Analisi di Mercato (Deep Research) ──────────────────────────────────

@celery_app.task(
    name="tasks.deep_research",
    bind=True,
    max_retries=0,           # nessun retry automatico — fail esplicito
    acks_late=True,
)
def run_deep_research_task(
    self,
    job_id: str,
    query: str,
    plan: str,
    user_id: Optional[int],
    language: str = "it",
) -> dict:
    """
    Esegue la Deep Research in background.
    Aggiorna il job in Redis ad ogni step del crew CrewAI.
    """
    logger.info(f"[task:deep_research] START — job={job_id} user={user_id} plan={plan}")

    try:
        mark_running(job_id)

        from app.services.deep_research_service import run_deep_research

        # Contatore step (closure)
        step_counter = {"n": 0}

        def on_task_done(task_output) -> None:
            """Chiamato da CrewAI dopo ogni Task completato."""
            step_counter["n"] += 1
            n = step_counter["n"]
            total = len(DEEP_RESEARCH_STEPS)
            label = DEEP_RESEARCH_STEPS[n - 1] if n <= total else "Step completato"
            mark_step(job_id, n, total, label)

        result = run_deep_research(
            query=query,
            properties=[],
            plan=plan,
            user_id=user_id,
            language=language,
            task_callback=on_task_done,
        )

        # ── Mappa i campi del service ai campi attesi dal frontend ────────────
        # Il router nel flusso sincrono fa questa mappatura in features.py.
        # Nel flusso asincrono il task deve farla prima di salvare in Redis.
        summary = result.get("summary", "")
        market  = result.get("market_overview", "")
        rec     = result.get("investment_recommendation", "")

        mapped_result = {
            # Campi che il frontend legge (struttura DeepResearchResponse)
            "market_context":           market or summary,
            "best_pick":                rec,
            "market_trend":             market,
            "action_plan":              rec,
            "opportunities":            [],
            "disclaimer": (
                "I risultati generati dall'AI hanno finalità esclusivamente "
                "informativa e non costituiscono consulenza finanziaria o immobiliare."
            ),
            # Campi raw completi (per eventuale uso futuro)
            "summary":                   summary,
            "market_overview":           market,
            "investment_recommendation": rec,
            "risks_opportunities":       result.get("risks_opportunities", ""),
            "properties_analysis":       result.get("properties_analysis", []),
            "llm_used":                  result.get("llm_used", "gemini"),
        }

        mark_completed(job_id, mapped_result)
        logger.info(f"[task:deep_research] DONE — job={job_id}")
        return result

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {str(exc)[:300]}"
        mark_failed(job_id, error_msg)
        logger.error(f"[task:deep_research] FAILED — job={job_id}: {error_msg}")
        raise


# ── Task: Calcola ROI ─────────────────────────────────────────────────────────

@celery_app.task(
    name="tasks.calcola_roi",
    bind=True,
    max_retries=0,
    acks_late=True,
)
def run_calcola_roi_task(
    self,
    job_id: str,
    properties: list,
    investment_goal: str,
    plan: str,
    user_id: Optional[int],
    language: str = "it",
) -> dict:
    """
    Esegue il Calcola ROI in background.
    Aggiorna il job in Redis ad ogni step del crew CrewAI.
    """
    logger.info(
        f"[task:calcola_roi] START — job={job_id} user={user_id} plan={plan} "
        f"goal={investment_goal} n_props={len(properties)}"
    )

    try:
        mark_running(job_id)

        from app.services.calculation_service import run_compare_roi

        step_counter = {"n": 0}

        def on_task_done(task_output) -> None:
            step_counter["n"] += 1
            n = step_counter["n"]
            total = len(CALCOLA_ROI_STEPS)
            label = CALCOLA_ROI_STEPS[n - 1] if n <= total else "Step completato"
            mark_step(job_id, n, total, label)

        result = run_compare_roi(
            properties=properties,
            investment_goal=investment_goal,
            plan=plan,
            user_id=user_id,
            language=language,
            task_callback=on_task_done,
        )

        # ── Mappa i campi del service ai campi attesi dal frontend ────────────
        # Stessa logica del router sincrono in features.py → _extract_winner
        recommendation = result.get("recommended_scenario", "")
        market         = result.get("market_analysis", "")
        summary        = result.get("summary", "")

        # Estrai il nome del vincitore dal testo della raccomandazione
        winner_label = _extract_winner_from_text(recommendation, properties)

        mapped_result = {
            # Campi che il frontend legge (struttura CompareROIResponse)
            "winner_label":       winner_label,
            "winner_reason":      summary,
            "comparison_summary": recommendation,
            "market_notes":       market,
            "results":            result.get("scenarios", []),
            "disclaimer": (
                "I risultati generati dall'AI hanno finalità esclusivamente "
                "informativa e non costituiscono consulenza finanziaria o immobiliare."
            ),
            "remaining_usage": None,
            # Campi raw completi
            "summary":              summary,
            "market_analysis":      market,
            "financial_analysis":   result.get("financial_analysis", ""),
            "recommended_scenario": recommendation,
            "llm_used":             result.get("llm_used", "gemini"),
        }

        mark_completed(job_id, mapped_result)
        logger.info(f"[task:calcola_roi] DONE — job={job_id}")
        return result

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {str(exc)[:300]}"
        mark_failed(job_id, error_msg)
        logger.error(f"[task:calcola_roi] FAILED — job={job_id}: {error_msg}")
        raise

# ── Helper ────────────────────────────────────────────────────────────────────

def _extract_winner_from_text(recommendation_text: str, properties: list) -> str:
    """
    Estrae il nome dell'immobile vincitore dal testo della raccomandazione.
    Replica la logica di _extract_winner() in features.py per il flusso asincrono.
    """
    if not recommendation_text or not properties:
        return properties[0].get("name", "Immobile 1") if properties else "Immobile 1"

    text_lower = recommendation_text.lower()
    keywords = [
        "consigliato", "migliore", "compra", "primo classificato",
        "vincitore", "recommended", "best", "buy", "winner", "rank 1",
    ]

    for kw in keywords:
        pos = text_lower.find(kw)
        if pos == -1:
            continue
        window = recommendation_text[max(0, pos - 100): pos + 150]
        for prop in properties:
            name = prop.get("name", "")
            if name and name.lower() in window.lower():
                return name

    # Fallback: restituisce il primo immobile
    return properties[0].get("name", "Immobile 1")