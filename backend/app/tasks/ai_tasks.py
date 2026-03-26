"""
backend/app/tasks/ai_tasks.py
SPRINT 4 — Celery tasks per le due feature AI.

AGGIORNAMENTO Sprint 5:
  - run_deep_research_task ora chiama run_market_analysis() (pipeline deterministica)
    invece di run_deep_research() (4 agenti CrewAI). Il nome del task Celery
    rimane "tasks.deep_research" per backward compatibility.
  - Progress callback: non piu BasedOn CrewAI task callback, ma step-based
    con firma (step_num, total_steps, label).
  - run_calcola_roi_task: invariato, CrewAI mantenuto per i dati strutturati.
"""

import logging
from typing import Optional

from app.worker import celery_app
from app.core.job_store import (
    mark_running, mark_step, mark_completed, mark_failed,
    DEEP_RESEARCH_STEPS, CALCOLA_ROI_STEPS,
)

logger = logging.getLogger(__name__)


# ── Task: Analisi di Mercato (pipeline deterministica) ────────────────────────

@celery_app.task(
    name="tasks.deep_research",
    bind=True,
    max_retries=0,
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
    Esegue l'Analisi di Mercato in background con pipeline deterministica.

    Pipeline 3-step (30-60s totali):
      Step 1: keyword extraction - pianifica le ricerche
      Step 2: ricerche parallele - dati reali dal web (Google Search grounding)
      Step 3: synthesis LLM - report strutturato

    I dati sono REALI e AGGIORNATI (Google Search grounding in Step 2).
    """
    logger.info(f"[task:deep_research] START -- job={job_id} user={user_id} plan={plan}")

    try:
        mark_running(job_id)

        from app.services.market_analysis_service import run_market_analysis

        def on_step(step_num: int, total_steps: int, label: str) -> None:
            mark_step(job_id, step_num, total_steps, label)

        result = run_market_analysis(
            query=query,
            plan=plan,
            user_id=user_id,
            language=language,
            progress_callback=on_step,
        )

        summary = result.get("summary", "")
        market  = result.get("market_overview", "")
        rec     = result.get("investment_recommendation", "")

        mapped_result = {
            "market_context":           market or summary,
            "best_pick":                rec,
            "market_trend":             market,
            "action_plan":              rec,
            "opportunities":            [],
            "disclaimer": (
                "I risultati generati dall'AI hanno finalita esclusivamente "
                "informativa e non costituiscono consulenza finanziaria o immobiliare."
            ),
            "summary":                   summary,
            "market_overview":           market,
            "investment_recommendation": rec,
            "risks_opportunities":       result.get("risks_opportunities", ""),
            "properties_analysis":       result.get("properties_analysis", []),
            "llm_used":                  result.get("llm_used", "gemini"),
            "pipeline":                  result.get("pipeline", "deterministic_v1"),
        }

        mark_completed(job_id, mapped_result)
        logger.info(f"[task:deep_research] DONE -- job={job_id}")
        return result

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {str(exc)[:300]}"
        mark_failed(job_id, error_msg)
        logger.error(f"[task:deep_research] FAILED -- job={job_id}: {error_msg}")
        raise


# ── Task: Calcola ROI (CrewAI mantenuto) ──────────────────────────────────────

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
    logger.info(
        f"[task:calcola_roi] START -- job={job_id} user={user_id} plan={plan} "
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

        recommendation = result.get("recommended_scenario", "")
        market         = result.get("market_analysis", "")
        summary        = result.get("summary", "")
        winner_label   = _extract_winner_from_text(recommendation, properties)

        mapped_result = {
            "winner_label":       winner_label,
            "winner_reason":      summary,
            "comparison_summary": recommendation,
            "market_notes":       market,
            "results":            result.get("scenarios", []),
            "disclaimer": (
                "I risultati generati dall'AI hanno finalita esclusivamente "
                "informativa e non costituiscono consulenza finanziaria o immobiliare."
            ),
            "remaining_usage":      None,
            "summary":              summary,
            "market_analysis":      market,
            "financial_analysis":   result.get("financial_analysis", ""),
            "recommended_scenario": recommendation,
            "llm_used":             result.get("llm_used", "gemini"),
        }

        mark_completed(job_id, mapped_result)
        logger.info(f"[task:calcola_roi] DONE -- job={job_id}")
        return result

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {str(exc)[:300]}"
        mark_failed(job_id, error_msg)
        logger.error(f"[task:calcola_roi] FAILED -- job={job_id}: {error_msg}")
        raise


# ── Helper ────────────────────────────────────────────────────────────────────

def _extract_winner_from_text(recommendation_text: str, properties: list) -> str:
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

    return properties[0].get("name", "Immobile 1")