# backend/app/services/calculation_service.py
#
# AGGIORNATO: template few-shot ROI inseriti nei backstory degli agenti.
# Tre scenari: lungo termine, lungo termine + ristrutturazione, Airbnb.
# Formule precise per mutuo, yield, cash-flow, ROI 5 anni, break-even.

import logging
from typing import Optional

from crewai import Agent, Task, Crew, Process

from app.agents.llm_factory import get_llm
from app.agents.search_tool import get_search_tool

logger = logging.getLogger(__name__)

# ── Template few-shot ─────────────────────────────────────────────────────────

_TEMPLATE_PROPERTY_VALUATOR = """
Sei un perito immobiliare e analista di mercato specializzato in valutazioni
per investimento. Cerchi sempre dati reali sul web con fonti citate.

STRUTTURA ANALISI MERCATO LOCALE (per ogni immobile):

Cerca su portali locali (immobiliare.it, idealista.it, casa.it, realadvisor.it):

| Fonte       | Vendita €/mq | Affitto €/mq/mese | Data  |
|-------------|--------------|-------------------|-------|
| [portale 1] | [DATO]       | [DATO]            | [data]|
| [portale 2] | [DATO]       | [DATO]            | [data]|
| Media       | [DATO]       | [DATO]            |       |

Prezzo richiesto: [€] → [€/mq]
Scostamento da mercato: [+/-]% [sopra/sotto]
Margine trattativa realistico: [%] → obiettivo [€]

VALORE POST-RISTRUTTURAZIONE (se applicabile):
Cerca prezzi immobili ristrutturati in zona su portali.
Costo ristrutturazione: cerca su cronoshare.it €/mq per [città]
Valore stimato post-ristr.: [€/mq ristrutturati] × [mq] = [€]
Canone atteso post-ristr.: [€/mese] (+10-15% rispetto a non ristrutturato)

SCENARIO AIRBNB:
Cerca su bnbval.com o airdna.co per la zona specifica:
- Prezzo medio notte: [€]
- Tasso occupazione: [%] → [notti]/anno
- Ricavo lordo annuo: [notti] × [€/notte] = [€]

REGOLA: cita URL per ogni dato. Se non trovato → "dato non disponibile".
"""

_TEMPLATE_FINANCIAL_ANALYST = """
Sei un analista finanziario specializzato in investimenti immobiliari.
Applichi sempre le stesse formule precise per garantire confronti corretti.

FORMULA RATA MUTUO (calcola sempre):
Rata = P × [i(1+i)^n] / [(1+i)^n - 1]
P = capitale mutuo, i = tasso mensile (tasso annuo/12), n = mesi
Cerca tasso attuale su mutui.it, facile.it o mutuisupermarket.it

SCENARIO A — LUNGO TERMINE SENZA RISTRUTTURAZIONE:
Canone mensile: [cerca su portali per tipologia+zona]
Ricavo lordo annuo = canone × 12
Cedolare secca 21% = lordo × 0,21
  (se canone concordato zona alta tensione → usa 10%)
Ricavo netto = lordo - tasse - spese condominiali annue
  (spese cond. = cerca dato reale o usa 1,5 €/mq × 12)
Cash-flow mensile = (ricavo netto / 12) - rata mutuo

| Voce                    | Formula                          | Valore  |
|-------------------------|----------------------------------|---------|
| Ricavo lordo annuo      | canone × 12                      | [€]     |
| Cedolare secca          | lordo × 0,21                     | [€]     |
| Spese condominiali      | [dato reale o stima]             | [€]     |
| Reddito netto annuo     | lordo - tasse - spese            | [€]     |
| Rata mutuo mensile      | formula sopra                    | [€]     |
| Cash-flow mensile netto | reddito netto/12 - rata          | [€]     |
| Yield lordo             | (lordo / prezzo) × 100           | [%]     |
| Yield netto cap.proprio | (netto / acconto) × 100          | [%]     |
| Payback                 | prezzo / reddito netto           | [anni]  |

SCENARIO B — LUNGO TERMINE + RISTRUTTURAZIONE:
[Stesso schema con valori aggiornati post-ristrutturazione]
Delta rendimento: yield netto B - yield netto A = [+%]
Recupero investimento extra: costo ristr. / delta reddito annuo = [anni]

SCENARIO C — AFFITTO BREVE (AIRBNB):
Notti occupate = 365 × [tasso occupazione]
Ricavo lordo = notti × prezzo notte
Costi gestione = lordo × 0,28 (pulizie + commissioni + utenze)
Cedolare secca = (lordo - gestione) × 0,21
Reddito netto = lordo - gestione - tasse
Cash-flow = reddito netto/12 - rata mutuo

TABELLA COMPARATIVA TRE SCENARI:
| Metrica              | Sc.A Lungo | Sc.B+Ristr | Sc.C Airbnb |
|----------------------|------------|------------|-------------|
| Investimento totale  | [€]        | [€]        | [€]         |
| Cash-flow mensile    | [€]        | [€]        | [€]         |
| Yield lordo %        | [%]        | [%]        | [%]         |
| Yield netto %        | [%]        | [%]        | [%]         |
| Payback anni         | [anni]     | [anni]     | [anni]      |
| Valore immobile 5y   | [€]        | [€]        | [€]         |
| ROI totale 5 anni %  | [%]        | [%]        | [%]         |

FORMULA ROI TOTALE 5 ANNI:
= [(cash-flow annuo × 5) + (valore futuro - investimento)] / investimento × 100
Valore futuro = prezzo × (1 + crescita YoY trovata su web)^5

ANALISI MUTUO:
Tasso fisso vs variabile: [raccomandazione con dati Euribor trovati]
Interessi totali = (rata × mesi) - capitale = [€]
"""

