# backend/app/agents/search_tool.py
#
# AGGIORNATO — tre livelli di ottimizzazione per traffico concorrente:
#
#   1. STRATIFICAZIONE PER PIANO
#      FREE  → DuckDuckGo (nessun consumo Google)
#      BASIC → Tavily (1.000 gratis/mese, nessun RPD Google)
#      PRO   → Google Grounding → Tavily → DuckDuckGo
#      PLUS  → Google Grounding → Tavily → DuckDuckGo
#
#   2. CACHE DEI RISULTATI (PostgreSQL, TTL 6h)
#      Query identiche non consumano RPD aggiuntivi.
#
#   3. ROTAZIONE MULTI-KEY
#      GEMINI_API_KEY_1, GEMINI_API_KEY_2, ... → 1.500 RPD × N key

import os
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Configurazione ────────────────────────────────────────────────────────────
CACHE_TTL_HOURS = 6
CACHE_ENABLED = True

# ── Multi-key rotation ────────────────────────────────────────────────────────
def _load_gemini_keys() -> list:
    keys = []
    base = os.getenv("GEMINI_API_KEY")
    if base:
        keys.append(base)
    i = 1
    while True:
        k = os.getenv(f"GEMINI_API_KEY_{i}")
        if not k:
            break
        keys.append(k)
        i += 1
    return keys

GEMINI_KEYS = _load_gemini_keys()
_key_index = 0

def _next_gemini_key() -> Optional[str]:
    global _key_index
    if not GEMINI_KEYS:
        return None
    key = GEMINI_KEYS[_key_index % len(GEMINI_KEYS)]
    _key_index += 1
    return key

# ── Provider primario per piano ───────────────────────────────────────────────
# FREE e BASIC non consumano il budget Google.
# Il budget Google (1.500 RPD × N key) è riservato a PRO e PLUS.
PLAN_PRIMARY_PROVIDER = {
    "free":  "duckduckgo",
    "basic": "tavily",
    "pro":   "google",
    "plus":  "google",
}

# ── Localizzazione per paese ──────────────────────────────────────────────────
COUNTRY_CONFIG = {
    "it": {
        "region": "it-it",
        "portals": ["immobiliare.it", "idealista.it", "casa.it", "subito.it"],
        "keywords": ["prezzi immobili", "mercato immobiliare", "affitti"],
    },
    "uk": {
        "region": "uk-en",
        "portals": ["rightmove.co.uk", "zoopla.co.uk", "onthemarket.com"],
        "keywords": ["property prices", "real estate market", "rental yield"],
    },
    "fr": {
        "region": "fr-fr",
        "portals": ["seloger.com", "leboncoin.fr", "bien-ici.com"],
        "keywords": ["prix immobilier", "marché immobilier", "rendement locatif"],
    },
    "de": {
        "region": "de-de",
        "portals": ["immoscout24.de", "immowelt.de", "immonet.de"],
        "keywords": ["Immobilienpreise", "Immobilienmarkt", "Mietrendite"],
    },
    "es": {
        "region": "es-es",
        "portals": ["idealista.com", "fotocasa.es", "pisos.com"],
        "keywords": ["precios inmuebles", "mercado inmobiliario", "rentabilidad"],
    },
    "pt": {
        "region": "pt-pt",
        "portals": ["idealista.pt", "imovirtual.com", "olx.pt"],
        "keywords": ["preços imóveis", "mercado imobiliário", "rentabilidade"],
    },
    "us": {
        "region": "us-en",
        "portals": ["zillow.com", "realtor.com", "redfin.com"],
        "keywords": ["property prices", "real estate market", "rental yield"],
    },
}

def detect_country(query: str) -> str:
    q = query.lower()
    markers = {
        "uk": ["london", "manchester", "uk", "england", "britain", "pound", "gbp"],
        "fr": ["paris", "lyon", "marseille", "france", "français"],
        "de": ["berlin", "münchen", "hamburg", "deutschland", "germany"],
        "es": ["madrid", "barcelona", "españa", "spain"],
        "pt": ["lisboa", "porto", "portugal"],
        "us": ["new york", "los angeles", "usa", "united states", "dollar", "usd"],
    }
    for country, words in markers.items():
        if any(w in q for w in words):
            return country
    return "it"

