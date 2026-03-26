"""
routers/features.py
SPRINT 5 — Dispatch asincrono via Celery + Redis.
Aggiornato per la nuova Pipeline Deterministica (market_analysis_service.py).

Comportamento:
    - Se Redis è disponibile (REDIS_URL configurata):
        POST /features/deep-research → ritorna {job_id, status: "queued"} subito
        Il frontend fa polling su GET /jobs/{job_id}
    - Se Redis NON è disponibile (dev locale senza Redis):
        Fallback automatico: simula il comportamento asincrono restituendo
        un finto job_id e salvando il risultato in memoria, così il frontend
        non crasha.
"""
import asyncio
import logging
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user, check_limit
from app.core.database import increment_usage
from app.core.job_store import create_job, _redis_available, _fallback_store
from app.services.market_analysis_service import run_market_analysis
from app.services.calculation_service import run_compare_roi
from app.models import (
    DeepResearchRequest, DeepResearchResponse,
    CompareROIRequest, CompareROIResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/features", tags=["AI Features"])

GOAL_MAP: dict[str, str] = {
    "Flipping — Vendita post-ristrutturazione": "flipping",
    "flipping":                                 "flipping",
    "Affitto a lungo termine":                  "affitto_lungo",
    "affitto_lungo":                            "affitto_lungo",
    "Affitto breve (Airbnb/Booking)":           "affitto_breve",
    "affitto_breve":                            "affitto_breve",
    "Prima casa con valorizzazione":            "prima_casa",
    "prima_casa":                               "prima_casa",
}


# ── /deep-research ────────────────────────────────────────────────────────────

@router.post(
    "/deep-research",
    summary="Analisi di mercato immobiliare",
    description="Limiti: FREE 1/g · BASIC 3/g · PRO 10/g · PLUS 20/g",
)
async def deep_research(
    payload: DeepResearchRequest,
    current_user: dict = Depends(get_current_user),
):
    remaining = check_limit(current_user, "deepresearch")
    plan      = current_user.get("plan", "free")
    language  = getattr(payload, "language", "it")

    logger.info(
        f"Deep Research | user={current_user['email']} | "
        f"plan={plan} | query={payload.query[:60]}"
    )

    # ── ASYNC: Redis + Celery disponibili ─────────────────────────────────────
    if _redis_available():
        from app.tasks.ai_tasks import run_deep_research_task
        from app.worker import queue_for_plan

        job_id = create_job(
            user_id=current_user.get("id"),
            plan=plan,
            feature="deepresearch",
        )

        run_deep_research_task.apply_async(
            args=[job_id, payload.query, plan, current_user.get("id"), language],
            queue=queue_for_plan(plan),
        )

        increment_usage(current_user["email"], "deepresearch")

        logger.info(
            f"[features] Deep Research queued — job={job_id} "
            f"queue={queue_for_plan(plan)}"
        )
        return {
            "job_id":          job_id,
            "status":          "queued",
            "poll_url":        f"/jobs/{job_id}",
            "remaining_usage": remaining,
        }

    # ── SYNC FALLBACK: Redis non disponibile (dev locale) ────────────────────
    logger.warning(
        "[features] Redis non disponibile — esecuzione sincrona (fallback)"
    )
    try:
        result: dict = await asyncio.to_thread(
            run_market_analysis,
            query=payload.query,
            plan=plan,
            user_id=current_user.get("id"),
            language=language,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Errore Deep Research: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Errore durante la ricerca.")

    increment_usage(current_user["email"], "deepresearch")

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
            "I risultati generati dall'AI hanno finalità esclusivamente informativa "
            "e non costituiscono consulenza finanziaria o immobiliare."
        ),
        "summary":                   summary,
        "market_overview":           market,
        "investment_recommendation": rec,
        "risks_opportunities":       result.get("risks_opportunities", ""),
        "properties_analysis":       result.get("properties_analysis", []),
        "llm_used":                  result.get("llm_used", "gemini"),
    }

    # FIX: Simula il comportamento asincrono per non far crashare il frontend
    fake_job_id = f"sync-fallback-{uuid.uuid4()}"
    _fallback_store[fake_job_id] = {
        "job_id": fake_job_id,
        "user_id": current_user.get("id"),
        "status": "completed",
        "progress": 100,
        "current_step": "Analisi completata",
        "step_num": 3,
        "total_steps": 3,
        "result": json.dumps(mapped_result),
        "error": None
    }

    return {
        "job_id":          fake_job_id,
        "status":          "queued",
        "poll_url":        f"/jobs/{fake_job_id}",
        "remaining_usage": remaining,
    }


# ── /calculate ────────────────────────────────────────────────────────────────

