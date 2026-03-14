"""
routers/billing.py
Stripe Embedded Checkout — ui_mode='embedded'
"""
import logging
import stripe
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request, Depends, Header
from pydantic import BaseModel
from typing import Optional

from app.config import settings
from app.core.security import get_current_user
from app.core.database import (
    get_user_by_email,
    update_user_plan,
    update_user_stripe,
    get_user_by_stripe_customer_id,
)
from app.models import Plan

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter(prefix="/billing", tags=["Billing"])

PRICE_IDS = {
    "basic": settings.STRIPE_PRICE_BASIC,
    "pro":   settings.STRIPE_PRICE_PRO,
    "plus":  settings.STRIPE_PRICE_PLUS,
}

PLAN_NAMES = {
    "basic": Plan.BASIC,
    "pro":   Plan.PRO,
    "plus":  Plan.PLUS,
}


# ─────────────────────────────────────────
# POST /billing/create-checkout-session
# Ritorna client_secret per Embedded Checkout
# ─────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan: str  # "basic" | "pro" | "plus"


@router.post("/create-checkout-session")
async def create_checkout_session(
    payload: CheckoutRequest,
    current_user: dict = Depends(get_current_user),
):
    plan = payload.plan.lower()
    if plan not in PRICE_IDS:
        raise HTTPException(status_code=400, detail=f"Piano non valido: {plan}")

    price_id = PRICE_IDS[plan]
    if not price_id:
        raise HTTPException(status_code=503, detail="Pagamenti non ancora configurati.")

    # Blocca downgrade (es. PLUS che prova a comprare BASIC)
    current_plan = current_user.get("plan", "free")
    plan_order = {"free": 0, "basic": 1, "pro": 2, "plus": 3}
    if plan_order.get(plan, 0) <= plan_order.get(current_plan, 0) and current_plan != "free":
        raise HTTPException(
            status_code=400,
            detail="Per effettuare un downgrade contatta il supporto."
        )

    email = current_user["email"]

    # Crea o recupera Stripe Customer
    stripe_customer_id = current_user.get("stripe_customer_id")
    if not stripe_customer_id:
        customer = stripe.Customer.create(
            email=email,
            name=current_user.get("name", ""),
            metadata={"user_email": email},
        )
        stripe_customer_id = customer.id
        update_user_stripe(email, stripe_customer_id=stripe_customer_id)

    try:
        session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            ui_mode="embedded",                          # ← Embedded Checkout
            return_url=f"{settings.FRONTEND_URL}/dashboard?payment=success&plan={plan}&session_id={{CHECKOUT_SESSION_ID}}",
            subscription_data={
                "trial_period_days": 14,
                "metadata": {"user_email": email, "plan": plan},
            },
            metadata={"user_email": email, "plan": plan},
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error per {email}: {e}")
        raise HTTPException(status_code=500, detail="Errore creazione sessione pagamento.")

    logger.info(f"Embedded checkout creato: {email} → {plan}")
    # Ritorna client_secret (NON publishable key — quello va nel frontend come env var)
    return {"client_secret": session.client_secret}


# ─────────────────────────────────────────
# POST /billing/webhook
# ─────────────────────────────────────────

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
):
    body = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            body, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info(f"Stripe webhook: {event_type}")

    if event_type == "checkout.session.completed":
        email    = data.get("metadata", {}).get("user_email")
        plan     = data.get("metadata", {}).get("plan")
        sub_id   = data.get("subscription")
        if email and plan:
            update_user_plan(email, PLAN_NAMES.get(plan, Plan.FREE))
            update_user_stripe(
                email,
                stripe_subscription_id=sub_id,
                trial_ends_at=(datetime.utcnow() + timedelta(days=14)).isoformat(),
            )
            logger.info(f"✅ Checkout completato: {email} → {plan}")

    elif event_type == "customer.subscription.updated":
        customer_id = data.get("customer")
        status      = data.get("status")
        user = get_user_by_stripe_customer_id(customer_id)
        if user:
            if status in ("active", "trialing"):
                price_id = data["items"]["data"][0]["price"]["id"]
                plan = _price_to_plan(price_id)
                if plan:
                    update_user_plan(user["email"], PLAN_NAMES[plan])
                    logger.info(f"Subscription aggiornata: {user['email']} → {plan}")
            elif status == "canceled":
                update_user_plan(user["email"], Plan.FREE)

    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")
        user = get_user_by_stripe_customer_id(customer_id)
        if user:
            update_user_plan(user["email"], Plan.FREE)
            update_user_stripe(user["email"], stripe_subscription_id=None)
            logger.info(f"Subscription cancellata: {user['email']} → free")

    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        user = get_user_by_stripe_customer_id(customer_id)
        if user:
            logger.warning(f"⚠️ Pagamento fallito: {user['email']}")

    elif event_type == "customer.subscription.trial_will_end":
        customer_id = data.get("customer")
        user = get_user_by_stripe_customer_id(customer_id)
        if user:
            logger.info(f"⏰ Trial in scadenza tra 3gg: {user['email']}")
            # TODO: email reminder

    return {"status": "ok"}


# ─────────────────────────────────────────
# POST /billing/cancel
# ─────────────────────────────────────────

@router.post("/cancel")
async def cancel_subscription(current_user: dict = Depends(get_current_user)):
    sub_id = current_user.get("stripe_subscription_id")
    if not sub_id:
        raise HTTPException(status_code=400, detail="Nessun abbonamento attivo.")
    try:
        stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail="Errore cancellazione abbonamento.")
    logger.info(f"Abbonamento cancellato (fine periodo): {current_user['email']}")
    return {"message": "Abbonamento cancellato. Accesso attivo fino alla fine del periodo."}


# ─────────────────────────────────────────
# GET /billing/status
# ─────────────────────────────────────────

@router.get("/status")
async def billing_status(current_user: dict = Depends(get_current_user)):
    sub_id       = current_user.get("stripe_subscription_id")
    trial_ends   = current_user.get("trial_ends_at")
    result = {
        "plan":             current_user.get("plan", "free"),
        "trial_ends_at":    trial_ends,
        "is_trialing":      False,
        "cancel_at_period": None,
        "next_billing":     None,
    }
    if sub_id:
        try:
            sub = stripe.Subscription.retrieve(sub_id)
            result["is_trialing"]      = sub.status == "trialing"
            result["cancel_at_period"] = sub.cancel_at_period_end
            result["next_billing"]     = datetime.fromtimestamp(
                sub.current_period_end
            ).isoformat() if sub.current_period_end else None
        except stripe.error.StripeError:
            pass
    return result


def _price_to_plan(price_id: str) -> Optional[str]:
    reverse = {v: k for k, v in PRICE_IDS.items() if v}
    return reverse.get(price_id)