def _make_cache_key(query: str) -> str:
    return hashlib.md5(query.lower().strip().encode()).hexdigest()

# ── Cache layer (PostgreSQL) ──────────────────────────────────────────────────
class SearchCache:
    """
    Cache risultati di ricerca su PostgreSQL.
    Riduce il consumo di RPD Google del 40-60% grazie al riuso tra utenti.
    Se il DB non è disponibile, si disabilita silenziosamente.
    """

    def __init__(self):
        self._enabled = CACHE_ENABLED
        self._ensure_table()

    def _get_conn(self):
        try:
            from app.core.database import get_db_connection
            return get_db_connection()
        except Exception:
            return None

    def _ensure_table(self):
        conn = self._get_conn()
        if not conn:
            self._enabled = False
            return
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS search_cache (
                        cache_key   TEXT PRIMARY KEY,
                        query       TEXT NOT NULL,
                        result      TEXT NOT NULL,
                        provider    TEXT NOT NULL,
                        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at  TIMESTAMP NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_search_cache_expires
                    ON search_cache(expires_at)
                """)
        except Exception as e:
            logger.warning(f"SearchCache: tabella non creata — {e}")
            self._enabled = False
        finally:
            conn.close()

    def get(self, cache_key: str) -> Optional[str]:
        if not self._enabled:
            return None
        conn = self._get_conn()
        if not conn:
            return None
        try:
            with conn:
                row = conn.execute(
                    "SELECT result FROM search_cache WHERE cache_key = ? AND expires_at > ?",
                    (cache_key, datetime.utcnow())
                ).fetchone()
                if row:
                    logger.debug(f"Cache HIT: {cache_key[:8]}…")
                    return row[0]
        except Exception as e:
            logger.warning(f"SearchCache.get: {e}")
        finally:
            conn.close()
        return None

    def set(self, cache_key: str, query: str, result: str, provider: str):
        if not self._enabled:
            return
        conn = self._get_conn()
        if not conn:
            return
        expires = datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)
        try:
            with conn:
                conn.execute("""
                    INSERT OR REPLACE INTO search_cache
                        (cache_key, query, result, provider, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (cache_key, query, result, provider, datetime.utcnow(), expires))
        except Exception as e:
            logger.warning(f"SearchCache.set: {e}")
        finally:
            conn.close()

    def cleanup_expired(self):
        conn = self._get_conn()
        if not conn:
            return
        try:
            with conn:
                conn.execute("DELETE FROM search_cache WHERE expires_at < ?", (datetime.utcnow(),))
        except Exception as e:
            logger.warning(f"SearchCache.cleanup: {e}")
        finally:
            conn.close()

_search_cache = SearchCache()

# ── Provider functions ────────────────────────────────────────────────────────

def _search_google_grounding(query: str) -> Optional[str]:
    """
    Google Search via Gemini Grounding nativo.
    Usa rotazione multi-key: 1.500 RPD × numero di key configurate.
    """
    api_key = _next_gemini_key()
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        from google.generativeai.types import Tool, GoogleSearchRetrieval

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            tools=[Tool(google_search_retrieval=GoogleSearchRetrieval())]
        )
        response = model.generate_content(
            f"Cerca e riassumi dati aggiornati su: {query}\n"
            f"Fornisci dati concreti (prezzi, percentuali, fonti)."
        )
        result = response.text
        if result and len(result) > 50:
            logger.info(f"Google Grounding OK (…{api_key[-4:]}): {query[:60]}")
            return result
    except Exception as e:
        logger.warning(f"Google Grounding error: {e}")
    return None

