"""
routers/users.py
Endpoint per gestione profilo utente e billing.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user, PLAN_LIMITS
from app.core.database import update_user_plan
from app.models import UserPublic, UpgradeRequest, UpgradeResponse, Plan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

# aggiornamento
# ─────────────────────────────────────────
# GET /users/me
# ─────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserPublic,
    summary="Profilo utente corrente",
)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Ritorna il profilo dell'utente autenticato con:
    - Dati anagrafici
    - Piano attuale
    - Contatori utilizzo giornaliero
    """
    return UserPublic(**current_user)


# ─────────────────────────────────────────
# GET /users/me/limits
# ─────────────────────────────────────────

@router.get(
    "/me/limits",
    summary="Limiti e utilizzo del piano corrente",
)
async def get_my_limits(current_user: dict = Depends(get_current_user)):
    """
    Ritorna i limiti del piano e l'utilizzo giornaliero corrente.
    """
    plan = current_user.get("plan", Plan.FREE.value)
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS[Plan.FREE.value])

    return {
        "plan": plan,
        "limits": limits,
        "usage_today": {
            "deepresearch": current_user.get("deepresearch_count", 0),
            "calcola": current_user.get("calcola_count", 0),
        },
        "remaining": {
            "deepresearch": max(
                0, limits["deepresearch"] - current_user.get("deepresearch_count", 0)
            ),
            "calcola": max(
                0, limits["calcola"] - current_user.get("calcola_count", 0)
            ),
        },
    }


# ─────────────────────────────────────────
# POST /users/billing/upgrade
# ─────────────────────────────────────────

@router.post(
    "/billing/upgrade",
    response_model=UpgradeResponse,
    summary="Upgrade piano abbonamento",
)
async def upgrade_plan(
    payload: UpgradeRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Aggiorna il piano dell'utente (FREE → PRO → PLUS).
    
    In produzione questo endpoint deve essere protetto da:
    - Verifica pagamento Stripe/PayPal
    - Webhook confirmation
    Per ora gestisce il cambio piano direttamente.
    """
    current_plan = current_user.get("plan", Plan.FREE.value)
    new_plan = payload.plan

    if current_plan == new_plan.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sei già sul piano {new_plan.value.upper()}.",
        )

    # Impedisce downgrade via questa route (serve endpoint dedicato)
    plan_order = {Plan.FREE: 0, Plan.PRO: 1, Plan.PLUS: 2}
    if plan_order.get(new_plan, 0) < plan_order.get(Plan(current_plan), 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Per effettuare il downgrade contatta il supporto.",
        )

    try:
        update_user_plan(current_user["email"], new_plan)
    except Exception as e:
        logger.error(f"Errore upgrade piano per {current_user['email']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore durante l'aggiornamento del piano.",
        )

    logger.info(
        f"Piano aggiornato: {current_user['email']} | "
        f"{current_plan} → {new_plan.value}"
    )

    return UpgradeResponse(
        message=f"Piano aggiornato a {new_plan.value.upper()} con successo!",
        new_plan=new_plan,
    )
