# backend/app/services/market_analysis_service.py
#
# Pipeline deterministica 3-step — sostituisce deep_research_service.py
# per la feature Deep Research / Analisi di Mercato.

import concurrent.futures
import json
import logging
import os
import time
import re
from typing import Optional, Callable

from google import genai
from google.genai import types
import litellm

from app.config import settings
from app.agents.search_tool import get_search_results
from app.utils.text_cleaner import clean_agent_output
# FIX: Importiamo get_current_gemini_key per la rotazione delle chiavi
from app.agents.llm_factory import get_fallback_llm, get_search_mode, get_current_gemini_key

logger = logging.getLogger(__name__)

# ── Lingue supportate ─────────────────────────────────────────────────────────

_LANG_NAMES = {
    "it": "Italian",  "en": "English",   "es": "Spanish",
    "fr": "French",   "de": "German",    "pt": "Portuguese",
    "nl": "Dutch",    "pl": "Polish",    "ru": "Russian",
    "zh": "Chinese",  "ja": "Japanese",  "ar": "Arabic",
}

# ── Client Gemini (lazy, singleton) ──────────────────────────────────────────

_gemini_client: Optional[genai.Client] = None

def _get_gemini_client() -> genai.Client:
    """
    Restituisce il client Gemini usando la rotazione delle chiavi.
    """
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    
    # FIX REALE: Usa la rotazione delle chiavi invece di leggere direttamente dal .env
    api_key = get_current_gemini_key()
    _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _model_for_plan(plan: str, step: str = "synthesis") -> str:
    """
    Seleziona il modello in base al piano e allo step.
    - Step 1 (keyword extraction): sempre Flash — è una chiamata veloce
    - Step 3 (synthesis): Pro per PLUS, Flash per gli altri
    """
    if step == "keyword":
        return "gemini-2.5-flash"
    
    # Se c'è un override nel .env, lo usiamo (ma solo per la sintesi)
    model_override = os.environ.get("GEMINI_MODEL_OVERRIDE", "").strip()
    if model_override:
        return model_override.replace("gemini/", "")
        
    return "gemini-2.5-pro" if plan in ("plus", "pro") else "gemini-2.5-flash"


# ── Helper per parsing JSON sicuro ────────────────────────────────────────────

def _parse_json_safe(text: str) -> dict:
    """Rimuove formattazione markdown e parsa il JSON in modo sicuro."""
    try:
        clean_text = re.sub(r"^```json\n?", "", text.strip(), flags=re.IGNORECASE)
        clean_text = re.sub(r"^```\n?", "", clean_text)
        clean_text = re.sub(r"```$", "", clean_text.strip())
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        logger.error(f"[market_analysis] Errore parsing JSON: {e}\nTesto: {text[:200]}...")
        return {
            "summary": "Analisi completata con formattazione parziale.",
            "market_overview": text,
            "properties_analysis": [],
            "risks_opportunities": "Dati non strutturati correttamente.",
            "investment_recommendation": "Si prega di riprovare formulando la richiesta in modo più specifico."
        }


# ── STEP 1: Estrazione keyword di ricerca ─────────────────────────────────────

_KEYWORD_PROMPT = """You are a real estate research assistant.
Extract 3 specific Google search queries from this investor request.
Each query must target a specific data point needed for investment analysis.

INVESTOR REQUEST:
{query}

Generate exactly 3 search queries. Cover:
1. Current sale prices per sqm in the specific zone/city (with year)
2. Current rental rates in the zone (monthly, per sqm)
3. YoY price trends and market forecasts for the zone

Output ONLY a valid JSON array of strings. No explanation, no markdown.
Example: ["prezzi vendita mq Napoli centro storico 2026", "affitti brevi Napoli normative 2026"]
"""

def _extract_keywords(query: str, plan: str) -> list[str]:
    """
    Step 1: chiede a Gemini Flash di pianificare le ricerche.
    Tempo stimato: 2-4 secondi.
    """
    try:
        client = _get_gemini_client()
        response = client.models.generate_content(
            model=_model_for_plan(plan, step="keyword"),
            contents=_KEYWORD_PROMPT.format(query=query[:800]),
            config=types.GenerateContentConfig(
                max_output_tokens=512,
                temperature=0.1,
                response_mime_type="application/json", # FIX: Forza output JSON nativo
            ),
        )
        text = response.text.strip()
        keywords = json.loads(text)
        if isinstance(keywords, list) and len(keywords) >= 1:
            logger.info(f"[market_analysis] Keywords: {keywords}")
            return keywords[:3]
    except Exception as e:
        logger.warning(f"[market_analysis] Keyword extraction fallita ({e}), uso fallback")

    # Fallback deterministico: costruisce query dalla prima parte della query
    city_hint = query[:80].split("\n")[0]
    return [
        f"prezzi immobili {city_hint} 2026",
        f"affitti {city_hint} 2026 euro mq",
        f"mercato immobiliare {city_hint} trend previsioni",
    ]


