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

        mark_completed(job_id, result)
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

        mark_completed(job_id, result)
        logger.info(f"[task:calcola_roi] DONE — job={job_id}")
        return result

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {str(exc)[:300]}"
        mark_failed(job_id, error_msg)
        logger.error(f"[task:calcola_roi] FAILED — job={job_id}: {error_msg}")
        raise