"""
models.py — aggiornato con piano BASIC e modelli Stripe
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class Plan(str, Enum):
    FREE  = "free"
    BASIC = "basic"   # €4.99/mese — NUOVO
    PRO   = "pro"     # €29/mese
    PLUS  = "plus"    # €79/mese


class UserRegister(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class UserPublic(BaseModel):
    id: int
    email: str
    name: str
    plan: Plan
    deepresearch_count: int
    calcola_count: int
    created_at: datetime
    trial_ends_at: Optional[str] = None
    stripe_subscription_id: Optional[str] = None

    class Config:
        from_attributes = True


class UserDB(UserPublic):
    hashed_password: Optional[str] = None
    google_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    usage_date: Optional[str] = None


# ─────────────────────────────────────────
# Billing Models
# ─────────────────────────────────────────

class UpgradeRequest(BaseModel):
    plan: Plan


class UpgradeResponse(BaseModel):
    message: str
    new_plan: Plan


class CheckoutResponse(BaseModel):
    checkout_url: str


class BillingStatus(BaseModel):
    plan: str
    trial_ends_at: Optional[str] = None
    is_trialing: bool = False
    cancel_at_period: Optional[bool] = None
    next_billing: Optional[str] = None


# ─────────────────────────────────────────
# Limiti per piano
# ─────────────────────────────────────────

PLAN_LIMITS = {
    Plan.FREE: {
        "deepresearch_daily": 1,
        "calcola_daily": 1,
        "storage_gb": 0,
        "export_docx": False,
    },
    Plan.BASIC: {
        "deepresearch_daily": 3,
        "calcola_daily": 3,
        "storage_gb": 0.5,
        "export_docx": True,
    },
    Plan.PRO: {
        "deepresearch_daily": 20,
        "calcola_daily": 20,
        "storage_gb": 2,
        "export_docx": True,
    },
    Plan.PLUS: {
        "deepresearch_daily": 999,  # illimitato
        "calcola_daily": 999,
        "storage_gb": 10,
        "export_docx": True,
    },
}


# ─────────────────────────────────────────
# Deep Research Models
# ─────────────────────────────────────────

class DeepResearchRequest(BaseModel):
    query: str = Field(
        ..., min_length=10, max_length=2000,
        description="Descrizione libera: zona, budget, obiettivo, preferenze",
    )


class FoundOpportunity(BaseModel):
    title: str
    estimated_price_range: str
    size_range: str
    zone: str
    price_per_sqm: float
    condition: str
    opportunity_score: float
    roi_potential: str
    renovation_estimate: str
    key_pros: List[str]
    key_cons: List[str]
    why_interesting: str


class DeepResearchResponse(BaseModel):
    market_context: str
    opportunities: List[FoundOpportunity]
    best_pick: str
    market_trend: str
    action_plan: str
    disclaimer: str
    remaining_usage: int


# ─────────────────────────────────────────
# Calcola ROI Models
# ─────────────────────────────────────────

class PropertyInput(BaseModel):
    label: str
    address: str
    purchase_price: float
    size_sqm: float
    condition: str = "da ristrutturare"
    rooms: int = 3
    floor: Optional[int] = None
    has_elevator: bool = False
    renovation_budget: Optional[float] = None
    mortgage_rate: Optional[float] = 3.5
    mortgage_years: Optional[int] = 20
    down_payment_pct: Optional[float] = 0.20
    notes: Optional[str] = None


class CompareROIRequest(BaseModel):
    properties: List[PropertyInput] = Field(..., min_length=1, max_length=5)
    goal: str = Field(default="flipping")


class RenovationScenario(BaseModel):
    name: str
    renovation_cost: float
    duration_months: int
    estimated_value_after: float
    estimated_rent_after: float
    roi_percent: float
    payback_years: float
    risk_level: str
    description: str


class PropertyROIResult(BaseModel):
    label: str
    address: str
    purchase_price: float
    price_per_sqm: float
    scenarios: List[RenovationScenario]
    best_scenario: str
    total_investment_mid: float
    net_roi_mid: float
    payback_mid: float
    risk_summary: str
    rank: int


class CompareROIResponse(BaseModel):
    results: List[PropertyROIResult]
    winner_label: str
    winner_reason: str
    comparison_summary: str
    market_notes: str
    disclaimer: str
    remaining_usage: int


# Legacy
class PropertyCalculationInput(BaseModel):
    purchase_price: float
    size_sqm: float
    location: str
    current_rent: Optional[float] = None
    renovation_budget: Optional[float] = None
    mortgage_rate: Optional[float] = 3.5
    mortgage_years: Optional[int] = 20
    down_payment_pct: Optional[float] = 0.20


class CalculationResponse(BaseModel):
    property_summary: str
    scenarios: List[RenovationScenario]
    recommended_scenario: str
    remaining_usage: int


STORAGE_MAX_BYTES = 2 * 1024 * 1024 * 1024
