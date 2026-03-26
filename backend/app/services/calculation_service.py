# backend/app/services/calculation_service.py
#
# SPRINT 5 — Calcolo ROI con CrewAI e Output JSON Strutturato.
# Accetta N immobili (max 5) + investment_goal.
# L'ultimo agente (Comparator) restituisce un JSON rigoroso per popolare
# le Card comparative nel frontend.

import json
import logging
import re
import time
from typing import Optional

from crewai import Agent, Task, Crew, Process

from app.agents.llm_factory import (
    get_llm, get_fallback_llm, should_fallback, get_search_mode
)
from app.agents.search_tool import get_search_tool

logger = logging.getLogger(__name__)


# ── Utilità lingua ────────────────────────────────────────────────────────────

def _build_lang_instruction(language: str) -> str:
    lang_names = {
        "it": "Italian",  "en": "English",   "fr": "French",
        "de": "German",   "es": "Spanish",   "pt": "Portuguese",
    }
    lang_name = lang_names.get(language, "Italian")
    return (
        f"CRITICAL LANGUAGE RULE: You MUST respond EXCLUSIVELY in {lang_name}. "
        f"Every single word of your response must be in {lang_name}. "
        f"Do NOT use any other language.\n\n"
    )


# ── Helper per parsing JSON sicuro ────────────────────────────────────────────

def _parse_json_safe(text: str) -> dict:
    """Rimuove formattazione markdown e parsa il JSON in modo sicuro."""
    try:
        clean_text = re.sub(r"^```json\n?", "", text.strip(), flags=re.IGNORECASE)
        clean_text = re.sub(r"^```\n?", "", clean_text)
        clean_text = re.sub(r"```$", "", clean_text.strip())
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        logger.error(f"[calcola_roi] Errore parsing JSON: {e}\nTesto: {text[:200]}...")
        return {}


# ── Template agenti ───────────────────────────────────────────────────────────

_TEMPLATE_PROPERTY_VALUATOR = """
You are an expert real estate appraiser.
You ALWAYS search for real data on the web with cited sources.

For each property you must find:
- Average sale price in local currency/sqm for the specific zone
- Average rental rate in local currency/sqm/month for the zone
- Average renovation costs from local estimators for that city/region

FUNDAMENTAL RULE: always cite source and date for every number.
If data is not available on the web, state 'data not available' — do not invent values.
Write everything in plain text with bullet lists.
"""

_TEMPLATE_FINANCIAL_ANALYST = """
You are a financial analyst specialized in real estate investment.
You apply precise formulas and compare properties in a clear way.

Search the current fixed mortgage rate for the target country from a reputable local source and cite it.

For each property calculate the metrics relevant to the investment goal.
Use the real data found by the Property Valuator.

Present numbers as bullet lists per property. Do NOT use markdown tables.
"""

# FIX: Il Comparator ora deve restituire SOLO JSON
_TEMPLATE_COMPARATOR = """
You are a senior real estate investment advisor.
Your task is to synthesize all analyses into a clear final recommendation.

You MUST respond ONLY with a valid JSON object strictly following this structure. 
Do not add markdown outside the JSON.

{{
  "summary": "1-2 sentences direct answer with the final verdict.",
  "market_analysis": "Brief summary of the market conditions found.",
  "financial_analysis": "Brief summary of the financial calculations.",
  "recommended_scenario": "Detailed explanation of why the winning property was chosen.",
  "results": [
    {{
      "label": "Property Name",
      "address": "Property Address",
      "purchase_price": 250000,
      "price_per_sqm": 2500,
      "best_scenario": "Brief description of the strategy for this property",
      "total_investment_mid": 300000,
      "net_roi_mid": 12.5,
      "payback_mid": 8.5,
      "risk_summary": "Brief summary of risks",
      "rank": 1,
      "scenarios": [
        {{
          "name": "Strategy Name (e.g., Flipping)",
          "renovation_cost": 40000,
          "duration_months": 6,
          "estimated_value_after": 350000,
          "estimated_rent_after": 0,
          "roi_percent": 12.5,
          "payback_years": 0,
          "risk_level": "Medium",
          "description": "Detailed description of this scenario"
        }}
      ]
    }}
  ]
}}

Ensure the "results" array contains exactly one object for each property analyzed.
Rank them from 1 (best) to N (worst).
"""

