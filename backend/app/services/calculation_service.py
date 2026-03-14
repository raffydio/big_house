"""
services/calculation_service.py  v3
Calcola ROI — confronto fino a 5 immobili con tabella comparativa.

AGGIORNATO: DeepSeek → Google Gemini 2.5 Pro via llm_factory
"""
import json
import logging
from crewai import Agent, Task, Crew, Process

from app.agents.llm_factory import get_llm   # ← unica riga che cambia
from app.models import (
    CompareROIRequest, CompareROIResponse,
    PropertyROIResult, RenovationScenario,
)

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "⚠️ Questi risultati sono generati da intelligenza artificiale a scopo "
    "puramente informativo. Non costituiscono consulenza finanziaria, "
    "immobiliare o legale. Verifica sempre con un professionista qualificato "
    "prima di prendere decisioni di investimento. — Big House AI è conforme "
    "al Reg. UE 2024/1689 (AI Act) e alla Legge italiana 132/2025."
)


async def run_compare_roi(data: CompareROIRequest) -> CompareROIResponse:
    llm = get_llm()   # ← Gemini 2.5 Pro da llm_factory

    props_summary = "\n".join([
        f"[{i+1}] {p.label} — {p.address} | €{p.purchase_price:,.0f} | {p.size_sqm}mq | "
        f"{p.rooms} locali | {p.condition} | ascensore: {'sì' if p.has_elevator else 'no'}"
        f"{f' | piano {p.floor}' if p.floor else ''}"
        f"{f' | note: {p.notes}' if p.notes else ''}"
        for i, p in enumerate(data.properties)
    ])

    goal_label = {
        "flipping": "vendita post-ristrutturazione (flipping)",
        "affitto_lungo": "affitto a lungo termine",
        "affitto_breve": "affitto breve (Airbnb/booking)",
        "prima_casa": "acquisto prima casa con valorizzazione",
    }.get(data.goal, data.goal)

    # AGENT 1 — Cost Estimator
    cost_estimator = Agent(
        role="Cost Estimator — Perito Immobiliare",
        goal=(
            "Stimare con precisione i costi di ristrutturazione per ogni immobile "
            "in 3 scenari (Conservativo, Medio, Premium) basandosi su "
            "prezzi reali del mercato edilizio italiano 2025-2026."
        ),
        backstory=(
            "Perito edile con 20 anni di esperienza nel mercato italiano. "
            "Conosci i prezzari regionali delle camere di commercio, i costi "
            "di manodopera per zona geografica, l'impatto di vincoli "
            "urbanistici e stato dell'immobile sui costi finali."
        ),
        llm=llm, verbose=False, allow_delegation=False,
    )

    task_costs = Task(
        description=(
            f"Obiettivo investitore: {goal_label}\n\n"
            f"Immobili da analizzare:\n{props_summary}\n\n"
            "Per ogni immobile (indicato col suo numero), stima i costi di "
            "ristrutturazione in 3 scenari. Rispondi con un array JSON:\n"
            "[\n"
            "  {\n"
            '    "index": 1,\n'
            '    "price_per_sqm_buy": numero (€/mq acquisto stima di mercato),\n'
            '    "scenarios": [\n'
            "      {\n"
            '        "name": "Conservativo",\n'
            '        "renovation_cost": numero totale €,\n'
            '        "duration_months": numero,\n'
            '        "estimated_value_after": numero €,\n'
            '        "estimated_rent_after": numero €/mese,\n'
            '        "description": "cosa include questo scenario"\n'
            "      },\n"
            '      {"name": "Medio", ...},\n'
            '      {"name": "Premium", ...}\n'
            "    ]\n"
            "  },\n"
            "  ...\n"
            "]\n"
            "Usa prezzi reali mercato edilizio 2025-2026. "
            "Considera zona geografica, condizioni immobile, presenza/assenza ascensore."
        ),
        expected_output="Array JSON con stime costi per ogni immobile",
        agent=cost_estimator,
    )

    # AGENT 2 — ROI Calculator
    roi_calculator = Agent(
        role="ROI Calculator — Analista Finanziario Immobiliare",
        goal=(
            "Calcolare ROI netto, payback e rendimento per ogni immobile "
            "in ogni scenario, includendo tutti i costi (imposte, notaio, "
            "agenzia, interessi mutuo). Formule precise e trasparenti."
        ),
        backstory=(
            "Analista finanziario specializzato in real estate italiano. "
            "Conosci a memoria la fiscalità immobiliare italiana: "
            "imposte di registro (2% prima casa, 9% seconda), IVA, "
            "cedolare secca, detrazioni 36%/50%, tasse plusvalenza."
        ),
        llm=llm, verbose=False, allow_delegation=False,
    )

    task_roi = Task(
        description=(
            f"Obiettivo: {goal_label}\n\n"
            f"Immobili:\n{props_summary}\n\n"
            "Dai costi stimati dal Cost Estimator, calcola per ogni immobile "
            "e ogni scenario:\n"
            "- roi_percent = (valore_post - prezzo_acquisto - costi_rinnovo - tasse_acquisto - spese_vendita) / investimento_totale * 100\n"
            "- payback_years = investimento_totale / rendita_netta_annua\n"
            "- risk_level = Basso|Medio|Alto (basato su entità intervento e mercato)\n\n"
            "Assumi: seconda casa (imposta 9%), agenzia vendita 3%+IVA, "
            f"mutuo al {data.properties[0].mortgage_rate or 3.5}% per "
            f"{data.properties[0].mortgage_years or 20} anni se finanziato.\n\n"
            "Restituisci array JSON stesso formato del Cost Estimator "
            "ma con campi aggiunti in ogni scenario:\n"
            '  "roi_percent": numero,\n'
            '  "payback_years": numero,\n'
            '  "risk_level": "Basso|Medio|Alto"\n'
            "Aggiungi campo 'best_scenario' con nome scenario consigliato "
            f"per obiettivo {goal_label}."
        ),
        expected_output="Array JSON con ROI calcolato per ogni immobile e scenario",
        agent=roi_calculator,
        context=[task_costs],
    )

    # AGENT 3 — Comparison Analyst
    comparison_analyst = Agent(
        role="Comparison Analyst — Portfolio Manager",
        goal=(
            "Confrontare tutti gli immobili, identificare il vincitore assoluto "
            "e produrre una tabella comparativa chiara. "
            "Ranking motivato con pro/contro specifici di ogni immobile."
        ),
        backstory=(
            "Portfolio manager con specializzazione in real estate italiano. "
            "Hai confrontato centinaia di opportunità di investimento. "
            "Il tuo giudizio è obiettivo e basato solo sui numeri."
        ),
        llm=llm, verbose=False, allow_delegation=False,
    )

    task_comparison = Task(
        description=(
            f"Obiettivo investitore: {goal_label}\n\n"
            f"Immobili:\n{props_summary}\n\n"
            "Dai calcoli ROI, produci il report finale in JSON:\n"
            "{\n"
            '  "ranked_results": [\n'
            "    {\n"
            '      "index": numero immobile (1-based),\n'
            '      "rank": posizione classifica (1=migliore),\n'
            '      "total_investment_mid": numero € (acquisto + ristrutturazione media),\n'
            '      "net_roi_mid": numero % ROI netto scenario medio,\n'
            '      "payback_mid": numero anni payback scenario medio,\n'
            '      "best_scenario": "nome scenario consigliato",\n'
            '      "risk_summary": "2 righe rischi specifici questo immobile"\n'
            "    }\n"
            "  ],\n"
            '  "winner_index": numero immobile vincitore,\n'
            '  "winner_reason": "perché questo è il migliore (3-4 righe)",\n'
            '  "comparison_table": "tabella ASCII comparativa con tutti i KPI",\n'
            '  "market_notes": "note generali di mercato utili"\n'
            "}"
        ),
        expected_output="JSON con ranking, vincitore e tabella comparativa",
        agent=comparison_analyst,
        context=[task_costs, task_roi],
    )

    crew = Crew(
        agents=[cost_estimator, roi_calculator, comparison_analyst],
        tasks=[task_costs, task_roi, task_comparison],
        process=Process.sequential,
        verbose=False,
    )

    try:
        crew.kickoff()
    except Exception as e:
        logger.error(f"Crew error: {e}")
        raise RuntimeError(f"Errore agenti AI: {e}")

    # ── Parsing output agenti ──
    costs_data      = _parse_json_list(task_costs.output.raw if task_costs.output else "")
    roi_data        = _parse_json_list(task_roi.output.raw if task_roi.output else "")
    comparison_data = _parse_json(task_comparison.output.raw if task_comparison.output else "")

    results: list[PropertyROIResult] = []
    ranked = comparison_data.get("ranked_results", [])

    for i, prop in enumerate(data.properties):
        prop_roi  = next((r for r in roi_data if r.get("index") == i + 1), {})
        prop_rank = next((r for r in ranked  if r.get("index") == i + 1), {})

        scenarios = []
        for sc in prop_roi.get("scenarios", []):
            try:
                scenarios.append(RenovationScenario(
                    name=sc.get("name", "Scenario"),
                    renovation_cost=float(sc.get("renovation_cost", 0)),
                    duration_months=int(sc.get("duration_months", 6)),
                    estimated_value_after=float(sc.get("estimated_value_after", prop.purchase_price)),
                    estimated_rent_after=float(sc.get("estimated_rent_after", 0)),
                    roi_percent=float(sc.get("roi_percent", 0)),
                    payback_years=float(sc.get("payback_years", 0)),
                    risk_level=sc.get("risk_level", "Medio"),
                    description=sc.get("description", ""),
                ))
            except Exception:
                continue

        if not scenarios:
            scenarios = _fallback_scenarios(prop)

        results.append(PropertyROIResult(
            label=prop.label,
            address=prop.address,
            purchase_price=prop.purchase_price,
            price_per_sqm=prop.purchase_price / prop.size_sqm if prop.size_sqm > 0 else 0,
            scenarios=scenarios,
            best_scenario=prop_roi.get("best_scenario", scenarios[1].name if len(scenarios) > 1 else scenarios[0].name),
            total_investment_mid=prop_rank.get("total_investment_mid",
                prop.purchase_price + (scenarios[1].renovation_cost if len(scenarios) > 1 else 0)),
            net_roi_mid=prop_rank.get("net_roi_mid",
                scenarios[1].roi_percent if len(scenarios) > 1 else 0),
            payback_mid=prop_rank.get("payback_mid",
                scenarios[1].payback_years if len(scenarios) > 1 else 0),
            risk_summary=prop_rank.get("risk_summary", "Analisi non disponibile."),
            rank=prop_rank.get("rank", i + 1),
        ))

    results.sort(key=lambda r: r.rank)

    winner_idx = comparison_data.get("winner_index", 1)
    winner = next(
        (p for p in data.properties if data.properties.index(p) + 1 == winner_idx),
        data.properties[0]
    )

    return CompareROIResponse(
        results=results,
        winner_label=winner.label,
        winner_reason=comparison_data.get("winner_reason", "Miglior rapporto ROI/rischio."),
        comparison_summary=comparison_data.get("comparison_table", ""),
        market_notes=comparison_data.get("market_notes", ""),
        disclaimer=DISCLAIMER,
        remaining_usage=0,
    )


