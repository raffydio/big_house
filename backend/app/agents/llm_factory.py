"""
agents/llm_factory.py
SPRINT 2/5 — Gestione LLM, Rotazione Chiavi e Fallback Claude

Logica completa:
  1. get_llm(plan)          → LLM Gemini primario per CrewAI
  2. get_current_gemini_key() → Chiave raw ruotata per Pipeline Deterministica
  3. get_fallback_llm(plan) → LLM Claude fallback
  4. should_fallback(exc)   → True se 429 / 503 / timeout / SearchError
  5. get_search_mode(llm_type) → "gemini" | "claude"
"""

import os
import threading
import logging
from crewai import LLM
from app.config import settings

logger = logging.getLogger(__name__)

# ── Mappa piano → modello Gemini (produzione) ─────────────────────────────────
PLAN_MODELS: dict[str, str] = {
    "free":  "gemini/gemini-2.5-flash",
    "basic": "gemini/gemini-2.5-flash",
    "pro":   "gemini/gemini-2.5-flash",
    "plus":  "gemini/gemini-2.5-pro",
}

# ── Mappa piano → modello Claude fallback ─────────────────────────────────────
PLAN_FALLBACK_MODELS: dict[str, str] = {
    "free":  "anthropic/claude-haiku-4-5-20251001",
    "basic": "anthropic/claude-haiku-4-5-20251001",
    "pro":   "anthropic/claude-haiku-4-5-20251001",
    "plus":  "anthropic/claude-sonnet-4-6",
}

PLAN_TEMPERATURE: dict[str, float] = {
    "free":  0.4,
    "basic": 0.3,
    "pro":   0.2,
    "plus":  0.2,
}

PLAN_MAX_TOKENS: dict[str, int] = {
    "free":  4096,
    "basic": 6144,
    "pro":   8192,
    "plus":  8192,
}

# ── Eccezioni che triggherano il fallback a Claude ────────────────────────────
FALLBACK_EXCEPTION_TYPES = (
    "ResourceExhausted",        # Google 429
    "ServiceUnavailable",       # Google 503
    "InternalServerError",      # Google 500
    "DeadlineExceeded",         # Timeout
    "RateLimitError",           # LiteLLM generico
    "APIStatusError",           # LiteLLM wrapper
    "SearchExhaustedError",     # search_tool.py — tutti i provider falliti
    "TimeoutError",             # Python built-in
    "ConnectionError",          # Rete
)

FALLBACK_STATUS_CODES = {429, 503, 500, 502, 504}

# ── Key rotation Gemini ───────────────────────────────────────────────────────
_key_lock  = threading.Lock()
_key_index = 0


def _get_gemini_keys() -> list[str]:
    keys = []
    primary = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY", "")
    if primary:
        keys.append(primary.strip())
    for suffix in ("_2", "_3"):
        k = os.environ.get(f"GEMINI_API_KEY{suffix}", "").strip()
        if k:
            keys.append(k)
    return keys


def _next_gemini_key(keys: list[str]) -> str:
    global _key_index
    with _key_lock:
        key = keys[_key_index % len(keys)]
        _key_index += 1
    return key


# ── NUOVO: Esporta la chiave corrente per i servizi NON-CrewAI ───────────────
def get_current_gemini_key() -> str:
    """
    Restituisce la chiave Gemini corrente applicando la rotazione.
    Usata dalla Pipeline Deterministica e dal Search Tool per bilanciare il carico.
    """
    keys = _get_gemini_keys()
    if not keys:
        raise RuntimeError(
            "Nessuna GEMINI_API_KEY trovata. "
            "Aggiungi GEMINI_API_KEY=AIzaSy... a backend/.env"
        )
    return _next_gemini_key(keys)


# ── LLM primario — Gemini (Per CrewAI) ────────────────────────────────────────

