"""
agents/llm_factory.py
KEY ROTATION — usa fino a 3 chiavi Gemini in round-robin per aggirare
il limite di 15 RPM del free tier (gemini-2.0-flash).

Con 3 chiavi → ~45 RPM effettivi, sufficiente per una run completa
di Deep Research (4 agenti, ~15-20 chiamate LLM totali).

.env atteso:
    GEMINI_API_KEY=AIza...      # chiave 1 (primaria)
    GEMINI_API_KEY_2=AIza...    # chiave 2 (opzionale)
    GEMINI_API_KEY_3=AIza...    # chiave 3 (opzionale)
    GEMINI_MODEL_OVERRIDE=gemini/gemini-2.0-flash   # per sviluppo senza fatturazione
"""
import os
import threading
import logging
from crewai import LLM
from app.config import settings

logger = logging.getLogger(__name__)

# ── Mappa piano → modello Gemini (produzione con fatturazione) ─────────────────
PLAN_MODELS: dict[str, str] = {
    "free":  "gemini/gemini-2.0-flash",   # free tier 1.500 RPD / 15 RPM
    "basic": "gemini/gemini-2.0-flash",   # free tier 1.500 RPD / 15 RPM
    "pro":   "gemini/gemini-2.5-flash",   # richiede fatturazione
    "plus":  "gemini/gemini-2.5-pro",     # richiede fatturazione
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

# ── Key rotation ───────────────────────────────────────────────────────────────
_key_lock  = threading.Lock()
_key_index = 0   # indice corrente (thread-safe)


def _get_api_keys() -> list[str]:
    """
    Raccoglie tutte le chiavi disponibili dal settings/env.
    Ordine: GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3.
    """
    keys = []
    # Chiave primaria (da settings o env diretto)
    primary = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY", "")
    if primary:
        keys.append(primary.strip())

    # Chiavi aggiuntive direttamente dall'env
    for suffix in ("_2", "_3"):
        k = os.environ.get(f"GEMINI_API_KEY{suffix}", "").strip()
        if k:
            keys.append(k)

    return keys


def _next_key(keys: list[str]) -> str:
    """Restituisce la prossima chiave in round-robin (thread-safe)."""
    global _key_index
    with _key_lock:
        key = keys[_key_index % len(keys)]
        _key_index += 1
    return key


def get_llm(plan: str = "free") -> LLM:
    """
    Ritorna un LLM Gemini calibrato per il piano utente, con key rotation.

    Override modello per sviluppo locale:
        GEMINI_MODEL_OVERRIDE=gemini/gemini-2.0-flash  nel .env
    """
    keys = _get_api_keys()
    if not keys:
        raise RuntimeError(
            "Nessuna GEMINI_API_KEY trovata. "
            "Aggiungi GEMINI_API_KEY=AIzaSy... a backend/.env"
        )

    api_key = _next_key(keys)
    key_label = f"...{api_key[-6:]}"   # log parziale per sicurezza

    # Imposta chiavi nell'ambiente (richiesto da LiteLLM/CrewAI)
    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GOOGLE_API_KEY"] = api_key

    # Normalizza piano
    normalized_plan = (plan or "free").lower()
    if normalized_plan not in PLAN_MODELS:
        logger.warning(f"Piano sconosciuto '{plan}', uso 'free'")
        normalized_plan = "free"

    # Override modello per sviluppo locale
    model_override = os.environ.get("GEMINI_MODEL_OVERRIDE", "").strip()
    if model_override:
        model = model_override
        logger.info(
            f"LLM | OVERRIDE={model} | piano={normalized_plan} | "
            f"key={key_label} | {len(keys)} chiave/i disponibili"
        )
    else:
        model = PLAN_MODELS[normalized_plan]
        logger.info(
            f"LLM | piano={normalized_plan} | modello={model} | "
            f"key={key_label} | {len(keys)} chiave/i disponibili"
        )

    return LLM(
        model=model,
        api_key=api_key,
        temperature=PLAN_TEMPERATURE[normalized_plan],
        max_tokens=PLAN_MAX_TOKENS[normalized_plan],
    )


def get_model_label(plan: str) -> str:
    """Nome leggibile del modello per il piano (usato nel frontend)."""
    labels = {
        "free":  "Gemini 2.0 Flash",
        "basic": "Gemini 2.0 Flash",
        "pro":   "Gemini 2.5 Flash",
        "plus":  "Gemini 2.5 Pro",
    }
    return labels.get((plan or "free").lower(), "Gemini 2.0 Flash")