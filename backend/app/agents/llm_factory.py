"""
agents/llm_factory.py
Factory per istanze LLM. Centralizza la configurazione del modello AI.
Tutte le credenziali vengono da config.py → .env

AGGIORNATO: DeepSeek → Google Gemini 2.5 Pro
"""
import logging
from crewai import LLM
from app.config import settings

logger = logging.getLogger(__name__)


def create_gemini_llm() -> LLM:
    """
    Crea e ritorna un'istanza LLM Google Gemini configurata per CrewAI.

    CrewAI usa LiteLLM come bridge → il model string deve avere
    il prefisso "gemini/" per essere riconosciuto correttamente.

    Legge da config:
    - GEMINI_API_KEY
    - GEMINI_MODEL  (default: gemini/gemini-2.5-pro-preview)

    Non usa @lru_cache perché CrewAI LLM mantiene stato interno;
    meglio creare istanze fresche per ogni Crew.
    """
    logger.debug(f"Creazione LLM Gemini: model={settings.GEMINI_MODEL}")

    return LLM(
        model=settings.GEMINI_MODEL,
        api_key=settings.GEMINI_API_KEY,
        temperature=0.3,    # Bassa temperatura per analisi finanziarie precise
        max_tokens=8192,    # Gemini 2.5 Pro supporta output più lunghi di DeepSeek
    )


def get_llm() -> LLM:
    """
    Entry point pubblico per ottenere l'LLM.
    Permette in futuro di switchare provider senza modificare gli agenti.
    """
    try:
        return create_gemini_llm()
    except Exception as e:
        logger.error(f"Errore nella creazione LLM Gemini: {e}")
        raise RuntimeError(f"Impossibile inizializzare il modello AI: {e}") from e