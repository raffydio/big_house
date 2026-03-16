"""
routers/features.py
- POST /features/deep-research
- POST /features/calculate

AGGIORNAMENTO: passa current_user["plan"] a run_deep_research e run_compare_roi
in modo che ogni piano usi il modello Gemini appropriato.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status

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
    description=(
        "L'utente descrive cosa cerca in linguaggio naturale. "
        "4 agenti AI analizzano il mercato e restituiscono 2-4 opportunità concrete.\n\n"
        "**Modello AI per piano:**\n"
        "- FREE: Gemini 2.5 Flash-Lite\n"
        "- BASIC: Gemini 2.5 Flash\n"
        "- PRO/PLUS: Gemini 2.5 Pro\n\n"
        "Limiti: FREE 1/g · BASIC 3/g · PRO 10/g · PLUS 20/g"
    ),
)
async def deep_research(
    payload: DeepResearchRequest,
    current_user: dict = Depends(get_current_user),
):
    remaining = check_limit(current_user, "deepresearch")
    plan = current_user.get("plan", "free")

    logger.info(
        f"Deep Research | user={current_user['email']} | "
        f"plan={plan} | query={payload.query[:60]}"
    )

    try:
        result = await run_deep_research(
            query=payload.query,
            plan=plan,              # ← nuovo parametro
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Errore Deep Research: {e}")
        raise HTTPException(status_code=500, detail="Errore durante la ricerca. Riprova.")

    increment_usage(current_user["email"], "deepresearch")
    result.remaining_usage = remaining
    return result


@router.post(
    "/calculate",
    response_model=CompareROIResponse,
    summary="Confronto ROI fino a 5 immobili",
    description=(
        "Inserisci 1-5 immobili già trovati. 3 agenti calcolano ROI e payback.\n\n"
        "**Modello AI per piano:**\n"
        "- FREE: Gemini 2.5 Flash-Lite\n"
        "- BASIC: Gemini 2.5 Flash\n"
        "- PRO/PLUS: Gemini 2.5 Pro\n\n"
        "Limiti: FREE 1/g · BASIC 3/g · PRO 10/g · PLUS 50/g"
    ),
)
async def calculate_roi(
    payload: CompareROIRequest,
    current_user: dict = Depends(get_current_user),
):
    remaining = check_limit(current_user, "calcola")
    plan = current_user.get("plan", "free")

    logger.info(
        f"Calcola ROI | user={current_user['email']} | "
        f"plan={plan} | immobili={len(payload.properties)} | goal={payload.goal}"
    )

    try:
        result = await run_compare_roi(
            data=payload,
            plan=plan,              # ← nuovo parametro
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Errore Calcola ROI: {e}")
        raise HTTPException(status_code=500, detail="Errore durante il calcolo. Riprova.")

    increment_usage(current_user["email"], "calcola")
    result.remaining_usage = remaining
    return result