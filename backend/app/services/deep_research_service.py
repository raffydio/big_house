# backend/app/services/deep_research_service.py
#
# SPRINT 2 — Aggiunto fallback Claude quando Gemini fallisce
# Logica: tenta Gemini → se should_fallback(exc) → riprova con Claude
# Il resto del codice (agenti, task, template) rimane invariato.

import logging
from typing import Optional

from crewai import Agent, Task, Crew, Process

from app.agents.llm_factory import (
    get_llm, get_fallback_llm, should_fallback, get_search_mode
)
from app.agents.search_tool import get_search_tool

logger = logging.getLogger(__name__)

# ── Template few-shot (invariati dallo Sprint 1) ──────────────────────────────

_TEMPLATE_MARKET_SCOUT = """
You are an expert real estate market analyst with 15 years of global experience.
You ALWAYS search for real data on the web and NEVER invent prices or statistics.

PORTAL SELECTION RULES:
- Identify the country from the property address or query.
- Use the leading real estate portals for that country.
  Examples: Zillow/Realtor (USA), Rightmove/Zoopla (UK), Idealista (ES/IT/PT),
  SeLoger/LeBonCoin (FR), ImmobilienScout24 (DE), Domain/REA (AU),
  PropertyFinder/Bayut (UAE/MENA), 99.co (SG), and equivalents worldwide.
- If the country is unclear, search for "[city] real estate market data [year]".

MANDATORY OUTPUT STRUCTURE for each city/area:

Indicator | Value | Source
Average sale price | [VALUE] [currency]/sqm | [source + date]
Average rental price | [VALUE] [currency]/sqm/month | [source + date]
YoY change | [VALUE] % | [source + date]
Gross yield | (rent*12)/sale*100 = [VALUE] %
Trend | GROWING/STABLE/DECLINING | [reason]

Most expensive neighborhoods (min 2): [name]: [VALUE] [currency]/sqm - [reason]
Most affordable neighborhoods (min 2): [name]: [VALUE] [currency]/sqm - [reason]

CRITICAL RULE: ALWAYS search the specific micro-market (neighborhood/district),
not the city average. Cite URL and date for every numeric data point.
Use local currency. Write 'data not available' if a value cannot be found.
"""

_TEMPLATE_PROPERTY_ANALYST = """
You are a certified property appraiser with global investment valuation experience.
You use only documented data and precise formulas.

UNIVERSAL FORMULAS (always apply):

GROSS YIELD = (monthly rent * 12) / purchase price * 100
NET YIELD = (annual rent * (1 - local_tax_rate) - annual service charges) / purchase price * 100
PAYBACK = purchase price / net annual income

SHORT-TERM RENTAL YIELD = (avg nightly rate * occupied nights * (1 - mgmt_fee_pct) - platform fees) / price * 100
Management costs = typically 25-30% of gross revenue.
Search occupancy rates on AirDNA, BnbVal, or local STR analytics platforms.

INVESTMENT SCORE 0-100 = weighted average:
- Net yield (weight 30%)
- Price deviation from market (weight 25%)
- Zone liquidity (weight 20%)
- Flipping or appreciation potential (weight 25%)

OUTPUT STRUCTURE per property:
Asking price: [VALUE] [currency] -> [VALUE] [currency]/sqm
Zone avg price: [VALUE] [currency]/sqm (source: [URL])
Deviation: [+/-]% [above/below] market
Estimated monthly rent: [VALUE] [currency] (source: [URL])
Gross yield: [%] | Net yield: [%] | Payback: [years]
Investment score: [0-100] - [breakdown by weight]
Recommended strategy: long-term rental / short-term rental / flipping / avoid
"""

_TEMPLATE_RISK_ASSESSOR = """
You are a real estate due diligence and risk analysis specialist.
You assess every factor with concrete evidence found on the web.

RISK CHECKLIST (rate each: HIGH/MEDIUM/LOW):

For BUY-TO-LET:
- Tenant default risk: search eviction rates and vacancy rates for the city/market
- Short-term rental regulations: search current STR rules, licensing, and night limits for the location
- Depreciation risk: YoY price trend in the specific zone
- Maintenance costs: estimate 1-1.5% of property value/year

For FLIPPING:
- Market risk: price forecasts for the zone in the next 12-24 months
- Construction risk: typical renovation budget overrun (usually 10-15%)
- Liquidity risk: average time-on-market for renovated properties in the zone
- Planning/zoning risk: local urban planning rules, permit requirements

RISK OUTPUT TEMPLATE:
Risk | Evidence found on web | Level (H/M/L) | Mitigation

OPPORTUNITY OUTPUT TEMPLATE:
Opportunity | Evidence | Estimated impact

Always search: urban renewal plans, new infrastructure, residential developments,
tax incentives or grants specific to the location and property type.
"""

