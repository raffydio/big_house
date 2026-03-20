"""
routers/features.py
SPRINT 3 — Aggiornato calculate_roi per la nuova firma run_compare_roi:
  - Passa l'intera lista properties invece del singolo immobile
  - Passa investment_goal invece dei parametri singoli
  - GOAL_MAP converte la label UI nel codice interno
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

# Mappa le label UI (quelle che il frontend manda) ai codici interni del service
GOAL_MAP: dict[str, str] = {
    # Valori esatti che il frontend manda (vedi pulsanti UI)
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
    response_model=DeepResearchResponse,
    summary="Analisi di mercato immobiliare",
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
            properties=[],
            plan=plan,
            user_id=current_user.get("id"),
            language=getattr(payload, "language", "it"),
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


# ── /calculate ────────────────────────────────────────────────────────────────

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

    # ── Valida lista immobili ─────────────────────────────────────────────────
    props_raw = payload.properties
    if not props_raw:
        raise HTTPException(status_code=422, detail="Inserire almeno un immobile.")

    # Normalizza ogni property a dict puro (gestisce Pydantic model o dict)
    def to_dict(p) -> dict:
        if hasattr(p, "model_dump"):
            return p.model_dump()
        if hasattr(p, "__dict__"):
            return {k: v for k, v in p.__dict__.items() if not k.startswith("_")}
        return dict(p)

    properties: list[dict] = [to_dict(p) for p in props_raw]

    # ── Normalizza campi per ogni immobile ───────────────────────────────────
    # Il frontend può mandare nomi diversi (label/name, purchase_price/price, ecc.)
    normalized: list[dict] = []
    for i, p in enumerate(properties):
        normalized.append({
            "name":             p.get("label") or p.get("name") or f"Immobile {i+1}",
            "address":          p.get("address", ""),
            "price":            float(p.get("purchase_price") or p.get("price") or 0),
            "size_sqm":         float(p.get("size_sqm") or 0),
            "rooms":            p.get("rooms") or p.get("locali"),
            "condition":        p.get("condition") or p.get("condizioni"),
            "floor":            p.get("floor") or p.get("piano"),
            "elevator":         p.get("elevator") or p.get("ascensore"),
            "renovation_budget": float(p["renovation_budget"])
                                 if p.get("renovation_budget") else None,
            "mortgage_rate":    float(p["mortgage_rate"])
                                if p.get("mortgage_rate") else None,
            "mortgage_years":   int(p.get("mortgage_years") or 20),
            "down_payment_pct": _normalize_down_payment(p.get("down_payment_pct")),
            "current_rent":     float(p["current_rent"])
                                if p.get("current_rent") else None,
            "notes":            p.get("notes") or p.get("note", ""),
        })

    # ── Risolvi goal (campo unificato — legacy: investment_goal) ─────────────
    # CompareROIRequest usa "goal"; versioni precedenti mandavano "investment_goal"
    raw_goal = (
        getattr(payload, "goal", None)
        or getattr(payload, "investment_goal", None)
        or "affitto_lungo"
    )
    investment_goal = GOAL_MAP.get(raw_goal, "affitto_lungo")

    logger.info(
        f"Calcola ROI | user={current_user['email']} | plan={plan} | "
        f"goal={investment_goal} | lang={getattr(payload, 'language', 'it')} | "
        f"immobili={len(normalized)}"
    )

    # ── Chiama il service con la nuova firma ──────────────────────────────────
    try:
        result: dict = await asyncio.to_thread(
            run_compare_roi,
            properties=normalized,
            investment_goal=investment_goal,
            plan=plan,
            user_id=current_user.get("id"),
            language=getattr(payload, "language", "it"),
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

    # ── Costruisci risposta ───────────────────────────────────────────────────
    # winner_label: primo immobile nella classifica (estratto dalla recommendation)
    winner_label = _extract_winner(result.get("recommended_scenario", ""), normalized)

    return CompareROIResponse(
        results=result.get("results", []),
        winner_label=winner_label,
        winner_reason=result.get("summary", ""),
        comparison_summary=result.get("recommended_scenario", ""),
        market_notes=result.get("market_analysis", ""),
        disclaimer=(
            "I risultati generati dall'AI hanno finalità esclusivamente informativa "
            "e non costituiscono consulenza finanziaria o immobiliare."
        ),
        remaining_usage=remaining,
    )


# ── Utility ───────────────────────────────────────────────────────────────────

def _normalize_down_payment(value) -> float:
    """
    Normalizza l'acconto in percentuale intera (es. 20.0).
    Gestisce sia 0.20 (decimale) che 20 (percentuale intera).
    """
    if value is None:
        return 20.0
    v = float(value)
    # Se <= 1 assume sia in formato decimale (0.20 → 20%)
    return v * 100 if v <= 1 else v


def _extract_winner(recommendation_text: str, properties: list[dict]) -> str:
    """
    Estrae il nome dell'immobile consigliato dalla raccomandazione testuale.
    Cerca il nome di ogni immobile nel testo e restituisce il primo trovato
    vicino a keyword come 'consigliato', 'migliore', 'COMPRA'.
    Se non trova nulla restituisce il nome del primo immobile.
    """
    if not recommendation_text or not properties:
        return properties[0].get("name", "Immobile 1") if properties else ""

    text_lower = recommendation_text.lower()
    keywords   = ["consigliato", "migliore", "compra", "primo classificato", "vincitore"]

    for kw in keywords:
        kw_pos = text_lower.find(kw)
        if kw_pos == -1:
            continue
        # Cerca il nome di un immobile nelle 200 caratteri intorno alla keyword
        window = recommendation_text[max(0, kw_pos - 100): kw_pos + 100]
        for prop in properties:
            name = prop.get("name", "")
            if name and name.lower() in window.lower():
                return name

    # Fallback: primo immobile
    return properties[0].get("name", "Immobile 1")