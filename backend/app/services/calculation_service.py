# backend/app/services/calculation_service.py
#
# SPRINT 2 — Aggiunto fallback Claude quando Gemini fallisce.
# Pattern identico a deep_research_service.py.

import logging
from typing import Optional

from crewai import Agent, Task, Crew, Process

from app.agents.llm_factory import (
    get_llm, get_fallback_llm, should_fallback, get_search_mode
)
from app.agents.search_tool import get_search_tool

logger = logging.getLogger(__name__)

# ── Template few-shot (invariati) ─────────────────────────────────────────────

_TEMPLATE_PROPERTY_VALUATOR = """
Sei un perito immobiliare e analista di mercato specializzato in valutazioni
per investimento. Cerchi sempre dati reali sul web con fonti citate.

STRUTTURA ANALISI MERCATO LOCALE (per ogni immobile):

Cerca su portali locali (immobiliare.it, idealista.it, casa.it, realadvisor.it):

Fonte | Vendita euro/mq | Affitto euro/mq/mese | Data
[portale 1] | [DATO] | [DATO] | [data]
[portale 2] | [DATO] | [DATO] | [data]
Media | [DATO] | [DATO] |

Prezzo richiesto: [euro] -> [euro/mq]
Scostamento da mercato: [+/-]% [sopra/sotto]
Margine trattativa realistico: [%] -> obiettivo [euro]

VALORE POST-RISTRUTTURAZIONE (se applicabile):
Cerca prezzi immobili ristrutturati in zona su portali.
Costo ristrutturazione: cerca su cronoshare.it euro/mq per [citta]
Valore stimato post-ristr.: [euro/mq ristrutturati] * [mq] = [euro]
Canone atteso post-ristr.: [euro/mese] (+10-15% rispetto a non ristrutturato)

SCENARIO AIRBNB:
Cerca su bnbval.com o airdna.co per la zona specifica:
- Prezzo medio notte: [euro]
- Tasso occupazione: [%] -> [notti]/anno
- Ricavo lordo annuo: [notti] * [euro/notte] = [euro]

REGOLA: cita URL per ogni dato. Se non trovato -> 'dato non disponibile'.
"""

_TEMPLATE_FINANCIAL_ANALYST = """
Sei un analista finanziario specializzato in investimenti immobiliari.
Applichi sempre le stesse formule precise per garantire confronti corretti.

FORMULA RATA MUTUO (calcola sempre):
Rata = P * [i(1+i)^n] / [(1+i)^n - 1]
P = capitale mutuo, i = tasso mensile (tasso annuo/12), n = mesi
Cerca tasso attuale su mutui.it, facile.it o mutuisupermarket.it

SCENARIO A - LUNGO TERMINE SENZA RISTRUTTURAZIONE:
Ricavo lordo annuo = canone * 12
Cedolare secca 21% = lordo * 0,21
Ricavo netto = lordo - tasse - spese condominiali annue
Cash-flow mensile = (ricavo netto / 12) - rata mutuo

Voce | Formula | Valore
Ricavo lordo annuo | canone * 12 | [euro]
Cedolare secca | lordo * 0,21 | [euro]
Spese condominiali | [dato reale o stima] | [euro]
Reddito netto annuo | lordo - tasse - spese | [euro]
Rata mutuo mensile | formula sopra | [euro]
Cash-flow mensile netto | reddito netto/12 - rata | [euro]
Yield lordo | (lordo / prezzo) * 100 | [%]
Yield netto cap.proprio | (netto / acconto) * 100 | [%]
Payback | prezzo / reddito netto | [anni]

SCENARIO B - LUNGO TERMINE + RISTRUTTURAZIONE:
Stesso schema con valori aggiornati post-ristrutturazione.
Delta rendimento: yield netto B - yield netto A = [+%]
Recupero investimento extra: costo ristr. / delta reddito annuo = [anni]

SCENARIO C - AFFITTO BREVE AIRBNB:
Notti occupate = 365 * [tasso occupazione]
Ricavo lordo = notti * prezzo notte
Costi gestione = lordo * 0,28
Cedolare secca = (lordo - gestione) * 0,21
Reddito netto = lordo - gestione - tasse
Cash-flow = reddito netto/12 - rata mutuo

TABELLA COMPARATIVA TRE SCENARI:
Metrica | Sc.A Lungo | Sc.B+Ristr | Sc.C Airbnb
Investimento totale | [euro] | [euro] | [euro]
Cash-flow mensile | [euro] | [euro] | [euro]
Yield lordo % | [%] | [%] | [%]
Yield netto % | [%] | [%] | [%]
Payback anni | [anni] | [anni] | [anni]
Valore immobile 5y | [euro] | [euro] | [euro]
ROI totale 5 anni % | [%] | [%] | [%]

FORMULA ROI TOTALE 5 ANNI:
= [(cash-flow annuo * 5) + (valore futuro - investimento)] / investimento * 100
Valore futuro = prezzo * (1 + crescita YoY trovata su web)^5
"""