# ── Istruzioni finanziarie specifiche per obiettivo ───────────────────────────

_GOAL_CONTEXT = {
    "flipping": {
        "label": "Flipping — Post-renovation resale",
        "horizon": "12-18 months",
        "financial_instructions": """
For each property calculate the FLIPPING MARGIN:
1. Total purchase cost = asking price + transaction costs (estimate 5-10%)
2. Renovation cost = budget provided (or estimate)
3. Total investment = purchase cost + renovation
4. Estimated resale price = renovated local-currency/sqm * sqm
5. Gross margin = estimated resale - total investment
6. Margin % = (gross margin / total investment) * 100
7. Annualized ROI = margin % / 1.5 * 100 (18-month base)
""",
    },
    "affitto_lungo": {
        "label": "Long-term rental",
        "horizon": "10-15 years",
        "financial_instructions": """
For each property calculate the RENTAL YIELD PARAMETERS:
1. Estimated monthly rent = local-currency/sqm/month * sqm
2. Gross annual income = monthly rent * 12
3. Net annual income = gross - tax (estimate 21%) - charges
4. Down payment = price * pct
5. Mortgage = price - down payment
6. Net monthly cash-flow = (net annual income / 12) - mortgage payment
7. Gross yield % = (gross annual / price) * 100
8. Net yield on own capital % = (net annual / down payment) * 100
9. Payback years = price / net annual income
""",
    },
    "affitto_breve": {
        "label": "Short-term rental (Airbnb/Booking)",
        "horizon": "3-5 years",
        "financial_instructions": """
For each property calculate SHORT-TERM RENTAL PARAMETERS:
1. Average nightly rate in the zone
2. Zone occupancy rate %
3. Gross annual revenue = nights * nightly rate
4. Management costs = gross * 0.28
5. Net annual income = gross - management - tax
6. Net monthly cash-flow = (net annual / 12) - mortgage payment
7. Gross yield % = (gross annual / price) * 100
8. Net yield on own capital % = (net annual / down payment) * 100
9. Payback years = price / net annual income
""",
    },
    "prima_casa": {
        "label": "Primary residence with appreciation",
        "horizon": "5-10 years",
        "financial_instructions": """
For each property calculate PRIMARY RESIDENCE PARAMETERS:
1. Purchase price + transaction costs (estimate 3-8%)
2. Down payment + mortgage + monthly payment
3. Affordability: monthly payment / average local income
4. Estimated value in 5 years = price * (1 + YoY growth)^5
5. Potential appreciation = 5y value - purchase price
""",
    },
}


# ── Funzione pubblica principale ──────────────────────────────────────────────

def run_compare_roi(
    properties: list[dict],
    investment_goal: str = "affitto_lungo",
    plan: str = "free",
    user_id: Optional[int] = None,
    language: str = "it",
    task_callback=None,
) -> dict:
    if not properties:
        raise ValueError("Almeno un immobile e richiesto.")
    if len(properties) > 5:
        properties = properties[:5]

    logger.info(
        f"[calcola_roi] START — user={user_id}, plan={plan}, "
        f"goal={investment_goal}, lang={language}, n_properties={len(properties)}"
    )

    kwargs = dict(
        properties=properties,
        investment_goal=investment_goal,
        plan=plan,
        user_id=user_id,
        language=language,
        task_callback=task_callback,
    )

    RETRY_WAITS_SECONDS = [0, 60, 120]
    last_gemini_exc: Exception | None = None

    for attempt, wait in enumerate(RETRY_WAITS_SECONDS):
        if wait > 0:
            logger.warning(
                f"[calcola_roi] Quota Gemini — attesa {wait}s prima tentativo "
                f"{attempt + 1}/{len(RETRY_WAITS_SECONDS)}"
            )
            time.sleep(wait)

        try:
            return _run_roi_crew(llm_type="gemini", **kwargs)
        except Exception as e:
            if should_fallback(e):
                last_gemini_exc = e
                logger.warning(
                    f"[calcola_roi] Gemini tentativo {attempt + 1}/{len(RETRY_WAITS_SECONDS)} "
                    f"fallito ({type(e).__name__}): {str(e)[:100]}"
                )
            else:
                raise

    logger.warning(f"[calcola_roi] Gemini esaurito dopo {len(RETRY_WAITS_SECONDS)} tentativi.")
    fallback_llm = get_fallback_llm(plan=plan)
    if fallback_llm is None:
        raise RuntimeError(
            "Gemini non disponibile dopo 3 tentativi e ANTHROPIC_API_KEY non configurata. "
            f"Ultimo errore Gemini: {type(last_gemini_exc).__name__}: {str(last_gemini_exc)[:200]}"
        )

    logger.info(f"[calcola_roi] Avvio con Claude fallback — piano={plan}")
    return _run_roi_crew(llm_type="claude", forced_llm=fallback_llm, **kwargs)