_TEMPLATE_INVESTMENT_STRATEGIST = """
You are a senior real estate investment advisor. Your recommendations
always include precise numbers, time horizon, and exit strategy.

MANDATORY OUTPUT STRUCTURE:

1. DIRECT ANSWER to the query (1-2 sentences with numbers)

2. COMPARISON TABLE (if multiple properties):
Metric | Prop.A | Prop.B | Prop.C
Price ([currency]) | [VALUE] | [VALUE] | [VALUE]
[currency]/sqm | [VALUE] | [VALUE] | [VALUE]
Market deviation (%) | [VALUE] | [VALUE] | [VALUE]
Gross yield (%) | [VALUE] | [VALUE] | [VALUE]
Net yield (%) | [VALUE] | [VALUE] | [VALUE]
Payback (years) | [VALUE] | [VALUE] | [VALUE]
Score 0-100 | [VALUE] | [VALUE] | [VALUE]
Recommended strategy | [text] | [text] | [text]

3. RANKING (best to worst with numerical justification)

4. STRATEGY for the top pick:
- Time horizon: [years]
- Expected return: [%] per year
- Exit strategy: [resale/rental/other]
- Maximum purchase price (break-even): [VALUE] [currency]

5. WARNINGS (2-3 critical points to verify before purchase)

6. FINAL VERDICT:
BUY / EVALUATE WITH CAUTION / AVOID
with justification in 3 lines and supporting numbers.

RULE: the verdict must always include numbers.
"""


# ── Funzione principale ───────────────────────────────────────────────────────

def run_deep_research(
    query: str,
    properties: list[dict],
    plan: str = "free",
    user_id: Optional[int] = None,
    language: str = "it",
    task_callback=None,
) -> dict:
    """
    Deep Research immobiliare con 4 agenti specializzati.
    SPRINT 2: tenta Gemini prima, fallback automatico su Claude se necessario.
    SPRINT 4: task_callback(task_output) opzionale — chiamato dopo ogni task
              CrewAI per aggiornare il progresso in Redis (via job_store).
    """
    logger.info(
        f"Deep Research START — user={user_id}, plan={plan}, "
        f"lang={language}, properties={len(properties)}, query='{query[:60]}'"
    )

    # ── Tentativo 1: Gemini ──
    try:
        return _run_crew(
            query=query,
            properties=properties,
            plan=plan,
            user_id=user_id,
            llm_type="gemini",
            language=language,
            task_callback=task_callback,
        )
    except Exception as e:
        if should_fallback(e):
            logger.warning(
                f"[deep_research] Gemini fallito ({type(e).__name__}), "
                f"passo a Claude. Errore: {str(e)[:120]}"
            )
        else:
            raise

    # ── Tentativo 2: Claude fallback ──
    fallback_llm = get_fallback_llm(plan=plan)
    if fallback_llm is None:
        raise RuntimeError(
            "Gemini non disponibile e ANTHROPIC_API_KEY non configurata. "
            "Aggiungi ANTHROPIC_API_KEY al .env per abilitare il fallback Claude."
        )

    logger.info(f"[deep_research] Avvio con Claude fallback — piano={plan}")
    return _run_crew(
        query=query,
        properties=properties,
        plan=plan,
        user_id=user_id,
        llm_type="claude",
        forced_llm=fallback_llm,
        language=language,
        task_callback=task_callback,
    )


