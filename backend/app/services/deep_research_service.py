"""
services/deep_research_service.py  v3
Deep Research — gli agenti CERCANO opportunità sul mercato
a partire da una query libera dell'utente.

AGGIORNATO: DeepSeek → Google Gemini 2.5 Pro via llm_factory
"""
import json
import logging
from crewai import Agent, Task, Crew, Process

from app.agents.llm_factory import get_llm   # ← unica riga che cambia rispetto a prima
from app.models import DeepResearchResponse, FoundOpportunity

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "⚠️ Questi risultati sono generati da intelligenza artificiale a scopo "
    "puramente informativo. Non costituiscono consulenza finanziaria, "
    "immobiliare o legale. Verifica sempre con un professionista qualificato "
    "prima di prendere decisioni di investimento. — Big House AI è conforme "
    "al Reg. UE 2024/1689 (AI Act) e alla Legge italiana 132/2025."
)


async def run_deep_research(query: str) -> DeepResearchResponse:
    llm = get_llm()   # ← Gemini 2.5 Pro da llm_factory

    # AGENT 1 — Market Scout
    market_scout = Agent(
        role="Market Scout Immobiliare",
        goal="Interpretare la query e identificare zona, budget, obiettivo. Stimare prezzi €/mq correnti.",
        backstory="Esperto mercato immobiliare italiano 2025-2026. Dati realistici sempre.",
        llm=llm, verbose=False, allow_delegation=False,
    )
    task_scout = Task(
        description=(
            f"Query investitore: '{query}'\n\n"
            "Rispondi in JSON:\n"
            "{\n"
            '  "zona_target": "zona/città",\n'
            '  "budget_max": numero euro,\n'
            '  "size_min_sqm": numero mq,\n'
            '  "obiettivo": "flipping|affitto_lungo|affitto_breve|prima_casa",\n'
            '  "prezzo_medio_zona_mq": numero,\n'
            '  "prezzo_ristrutturato_mq": numero,\n'
            '  "market_context": "3-4 righe panoramica mercato zona"\n'
            "}"
        ),
        expected_output="JSON analisi richiesta e dati mercato",
        agent=market_scout,
    )

    # AGENT 2 — Zone Analyzer
    zone_analyzer = Agent(
        role="Zone Analyzer — Analista Territorio",
        goal="Trend prezzi, rischi zona, domanda affitti, normativa affitti brevi.",
        backstory="Specialista micro-mercati urbani italiani. Citi fonti: Tecnocasa, OMI, Idealista.",
        llm=llm, verbose=False, allow_delegation=False,
    )
    task_zone = Task(
        description=(
            "Dai dati del Market Scout, produci JSON:\n"
            "{\n"
            '  "trend_12m": "% crescita/calo prezzi ultimi 12 mesi",\n'
            '  "previsione_12m": "stima prossimi 12 mesi",\n'
            '  "fattori_positivi": ["lista"],\n'
            '  "fattori_rischio": ["lista"],\n'
            '  "domanda_affitti": "alta|media|bassa + motivazione",\n'
            '  "normativa_airbnb": "situazione affitti brevi comune",\n'
            '  "market_trend_text": "paragrafo per report"\n'
            "}"
        ),
        expected_output="JSON trend e rischi zona",
        agent=zone_analyzer,
        context=[task_scout],
    )

    # AGENT 3 — Opportunity Ranker
    opportunity_ranker = Agent(
        role="Opportunity Ranker — Cacciatore di Opportunità",
        goal="Genera 2-4 opportunità concrete e realistiche nella zona, compatibili col budget.",
        backstory="Investment advisor immobiliare specializzato value-add Italia. Stime conservative e reali.",
        llm=llm, verbose=False, allow_delegation=False,
    )
    task_opportunities = Task(
        description=(
            "Genera array JSON di 2-4 opportunità ordinate per score decrescente.\n"
            "Ogni elemento:\n"
            "{\n"
            '  "title": "descrizione breve",\n'
            '  "estimated_price_range": "€X – €Y",\n'
            '  "size_range": "X – Y mq",\n'
            '  "zone": "sotto-zona specifica",\n'
            '  "price_per_sqm": numero,\n'
            '  "condition": "stato",\n'
            '  "opportunity_score": numero 0-10,\n'
            '  "roi_potential": "descrizione ROI",\n'
            '  "renovation_estimate": "€X – €Y (livello)",\n'
            '  "key_pros": ["pro1","pro2","pro3"],\n'
            '  "key_cons": ["contro1","contro2"],\n'
            '  "why_interesting": "paragrafo motivazione"\n'
            "}\n"
            "Solo dati realistici. No ROI gonfiati."
        ),
        expected_output="Array JSON opportunità ordinate per score",
        agent=opportunity_ranker,
        context=[task_scout, task_zone],
    )

    # AGENT 4 — Report Writer
    report_writer = Agent(
        role="Report Writer — Investment Advisor Senior",
        goal="Sintesi finale: best pick motivato e action plan concreto in 5-7 passi.",
        backstory="500+ investitori assistiti nel mercato italiano. Raccomandazioni concrete, non generiche.",
        llm=llm, verbose=False, allow_delegation=False,
    )
    task_report = Task(
        description=(
            "Produci JSON finale:\n"
            "{\n"
            '  "best_pick": "quale opportunità scegliere e perché (2-3 righe)",\n'
            '  "action_plan": "passi concreti numerati da fare subito",\n'
            '  "comparison_summary": "tabella comparativa testuale opportunità"\n'
            "}\n"
            "Action plan specifico: es. '1. Contatta 3 agenzie zona X' non 'Valuta il mercato'."
        ),
        expected_output="JSON best_pick, action_plan, comparison_summary",
        agent=report_writer,
        context=[task_scout, task_zone, task_opportunities],
    )

    crew = Crew(
        agents=[market_scout, zone_analyzer, opportunity_ranker, report_writer],
        tasks=[task_scout, task_zone, task_opportunities, task_report],
        process=Process.sequential,
        verbose=False,
    )

    try:
        crew.kickoff()
    except Exception as e:
        logger.error(f"Crew error: {e}")
        raise RuntimeError(f"Errore agenti AI: {e}")

    # ── Parsing output agenti ──
    scout_data  = _parse_json(task_scout.output.raw if task_scout.output else "")
    zone_data   = _parse_json(task_zone.output.raw if task_zone.output else "")
    opps_data   = _parse_json_list(task_opportunities.output.raw if task_opportunities.output else "")
    report_data = _parse_json(task_report.output.raw if task_report.output else "")

    opportunities = []
    for opp in opps_data[:4]:
        try:
            opportunities.append(FoundOpportunity(
                title=opp.get("title", "Opportunità immobiliare"),
                estimated_price_range=opp.get("estimated_price_range", "N/D"),
                size_range=opp.get("size_range", "N/D"),
                zone=opp.get("zone", scout_data.get("zona_target", "N/D")),
                price_per_sqm=float(opp.get("price_per_sqm", 0)),
                condition=opp.get("condition", "Da ristrutturare"),
                opportunity_score=float(opp.get("opportunity_score", 7.0)),
                roi_potential=opp.get("roi_potential", "N/D"),
                renovation_estimate=opp.get("renovation_estimate", "N/D"),
                key_pros=opp.get("key_pros", []),
                key_cons=opp.get("key_cons", []),
                why_interesting=opp.get("why_interesting", ""),
            ))
        except Exception:
            continue

    if not opportunities:
        opportunities = _fallback_opportunity(query, scout_data)

    return DeepResearchResponse(
        market_context=_to_str(scout_data.get("market_context", "")),
        opportunities=opportunities,
        best_pick=_to_str(report_data.get("best_pick", "Vedi opportunità trovate.")),
        market_trend=_to_str(zone_data.get("market_trend_text", "")),
        action_plan=_to_str(report_data.get("action_plan", "")),
        comparison_summary=_to_str(report_data.get("comparison_summary", "")),
        disclaimer=DISCLAIMER,
        remaining_usage=0,
    )