@router.post(
    "/calculate",
    summary="Confronto ROI fino a 5 immobili",
    description="Limiti: FREE 1/g · BASIC 3/g · PRO 10/g · PLUS 50/g",
)
async def calculate_roi(
    payload: CompareROIRequest,
    current_user: dict = Depends(get_current_user),
):
    remaining = check_limit(current_user, "calcola")
    plan      = current_user.get("plan", "free")

    props_raw = payload.properties
    if not props_raw:
        raise HTTPException(status_code=422, detail="Inserire almeno un immobile.")

    def to_dict(p) -> dict:
        if hasattr(p, "model_dump"):
            return p.model_dump()
        if hasattr(p, "__dict__"):
            return {k: v for k, v in p.__dict__.items() if not k.startswith("_")}
        return dict(p)

    properties: list[dict] = [to_dict(p) for p in props_raw]

    normalized: list[dict] = []
    for i, p in enumerate(properties):
        normalized.append({
            "name":              p.get("label") or p.get("name") or f"Immobile {i+1}",
            "address":           p.get("address", ""),
            "price":             float(p.get("purchase_price") or p.get("price") or 0),
            "size_sqm":          float(p.get("size_sqm") or 0),
            "rooms":             p.get("rooms") or p.get("locali"),
            "condition":         p.get("condition") or p.get("condizioni"),
            "floor":             p.get("floor") or p.get("piano"),
            "elevator":          p.get("elevator") or p.get("ascensore"),
            "renovation_budget": float(p["renovation_budget"])
                                 if p.get("renovation_budget") else None,
            "mortgage_rate":     float(p["mortgage_rate"])
                                 if p.get("mortgage_rate") else None,
            "mortgage_years":    int(p.get("mortgage_years") or 20),
            "down_payment_pct":  _normalize_down_payment(p.get("down_payment_pct")),
            "current_rent":      float(p["current_rent"])
                                 if p.get("current_rent") else None,
            "notes":             p.get("notes") or p.get("note", ""),
        })

    raw_goal = (
        getattr(payload, "goal", None)
        or getattr(payload, "investment_goal", None)
        or "affitto_lungo"
    )
    investment_goal = GOAL_MAP.get(raw_goal, "affitto_lungo")
    language        = getattr(payload, "language", "it")

    logger.info(
        f"Calcola ROI | user={current_user['email']} | plan={plan} | "
        f"goal={investment_goal} | lang={language} | immobili={len(normalized)}"
    )

    # ── ASYNC: Redis + Celery disponibili ─────────────────────────────────────
    if _redis_available():
        from app.tasks.ai_tasks import run_calcola_roi_task
        from app.worker import queue_for_plan

        job_id = create_job(
            user_id=current_user.get("id"),
            plan=plan,
            feature="calcola",
        )

        run_calcola_roi_task.apply_async(
            args=[job_id, normalized, investment_goal, plan,
                  current_user.get("id"), language],
            queue=queue_for_plan(plan),
        )

        increment_usage(current_user["email"], "calcola")

        logger.info(
            f"[features] Calcola ROI queued — job={job_id} "
            f"queue={queue_for_plan(plan)}"
        )
        return {
            "job_id":          job_id,
            "status":          "queued",
            "poll_url":        f"/jobs/{job_id}",
            "remaining_usage": remaining,
        }

    # ── SYNC FALLBACK ─────────────────────────────────────────────────────────
    logger.warning(
        "[features] Redis non disponibile — esecuzione sincrona (fallback)"
    )
    try:
        result: dict = await asyncio.to_thread(
            run_compare_roi,
            properties=normalized,
            investment_goal=investment_goal,
            plan=plan,
            user_id=current_user.get("id"),
            language=language,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Errore Calcola ROI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Errore durante il calcolo.")

    increment_usage(current_user["email"], "calcola")

    recommendation = result.get("recommended_scenario", "")
    market         = result.get("market_analysis", "")
    summary        = result.get("summary", "")
    winner_label   = _extract_winner(recommendation, normalized)

    mapped_result = {
        "winner_label":       winner_label,
        "winner_reason":      summary,
        "comparison_summary": recommendation,
        "market_notes":       market,
        "results":            result.get("scenarios", []),
        "disclaimer": (
            "I risultati generati dall'AI hanno finalità esclusivamente "
            "informativa e non costituiscono consulenza finanziaria o immobiliare."
        ),
        "remaining_usage":      None,
        "summary":              summary,
        "market_analysis":      market,
        "financial_analysis":   result.get("financial_analysis", ""),
        "recommended_scenario": recommendation,
        "llm_used":             result.get("llm_used", "gemini"),
    }

    # FIX: Simula il comportamento asincrono per non far crashare il frontend
    fake_job_id = f"sync-fallback-{uuid.uuid4()}"
    _fallback_store[fake_job_id] = {
        "job_id": fake_job_id,
        "user_id": current_user.get("id"),
        "status": "completed",
        "progress": 100,
        "current_step": "Calcolo completato",
        "step_num": 3,
        "total_steps": 3,
        "result": json.dumps(mapped_result),
        "error": None
    }

    return {
        "job_id":          fake_job_id,
        "status":          "queued",
        "poll_url":        f"/jobs/{fake_job_id}",
        "remaining_usage": remaining,
    }


# ── Utility ───────────────────────────────────────────────────────────────────

def _normalize_down_payment(value) -> float:
    if value is None:
        return 20.0
    v = float(value)
    return v * 100 if v <= 1 else v


def _extract_winner(recommendation_text: str, properties: list[dict]) -> str:
    if not recommendation_text or not properties:
        return properties[0].get("name", "Immobile 1") if properties else ""

    text_lower = recommendation_text.lower()
    keywords   = ["consigliato", "migliore", "compra", "primo classificato", "vincitore",
                  "recommended", "best", "buy", "winner"]

    for kw in keywords:
        kw_pos = text_lower.find(kw)
        if kw_pos == -1:
            continue
        window = recommendation_text[max(0, kw_pos - 100): kw_pos + 100]
        for prop in properties:
            name = prop.get("name", "")
            if name and name.lower() in window.lower():
                return name

    return properties[0].get("name", "Immobile 1")