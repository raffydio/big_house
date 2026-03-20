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

# ── Template agenti ───────────────────────────────────────────────────────────

_TEMPLATE_PROPERTY_VALUATOR = """
Sei un perito immobiliare esperto con 15 anni di esperienza in valutazioni
per investimento in Italia. Cerchi sempre dati reali sul web con fonti citate.

Per ogni immobile fornito cerchi su portali locali:
- immobiliare.it, idealista.it, casa.it, realadvisor.it

Per ogni immobile devi trovare:
- Prezzo medio di vendita euro/mq nella zona specifica (non media citta)
- Canone medio di affitto euro/mq/mese nella zona
- Prezzi di immobili ristrutturati simili nella zona (se applicabile)
- Costi medi di ristrutturazione da cronoshare.it per quella citta

REGOLA FONDAMENTALE: cita sempre fonte e data per ogni dato numerico.
Se un dato non e disponibile sul web, indica "dato non disponibile" senza inventare.
NON usare tabelle markdown. Scrivi tutto in testo chiaro con elenchi puntati.
"""

_TEMPLATE_FINANCIAL_ANALYST = """
Sei un analista finanziario specializzato in investimenti immobiliari italiani.
Applichi formule precise e confronti gli immobili in modo chiaro.

FORMULA RATA MUTUO (quando applicabile):
Rata mensile = P * [i(1+i)^n] / [(1+i)^n - 1]
dove P = capitale, i = tasso mensile (tasso annuo / 12), n = numero mesi

Cerca il tasso mutuo fisso attuale su mutui.it o facile.it e citalo con fonte.

Per ogni immobile calcoli le metriche rilevanti in base all'obiettivo.
Usa i dati reali trovati dal Property Valuator.

NON usare tabelle markdown con trattini e pipe.
Presenta i numeri come elenchi puntati per ogni immobile, ad esempio:

  Immobile 1 - Via Roma 10, Napoli
  - Prezzo acquisto: 250.000 euro
  - Costo ristrutturazione: 40.000 euro
  - Costi accessori (notaio 2% + agenzia 3% + IMU 1%): 15.000 euro
  - Investimento totale: 305.000 euro
  - Prezzo rivendita stimato: 340.000 euro
  - Margine di profitto lordo: 35.000 euro
  - Margine %: 11.5%
  - Score: 72/100 (breakdown: scostamento 80/100, margine 65/100, liquidita 70/100, rischio 75/100)
"""

_TEMPLATE_COMPARATOR = """
Sei un consulente senior di investimenti immobiliari.
Produci raccomandazioni con numeri precisi e motivazioni concrete.

Il tuo compito e sintetizzare le analisi in una raccomandazione finale chiara.

STRUTTURA OUTPUT OBBLIGATORIA (testo puro, nessuna tabella markdown):

1. RISPOSTA DIRETTA (2-3 frasi con i numeri chiave)

2. CONFRONTO IMMOBILI
   Per ogni immobile: nome, metrica principale, score, 1 pro e 1 contro.

3. CLASSIFICA DAL MIGLIORE AL PEGGIORE
   Con motivazione numerica per ogni posizione.

4. IMMOBILE CONSIGLIATO
   Nome, strategia dettagliata, numeri chiave, orizzonte temporale.

5. AVVERTENZE CRITICHE (2-3 punti)
   Solo le piu importanti da verificare prima dell'acquisto.

6. VERDICT: COMPRA / VALUTA CON CAUTELA / EVITA
   Con 3 numeri a supporto e motivazione in 2 righe.

NON usare mai tabelle markdown con | e ----.
Usa solo testo, elenchi puntati e numeri.
"""

# ── Istruzioni finanziarie specifiche per obiettivo ───────────────────────────