# ── Helpers parsing ────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    if not raw:
        return {}
    cleaned = raw.strip()
    if "```" in cleaned:
        for part in cleaned.split("```"):
            p = part.lstrip("json").strip()
            if p.startswith("{"):
                cleaned = p
                break
    try:
        return json.loads(cleaned)
    except Exception:
        s, e = cleaned.find("{"), cleaned.rfind("}") + 1
        if s != -1 and e > s:
            try:
                return json.loads(cleaned[s:e])
            except Exception:
                pass
    return {}


def _parse_json_list(raw: str) -> list:
    if not raw:
        return []
    cleaned = raw.strip()
    if "```" in cleaned:
        for part in cleaned.split("```"):
            p = part.lstrip("json").strip()
            if p.startswith("["):
                cleaned = p
                break
    s, e = cleaned.find("["), cleaned.rfind("]") + 1
    if s != -1 and e > s:
        try:
            return json.loads(cleaned[s:e])
        except Exception:
            pass
    obj = _parse_json(cleaned)
    return [obj] if obj else []


def _fallback_opportunity(query: str, scout: dict) -> list:
    return [FoundOpportunity(
        title=f"Opportunità in {scout.get('zona_target', 'zona cercata')}",
        estimated_price_range=f"Entro €{scout.get('budget_max', 200000):,.0f}",
        size_range=f"Da {scout.get('size_min_sqm', 60)} mq",
        zone=scout.get("zona_target", "Zona ricercata"),
        price_per_sqm=float(scout.get("prezzo_medio_zona_mq", 2500)),
        condition="Da ristrutturare",
        opportunity_score=7.0,
        roi_potential="Da verificare con agente locale",
        renovation_estimate="€600 – €1.000/mq",
        key_pros=["Zona compatibile con budget", "Mercato in crescita"],
        key_cons=["Stima generica — verificare con sopralluogo"],
        why_interesting=f"Ricerca: {query[:200]}. Contatta agenzie locali per offerte aggiornate.",
    )]


def _to_str(val) -> str:
    """Converte lista o qualsiasi tipo in stringa — i modelli a volte restituiscono liste invece di stringhe."""
    if isinstance(val, list):
        return "\n".join(str(v) for v in val)
    return str(val) if val else ""