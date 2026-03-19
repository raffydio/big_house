"""
agents/search_tool.py

Tool di ricerca web per gli agenti CrewAI di Big House AI.
Riscritto con il nuovo SDK google.genai (GA, maggio 2025).
Rimosso google.generativeai (deprecato novembre 2025).

CASCATA SEARCH — due modalità in base all'LLM attivo:

    Modalità GEMINI (default):
        1. Google Search Tool nativo (google.genai grounding)
        2. DuckDuckGo (fallback gratuito)
        3. Brave Search API (fallback finale)

    Modalità CLAUDE (attivata da llm_factory quando Gemini fallisce):
        1. DuckDuckGo (primario)
        2. Brave Search API (fallback)

    Se tutti i provider falliscono → SearchExhaustedError (non blocca il crew,
    gli agenti continuano con la conoscenza di training del modello).
"""

import os
import logging
from typing import Optional

from crewai.tools import tool   # ← corretto per CrewAI 1.10.x

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Eccezione custom
# ─────────────────────────────────────────────

class SearchExhaustedError(Exception):
    """Tutti i provider di ricerca hanno fallito."""
    pass


# ─────────────────────────────────────────────
# Provider 1 — Google Search Tool nativo
# ─────────────────────────────────────────────

def _search_google(query: str, model: str = "gemini-2.5-flash") -> str:
    from google import genai
    from google.genai import types

    client = genai.Client()
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    config = types.GenerateContentConfig(tools=[grounding_tool])

    response = client.models.generate_content(
        model=model,
        contents=(
            f"Cerca informazioni aggiornate su: {query}. "
            f"Fornisci dati numerici specifici se disponibili "
            f"(prezzi €/mq, rendimenti, trend di mercato)."
        ),
        config=config,
    )

    if not response.text:
        raise ValueError("Google Search ha restituito risposta vuota")

    logger.info(f"[search_tool] Google Search OK — query: {query[:50]}...")
    return response.text


# ─────────────────────────────────────────────
# Provider 2 — DuckDuckGo
# ─────────────────────────────────────────────

def _search_duckduckgo(query: str, max_results: int = 5) -> str:
    from duckduckgo_search import DDGS

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))

    if not results:
        raise ValueError("DuckDuckGo non ha restituito risultati")

    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(f"{i}. {r.get('title','')}\n{r.get('body','')}\nFonte: {r.get('href','')}")

    logger.info(f"[search_tool] DuckDuckGo OK — {len(results)} risultati per: {query[:50]}...")
    return "\n\n".join(formatted)


# ─────────────────────────────────────────────
# Provider 3 — Brave Search API
# ─────────────────────────────────────────────

def _search_brave(query: str, count: int = 5) -> str:
    import requests

    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        raise ValueError("BRAVE_SEARCH_API_KEY non configurata nel .env")

    response = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
        params={"q": query, "count": count, "country": "it", "search_lang": "it"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    web_results = data.get("web", {}).get("results", [])
    if not web_results:
        raise ValueError("Brave Search non ha restituito risultati")

    formatted = []
    for i, r in enumerate(web_results, 1):
        formatted.append(f"{i}. {r.get('title','')}\n{r.get('description','')}\nFonte: {r.get('url','')}")

    logger.info(f"[search_tool] Brave Search OK — {len(web_results)} risultati per: {query[:50]}...")
    return "\n\n".join(formatted)


# ─────────────────────────────────────────────
# Funzione principale — Cascata search
# ─────────────────────────────────────────────

def get_search_results(
    query: str,
    mode: str = "gemini",
    gemini_model: Optional[str] = None,
) -> str:
    """
    Esegue la ricerca web con cascata di fallback.
    Modalità GEMINI:  Google Search → DuckDuckGo → Brave
    Modalità CLAUDE:  DuckDuckGo → Brave
    """
    model = gemini_model or os.getenv("GEMINI_MODEL_OVERRIDE", "gemini/gemini-2.5-flash")
    model_name = model.replace("gemini/", "")
    providers_tried = []

    if mode == "gemini":
        try:
            return _search_google(query, model=model_name)
        except Exception as e:
            providers_tried.append(f"Google Search: {type(e).__name__} — {str(e)[:80]}")
            logger.warning(f"[search_tool] Google Search fallito, passo a DuckDuckGo. Errore: {e}")

    try:
        return _search_duckduckgo(query)
    except Exception as e:
        providers_tried.append(f"DuckDuckGo: {type(e).__name__} — {str(e)[:80]}")
        logger.warning(f"[search_tool] DuckDuckGo fallito, passo a Brave. Errore: {e}")

    try:
        return _search_brave(query)
    except Exception as e:
        providers_tried.append(f"Brave Search: {type(e).__name__} — {str(e)[:80]}")
        logger.error("[search_tool] Brave Search fallito. Tutti i provider esauriti.")

    raise SearchExhaustedError(
        f"Tutti i provider di ricerca hanno fallito per la query '{query[:50]}': {' | '.join(providers_tried)}"
    )


# ─────────────────────────────────────────────
# get_search_tool() — compatibilità con i service
# Richiesta da deep_research_service.py e calculation_service.py
# ─────────────────────────────────────────────

def get_search_tool(plan: str = "free", mode: str = "gemini"):
    """
    Factory function richiesta dai service.
    Restituisce il tool CrewAI appropriato in base alla modalità LLM.

    Args:
        plan: Piano utente (reserved per futura logica)
        mode: "gemini" oppure "claude"

    Returns:
        Tool CrewAI da passare agli agenti
    """
    if mode == "claude":
        return ricerca_immobiliare_claude
    return ricerca_immobiliare


# ─────────────────────────────────────────────
# CrewAI Tool — Modalità GEMINI
# ─────────────────────────────────────────────

@tool("Ricerca Immobiliare Web")
def ricerca_immobiliare(query: str) -> str:
    """
    Cerca informazioni aggiornate sul mercato immobiliare italiano.
    Usa Google Search con fallback su DuckDuckGo e Brave Search.
    Fornisce prezzi euro/mq, rendimenti, trend di zona, dati catastali.
    """
    try:
        return get_search_results(query, mode="gemini")
    except SearchExhaustedError as e:
        logger.error(f"[ricerca_immobiliare] SearchExhaustedError: {e}")
        return (
            "ATTENZIONE: La ricerca web non è disponibile al momento. "
            "Procedi con i dati di training del modello e segnala "
            "nell'output che i dati potrebbero non essere aggiornati."
        )


# ─────────────────────────────────────────────
# CrewAI Tool — Modalità CLAUDE
# ─────────────────────────────────────────────

@tool("Ricerca Immobiliare Web Claude")
def ricerca_immobiliare_claude(query: str) -> str:
    """
    Cerca informazioni aggiornate sul mercato immobiliare italiano.
    Usa DuckDuckGo con fallback su Brave Search.
    Versione per agenti Claude, senza Google Search nativo.
    """
    try:
        return get_search_results(query, mode="claude")
    except SearchExhaustedError as e:
        logger.error(f"[ricerca_immobiliare_claude] SearchExhaustedError: {e}")
        return (
            "ATTENZIONE: La ricerca web non è disponibile al momento. "
            "Procedi con i dati di training del modello e segnala "
            "nell'output che i dati potrebbero non essere aggiornati."
        )