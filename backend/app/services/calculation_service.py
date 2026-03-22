# backend/app/services/calculation_service.py
#
# SPRINT 3 — Riscrittura completa.
# Accetta N immobili (max 5) + investment_goal invece di un singolo immobile.
# Output testo puro, nessuna tabella markdown.
#
# investment_goal valori:
#   "flipping"       — vendita post-ristrutturazione entro 12-18 mesi
#   "affitto_lungo"  — affitto residenziale a lungo termine
#   "affitto_breve"  — affitto breve Airbnb/Booking
#   "prima_casa"     — acquisto prima casa con valorizzazione

import logging
from typing import Optional

from crewai import Agent, Task, Crew, Process

from app.agents.llm_factory import (
    get_llm, get_fallback_llm, should_fallback, get_search_mode
)
from app.agents.search_tool import get_search_tool

logger = logging.getLogger(__name__)


# ── Utilità lingua ────────────────────────────────────────────────────────────

def _build_lang_instruction(language: str) -> str:
    """
    Istruzione lingua da iniettare in testa a ogni task.
    Il modello risponderà ESCLUSIVAMENTE nella lingua indicata.
    """
    lang_names = {
        "it": "Italian",  "en": "English",   "fr": "French",
        "de": "German",   "es": "Spanish",   "pt": "Portuguese",
        "nl": "Dutch",    "pl": "Polish",    "ru": "Russian",
        "zh": "Chinese",  "ja": "Japanese",  "ar": "Arabic",
    }
    lang_name = lang_names.get(language, "English")
    return (
        f"CRITICAL LANGUAGE RULE: You MUST respond EXCLUSIVELY in {lang_name} "
        f"(language code: {language}). "
        f"Every single word of your response must be in {lang_name}. "
        f"Do NOT use any other language regardless of what language "
        f"your instructions are written in. "
        f"The user's query is in {lang_name} — match that language exactly.\n\n"
    )


# ── Template agenti ───────────────────────────────────────────────────────────

_TEMPLATE_PROPERTY_VALUATOR = """
You are an expert real estate appraiser with 15 years of global investment valuation experience.
You ALWAYS search for real data on the web with cited sources.

For each property, search on the leading local portals for the target country.
Examples: Zillow/Realtor (USA), Rightmove/Zoopla (UK), Idealista (ES/IT/PT),
SeLoger (FR), ImmobilienScout24 (DE), Domain (AU), PropertyFinder (UAE), etc.

For each property you must find:
- Average sale price in local currency/sqm for the specific zone (not the city average)
- Average rental rate in local currency/sqm/month for the zone
- Prices of comparable renovated properties in the zone (if applicable)
- Average renovation costs from local estimators for that city/region

FUNDAMENTAL RULE: always cite source and date for every number.
If data is not available on the web, state 'data not available' — do not invent values.
Do NOT use markdown tables. Write everything in plain text with bullet lists.
"""

_TEMPLATE_FINANCIAL_ANALYST = """
You are a financial analyst specialized in global real estate investment.
You apply precise formulas and compare properties in a clear way.

MORTGAGE PAYMENT FORMULA (when applicable):
Monthly payment = P * [i(1+i)^n] / [(1+i)^n - 1]
where P = principal, i = monthly rate (annual rate / 12), n = number of months

Search the current fixed mortgage rate for the target country from a reputable local source
(e.g. a central bank, bank comparison site, or financial news) and cite it.

For each property calculate the metrics relevant to the investment goal.
Use the real data found by the Property Valuator.

Do NOT use markdown tables with dashes and pipes.
Present numbers as bullet lists per property, for example:

  Property 1 - 10 Main Street, Manchester
  - Purchase price: 250,000 GBP
  - Renovation budget: 40,000 GBP
  - Transaction costs (stamp duty + agency + legal fees ~5-8%): 18,000 GBP
  - Total investment: 308,000 GBP
  - Estimated resale value: 345,000 GBP
  - Gross profit margin: 37,000 GBP
  - Margin %: 12.0%
  - Score: 74/100 (breakdown: market deviation 80/100, margin 68/100, liquidity 72/100, risk 76/100)
"""