def get_llm(plan: str = "free") -> LLM:
    """
    Restituisce LLM Gemini calibrato per il piano, con key rotation.
    Override modello: GEMINI_MODEL_OVERRIDE nel .env
    """
    api_key = get_current_gemini_key()
    key_label = f"...{api_key[-6:]}"

    normalized = (plan or "free").lower()
    if normalized not in PLAN_MODELS:
        logger.warning(f"Piano sconosciuto '{plan}', uso 'free'")
        normalized = "free"

    model_override = os.environ.get("GEMINI_MODEL_OVERRIDE", "").strip()
    if model_override:
        model = model_override
        logger.info(f"LLM | OVERRIDE={model} | piano={normalized} | key={key_label}")
    else:
        model = PLAN_MODELS[normalized]
        logger.info(f"LLM | piano={normalized} | modello={model} | key={key_label}")

    return LLM(
        model=model,
        api_key=api_key,
        temperature=PLAN_TEMPERATURE[normalized],
        max_tokens=PLAN_MAX_TOKENS[normalized],
    )


# ── LLM fallback — Claude ─────────────────────────────────────────────────────

def get_fallback_llm(plan: str = "free") -> LLM | None:
    """
    Restituisce LLM Claude fallback per il piano.
    Restituisce None se ANTHROPIC_API_KEY non è configurata.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()  # al momento non c'è
    if not api_key:
        logger.warning(
            "[llm_factory] ANTHROPIC_API_KEY non configurata — "
            "fallback Claude non disponibile"
        )
        return None

    normalized = (plan or "free").lower()
    if normalized not in PLAN_FALLBACK_MODELS:
        normalized = "free"

    model = PLAN_FALLBACK_MODELS[normalized]
    key_label = f"...{api_key[-6:]}"

    logger.info(
        f"LLM FALLBACK | piano={normalized} | modello={model} | key={key_label}"
    )

    return LLM(
        model=model,
        api_key=api_key,
        temperature=PLAN_TEMPERATURE[normalized],
        max_tokens=PLAN_MAX_TOKENS[normalized],
    )


# ── Logica fallback — decide se switchare a Claude ────────────────────────────

def should_fallback(exc: Exception) -> bool:
    """
    Restituisce True se l'eccezione indica che Gemini non è disponibile.
    """
    exc_type = type(exc).__name__

    if exc_type in FALLBACK_EXCEPTION_TYPES:
        logger.info(f"[llm_factory] should_fallback=True — tipo: {exc_type}")
        return True

    status_code = getattr(exc, "status_code", None)
    if status_code in FALLBACK_STATUS_CODES:
        logger.info(f"[llm_factory] should_fallback=True — HTTP {status_code}")
        return True

    exc_msg = str(exc).lower()
    fallback_keywords = [
        "429", "rate limit", "quota", "resource exhausted",
        "503", "service unavailable", "timeout", "timed out",
        "connection", "search exhausted", "overloaded"
    ]
    for kw in fallback_keywords:
        if kw in exc_msg:
            logger.info(f"[llm_factory] should_fallback=True — keyword: '{kw}'")
            return True

    return False


# ── Modalità search in base all'LLM attivo ───────────────────────────────────

def get_search_mode(llm_type: str = "gemini") -> str:
    return "claude" if llm_type == "claude" else "gemini"


# ── Label leggibile del modello ───────────────────────────────────────────────

def get_model_label(plan: str, llm_type: str = "gemini") -> str:
    if llm_type == "claude":
        labels = {
            "free":  "Claude Haiku 4.5",
            "basic": "Claude Haiku 4.5",
            "pro":   "Claude Haiku 4.5",
            "plus":  "Claude Sonnet 4.6",
        }
        return labels.get((plan or "free").lower(), "Claude Haiku 4.5")

    labels = {
        "free":  "Gemini 2.5 Flash",
        "basic": "Gemini 2.5 Flash",
        "pro":   "Gemini 2.5 Flash",
        "plus":  "Gemini 2.5 Pro",
    }
    return labels.get((plan or "free").lower(), "Gemini 2.5 Flash")