_TEMPLATE_SCENARIO_RECOMMENDER = """
Sei un consulente senior di investimenti immobiliari. Produci sempre
raccomandazioni con numeri precisi e motivazioni concrete.

STRUTTURA OUTPUT OBBLIGATORIA:

1. TABELLA COMPARATIVA (replica da financial analyst con tutti i valori)

2. ANALISI MUTUO:
   Tasso fisso trovato: [%] (fonte: [URL])
   Rata mensile: [euro]
   Interessi totali [N] anni: [euro]
   Fisso vs variabile: [raccomandazione con motivazione]

3. RISCHI PER SCENARIO:
Rischio | Sc.A | Sc.B | Sc.C | Mitigazione
Tasso variabile | [.] | [.] | [.] | Preferire fisso
Inquilino moroso | [.] | [.] | N/A | Fideiussione
Normative Airbnb | N/A | N/A | [.] | Monitorare CIN
Sforamento ristr. | N/A | [.] | [.] | Contingenza +10%

4. SCENARIO CONSIGLIATO: [A, B o C]
   Motivazione con 3 numeri chiave.

5. BREAK-EVEN PRICE:
   FORMULA: rendita netta annua / yield minimo 4% = prezzo max sostenibile
   Calcolato: [euro]
   Non acquistare oltre [euro] con queste condizioni di mercato.

6. VERDICT FINALE:
   COMPRA / VALUTA CON CAUTELA / EVITA
   Scenario ottimale: [A/B/C]
   ROI atteso: [%] a [N] anni
   Cash-flow mensile: [+/-euro]
"""


# ── Funzione principale ───────────────────────────────────────────────────────

def run_compare_roi(
    purchase_price: float,
    size_sqm: float,
    location: str,
    current_rent: Optional[float] = None,
    target_rent: Optional[float] = None,
    renovation_budget: Optional[float] = None,
    mortgage_rate: Optional[float] = None,
    mortgage_years: Optional[int] = 20,
    down_payment_pct: Optional[float] = 30.0,
    plan: str = "free",
    user_id: Optional[int] = None,
) -> dict:
    """
    Calcola ROI immobiliare con tre scenari e analisi mutuo completa.
    SPRINT 2: tenta Gemini prima, fallback automatico su Claude se necessario.
    """
    logger.info(
        f"Calcola ROI START — user={user_id}, plan={plan}, "
        f"location='{location}', price={purchase_price}"
    )

    kwargs = dict(
        purchase_price=purchase_price,
        size_sqm=size_sqm,
        location=location,
        current_rent=current_rent,
        target_rent=target_rent,
        renovation_budget=renovation_budget,
        mortgage_rate=mortgage_rate,
        mortgage_years=mortgage_years,
        down_payment_pct=down_payment_pct,
        plan=plan,
        user_id=user_id,
    )

    # ── Tentativo 1: Gemini ──
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

    # ── Tentativo 2: Claude fallback ──
    fallback_llm = get_fallback_llm(plan=plan)
    if fallback_llm is None:
        raise RuntimeError(
            "Gemini non disponibile e ANTHROPIC_API_KEY non configurata. "
            "Aggiungi ANTHROPIC_API_KEY al .env per abilitare il fallback Claude."
        )

    logger.info(f"[calcola_roi] Avvio con Claude fallback — piano={plan}")
    return _run_roi_crew(llm_type="claude", forced_llm=fallback_llm, **kwargs)