_GOAL_CONTEXT = {
    "flipping": {
        "label": "Flipping — Vendita post-ristrutturazione",
        "horizon": "12-18 mesi",
        "financial_instructions": """
Per ogni immobile calcola il MARGINE DI FLIPPING:

1. Costo totale acquisto = prezzo + costi accessori (notaio 2% + agenzia 3% + IMU 1%)
2. Costo ristrutturazione = budget indicato (o stima da cronoshare.it se non indicato)
3. Investimento totale = costo acquisto + ristrutturazione
4. Prezzo rivendita stimato = euro/mq ristrutturati zona * superficie
5. Margine lordo = prezzo rivendita stimato - investimento totale
6. Margine % = (margine lordo / investimento totale) * 100
7. ROI annualizzato = margine % / 1.5 * 100 (su base 18 mesi)
8. Break-even price = prezzo rivendita - ristrutturazione - costi accessori

Score 0-100 pesato su:
- Scostamento prezzo acquisto da mercato (25%): piu sotto mercato = score alto
- Margine flipping % (35%): target 20%+ = score alto
- Liquidita zona (25%): stima dalla vivacita mercato locale
- Rischio cantiere (15%): stato immobile e complessita ristrutturazione

NON calcolare yield da affitto o cash-flow mensile per questo obiettivo.
""",
    },
    "affitto_lungo": {
        "label": "Affitto a lungo termine",
        "horizon": "10-15 anni",
        "financial_instructions": """
Per ogni immobile calcola i PARAMETRI DI REDDITEZZA DA AFFITTO:

1. Canone mensile stimato = euro/mq/mese zona * superficie (o canone indicato)
2. Ricavo lordo annuo = canone * 12
3. Cedolare secca 21% = ricavo lordo * 0.21
4. Spese condominiali annue = dato reale o stima 600-1200 euro/anno
5. Reddito netto annuo = lordo - cedolare - spese cond.
6. Acconto 20% (o % indicata) = prezzo * 0.20
7. Mutuo = prezzo - acconto
8. Cerca tasso mutuo fisso attuale su mutui.it
9. Rata mensile mutuo = calcola con formula esatta
10. Cash-flow mensile netto = (reddito netto / 12) - rata mutuo
11. Yield lordo % = (lordo / prezzo) * 100
12. Yield netto su capitale proprio % = (netto / acconto) * 100
13. Payback anni = prezzo / reddito netto

Score 0-100 pesato su:
- Yield lordo % (30%): target 6%+ = score alto
- Cash-flow mensile (30%): positivo = score alto
- Scostamento prezzo da mercato (20%)
- Trend affitti zona (20%)
""",
    },
    "affitto_breve": {
        "label": "Affitto breve (Airbnb/Booking)",
        "horizon": "3-5 anni",
        "financial_instructions": """
Per ogni immobile calcola i PARAMETRI AIRBNB:

Cerca su bnbval.com o airdna.co per la zona specifica:
1. Prezzo medio notte zona
2. Tasso di occupazione zona %
3. Notti occupate anno = 365 * tasso occupazione
4. Ricavo lordo annuo = notti * prezzo notte
5. Costi gestione = lordo * 0.28
6. Cedolare secca = (lordo - gestione) * 0.21
7. Reddito netto annuo = lordo - gestione - cedolare
8. Acconto 20% + mutuo + rata mensile (formula + tasso web)
9. Cash-flow mensile netto = (netto / 12) - rata mutuo
10. Yield lordo % = (lordo / prezzo) * 100
11. Yield netto su cap. proprio % = (netto / acconto) * 100
12. Payback anni = prezzo / reddito netto

Nota normativa CIN 2026: dal 3 immobile in poi scatta P.IVA obbligatoria.

Score 0-100 pesato su:
- Potenziale ricavo lordo annuo (30%)
- Tasso occupazione zona (30%)
- Cash-flow mensile (25%)
- Rischio normativo e stagionalita (15%)
""",
    },
    "prima_casa": {
        "label": "Prima casa con valorizzazione",
        "horizon": "5-10 anni",
        "financial_instructions": """
Per ogni immobile calcola i PARAMETRI PRIMA CASA:

1. Prezzo acquisto + costi accessori (prima casa: imposta 2% invece di 9%)
2. Acconto 10-20% + mutuo + rata mensile (formula + tasso web)
3. Sostenibilita rata: rata / reddito medio zona (target < 30%)
4. Crescita YoY zona trovata su portali: applica a 5 anni
5. Valore stimato a 5 anni = prezzo * (1 + crescita YoY)^5
6. Plusvalenza potenziale = valore 5y - prezzo acquisto
7. Se da ristrutturare: costo totale e valore post-ristr.
8. Risparmio affitto vs mutuo = canone zona - rata mutuo

Score 0-100 pesato su:
- Sostenibilita rata (30%): rata < 30% reddito = score alto
- Potenziale valorizzazione % a 5 anni (30%)
- Qualita zona e servizi (20%)
- Stato immobile e costi immediati (20%)
""",
    },
}


# ── Funzione pubblica principale ──────────────────────────────────────────────

def run_compare_roi(
    properties: list[dict],
    investment_goal: str = "affitto_lungo",
    plan: str = "free",
    user_id: Optional[int] = None,
) -> dict:
    """
    Calcola ROI comparativo per N immobili (max 5).

    Ogni property dict puo contenere:
        name, address, price, size_sqm, rooms, condition,
        renovation_budget, mortgage_rate, mortgage_years,
        down_payment_pct, current_rent, floor, elevator, notes
    """
    if not properties:
        raise ValueError("Almeno un immobile e richiesto.")
    if len(properties) > 5:
        properties = properties[:5]

    logger.info(
        f"[calcola_roi] START — user={user_id}, plan={plan}, "
        f"goal={investment_goal}, n_properties={len(properties)}"
    )

    kwargs = dict(
        properties=properties,
        investment_goal=investment_goal,
        plan=plan,
        user_id=user_id,
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
) -> dict:
    llm         = forced_llm or get_llm(plan=plan)
    search_mode = get_search_mode(llm_type)
    search_tool = get_search_tool(plan=plan, mode=search_mode)

    goal_info    = _GOAL_CONTEXT.get(investment_goal, _GOAL_CONTEXT["affitto_lungo"])
    goal_label   = goal_info["label"]
    goal_horizon = goal_info["horizon"]
    goal_fin_inst = goal_info["financial_instructions"]
    props_text   = _format_properties(properties)

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
    )

    task_financials = Task(
        description=(
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
    )

    task_comparison = Task(
        description=(
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