# ── Crew interno ──────────────────────────────────────────────────────────────

def _run_roi_crew(
    properties: list[dict],
    investment_goal: str,
    plan: str,
    user_id: Optional[int],
    llm_type: str,
    forced_llm=None,
    language: str = "it",
    task_callback=None,
) -> dict:
    llm         = forced_llm or get_llm(plan=plan)
    search_mode = get_search_mode(llm_type)
    search_tool = get_search_tool(plan=plan, mode=search_mode)

    goal_info    = _GOAL_CONTEXT.get(investment_goal, _GOAL_CONTEXT["affitto_lungo"])
    goal_label   = goal_info["label"]
    goal_horizon = goal_info["horizon"]
    goal_fin_inst = goal_info["financial_instructions"]
    props_text   = _format_properties(properties)
    lang_instr   = _build_lang_instruction(language)

    property_valuator = Agent(
        role="Property Valuator",
        goal="Trovare prezzi reali di vendita e affitto per ogni zona.",
        backstory=_TEMPLATE_PROPERTY_VALUATOR,
        llm=llm,
        tools=[search_tool] if search_tool else [],
        verbose=True,
        allow_delegation=False,
        max_iter=4,
    )

    financial_analyst = Agent(
        role="Financial Analyst",
        goal=f"Calcolare metriche finanziarie per '{goal_label}'.",
        backstory=_TEMPLATE_FINANCIAL_ANALYST,
        llm=llm,
        tools=[search_tool] if search_tool else [],
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )

    comparator = Agent(
        role="Investment Comparator",
        goal="Confrontare gli immobili e restituire un JSON strutturato.",
        backstory=_TEMPLATE_COMPARATOR,
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )

    task_valuation = Task(
        description=(
            f"{lang_instr}"
            f"OBIETTIVO INVESTIMENTO: {goal_label} (orizzonte {goal_horizon})\n\n"
            f"IMMOBILI DA ANALIZZARE:\n{props_text}\n\n"
            f"Per ogni immobile cerca prezzi vendita e affitto."
        ),
        expected_output="Prezzi mercato con fonti. Testo puro.",
        agent=property_valuator,
        callback=task_callback,
    )

    task_financials = Task(
        description=(
            f"{lang_instr}"
            f"Calcola le metriche finanziarie per ogni immobile.\n\n"
            f"OBIETTIVO: {goal_label}\n\n"
            f"IMMOBILI:\n{props_text}\n\n"
            f"ISTRUZIONI DI CALCOLO:\n{goal_fin_inst}\n\n"
        ),
        expected_output="Calcoli finanziari completi. Testo puro con elenchi.",
        agent=financial_analyst,
        context=[task_valuation],
        callback=task_callback,
    )

    task_comparison = Task(
        description=(
            f"{lang_instr}"
            f"Sintetizza e produci la raccomandazione finale in formato JSON.\n\n"
            f"OBIETTIVO: {goal_label} (orizzonte {goal_horizon})\n\n"
            f"IMMOBILI:\n{props_text}\n\n"
        ),
        expected_output="Un oggetto JSON valido con la struttura richiesta.",
        agent=comparator,
        context=[task_valuation, task_financials],
        callback=task_callback,
    )

    crew = Crew(
        agents=[property_valuator, financial_analyst, comparator],
        tasks=[task_valuation, task_financials, task_comparison],
        process=Process.sequential,
        verbose=True,
    )

    logger.info(f"[calcola_roi] CrewAI kickoff (llm_type={llm_type})...")
    result = crew.kickoff()
    logger.info(f"[calcola_roi] CrewAI completato (llm_type={llm_type})")

    task_outputs = result.tasks_output if hasattr(result, "tasks_output") else []

    def get_output(idx: int) -> str:
        try:
            return str(task_outputs[idx].raw) if idx < len(task_outputs) else ""
        except Exception:
            return ""

    # FIX: Estraiamo il JSON dall'ultimo task
    final_output_text = get_output(2)
    parsed_data = _parse_json_safe(final_output_text)

    # Fallback se il JSON è vuoto o malformato
    if not parsed_data:
        logger.warning("[calcola_roi] Fallback: JSON non valido, uso testo grezzo.")
        from app.utils.text_cleaner import clean_agent_output
        clean_text = clean_agent_output(final_output_text)
        parsed_data = {
            "summary": "Analisi completata.",
            "market_analysis": "Dati non strutturati correttamente.",
            "financial_analysis": clean_text,
            "recommended_scenario": "Vedi testo sopra.",
            "results": []
        }

    return {
        "summary":               parsed_data.get("summary", ""),
        "investment_goal":       investment_goal,
        "investment_goal_label": goal_label,
        "properties_count":      len(properties),
        "market_analysis":       parsed_data.get("market_analysis", ""),
        "financial_analysis":    parsed_data.get("financial_analysis", ""),
        "recommended_scenario":  parsed_data.get("recommended_scenario", ""),
        "results":               parsed_data.get("results", []), # FIX: Passiamo l'array results
        "scenarios":             parsed_data.get("results", []), # Manteniamo per compatibilità
        "remaining_usage":       None,
        "llm_used":              llm_type,
    }