# ── Helpers ────────────────────────────────────────────────────

def _fallback_scenarios(prop) -> list[RenovationScenario]:
    """Scenari deterministici di fallback se l'AI non risponde."""
    base = prop.purchase_price
    sqm  = prop.size_sqm or 80

    scenarios_cfg = [
        ("Conservativo", 600,  4, 0.12, 0.05, "Basso"),
        ("Medio",        900,  6, 0.18, 0.08, "Medio"),
        ("Premium",     1400,  9, 0.28, 0.12, "Alto"),
    ]
    results = []
    for name, cost_sqm, months, val_uplift, rent_yield, risk in scenarios_cfg:
        reno     = cost_sqm * sqm
        val_after = base * (1 + val_uplift)
        rent     = val_after * rent_yield / 12
        roi      = ((val_after - base - reno) / (base + reno)) * 100
        payback  = (base + reno) / (rent * 12) if rent > 0 else 99
        results.append(RenovationScenario(
            name=name,
            renovation_cost=reno,
            duration_months=months,
            estimated_value_after=val_after,
            estimated_rent_after=rent,
            roi_percent=round(roi, 1),
            payback_years=round(payback, 1),
            risk_level=risk,
            description=f"Scenario {name.lower()}: €{cost_sqm}/mq di ristrutturazione su {sqm}mq.",
        ))
    return results


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