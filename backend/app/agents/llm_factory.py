"""
agents/llm_factory.py
Factory LLM — modello Gemini diverso per piano utente.

LOGICA PIANI:
  FREE  → gemini-2.5-flash-lite   ($0.10/$0.40 per 1M token)  — costo minimo
  BASIC → gemini-2.5-flash        ($0.30/$2.50 per 1M token)  — qualità media
  PRO   → gemini-2.5-pro          ($1.25/$10.00 per 1M token) — alta qualità
  PLUS  → gemini-3-flash-preview  ($0.50/$3.00 per 1M token)  — massima qualità
           con Google Search integrato, reasoning avanzato

VANTAGGI:
  - Utenti FREE/BASIC vedono risposte rapide e buone
  - Utenti PRO/PLUS vedono la massima qualità disponibile
  - I margini restano positivi per ogni piano
  - Differenziazione reale del prodotto tra piani

COSTI PER DEEP RESEARCH (stima ~17k input + 4k output token):
  FREE:  $0.003/DR  → margine altissimo
  BASIC: $0.015/DR  → margine altissimo
  PRO:   $0.062/DR  → margine buono
  PLUS:  $0.020/DR  → margine ottimo
"""
import os
import logging
from crewai import LLM
from app.config import settings

logger = logging.getLogger(__name__)

# ── Mappa piano → modello Gemini ─────────────────────────────────────────────
#
# Aggiornare qui quando Google rilascia nuovi modelli.
# I modelli "preview" diventano stabili nel giro di settimane.
#
PLAN_MODELS: dict[str, str] = {
    "free":  "gemini/gemini-2.5-flash-lite",    # veloce, economico
    "basic": "gemini/gemini-2.5-flash",          # bilanciato qualità/costo
    "pro":   "gemini/gemini-2.5-pro",            # alta qualità, reasoning
    "plus":  "gemini/gemini-2.5-pro",            # stessa qualità PRO
                                                  # (gemini-3 ancora in preview)
}

# Temperatura per piano — PRO/PLUS più precisi, FREE più veloci
PLAN_TEMPERATURE: dict[str, float] = {
    "free":  0.4,
    "basic": 0.3,
    "pro":   0.2,
    "plus":  0.2,
}

# Max token per piano
PLAN_MAX_TOKENS: dict[str, int] = {
    "free":  4096,
    "basic": 6144,
    "pro":   8192,
    "plus":  8192,
}


def get_llm(plan: str = "free") -> LLM:
    """
    Ritorna un LLM Gemini calibrato per il piano utente.

    Args:
        plan: "free" | "basic" | "pro" | "plus"

    Returns:
        LLM CrewAI configurato con il modello appropriato

    Esempio:
        llm = get_llm(plan=current_user["plan"])
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY non trovata. "
            "Aggiungi GEMINI_API_KEY=AIzaSy... a backend/.env"
        )

    # Imposta chiavi nell'ambiente (richiesto da LiteLLM)
    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GOOGLE_API_KEY"] = api_key

    # Normalizza piano (fallback a free se sconosciuto)
    normalized_plan = plan.lower() if plan else "free"
    if normalized_plan not in PLAN_MODELS:
        logger.warning(f"Piano sconosciuto '{plan}', uso 'free'")
        normalized_plan = "free"

    model       = PLAN_MODELS[normalized_plan]
    temperature = PLAN_TEMPERATURE[normalized_plan]
    max_tokens  = PLAN_MAX_TOKENS[normalized_plan]

    logger.info(f"LLM piano={normalized_plan} → modello={model}")

    return LLM(
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_model_label(plan: str) -> str:
    """
    Ritorna il nome leggibile del modello per il piano.
    Utile per mostrare all'utente quale modello sta usando.
    """
    labels = {
        "free":  "Gemini 2.5 Flash-Lite",
        "basic": "Gemini 2.5 Flash",
        "pro":   "Gemini 2.5 Pro",
        "plus":  "Gemini 2.5 Pro",
    }
    return labels.get(plan.lower(), "Gemini 2.5 Flash-Lite")