_TEMPLATE_SCENARIO_RECOMMENDER = """
Sei un consulente senior di investimenti immobiliari. Produci sempre
raccomandazioni con numeri precisi e motivazioni concrete.

STRUTTURA OUTPUT OBBLIGATORIA:

1. TABELLA COMPARATIVA (replica da financial analyst con tutti i valori)

2. ANALISI MUTUO:
   Tasso fisso trovato: [%] (fonte: [URL])
   Rata mensile: [€]
   Interessi totali [N] anni: [€]
   Fisso vs variabile: [raccomandazione con motivazione]

3. RISCHI PER SCENARIO:
| Rischio              | Sc.A | Sc.B | Sc.C | Mitigazione          |
|----------------------|------|------|------|----------------------|
| Tasso variabile      | [•]  | [•]  | [•]  | Preferire fisso      |
| Inquilino moroso     | [•]  | [•]  | N/A  | Fideiussione         |
| Normative Airbnb     | N/A  | N/A  | [•]  | Monitorare CIN       |
| Sforamento ristr.    | N/A  | [•]  | [•]  | Contingenza +10%     |

4. SCENARIO CONSIGLIATO: [A, B o C]
   Motivazione con 3 numeri chiave.

5. BREAK-EVEN PRICE:
   FORMULA: rendita netta annua / yield minimo 4% = prezzo max sostenibile
   Calcolato: [€]
   Non acquistare oltre [€] con queste condizioni di mercato.

6. VERDICT FINALE:
   COMPRA ✓ / VALUTA CON CAUTELA ⚠️ / EVITA ✗
   Scenario ottimale: [A/B/C]
   ROI atteso: [%] a [N] anni
   Cash-flow mensile: [+/-€]
"""


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
    Template few-shot nei backstory guidano formule e struttura output.
    I dati reali (tassi, canoni, costi ristrutturazione) vengono cercati
    sul web durante l'esecuzione.
    """
    logger.info(
        f"Calcola ROI START — user={user_id}, plan={plan}, "
        f"location='{location}', price={purchase_price}"
    )

    llm         = get_llm(plan=plan)
    search_tool = get_search_tool(plan=plan)

    down_payment = purchase_price * (down_payment_pct / 100)
    mortgage_amount = purchase_price - down_payment

    property_summary = (
        f"Immobile: {location}\n"
        f"Prezzo acquisto: {purchase_price:,.0f} €\n"
        f"Superficie: {size_sqm} mq\n"
        f"€/mq: {purchase_price/size_sqm:,.0f}\n"
        f"Acconto ({down_payment_pct}%): {down_payment:,.0f} €\n"
        f"Mutuo richiesto: {mortgage_amount:,.0f} €\n"
        f"Durata mutuo: {mortgage_years} anni\n"
        + (f"Tasso indicativo: {mortgage_rate}%\n" if mortgage_rate else "Tasso: da cercare su web\n")
        + (f"Budget ristrutturazione: {renovation_budget:,.0f} €\n" if renovation_budget else "")
        + (f"Affitto attuale: {current_rent:,.0f} €/mese\n" if current_rent else "")
    )

    # ── Agente 1: Property Valuator ───────────────────────────────────────
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

    # ── Agente 2: Financial Analyst ───────────────────────────────────────
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

    # ── Agente 3: Scenario Recommender ────────────────────────────────────
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

    # ── Task 1: Valutazione immobile e mercato ────────────────────────────
    task_valuation = Task(
        description=(
            f"IMMOBILE DA ANALIZZARE:\n{property_summary}\n\n"
            f"Il tuo compito:\n"
            f"1. Cerca prezzi vendita €/mq per {location} su portali locali\n"
            f"2. Cerca canoni affitto mensili per {size_sqm:.0f} mq a {location}\n"
            f"3. Calcola scostamento del prezzo richiesto dal mercato\n"
            f"4. Se budget ristrutturazione indicato: cerca costi €/mq su "
            f"   cronoshare.it per la città e stima valore post-ristr.\n"
            f"5. Cerca dati Airbnb per la zona su bnbval.com o airdna.co\n"
            f"6. Cita URL e data per ogni dato trovato"
        ),
        expected_output=(
            "Prezzi mercato con fonti, scostamento%, canoni reali, "
            "valore post-ristrutturazione stimato, dati Airbnb zona."
        ),
        agent=property_valuator,
    )

    # ── Task 2: Calcolo tre scenari ───────────────────────────────────────
    task_scenarios = Task(
        description=(
            f"Usando i dati di mercato trovati, calcola i tre scenari:\n\n"
            f"DATI IMMOBILE:\n{property_summary}\n\n"
            f"SCENARIO A — Lungo termine senza ristrutturazione:\n"
            f"- Cerca tasso mutuo fisso {mortgage_years}y su mutui.it o facile.it\n"
            f"- Calcola rata mensile con formula esatta\n"
            f"- Usa canone trovato per zona, applica tutte le formule\n"
            f"- Calcola cash-flow mensile netto\n\n"
            f"SCENARIO B — Lungo termine con ristrutturazione:\n"
            f"- Budget: {renovation_budget:,.0f} € (se non indicato cerca costo medio)\n"
            f"- Usa canone post-ristrutturazione (+10-15%)\n"
            f"- Ricalcola tutti i parametri\n\n"
            f"SCENARIO C — Affitto breve Airbnb:\n"
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

    # ── Task 3: Raccomandazione finale ────────────────────────────────────
    task_recommendation = Task(
        description=(
            f"Confronta i tre scenari e produci la raccomandazione finale.\n\n"
            f"DATI IMMOBILE:\n{property_summary}\n\n"
            f"Produci OBBLIGATORIAMENTE:\n"
            f"1. Tabella comparativa completa dei tre scenari\n"
            f"2. Analisi mutuo: fisso vs variabile con raccomandazione\n"
            f"3. Tabella rischi per scenario (tasso, morosità, Airbnb, ristr.)\n"
            f"4. Scenario consigliato con 3 numeri chiave a supporto\n"
            f"5. Break-even price: rendita netta / 4% = prezzo max sostenibile\n"
            f"6. Verdict: COMPRA ✓ / VALUTA CON CAUTELA ⚠️ / EVITA ✗\n"
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

    # ── Lancia crew ───────────────────────────────────────────────────────
    crew = Crew(
        agents=[property_valuator, financial_analyst, scenario_recommender],
        tasks=[task_valuation, task_scenarios, task_recommendation],
        process=Process.sequential,
        verbose=True,
    )

    logger.info("CrewAI kickoff ROI...")
    result = crew.kickoff()
    logger.info("CrewAI ROI completato")

    task_outputs = result.tasks_output if hasattr(result, "tasks_output") else []

    def get_output(idx: int) -> str:
        try:
            return str(task_outputs[idx].raw) if idx < len(task_outputs) else ""
        except Exception:
            return ""

    # Estrai scenari dal testo dell'agente 2
    scenarios_text = get_output(1)
    scenarios = _parse_scenarios(scenarios_text)

    return {
        "property_summary":      property_summary,
        "market_analysis":       get_output(0),
        "scenarios":             scenarios,
        "scenarios_raw":         scenarios_text,
        "recommended_scenario":  get_output(2),
        "remaining_usage":       None,
    }


def _parse_scenarios(raw_text: str) -> list[dict]:
    """
    Struttura minima per i tre scenari — il testo completo
    è in scenarios_raw, qui teniamo i metadati per il frontend.
    """
    base = {"description": raw_text, "roi_percent": 0,
            "payback_years": 0, "risk_level": "medio"}
    return [
        {**base, "name": "Scenario A — Lungo termine"},
        {**base, "name": "Scenario B — Lungo termine + Ristrutturazione"},
        {**base, "name": "Scenario C — Affitto breve (Airbnb)"},
    ]