def _build_language_instruction(language: str) -> str:
    """
    Restituisce l'istruzione lingua da iniettare in testa a ogni task.
    Supporta tutti i codici ISO 639-1 — il modello gestisce la traduzione.
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


def _run_crew(
    query: str,
    properties: list[dict],
    plan: str,
    user_id: Optional[int],
    llm_type: str,
    forced_llm=None,
    language: str = "it",
    task_callback=None,
) -> dict:
    """
    Esegue il crew CrewAI con il provider LLM specificato.
    llm_type: "gemini" | "claude"
    forced_llm: se fornito, usa questo LLM invece di chiamare get_llm()
    language: codice ISO della lingua in cui rispondere
    task_callback: callable(task_output) opzionale — chiamato dopo ogni Task
    """
    llm         = forced_llm or get_llm(plan=plan)
    search_mode = get_search_mode(llm_type)
    search_tool = get_search_tool(plan=plan, mode=search_mode)
    props_text  = _format_properties(properties)
    lang_instr  = _build_language_instruction(language)

    logger.info(f"[deep_research] crew LLM={llm_type}, search_mode={search_mode}, lang={language}")

    # ── Agenti ───────────────────────────────────────────────────────────────
    market_scout = Agent(
        role="Market Scout Immobiliare",
        goal=(
            "Trovare i prezzi reali di vendita e affitto per la zona "
            "specifica di ogni immobile. Analizzare il micro-mercato "
            "locale, non la media della citta."
        ),
        backstory=_TEMPLATE_MARKET_SCOUT,
        llm=llm,
        tools=[search_tool] if search_tool else [],
        verbose=True,
        allow_delegation=False,
    )

    property_analyst = Agent(
        role="Property Analyst",
        goal=(
            "Valutare ogni immobile con le formule precise di yield lordo, "
            "netto, payback e score 0-100. Confrontare con i prezzi reali "
            "trovati dal Market Scout."
        ),
        backstory=_TEMPLATE_PROPERTY_ANALYST,
        llm=llm,
        tools=[search_tool] if search_tool else [],
        verbose=True,
        allow_delegation=False,
    )

    risk_assessor = Agent(
        role="Risk and Opportunity Assessor",
        goal=(
            "Identificare rischi concreti e opportunita reali per ogni "
            "immobile. Valutare ogni fattore ALTO/MEDIO/BASSO con "
            "evidenze trovate sul web."
        ),
        backstory=_TEMPLATE_RISK_ASSESSOR,
        llm=llm,
        tools=[search_tool] if search_tool else [],
        verbose=True,
        allow_delegation=False,
    )

    investment_strategist = Agent(
        role="Investment Strategist Immobiliare",
        goal=(
            "Sintetizzare le analisi in una raccomandazione con tabella "
            "comparativa, classifica, strategia e verdict finale con numeri."
        ),
        backstory=_TEMPLATE_INVESTMENT_STRATEGIST,
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    # ── Determina se l'investitore ha fornito immobili specifici ─────────────
    # Se non ci sono proprietà, i task 2 e 3 operano in modalità
    # "simulazione di mercato": l'agente costruisce profili tipici
    # compatibili con la query e li analizza come se fossero immobili reali.
    has_properties = bool(properties)

    if has_properties:
        props_context_market = (
            f"PROPERTIES TO ANALYZE:\n{props_text}\n\n"
            "For each property:\n"
            "1. Search the SPECIFIC micro-market of the area (not the city average)\n"
            "2. Find sale prices in local currency/sqm from local portals\n"
            "3. Find rental rates in local currency/sqm/month\n"
            "4. Find YoY price change and current trend\n"
            "5. Identify most expensive and most affordable neighborhoods\n"
            "6. Cite URL and date for every data point — never invent numbers"
        )
        props_context_property = (
            f"PROPERTIES TO VALUE:\n{props_text}\n\n"
            "For each property apply exact formulas:\n"
            "1. Calculate local-currency/sqm and deviation from local market (%)\n"
            "2. Find the real monthly rental for that zone and property type\n"
            "3. Calculate gross yield, net yield (apply local rental tax rate), payback\n"
            "4. If renovation needed: calculate flipping margin\n"
            "   (typical transaction costs: taxes + agency + notary — use local rates\n"
            "    or estimate 5-10% if unknown; renovation budget if provided)\n"
            "5. Assign score 0-100 using the weighted average of 4 factors\n"
            "6. Recommend strategy: long-term rental / short-term rental / flipping / avoid"
        )
        props_context_risk = (
            f"PROPERTIES TO ANALYZE:\n{props_text}\n\n"
            "For each zone search:\n"
            "1. Eviction / vacancy data for the city or region\n"
            "2. Current short-term rental regulations for the location (permits, night caps)\n"
            "3. Price forecasts for the zone in the next 12-24 months\n"
            "4. Urban renewal plans or new infrastructure projects\n"
            "5. For renovation properties: calculate break-even price\n"
            "   (estimated resale value - total costs = max sustainable purchase price)\n"
            "Rate every risk: HIGH/MEDIUM/LOW with evidence."
        )
    else:
        # Simulation mode: no specific properties provided by the user.
        # Market Scout identifies the best zones, then Property Analyst
        # builds 3 typical profiles compatible with the query and analyzes them.
        props_context_market = (
            "The investor has NOT provided specific properties.\n"
            "Your task is to analyze the market of the city/zone indicated in the query "
            "and identify the BEST AREAS where opportunities matching "
            "the investor's criteria can be found.\n\n"
            "For each area/neighborhood found:\n"
            "1. Search sale prices in local currency/sqm from leading local portals\n"
            "2. Search rental rates in local currency/sqm/month\n"
            "3. Search YoY change and market trend\n"
            "4. Identify which zones fall within the budget mentioned in the query\n"
            "5. Cite URL and date for every data point — never invent numbers\n\n"
            "IMPORTANT: conclude by listing the TOP 3 most promising zones/areas "
            "with average sale and rental prices found."
        )
        props_context_property = (
            "The investor has NOT provided specific properties.\n"
            "Based on the market data found by the Market Scout, "
            "BUILD and ANALYZE 3 typical property profiles compatible "
            "with the investor's query. Name each one (e.g. Profile A, B, C).\n\n"
            f"INVESTOR QUERY: {query}\n\n"
            "For EACH profile apply exact formulas:\n"
            "1. Define: zone, purchase price, size, condition\n"
            "2. Calculate local-currency/sqm and deviation from local market (%)\n"
            "3. Calculate gross yield, net yield (apply local rental tax), payback\n"
            "4. If renovation needed: estimate cost from local sources and calculate\n"
            "   flipping margin (transaction costs: taxes + agency + notary ~5-10%\n"
            "    unless local data is available)\n"
            "5. Assign score 0-100 using weighted average of 4 factors\n"
            "6. Recommend strategy: long-term rental / short-term rental / flipping / avoid\n\n"
            "RULE: use ONLY real prices and data found by the Market Scout. "
            "Do not invent values. If rental data for a zone is missing, "
            "use data from the nearest comparable market."
        )
        props_context_risk = (
            "The investor has NOT provided specific properties.\n"
            "Analyze risks and opportunities for the 3 zones/profiles identified.\n\n"
            f"INVESTOR QUERY: {query}\n\n"
            "For each zone/profile search:\n"
            "1. Eviction / vacancy data for the city or region\n"
            "2. Current short-term rental regulations for the location\n"
            "3. Price forecasts for the zone in the next 12-24 months\n"
            "4. Urban renewal plans or new infrastructure projects\n"
            "5. For renovation profiles: calculate break-even price\n"
            "   (estimated resale value - total costs = max sustainable purchase price)\n"
            "Rate every risk: HIGH/MEDIUM/LOW with evidence and source."
        )

    # ── Task ─────────────────────────────────────────────────────────────────
    task_market = Task(
        description=(
            f"{lang_instr}"
            f"INVESTOR QUERY: {query}\n\n"
            f"{props_context_market}"
        ),
        expected_output=(
            "Per ogni zona: sale price local-currency/sqm, rent local-currency/sqm/month, "
            "YoY%, trend, expensive/affordable neighborhoods. "
            "Every data point with cited URL. "
            "If no specific properties: TOP 3 most promising zones with prices."
        ),
        agent=market_scout,
        callback=task_callback,
    )

    task_property = Task(
        description=(
            f"{lang_instr}"
            f"Using the market data found, proceed with valuation:\n\n"
            f"{props_context_property}"
        ),
        expected_output=(
            "Per ogni immobile o profilo simulato: euro/mq, scostamento%, "
            "yield lordo%, yield netto%, payback anni, "
            "margine flipping% se applicabile, score 0-100 con breakdown, "
            "strategia consigliata."
        ),
        agent=property_analyst,
        context=[task_market],
        callback=task_callback,
    )

    task_risk = Task(
        description=(
            f"{lang_instr}"
            f"Analizza rischi e opportunita:\n\n"
            f"{props_context_risk}"
        ),
        expected_output=(
            "Tabella rischi con livello A/M/B e fonte. "
            "Tabella opportunita con impatto stimato. "
            "Break-even price per immobili/profili da ristrutturare."
        ),
        agent=risk_assessor,
        context=[task_market, task_property],
        callback=task_callback,
    )

    task_recommendation = Task(
        description=(
            f"{lang_instr}"
            f"Sintetizza tutto in una raccomandazione finale strutturata.\n\n"
            f"QUERY ORIGINALE: {query}\n\n"
            "Produci OBBLIGATORIAMENTE:\n"
            "1. Risposta diretta alla query (1-2 frasi con numeri)\n"
            "2. Tabella comparativa con tutte le metriche per ogni immobile\n"
            "3. Classifica dal migliore al peggiore con motivazione numerica\n"
            "4. Strategia dettagliata per il primo classificato\n"
            "5. 2-3 avvertenze critiche da verificare prima dell'acquisto\n"
            "6. VERDICT: COMPRA / VALUTA CON CAUTELA / EVITA\n"
            "   con motivazione in 3 righe e numeri a supporto"
        ),
        expected_output=(
            "Risposta diretta, tabella comparativa completa, classifica "
            "motivata, strategia con numeri, avvertenze, verdict finale."
        ),
        agent=investment_strategist,
        context=[task_market, task_property, task_risk],
        callback=task_callback,
    )

    # ── Esecuzione ────────────────────────────────────────────────────────────
    crew = Crew(
        agents=[market_scout, property_analyst, risk_assessor, investment_strategist],
        tasks=[task_market, task_property, task_risk, task_recommendation],
        process=Process.sequential,
        verbose=True,
    )

    logger.info(f"[deep_research] CrewAI kickoff (llm_type={llm_type})...")
    result = crew.kickoff()
    logger.info(f"[deep_research] CrewAI completato (llm_type={llm_type})")

    task_outputs = result.tasks_output if hasattr(result, "tasks_output") else []

    def get_output(idx: int) -> str:
        try:
            return str(task_outputs[idx].raw) if idx < len(task_outputs) else ""
        except Exception:
            return ""

    # Cleanup markdown dall'output
    from app.utils.text_cleaner import clean_agent_output

    market_text    = clean_agent_output(get_output(0))
    property_text  = clean_agent_output(get_output(1))
    risk_text      = clean_agent_output(get_output(2))
    recommendation = clean_agent_output(get_output(3))

    # IMPORTANTE: str(result) in CrewAI == output ultimo task == recommendation.
    # Usarlo come "summary" causa la triplicazione nel docx.
    # Estraiamo solo la prima riga significativa come titolo breve.
    summary_lines = [l.strip() for l in recommendation.splitlines() if l.strip()]
    short_summary = summary_lines[0] if summary_lines else "Analisi completata."

    return {
        "summary":                   short_summary,
        "market_overview":           market_text,
        "properties_analysis":       _parse_properties_analysis(property_text, properties),
        "risks_opportunities":       risk_text,
        "investment_recommendation": recommendation,
        "remaining_usage":           None,
        "llm_used":                  llm_type,
    }


# ── Helper ────────────────────────────────────────────────────────────────────

def _format_properties(properties: list[dict]) -> str:
    if not properties:
        return "Nessuna proprieta specificata."
    parts = []
    for i, p in enumerate(properties, 1):
        lines = [f"Proprieta {i}:"]
        if p.get("address"):   lines.append(f"  Indirizzo:  {p['address']}")
        if p.get("price"):     lines.append(f"  Prezzo:     {p['price']:,.0f} euro")
        if p.get("size_sqm"):  lines.append(f"  Superficie: {p['size_sqm']} mq")
        if p.get("price") and p.get("size_sqm"):
            lines.append(f"  euro/mq:    {p['price'] / p['size_sqm']:,.0f}")
        if p.get("rooms"):     lines.append(f"  Locali:     {p['rooms']}")
        if p.get("condition"): lines.append(f"  Condizioni: {p['condition']}")
        if p.get("notes"):     lines.append(f"  Note:       {p['notes']}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def _parse_properties_analysis(raw_text: str, properties: list[dict]) -> list[dict]:
    if not raw_text:
        return [
            {"address": p.get("address", f"Proprieta {i+1}"),
             "recommendation": "Analisi non disponibile",
             "risks": [], "opportunities": []}
            for i, p in enumerate(properties)
        ]
    return [
        {"address":        p.get("address", f"Proprieta {i+1}"),
         "price_asked":    p.get("price"),
         "size_sqm":       p.get("size_sqm"),
         "recommendation": raw_text,
         "risks":          [],
         "opportunities":  []}
        for i, p in enumerate(properties)
    ]