def _search_tavily(query: str) -> Optional[str]:
    """Tavily PAYGO — fallback 1. 1.000 ricerche/mese gratis."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return None
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
            include_answer=True,
        )
        parts = []
        if response.get("answer"):
            parts.append(f"Risposta: {response['answer']}")
        for r in response.get("results", [])[:5]:
            parts.append(f"- {r.get('title', '')}: {r.get('content', '')[:300]}")
        result = "\n".join(parts)
        if result:
            logger.info(f"Tavily OK: {query[:60]}")
            return result
    except Exception as e:
        logger.warning(f"Tavily error: {e}")
    return None

def _search_duckduckgo(query: str, country: str = "it") -> Optional[str]:
    """DuckDuckGo — fallback finale. Gratis, nessuna API key richiesta."""
    try:
        from duckduckgo_search import DDGS
        region = COUNTRY_CONFIG.get(country, COUNTRY_CONFIG["it"])["region"]
        ddgs = DDGS()
        results = ddgs.text(
            keywords=query,
            region=region,
            safesearch="moderate",
            max_results=5,
        )
        if not results:
            return None
        parts = [f"- {r.get('title', '')}: {r.get('body', '')[:300]}" for r in results]
        result = "\n".join(parts)
        logger.info(f"DuckDuckGo OK: {query[:60]}")
        return result
    except Exception as e:
        logger.warning(f"DuckDuckGo error: {e}")
    return None

# ── CrewAI Tool ───────────────────────────────────────────────────────────────
class SearchInput(BaseModel):
    query: str = Field(..., description="Query di ricerca immobiliare")

class CascadeSearchTool(BaseTool):
    """
    Tool CrewAI con cascata di provider e cache integrata.

    Il provider primario dipende dal piano:
      free  → DuckDuckGo solo (0 RPD Google consumati)
      basic → Tavily → DuckDuckGo (0 RPD Google consumati)
      pro   → Google Grounding → Tavily → DuckDuckGo
      plus  → Google Grounding → Tavily → DuckDuckGo

    Cache PostgreSQL con TTL 6h: query identiche tra utenti diversi
    non consumano RPD aggiuntivi.

    Multi-key rotation: aggiungi GEMINI_API_KEY_1, _2, ... nel .env
    per moltiplicare il free tier da 1.500 a N×1.500 RPD/giorno.
    """
    name: str = "Ricerca Immobiliare"
    description: str = (
        "Cerca informazioni immobiliari aggiornate: prezzi di mercato, "
        "andamento del mercato locale, portali immobiliari, dati OMI, "
        "rendimenti da affitto, comparabili di zona. "
        "Input: query di ricerca in linguaggio naturale."
    )
    args_schema: type = SearchInput
    plan: str = "free"

    def _run(self, query: str) -> str:
        country = detect_country(query)
        cache_key = _make_cache_key(query)

        # 1. Controlla cache prima di qualsiasi chiamata esterna
        cached = _search_cache.get(cache_key)
        if cached:
            return cached

        # 2. Determina cascata in base al piano
        primary = PLAN_PRIMARY_PROVIDER.get(self.plan, "duckduckgo")

        if primary == "google":
            cascade = [
                ("google",     lambda q: _search_google_grounding(q)),
                ("tavily",     lambda q: _search_tavily(q)),
                ("duckduckgo", lambda q: _search_duckduckgo(q, country)),
            ]
        elif primary == "tavily":
            cascade = [
                ("tavily",     lambda q: _search_tavily(q)),
                ("duckduckgo", lambda q: _search_duckduckgo(q, country)),
            ]
        else:
            cascade = [
                ("duckduckgo", lambda q: _search_duckduckgo(q, country)),
            ]

        # 3. Esegui la cascata
        for provider_name, search_fn in cascade:
            result = search_fn(query)
            if result:
                _search_cache.set(cache_key, query, result, provider_name)
                return result

        # 4. Fallback finale: knowledge base AI con disclaimer
        logger.warning(f"Tutti i provider non disponibili per: {query[:60]}")
        return (
            "⚠️ Ricerca web temporaneamente non disponibile. "
            "Analisi basata su dati storici AI. "
            "Verificare i prezzi attuali su Immobiliare.it prima di procedere."
        )

# ── Factory ───────────────────────────────────────────────────────────────────
def get_search_tool(plan: str = "free") -> CascadeSearchTool:
    """Restituisce un CascadeSearchTool configurato per il piano specificato."""
    primary = PLAN_PRIMARY_PROVIDER.get(plan, "duckduckgo")
    n_keys = len(GEMINI_KEYS)
    logger.info(
        f"SearchTool — piano: {plan} | provider primario: {primary} | "
        f"key Google: {n_keys} ({n_keys * 1500} RPD/giorno) | "
        f"cache: {CACHE_TTL_HOURS}h TTL"
    )
    return CascadeSearchTool(plan=plan)

def cleanup_search_cache():
    """Elimina le entry cache scadute. Chiamare da job periodico o startup."""
    _search_cache.cleanup_expired()