# ── STEP 2: Ricerche web parallele ────────────────────────────────────────────

def _run_parallel_searches(keywords: list[str]) -> dict[str, str]:
    """
    Step 2: esegue le ricerche in parallelo via ThreadPoolExecutor.
    Usa get_search_results() da search_tool.py.
    """
    results: dict[str, str] = {}

    def _search_one(keyword: str) -> tuple[str, str]:
        try:
            result = get_search_results(keyword, mode="gemini")
            return keyword, result
        except Exception as e:
            logger.warning(f"[market_analysis] Search fallita '{keyword[:40]}': {e}")
            return keyword, f"[Dati non disponibili per: {keyword}]"

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_search_one, kw): kw for kw in keywords}
        for future in concurrent.futures.as_completed(futures, timeout=60):
            try:
                keyword, result = future.result()
                results[keyword] = result
            except Exception as e:
                logger.error(f"[market_analysis] Errore future: {e}")

    logger.info(f"[market_analysis] Step 2: {len(results)}/{len(keywords)} ricerche completate")
    return results


# ── STEP 3: Sintesi con LLM ───────────────────────────────────────────────────

_SYNTHESIS_PROMPT = """You are a Senior Real Estate Investment Advisor.
Based EXCLUSIVELY on the web research data provided below, write a comprehensive investment analysis.

LANGUAGE RULE: Respond EXCLUSIVELY in {lang_name}. Every single word must be in {lang_name}.

CRITICAL TONE RULE: DO NOT use conversational filler. DO NOT say "Here is the analysis" or "Certainly". 
Start immediately with the hard data. Be clinical, professional, and objective.

USER REQUEST:
{query}

WEB RESEARCH DATA:
{search_results}

You MUST respond ONLY with a valid JSON object strictly following this structure. 
Do not add markdown outside the JSON.

{{
  "summary": "1-2 sentences direct answer to the user's request. No greetings.",
  "market_overview": "Detailed market analysis, prices per sqm, and trends found in the data.",
  "properties_analysis": [
    {{
      "title": "Name of the area or simulated property profile",
      "estimated_price_range": "e.g., 150.000€ - 180.000€",
      "size_range": "e.g., 70-90 mq",
      "zone": "Specific neighborhood",
      "price_per_sqm": 2500,
      "condition": "e.g., To renovate",
      "opportunity_score": 8.5,
      "roi_potential": "e.g., 6.5% Gross Yield",
      "renovation_estimate": "e.g., 30.000€",
      "key_pros": ["Pro 1", "Pro 2"],
      "key_cons": ["Con 1", "Con 2"],
      "why_interesting": "Brief explanation of why this fits the user's query."
    }}
  ],
  "risks_opportunities": "Detailed bullet points of risks (e.g., regulations, market shifts) and opportunities.",
  "investment_recommendation": "Final verdict: BUY / EVALUATE WITH CAUTION / AVOID, with numerical justification."
}}

Generate 1 to 3 items inside the "properties_analysis" array based on the data.
"""

def _synthesize(
    query: str,
    search_results: dict[str, str],
    language: str,
    plan: str,
) -> str:
    """
    Step 3: chiama Gemini con tutti i dati raccolti e un prompt rigido.
    """
    lang_name = _LANG_NAMES.get(language, "Italian")

    # Assembla il testo delle ricerche con limite token
    search_text_parts = []
    total_chars = 0
    max_chars = 12000

    for i, (keyword, result) in enumerate(search_results.items(), 1):
        section = f"\n--- RICERCA {i}: {keyword} ---\n{result}\n"
        if total_chars + len(section) > max_chars:
            search_text_parts.append("\n...[ricerche troncate per limiti di spazio]")
            break
        search_text_parts.append(section)
        total_chars += len(section)

    search_text = "".join(search_text_parts)

    prompt = _SYNTHESIS_PROMPT.format(
        lang_name=lang_name,
        query=query[:600],
        search_results=search_text,
    )

    client = _get_gemini_client()
    model = _model_for_plan(plan, step="synthesis")

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=8192,
            temperature=0.2,
            response_mime_type="application/json", # FIX: Forza output JSON nativo per lo Step 3
        ),
    )

    if not response.text:
        raise ValueError("Gemini ha restituito risposta vuota in Step 3")

    logger.info(f"[market_analysis] Step 3 completato — {len(response.text)} chars, modello={model}")
    return response.text


