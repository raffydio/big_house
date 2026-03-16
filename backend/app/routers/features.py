"""
routers/features.py
CORRETTO:
  1. asyncio.to_thread — CrewAI sincrono non blocca FastAPI
  2. run_compare_roi chiamato con la firma ORIGINALE del service
     (parametri singoli estratti dal payload)
  3. run_deep_research: properties=[] default
"""
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user, check_limit
from app.core.database import increment_usage
from app.services.deep_research_service import run_deep_research
from app.services.calculation_service import run_compare_roi
from app.models import (
    DeepResearchRequest, DeepResearchResponse,
    CompareROIRequest, CompareROIResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/features", tags=["AI Features"])


@router.post(
    "/deep-research",
    response_model=DeepResearchResponse,
    summary="Ricerca opportunità immobiliari sul mercato",
    description="Limiti: FREE 1/g · BASIC 3/g · PRO 10/g · PLUS 20/g",
)
async def deep_research(
    payload: DeepResearchRequest,
    current_user: dict = Depends(get_current_user),
):
    remaining = check_limit(current_user, "deepresearch")
    plan      = current_user.get("plan", "free")

    logger.info(
        f"Deep Research | user={current_user['email']} | "
        f"plan={plan} | query={payload.query[:60]}"
    )

    try:
        result: dict = await asyncio.to_thread(
            run_deep_research,
            query=payload.query,
            properties=[],      # frontend manda solo query
            plan=plan,
            user_id=current_user.get("id"),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Errore Deep Research: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Errore durante la ricerca. Riprova tra qualche secondo."
        )

    increment_usage(current_user["email"], "deepresearch")

    summary = result.get("summary", "")
    market  = result.get("market_overview", "")
    rec     = result.get("investment_recommendation", "")

    return DeepResearchResponse(
        market_context=market or summary,
        opportunities=[],
        best_pick=rec,
        market_trend=market,
        action_plan=rec,
        disclaimer=(
            "I risultati generati dall'AI hanno finalità esclusivamente informativa "
            "e non costituiscono consulenza finanziaria o immobiliare."
        ),
        remaining_usage=remaining,
    )


@router.post(
    "/calculate",
    response_model=CompareROIResponse,
    summary="Confronto ROI fino a 5 immobili",
    description="Limiti: FREE 1/g · BASIC 3/g · PRO 10/g · PLUS 50/g",
)
async def calculate_roi(
    payload: CompareROIRequest,
    current_user: dict = Depends(get_current_user),
):
    remaining = check_limit(current_user, "calcola")
    plan      = current_user.get("plan", "free")

    logger.info(
        f"Calcola ROI | user={current_user['email']} | "
        f"plan={plan} | immobili={len(payload.properties)}"
    )

    # Estrai il primo immobile per i parametri principali del service
    # Il service originale accetta parametri singoli, non il payload intero
    props = payload.properties
    if not props:
        raise HTTPException(status_code=422, detail="Inserire almeno un immobile.")

    first = props[0]
    # Supporta sia dict che oggetti Pydantic
    if hasattr(first, "model_dump"):
        p = first.model_dump()
    elif hasattr(first, "__dict__"):
        p = first.__dict__
    else:
        p = dict(first)

    # Costruisce la location combinando label e address
    location = f"{p.get('label', '')} — {p.get('address', '')}".strip(" —")
    if len(props) > 1:
        other_labels = ", ".join(
            getattr(pr, "label", None) or (dict(pr) if isinstance(pr, dict) else pr.__dict__).get("label", f"Imm.{i+2}")
            for i, pr in enumerate(props[1:])
        )
        location += f" (+ {other_labels})"

    try:
        result: dict = await asyncio.to_thread(
            run_compare_roi,
            # Firma originale del service con parametri singoli
            purchase_price   = float(p.get("purchase_price", 0)),
            size_sqm         = float(p.get("size_sqm", 0)),
            location         = location,
            current_rent     = p.get("current_rent"),
            renovation_budget= p.get("renovation_budget"),
            mortgage_rate    = p.get("mortgage_rate", 3.5),
            mortgage_years   = int(p.get("mortgage_years", 20)),
            down_payment_pct = float(p.get("down_payment_pct") or 0.20) * 100
                               if (p.get("down_payment_pct") or 0) <= 1
                               else float(p.get("down_payment_pct", 20)),
            plan             = plan,
            user_id          = current_user.get("id"),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Errore Calcola ROI: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Errore durante il calcolo. Riprova tra qualche secondo."
        )

    increment_usage(current_user["email"], "calcola")

    return CompareROIResponse(
        results=result.get("results", []),
        winner_label=result.get("winner_label", location),
        winner_reason=result.get("winner_reason", ""),
        comparison_summary=result.get("recommended_scenario", ""),
        market_notes=result.get("market_analysis", ""),
        disclaimer=(
            "I risultati generati dall'AI hanno finalità esclusivamente informativa "
            "e non costituiscono consulenza finanziaria o immobiliare."
        ),
        remaining_usage=remaining,
    )