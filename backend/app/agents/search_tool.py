"""
agents/search_tool.py

Tool di ricerca web per gli agenti CrewAI di Big House AI.
Riscritto con il nuovo SDK google.genai (GA, maggio 2025).

CASCATA SEARCH — due modalità in base all'LLM attivo:
    Modalità GEMINI: Google Search -> DuckDuckGo -> Brave
    Modalità CLAUDE: DuckDuckGo -> Brave
"""

import os
import logging
from typing import Optional

from crewai.tools import tool

logger = logging.getLogger(__name__)

class SearchExhaustedError(Exception):
    """Tutti i provider di ricerca hanno fallito."""
    pass

# Helper per tagliare i token in eccesso
def _truncate_text(text: str, max_length: int = 1500) -> str:
    if not text: return ""
    return text[:max_length] + "\n...[TESTO TRONCATO PER LIMITI DI SPAZIO]" if len(text) > max_length else text

# ─────────────────────────────────────────────
# Provider 1 — Google Search Tool nativo
# ─────────────────────────────────────────────
def _search_google(query: str, model: str = "gemini-2.5-flash") -> str:
    from google import genai
    from google.genai import types

    client = genai.Client()
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    config = types.GenerateContentConfig(tools=[grounding_tool])

    # Chiediamo esplicitamente a Gemini di essere conciso per risparmiare token
    response = client.models.generate_content(
        model=model,
        contents=(
            f"Cerca informazioni aggiornate su: {query}. "
            f"Fornisci dati numerici specifici se disponibili (prezzi €/mq, rendimenti, trend). "
            f"SII ESTREMAMENTE CONCISO. Riassumi i dati chiave in massimo 1500 caratteri."
        ),
        config=config,
    )

    if not response.text:
        raise ValueError("Google Search ha restituito risposta vuota")

    logger.info(f"[search_tool] Google Search OK — query: {query[:50]}...")
    return _truncate_text(response.text, 2000)

# ─────────────────────────────────────────────
# Provider 2 — DuckDuckGo
# ─────────────────────────────────────────────
def _search_duckduckgo(query: str, max_results: int = 3) -> str: # Ridotto da 5 a 3
    from duckduckgo_search import DDGS

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))

    if not results:
        raise ValueError("DuckDuckGo non ha restituito risultati")

    formatted = []
    for i, r in enumerate(results, 1):
        # Tronchiamo il body del singolo risultato a 400 caratteri
        body = r.get('body','')[:400] + "..."
        formatted.append(f"{i}. {r.get('title','')}\n{body}\nFonte: {r.get('href','')}")

    logger.info(f"[search_tool] DuckDuckGo OK — {len(results)} risultati per: {query[:50]}...")
    return _truncate_text("\n\n".join(formatted), 1500)

# ─────────────────────────────────────────────
# Provider 3 — Brave Search API
# ─────────────────────────────────────────────
def _search_brave(query: str, count: int = 3) -> str: # Ridotto da 5 a 3
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
        desc = r.get('description','')[:400] + "..."
        formatted.append(f"{i}. {r.get('title','')}\n{desc}\nFonte: {r.get('url','')}")

    logger.info(f"[search_tool] Brave Search OK — {len(web_results)} risultati per: {query[:50]}...")
    return _truncate_text("\n\n".join(formatted), 1500)

# ─────────────────────────────────────────────
# Funzione principale — Cascata search
# ─────────────────────────────────────────────
def get_search_results(query: str, mode: str = "gemini", gemini_model: Optional[str] = None) -> str:
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

    raise SearchExhaustedError(f"Tutti i provider hanno fallito: {' | '.join(providers_tried)}")

# ─────────────────────────────────────────────
# Factory e Tools
# ─────────────────────────────────────────────
def get_search_tool(plan: str = "free", mode: str = "gemini"):
    if mode == "claude": return ricerca_immobiliare_claude
    return ricerca_immobiliare

@tool("Ricerca Immobiliare Web")
def ricerca_immobiliare(query: str) -> str:
    """Cerca info sul mercato immobiliare. Usa query brevi e mirate. Non cercare più di 2 volte la stessa cosa."""
    try:
        return get_search_results(query, mode="gemini")
    except SearchExhaustedError as e:
        return "ATTENZIONE: Ricerca web non disponibile. Usa i tuoi dati di training."

@tool("Ricerca Immobiliare Web Claude")
def ricerca_immobiliare_claude(query: str) -> str:
    """Cerca info sul mercato immobiliare. Usa query brevi e mirate. Non cercare più di 2 volte la stessa cosa."""
    try:
        return get_search_results(query, mode="claude")
    except SearchExhaustedError as e:
        return "ATTENZIONE: Ricerca web non disponibile. Usa i tuoi dati di training."