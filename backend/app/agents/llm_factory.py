"""
agents/llm_factory.py
Factory LLM — Google Gemini 2.5 Pro via LiteLLM.

COME FUNZIONA LA CHIAVE API (sicuro, nessuna esposizione nel codice):
  1. La chiave è SOLO in backend/.env: GEMINI_API_KEY=AIzaSy...
  2. pydantic-settings la carica in settings.GEMINI_API_KEY
  3. Qui viene copiata in os.environ["GEMINI_API_KEY"] che è
     quello che LiteLLM cerca internamente — NON è mai nel codice sorgente.

IMPORTANTE: assicurati che backend/.env NON sia committato su GitHub.
Aggiungi ".env" a .gitignore se non l'hai già fatto.
"""
import os
import logging
from crewai import LLM
from app.config import settings

logger = logging.getLogger(__name__)


def create_gemini_llm() -> LLM:
    """
    Crea un'istanza LLM Gemini per CrewAI.

    LiteLLM (bridge interno di CrewAI) cerca la chiave API in:
      1. os.environ["GEMINI_API_KEY"]   ← quello che impostiamo qui
      2. Il parametro api_key del costruttore (meno affidabile con alcune versioni)

    Impostiamo ENTRAMBI per massima compatibilità.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY non trovata. "
            "Aggiungi GEMINI_API_KEY=AIzaSy... a backend/.env"
        )

    # ── Imposta la chiave nell'ambiente del processo ──────────────────────
    # LiteLLM la cerca qui. La chiave non è mai nel codice sorgente:
    # viene letta da .env → pydantic settings → os.environ (solo in RAM).
    os.environ["GEMINI_API_KEY"] = api_key
    # Alcune versioni LiteLLM usano anche GOOGLE_API_KEY come alias
    os.environ["GOOGLE_API_KEY"] = api_key

    model = settings.GEMINI_MODEL  # "gemini/gemini-2.5-pro-preview"
    logger.info(f"Inizializzazione LLM: {model}")

    return LLM(
        model=model,
        api_key=api_key,          # passato anche qui per sicurezza
        temperature=0.3,
        max_tokens=8192,
    )


def get_llm() -> LLM:
    """
    Entry point pubblico.
    Permette in futuro di switchare provider senza modificare gli agenti.
    """
    try:
        return create_gemini_llm()
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Errore creazione LLM: {e}")
        raise RuntimeError(f"Impossibile inizializzare il modello AI: {e}") from e