def _synthesize_with_claude_fallback(
    query: str,
    search_results: dict[str, str],
    language: str,
    plan: str,
) -> str:
    """
    Fallback Claude per Step 3 se Gemini è in quota.
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY non configurata — fallback Claude non disponibile")

    lang_name = _LANG_NAMES.get(language, "Italian")

    search_text = "\n".join(
        f"--- {kw} ---\n{res}" for kw, res in search_results.items()
    )[:10000]

    prompt = _SYNTHESIS_PROMPT.format(
        lang_name=lang_name,
        query=query[:600],
        search_results=search_text,
    )

    model = "claude-sonnet-4-6" if plan == "plus" else "claude-haiku-4-5-20251001"
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text
    logger.info(f"[market_analysis] Claude fallback completato — {len(text)} chars")
    return text


# ── Funzione pubblica principale ──────────────────────────────────────────────

def run_market_analysis(
    query: str,
    plan: str = "free",
    user_id: Optional[int] = None,
    language: str = "it",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> dict:
    """
    Pipeline deterministica 3-step per l'analisi di mercato immobiliare.
    """
    TOTAL_STEPS = 3
    logger.info(
        f"[market_analysis] START — user={user_id}, plan={plan}, "
        f"lang={language}, query='{query[:60]}'"
    )

    # ── STEP 1: Keyword extraction ───────────────────────────────────────────
    if progress_callback:
        progress_callback(1, TOTAL_STEPS, "Pianificazione ricerche di mercato...")

    keywords = _extract_keywords(query, plan)

    # ── STEP 2: Parallel searches ────────────────────────────────────────────
    if progress_callback:
        progress_callback(2, TOTAL_STEPS, "Ricerca dati in tempo reale dal web...")

    search_results = _run_parallel_searches(keywords)

    if not search_results:
        logger.error("[market_analysis] Nessun risultato di ricerca ottenuto")
        raise RuntimeError(
            "Le ricerche web non hanno restituito dati. "
            "Verifica la GEMINI_API_KEY e la connessione internet."
        )

    # ── STEP 3: Synthesis con retry su 429/503 ───────────────────────────────
    if progress_callback:
        progress_callback(3, TOTAL_STEPS, "Generazione report di investimento...")

    synthesis_text: Optional[str] = None
    last_exc: Optional[Exception] = None
    RETRY_WAITS = [0, 30, 60]  

    for attempt, wait in enumerate(RETRY_WAITS):
        if wait > 0:
            logger.warning(
                f"[market_analysis] Quota Gemini — attesa {wait}s "
                f"(tentativo {attempt + 1}/{len(RETRY_WAITS)})"
            )
            time.sleep(wait)
        try:
            synthesis_text = _synthesize(query, search_results, language, plan)
            break
        except Exception as e:
            last_exc = e
            exc_msg = str(e).lower()
            # FIX: Cattura robusta di TUTTI gli errori API (incluso il 503 del nuovo SDK)
            is_api_error = any(kw in exc_msg for kw in [
                "429", "503", "500", "502", "504", "quota", "rate limit", 
                "resource exhausted", "unavailable", "overloaded"
            ])
            if is_api_error:
                logger.warning(
                    f"[market_analysis] Errore API Google al tentativo {attempt + 1}: {str(e)[:120]}"
                )
            else:
                logger.error(f"[market_analysis] Errore non recuperabile: {e}")
                raise

    # Fallback Claude se Gemini esaurito
    if synthesis_text is None:
        logger.warning("[market_analysis] Gemini esaurito dopo 3 tentativi. Provo Claude.")
        try:
            synthesis_text = _synthesize_with_claude_fallback(
                query, search_results, language, plan
            )
        except Exception as claude_exc:
            raise RuntimeError(
                f"Tutti i provider LLM non disponibili.\n"
                f"Gemini: {last_exc}\n"
                f"Claude: {claude_exc}\n"
                "Aggiungi ANTHROPIC_API_KEY al .env per abilitare il fallback."
            )

    # ── Output strutturato ────────────────────────────────────────────────────
    # FIX: Parsiamo il JSON in modo sicuro
    final_report_data = _parse_json_safe(synthesis_text)

    logger.info(f"[market_analysis] COMPLETED — {len(synthesis_text)} chars totali")

    return {
        "summary":                   final_report_data.get("summary", "Analisi completata."),
        "market_overview":           final_report_data.get("market_overview", "Dati di mercato non disponibili."),
        "investment_recommendation": final_report_data.get("investment_recommendation", "Valutare con attenzione."),
        "risks_opportunities":       final_report_data.get("risks_opportunities", "Nessun rischio specifico evidenziato."),
        "properties_analysis":       final_report_data.get("properties_analysis", []),
        "remaining_usage":           None,
        "llm_used":                  "gemini" if last_exc is None else "claude",
        "pipeline":                  "deterministic_v1",
        "keywords_used":             keywords,
        "searches_count":            len(search_results),
    }