# ── Helper ────────────────────────────────────────────────────────────────────

def _format_properties(properties: list[dict]) -> str:
    parts = []
    for i, p in enumerate(properties, 1):
        lines = [f"Immobile {i}: {p.get('name', '')}"]
        if p.get("address"):
            lines.append(f"  Indirizzo:            {p['address']}")
        if p.get("price"):
            lines.append(f"  Prezzo richiesto:     {p['price']:,.0f} euro")
        if p.get("size_sqm"):
            lines.append(f"  Superficie:           {p['size_sqm']} mq")
        if p.get("price") and p.get("size_sqm"):
            lines.append(f"  euro/mq:              {p['price'] / p['size_sqm']:,.0f}")
        if p.get("rooms"):
            lines.append(f"  Locali:               {p['rooms']}")
        if p.get("condition"):
            lines.append(f"  Condizioni:           {p['condition']}")
        if p.get("floor"):
            lines.append(f"  Piano:                {p['floor']}")
        if p.get("elevator") is not None:
            lines.append(f"  Ascensore:            {'Si' if p['elevator'] else 'No'}")
        if p.get("renovation_budget"):
            lines.append(f"  Budget ristrutturaz.: {p['renovation_budget']:,.0f} euro")
        if p.get("mortgage_rate"):
            lines.append(f"  Tasso mutuo indicat.: {p['mortgage_rate']}%")
        if p.get("mortgage_years"):
            lines.append(f"  Durata mutuo:         {p['mortgage_years']} anni")
        if p.get("down_payment_pct"):
            lines.append(f"  Acconto:              {p['down_payment_pct']}%")
        if p.get("current_rent"):
            lines.append(f"  Affitto attuale:      {p['current_rent']:,.0f} euro/mese")
        if p.get("notes"):
            lines.append(f"  Note:                 {p['notes']}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)