def _run_roi_crew(
    purchase_price: float,
    size_sqm: float,
    location: str,
    current_rent: Optional[float],
    target_rent: Optional[float],
    renovation_budget: Optional[float],
    mortgage_rate: Optional[float],
    mortgage_years: int,
    down_payment_pct: float,
    plan: str,
    user_id: Optional[int],
    llm_type: str,
    forced_llm=None,
) -> dict:
    """Esegue il crew ROI con il provider LLM specificato."""
    llm         = forced_llm or get_llm(plan=plan)
    search_mode = get_search_mode(llm_type)
    search_tool = get_search_tool(plan=plan, mode=search_mode)

    logger.info(f"[calcola_roi] crew LLM={llm_type}, search_mode={search_mode}")

    down_payment    = purchase_price * (down_payment_pct / 100)
    mortgage_amount = purchase_price - down_payment

    property_summary = (
        f"Immobile: {location}\n"
        f"Prezzo acquisto: {purchase_price:,.0f} euro\n"
        f"Superficie: {size_sqm} mq\n"
        f"euro/mq: {purchase_price/size_sqm:,.0f}\n"
        f"Acconto ({down_payment_pct}%): {down_payment:,.0f} euro\n"
        f"Mutuo richiesto: {mortgage_amount:,.0f} euro\n"
        f"Durata mutuo: {mortgage_years} anni\n"
        + (f"Tasso indicativo: {mortgage_rate}%\n" if mortgage_rate else "Tasso: da cercare su web\n")
        + (f"Budget ristrutturazione: {renovation_budget:,.0f} euro\n" if renovation_budget else "")
        + (f"Affitto attuale: {current_rent:,.0f} euro/mese\n" if current_rent else "")
    )

    # ── Agenti ───────────────────────────────────────────────────────────────
    property_valuator = Agent(
        role="Property Valuator",
        goal=(
            "Trovare prezzi reali di vendita e affitto per la zona specifica. "
            "Valutare il prezzo richiesto rispetto al mercato. "
            "Stimare il valore post-ristrutturazione se applicabile."
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
            "Calcolare i tre scenari ROI con formule precise: "
            "yield lordo/netto, cash-flow mensile, payback, ROI 5 anni. "
            "Cercare il tasso mutuo reale attuale sul web."
        ),
        backstory=_TEMPLATE_FINANCIAL_ANALYST,
        llm=llm,
        tools=[search_tool] if search_tool else [],
        verbose=True,
        allow_delegation=False,
    )

    scenario_recommender = Agent(
        role="Scenario Recommender",
        goal=(
            "Confrontare i tre scenari, identificare i rischi per ognuno, "
            "raccomandare lo scenario ottimale con motivazione numerica "
            "e calcolare il break-even price."
        ),
        backstory=_TEMPLATE_SCENARIO_RECOMMENDER,
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    # ── Task ─────────────────────────────────────────────────────────────────
    task_valuation = Task(
        description=(
            f"IMMOBILE DA ANALIZZARE:\n{property_summary}\n\n"
            f"Il tuo compito:\n"
            f"1. Cerca prezzi vendita euro/mq per {location} su portali locali\n"
            f"2. Cerca canoni affitto mensili per {size_sqm:.0f} mq a {location}\n"
            f"3. Calcola scostamento del prezzo richiesto dal mercato\n"
            f"4. Se budget ristrutturazione indicato: cerca costi euro/mq su "
            f"   cronoshare.it per la citta e stima valore post-ristr.\n"
            f"5. Cerca dati Airbnb per la zona su bnbval.com o airdna.co\n"
            f"6. Cita URL e data per ogni dato trovato"
        ),
        expected_output=(
            "Prezzi mercato con fonti, scostamento%, canoni reali, "
            "valore post-ristrutturazione stimato, dati Airbnb zona."
        ),
        agent=property_valuator,
    )

    task_scenarios = Task(
        description=(
            f"Usando i dati di mercato trovati, calcola i tre scenari:\n\n"
            f"DATI IMMOBILE:\n{property_summary}\n\n"
            f"SCENARIO A - Lungo termine senza ristrutturazione:\n"
            f"- Cerca tasso mutuo fisso {mortgage_years}y su mutui.it o facile.it\n"
            f"- Calcola rata mensile con formula esatta\n"
            f"- Usa canone trovato per zona, applica tutte le formule\n"
            f"- Calcola cash-flow mensile netto\n\n"
            f"SCENARIO B - Lungo termine con ristrutturazione:\n"
            f"- Budget: {renovation_budget:,.0f} euro (se non indicato cerca costo medio)\n"
            f"- Usa canone post-ristrutturazione (+10-15%)\n"
            f"- Ricalcola tutti i parametri\n\n"
            f"SCENARIO C - Affitto breve Airbnb:\n"
            f"- Usa dati notti/occupazione trovati per la zona\n"
            f"- Applica costi gestione 28% e cedolare 21%\n\n"
            f"Per tutti: yield lordo%, yield netto%, cash-flow mensile, "
            f"payback, valore a 5 anni, ROI totale 5 anni.\n"
            f"Produci tabella comparativa dei tre scenari."
        ),
        expected_output=(
            "Tasso mutuo trovato con fonte, rata calcolata, "
            "tabella tre scenari con tutte le metriche, "
            "calcolo ROI totale 5 anni per ogni scenario."
        ),
        agent=financial_analyst,
        context=[task_valuation],
    )

    task_recommendation = Task(
        description=(
            f"Confronta i tre scenari e produci la raccomandazione finale.\n\n"
            f"DATI IMMOBILE:\n{property_summary}\n\n"
            f"Produci OBBLIGATORIAMENTE:\n"
            f"1. Tabella comparativa completa dei tre scenari\n"
            f"2. Analisi mutuo: fisso vs variabile con raccomandazione\n"
            f"3. Tabella rischi per scenario\n"
            f"4. Scenario consigliato con 3 numeri chiave a supporto\n"
            f"5. Break-even price: rendita netta / 4% = prezzo max sostenibile\n"
            f"6. Verdict: COMPRA / VALUTA CON CAUTELA / EVITA\n"
            f"   con scenario ottimale, ROI atteso e cash-flow mensile"
        ),
        expected_output=(
            "Tabella comparativa, analisi mutuo, rischi per scenario, "
            "scenario consigliato con motivazione, break-even price, "
            "verdict finale con numeri."
        ),
        agent=scenario_recommender,
        context=[task_valuation, task_scenarios],
    )

    # ── Esecuzione ────────────────────────────────────────────────────────────
    crew = Crew(
        agents=[property_valuator, financial_analyst, scenario_recommender],
        tasks=[task_valuation, task_scenarios, task_recommendation],
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

    scenarios_text = clean_agent_output(get_output(1))
    scenarios = _parse_scenarios(scenarios_text)

    return {
        "property_summary":      property_summary,
        "market_analysis":       clean_agent_output(get_output(0)),
        "scenarios":             scenarios,
        "scenarios_raw":         scenarios_text,
        "recommended_scenario":  clean_agent_output(get_output(2)),
        "remaining_usage":       None,
        "llm_used":              llm_type,
    }


def _parse_scenarios(raw_text: str) -> list[dict]:
    base = {
        "description": raw_text,
        "roi_percent": 0,
        "payback_years": 0,
        "risk_level": "medio",
    }
    return [
        {**base, "name": "Scenario A - Lungo termine"},
        {**base, "name": "Scenario B - Lungo termine + Ristrutturazione"},
        {**base, "name": "Scenario C - Affitto breve (Airbnb)"},
    ]