_TEMPLATE_COMPARATOR = """
You are a senior real estate investment advisor.
You produce recommendations with precise numbers and concrete justifications.

Your task is to synthesize all analyses into a clear final recommendation.

MANDATORY OUTPUT STRUCTURE (plain text, no markdown tables):

1. DIRECT ANSWER (2-3 sentences with key numbers)

2. PROPERTY COMPARISON
   For each property: name, key metric, score, 1 pro and 1 con.

3. RANKING (best to worst)
   With numerical justification for each position.

4. RECOMMENDED PROPERTY
   Name, detailed strategy, key numbers, time horizon.

5. CRITICAL WARNINGS (2-3 points)
   The most important things to verify before purchasing.

6. VERDICT: BUY / EVALUATE WITH CAUTION / AVOID
   With 3 supporting numbers and 2-line justification.

NEVER use markdown tables with | and ----.
Use only plain text, bullet lists, and numbers.
"""

# ── Istruzioni finanziarie specifiche per obiettivo ───────────────────────────

_GOAL_CONTEXT = {
    "flipping": {
        "label": "Flipping — Post-renovation resale",
        "horizon": "12-18 months",
        "financial_instructions": """
For each property calculate the FLIPPING MARGIN:

1. Total purchase cost = asking price + transaction costs
   (taxes + agency + legal/notary fees — use actual local rates
    or estimate 5-10% if local data is unavailable)
2. Renovation cost = budget provided (or estimate from local sources if not provided)
3. Total investment = purchase cost + renovation
4. Estimated resale price = renovated local-currency/sqm * sqm
5. Gross margin = estimated resale - total investment
6. Margin % = (gross margin / total investment) * 100
7. Annualized ROI = margin % / 1.5 * 100 (18-month base)
8. Break-even price = resale value - renovation - transaction costs

Score 0-100 weighted on:
- Purchase price deviation from market (25%): further below = higher score
- Flipping margin % (35%): target 20%+ = high score
- Zone liquidity (25%): estimated from local market activity
- Construction risk (15%): property condition and renovation complexity

Do NOT calculate rental yield or monthly cash-flow for this goal.
""",
    },
    "affitto_lungo": {
        "label": "Long-term rental",
        "horizon": "10-15 years",
        "financial_instructions": """
For each property calculate the RENTAL YIELD PARAMETERS:

1. Estimated monthly rent = local-currency/sqm/month * sqm (or provided rent)
2. Gross annual income = monthly rent * 12
3. Local rental income tax = gross income * local_tax_rate
   (search the applicable rate for the country; common range: 15-30%)
4. Annual service/maintenance charges = actual figure or estimate 1% of value/year
5. Net annual income = gross - tax - charges
6. Down payment (% provided or default 20%) = price * pct
7. Mortgage = price - down payment
8. Search current fixed mortgage rate from a local source and cite it
9. Monthly mortgage payment = calculate with exact formula
10. Net monthly cash-flow = (net annual income / 12) - mortgage payment
11. Gross yield % = (gross annual / price) * 100
12. Net yield on own capital % = (net annual / down payment) * 100
13. Payback years = price / net annual income

Score 0-100 weighted on:
- Gross yield % (30%): target 6%+ = high score
- Monthly cash-flow (30%): positive = high score
- Price deviation from market (20%)
- Rental trend in zone (20%)
""",
    },
    "affitto_breve": {
        "label": "Short-term rental (Airbnb/Booking)",
        "horizon": "3-5 years",
        "financial_instructions": """
For each property calculate SHORT-TERM RENTAL PARAMETERS:

Search on AirDNA, BnbVal, or local STR analytics for the specific zone:
1. Average nightly rate in the zone
2. Zone occupancy rate %
3. Occupied nights/year = 365 * occupancy rate
4. Gross annual revenue = nights * nightly rate
5. Management costs = gross * 0.28 (platform fees + cleaning + management)
6. Local short-term rental income tax = (gross - management) * local_tax_rate
   (search applicable rate for the country)
7. Net annual income = gross - management - tax
8. Down payment + mortgage + monthly payment (formula + current local rate)
9. Net monthly cash-flow = (net annual / 12) - mortgage payment
10. Gross yield % = (gross annual / price) * 100
11. Net yield on own capital % = (net annual / down payment) * 100
12. Payback years = price / net annual income

Regulatory note: search current STR regulations for the specific city/country
(licensing, night caps, registration requirements). Note any restrictions found.

Score 0-100 weighted on:
- Gross annual revenue potential (30%)
- Zone occupancy rate (30%)
- Net monthly cash-flow (25%)
- Regulatory and seasonality risk (15%)
""",
    },
    "prima_casa": {
        "label": "Primary residence with appreciation",
        "horizon": "5-10 years",
        "financial_instructions": """
For each property calculate PRIMARY RESIDENCE PARAMETERS:

1. Purchase price + transaction costs
   (apply local first-home buyer rates if available, otherwise estimate 3-8%)
2. Down payment (10-20%) + mortgage + monthly payment (formula + current local rate)
3. Affordability: monthly payment / average local income (target < 30%)
4. YoY zone growth found on portals: project 5 years
5. Estimated value in 5 years = price * (1 + YoY growth)^5
6. Potential appreciation = 5y value - purchase price
7. If renovation needed: total cost and post-renovation value
8. Rent vs buy comparison = zone rental rate - mortgage payment

Score 0-100 weighted on:
- Payment affordability (30%): payment < 30% income = high score
- 5-year appreciation potential % (30%)
- Zone quality and amenities (20%)
- Property condition and immediate costs (20%)
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
    """
    Calcola ROI comparativo per N immobili (max 5).
    SPRINT 4: task_callback(task_output) opzionale per progress tracking.
    """
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

    try:
        return _run_roi_crew(llm_type="gemini", **kwargs)
    except Exception as e:
        if should_fallback(e):
            logger.warning(
                f"[calcola_roi] Gemini fallito ({type(e).__name__}), "
                f"passo a Claude. Errore: {str(e)[:120]}"
            )
        else:
            raise

    fallback_llm = get_fallback_llm(plan=plan)
    if fallback_llm is None:
        raise RuntimeError(
            "Gemini non disponibile e ANTHROPIC_API_KEY non configurata."
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

    # ── Agenti ───────────────────────────────────────────────────────────────
    property_valuator = Agent(
        role="Property Valuator",
        goal=(
            "Trovare prezzi reali di vendita e affitto per ogni zona. "
            "Valutare il prezzo richiesto vs mercato locale. "
            "Stimare valori post-ristrutturazione dove necessario."
        ),
        backstory=_TEMPLATE_PROPERTY_VALUATOR,
        llm=llm,
        tools=[search_tool] if search_tool else [],
        verbose=True,
        allow_delegation=False,
    )

    financial_analyst = Agent(
        role="Financial Analyst Immobiliare",
        goal=(
            f"Calcolare metriche finanziarie per ogni immobile "
            f"in ottica '{goal_label}'. "
            "Produrre numeri precisi e score 0-100 per ogni immobile."
        ),
        backstory=_TEMPLATE_FINANCIAL_ANALYST,
        llm=llm,
        tools=[search_tool] if search_tool else [],
        verbose=True,
        allow_delegation=False,
    )

    comparator = Agent(
        role="Investment Comparator",
        goal=(
            "Confrontare tutti gli immobili, classificarli e "
            "raccomandare la scelta ottimale con numeri."
        ),
        backstory=_TEMPLATE_COMPARATOR,
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    # ── Task ─────────────────────────────────────────────────────────────────
    task_valuation = Task(
        description=(
            f"{lang_instr}"
            f"OBIETTIVO INVESTIMENTO: {goal_label} (orizzonte {goal_horizon})\n\n"
            f"IMMOBILI DA ANALIZZARE:\n{props_text}\n\n"
            f"Per ogni immobile:\n"
            f"1. Cerca prezzi vendita euro/mq nella zona specifica su portali\n"
            f"2. Cerca canoni affitto per metratura simile nella zona\n"
            f"3. Calcola scostamento del prezzo richiesto dal mercato (%)\n"
            f"4. Se 'da ristrutturare': cerca costi medi su cronoshare.it "
            f"   e stima valore post-ristrutturazione\n"
            f"5. Cita URL e data per ogni dato\n\n"
            f"Scrivi in testo puro, nessuna tabella markdown."
        ),
        expected_output=(
            "Per ogni immobile: prezzi mercato con fonti, scostamento %, "
            "canoni reali, valore post-ristr. se applicabile. Testo puro."
        ),
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
            f"Per ogni immobile: tutti i calcoli richiesti + score 0-100.\n"
            f"Formato: elenchi puntati per immobile. Nessuna tabella markdown."
        ),
        expected_output=(
            "Per ogni immobile: calcoli finanziari completi per l'obiettivo, "
            "score 0-100 con breakdown. Testo puro con elenchi."
        ),
        agent=financial_analyst,
        context=[task_valuation],
        callback=task_callback,
    )

    task_comparison = Task(
        description=(
            f"{lang_instr}"
            f"Sintetizza e produci la raccomandazione finale.\n\n"
            f"OBIETTIVO: {goal_label} (orizzonte {goal_horizon})\n\n"
            f"IMMOBILI:\n{props_text}\n\n"
            f"Produci in testo puro:\n"
            f"1. Risposta diretta (2-3 frasi con numeri)\n"
            f"2. Confronto immobili (nome, metrica, score, pro, contro)\n"
            f"3. Classifica motivata numericamente\n"
            f"4. Immobile consigliato con strategia e numeri\n"
            f"5. 2-3 avvertenze critiche\n"
            f"6. VERDICT: COMPRA / VALUTA CON CAUTELA / EVITA + 3 numeri\n\n"
            f"VIETATO: tabelle markdown con | e ----."
        ),
        expected_output=(
            "Testo puro: risposta diretta, confronto, classifica, "
            "consiglio con numeri, avvertenze, verdict."
        ),
        agent=comparator,
        context=[task_valuation, task_financials],
        callback=task_callback,
    )

    # ── Esecuzione ────────────────────────────────────────────────────────────
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

    from app.utils.text_cleaner import clean_agent_output

    market_analysis = clean_agent_output(get_output(0))
    financials_raw  = clean_agent_output(get_output(1))
    recommendation  = clean_agent_output(get_output(2))

    summary_lines = [l.strip() for l in recommendation.splitlines() if l.strip()]
    short_summary = summary_lines[0] if summary_lines else "Analisi completata."

    return {
        "summary":               short_summary,
        "investment_goal":       investment_goal,
        "investment_goal_label": goal_label,
        "properties_count":      len(properties),
        "market_analysis":       market_analysis,
        "financial_analysis":    financials_raw,
        "recommended_scenario":  recommendation,
        # Campo legacy per compatibilita frontend
        "scenarios":             _build_scenarios_compat(properties, financials_raw),
        "scenarios_raw":         financials_raw,
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


def _build_scenarios_compat(properties: list[dict], financials_raw: str) -> list[dict]:
    """Compatibilita con il frontend che si aspetta una lista 'scenarios'."""
    return [
        {
            "name": p.get("name") or p.get("address") or f"Immobile {i+1}",
            "description": financials_raw,
            "roi_percent": 0,
            "payback_years": 0,
            "risk_level": "medio",
        }
        for i, p in enumerate(properties)
    ]