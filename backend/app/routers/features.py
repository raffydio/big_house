"""
routers/features.py  v2
- POST /features/deep-research  → query libera, agenti cercano opportunità
- POST /features/calculate      → confronto ROI fino a 5 immobili
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
        "4 agenti AI analizzano il mercato e restituiscono 2-4 opportunità concrete. "
        "Limiti: FREE 1/g · PRO 5/g · PLUS 20/g"
    ),
)
async def deep_research(
    payload: DeepResearchRequest,
    current_user: dict = Depends(get_current_user),
):
    remaining = check_limit(current_user, "deepresearch")
    logger.info(f"Deep Research | user={current_user['email']} | query={payload.query[:60]}")

    try:
        result = await run_deep_research(query=payload.query)
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
        "Inserisci 1-5 immobili già trovati. 3 agenti calcolano ROI, payback "
        "e scenario ottimale per ogni immobile e producono una tabella comparativa. "
        "Limiti: FREE 3/g · PRO 20/g · PLUS 100/g"
    ),
)
async def calculate_roi(
    payload: CompareROIRequest,
    current_user: dict = Depends(get_current_user),
):
    remaining = check_limit(current_user, "calcola")
    logger.info(
        f"Calcola ROI | user={current_user['email']} | "
        f"immobili={len(payload.properties)} | goal={payload.goal}"
    )

    try:
        result = await run_compare_roi(data=payload)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Errore Calcola ROI: {e}")
        raise HTTPException(status_code=500, detail="Errore durante il calcolo. Riprova.")

    increment_usage(current_user["email"], "calcola")
    result.remaining_usage = remaining
    return result
