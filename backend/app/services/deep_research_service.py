# backend/app/services/deep_research_service.py
#
# AGGIORNATO: template few-shot inseriti nei backstory degli agenti.
# Ogni agente conosce la struttura di output attesa e le formule corrette.
# I dati reali vengono sempre cercati sul web tramite search_tool.

import logging
from typing import Optional

from crewai import Agent, Task, Crew, Process

from app.agents.llm_factory import get_llm
from app.agents.search_tool import get_search_tool

logger = logging.getLogger(__name__)

# ── Template few-shot ─────────────────────────────────────────────────────────
# Estratti da agent_templates.md — versione compatta per i backstory

_TEMPLATE_MARKET_SCOUT = """
Sei un esperto analista di mercato immobiliare con 15 anni di esperienza.
Conosci OMI, Immobiliare.it, Idealista, Tecnocasa, Nomisma e i principali
portali internazionali. Cerchi SEMPRE dati reali sul web e non inventi mai
prezzi o statistiche.

PORTALI PER PAESE:
- Italia: immobiliare.it, idealista.it, casa.it, realadvisor.it
- Spagna: idealista.com, fotocasa.es
- Portogallo: idealista.pt, imovirtual.com
- Francia: seloger.com, leboncoin.fr
- Germania: immoscout24.de, immowelt.de
- UK: rightmove.co.uk, zoopla.co.uk
- Olanda: funda.nl, pararius.nl
- USA: zillow.com, realtor.com
- UAE: propertyfinder.ae, bayut.com

STRUTTURA OUTPUT OBBLIGATORIA per ogni città/zona analizzata:

| Indicatore           | Valore          | Fonte          |
|----------------------|-----------------|----------------|
| Prezzo medio vendita | [DATO] €/mq     | [fonte + data] |
| Prezzo medio affitto | [DATO] €/mq/mese| [fonte + data] |
| Variazione YoY       | [DATO] %        | [fonte + data] |
| Rendimento lordo     | ([affitto]×12)/[vendita]×100 = [DATO] % |
| Trend                | CRESCITA/STABILE/CALO | [motivazione] |

Quartieri più costosi (minimo 2): [nome]: [DATO] €/mq — [motivazione]
Quartieri più economici (minimo 2): [nome]: [DATO] €/mq — [motivazione]

REGOLA CRITICA: cerca SEMPRE il micro-mercato specifico (zona/quartiere),
non la media della città. Cita URL e data per ogni dato numerico.
Se un dato non è disponibile scrivi "dato non disponibile".
"""

_TEMPLATE_PROPERTY_ANALYST = """
Sei un perito immobiliare certificato con esperienza in valutazioni
per investimento. Usi solo dati documentati e formule precise.

FORMULE UNIVERSALI DA APPLICARE SEMPRE:

YIELD LORDO = (affitto mensile × 12) / prezzo acquisto × 100
YIELD NETTO = (affitto annuo × 0,79 - spese condominiali annue) / prezzo acquisto × 100
PAYBACK = prezzo acquisto / reddito netto annuo

CANONE CONCORDATO: se zona alta tensione abitativa → cedolare 10% invece di 21%
Ricalcola: yield netto = (affitto annuo × 0,90 - spese cond.) / prezzo × 100

YIELD AIRBNB = (prezzo notte × notti occupate × 0,79 - costi gestione) / prezzo × 100
Costi gestione Airbnb = 28% del ricavo lordo (pulizie + commissioni + utenze)
Cerca tasso occupazione su bnbval.com o airdna.co per la zona specifica.

SCORE INVESTIMENTO 0-100 = media ponderata:
- Yield netto (peso 30%)
- Scostamento prezzo da mercato (peso 25%)
- Liquidità zona (peso 20%)
- Potenziale flipping o rivalutazione (peso 25%)

STRUTTURA OUTPUT per ogni immobile:

Prezzo richiesto: [€] → [€/mq]
Prezzo medio zona: [€/mq] (fonte: [URL])
Scostamento: [+/-]% [sopra/sotto] mercato
Canone mensile stimato: [€] (fonte: [URL])
Yield lordo: [%] | Yield netto: [%] | Payback: [anni]
Score investimento: [0-100] — [motivazione con pesi]
Strategia consigliata: buy-to-let lungo / buy-to-let breve / flipping / evita

VERDICT PER CONFRONTO (se più immobili):
"Acquisterei [immobile X] perché [€/mq] vs media zona [€/mq],
yield netto [%], margine [€] e tempo vendita stimato [mesi]."
Massimo 5 righe. Sempre con numeri a supporto.
"""

_TEMPLATE_RISK_ASSESSOR = """
Sei uno specialista in due diligence immobiliare e analisi di rischio.
Valuti ogni fattore con evidenze concrete trovate sul web.

CHECKLIST RISCHI DA VALUTARE (livello ALTO/MEDIO/BASSO):

Per BUY-TO-LET:
- Inquilino moroso: cerca dati sfratti/1000 contratti per la città
- Normative affitti brevi: cerca aggiornamenti CIN e limiti giorni 2026
- Deprezzamento: YoY prezzi zona → rischio se negativo o < 1%
- Costi manutenzione: stima 1% valore immobile/anno

Per FLIPPING:
- Rischio mercato: previsioni prezzi zona 2026-2027
- Rischio cantiere: sforamento medio 10-15% del budget ristrutturazione
- Rischio liquidità: tempo medio vendita ristrutturati in zona
- Vincoli urbanistici: piano regolatore, delibere condominiali

TEMPLATE RISCHI:
| Rischio           | Evidenza trovata sul web     | Livello | Mitigazione        |
|-------------------|------------------------------|---------|--------------------|
| [nome rischio]    | [dato reale con fonte]       | A/M/B   | [azione concreta]  |

TEMPLATE OPPORTUNITÀ:
| Opportunità        | Evidenza                     | Impatto stimato    |
|--------------------|------------------------------|--------------------|
| [nome opportunità] | [dato reale con fonte URL]   | +[%] valore stimato|

Cerca sempre: piani di riqualificazione urbana, nuove infrastrutture metro,
sviluppi residenziali, agevolazioni fiscali specifiche per la zona.

Per FLIPPING cerca anche:
FORMULA BREAK-EVEN PRICE = valore rivendita stimato - costi fissi
  (ristrutturazione + notaio + agenzia + IMU)
Se prezzo richiesto > break-even → segnalare come rischio critico.
"""

_TEMPLATE_INVESTMENT_STRATEGIST = """
Sei un consulente d'investimento immobiliare senior. Le tue raccomandazioni
includono sempre numeri precisi, orizzonte temporale e strategia di uscita.

STRUTTURA OUTPUT OBBLIGATORIA:

1. RISPOSTA DIRETTA alla query (1-2 frasi con numeri)

2. TABELLA COMPARATIVA (se più immobili):
| Metrica                    | Imm.A  | Imm.B  | Imm.C  |
|----------------------------|--------|--------|--------|
| Prezzo (€)                 | [DATO] | [DATO] | [DATO] |
| €/mq                       | [DATO] | [DATO] | [DATO] |
| Scostamento mercato (%)    | [DATO] | [DATO] | [DATO] |
| Yield lordo (%)            | [DATO] | [DATO] | [DATO] |
| Yield netto (%)            | [DATO] | [DATO] | [DATO] |
| Payback (anni)             | [DATO] | [DATO] | [DATO] |
| Margine flipping netto (%) | [DATO] | [DATO] | [DATO] |
| Score 0-100                | [DATO] | [DATO] | [DATO] |
| Strategia consigliata      | [txt]  | [txt]  | [txt]  |

3. CLASSIFICA (dal migliore al peggiore):
Rank 1: [immobile] — [motivazione con numeri]
Rank N: [immobile] — [motivazione con numeri]

4. STRATEGIA per il migliore:
- Orizzonte temporale: [anni]
- Rendimento atteso: [%] annuo
- Exit strategy: [rivendita/affitto/altro]
- Prezzo massimo acquisto (break-even): [€]

5. AVVERTENZE (2-3 punti critici da verificare prima dell'acquisto)

6. VERDICT FINALE:
COMPRA ✓ / VALUTA CON CAUTELA ⚠️ / EVITA ✗
con motivazione in 3 righe e numeri.

FORMULE PER FLIPPING:
MARGINE LORDO = prezzo rivendita - (acquisto + ristrutturazione + spese)
MARGINE NETTO = margine lordo - (margine lordo × 0,26) [plusvalenza <5 anni]
ROI ANNUALIZZATO = (margine netto / totale investimento / anni) × 100
Spese standard: notaio 2% + agenzia 3% + IMU ~1% del prezzo acquisto

FORMULA ROI TOTALE 5 ANNI:
= [(cash-flow annuo × 5) + (valore futuro - investimento)] / investimento × 100
Valore futuro = prezzo acquisto × (1 + crescita YoY)^5
"""


def run_deep_research(
    query: str,
    properties: list[dict],
    plan: str = "free",
    user_id: Optional[int] = None,
) -> dict:
    """
    Deep Research immobiliare con 4 agenti specializzati.
    I template few-shot nei backstory guidano struttura e formule.
    I dati reali vengono cercati sul web durante l'esecuzione.
    """
    logger.info(
        f"Deep Research START — user={user_id}, plan={plan}, "
        f"properties={len(properties)}, query='{query[:60]}'"
    )

    llm         = get_llm(plan=plan)
    search_tool = get_search_tool(plan=plan)
    props_text  = _format_properties(properties)

    # ── Agente 1: Market Scout ────────────────────────────────────────────
    market_scout = Agent(
        role="Market Scout Immobiliare",
        goal=(
            "Trovare i prezzi reali di vendita e affitto per la zona "
            "specifica di ogni immobile. Analizzare il micro-mercato "
            "locale, non la media della città."
        ),
        backstory=_TEMPLATE_MARKET_SCOUT,
        llm=llm,
        tools=[search_tool] if search_tool else [],
        verbose=True,
        allow_delegation=False,
    )

    # ── Agente 2: Property Analyst ────────────────────────────────────────
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

    # ── Agente 3: Risk & Opportunity Assessor ─────────────────────────────
    risk_assessor = Agent(
        role="Risk & Opportunity Assessor",
        goal=(
            "Identificare rischi concreti e opportunità reali per ogni "
            "immobile. Valutare ogni fattore ALTO/MEDIO/BASSO con "
            "evidenze trovate sul web."
        ),
        backstory=_TEMPLATE_RISK_ASSESSOR,
        llm=llm,
        tools=[search_tool] if search_tool else [],
        verbose=True,
        allow_delegation=False,
    )

    # ── Agente 4: Investment Strategist ───────────────────────────────────
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

    # ── Task 1: Analisi mercato ───────────────────────────────────────────
    task_market = Task(
        description=(
            f"QUERY INVESTITORE: {query}\n\n"
            f"PROPRIETÀ DA ANALIZZARE:\n{props_text}\n\n"
            f"Per ogni proprietà:\n"
            f"1. Cerca il micro-mercato SPECIFICO della zona (non la media città)\n"
            f"2. Trova prezzi vendita €/mq per quella zona su portali locali\n"
            f"3. Trova canoni affitto €/mq/mese per quella zona\n"
            f"4. Trova variazione YoY prezzi e trend attuale\n"
            f"5. Identifica i quartieri più costosi e più economici\n"
            f"6. Cita URL e data per ogni dato — mai inventare numeri"
        ),
        expected_output=(
            "Per ogni zona: prezzo vendita €/mq, affitto €/mq/mese, "
            "YoY%, trend, quartieri costosi/economici. "
            "Ogni dato con fonte URL citata."
        ),
        agent=market_scout,
    )

    # ── Task 2: Valutazione immobili ──────────────────────────────────────
    task_property = Task(
        description=(
            f"Usando i dati di mercato trovati, valuta ogni immobile:\n\n"
            f"PROPRIETÀ:\n{props_text}\n\n"
            f"Per ogni immobile applica le formule esatte:\n"
            f"1. Calcola €/mq e scostamento dal mercato locale (%)\n"
            f"2. Trova canone mensile reale per quella zona e tipologia\n"
            f"3. Calcola yield lordo, yield netto (×0,79 - spese cond.), payback\n"
            f"4. Se da ristrutturare: calcola margine flipping con formula\n"
            f"   (notaio 2% + agenzia 3% + IMU 1% + costo ristr. da cronoshare.it)\n"
            f"5. Assegna score 0-100 con media ponderata dei 4 fattori\n"
            f"6. Indica strategia: buy-to-let lungo/breve/flipping/evita"
        ),
        expected_output=(
            "Per ogni immobile: €/mq, scostamento%, yield lordo%, "
            "yield netto%, payback anni, margine flipping% se applicabile, "
            "score 0-100 con breakdown, strategia consigliata."
        ),
        agent=property_analyst,
        context=[task_market],
    )

    # ── Task 3: Rischi e opportunità ──────────────────────────────────────
    task_risk = Task(
        description=(
            f"Analizza rischi e opportunità per ogni immobile:\n\n"
            f"PROPRIETÀ:\n{props_text}\n\n"
            f"Per ogni zona cerca:\n"
            f"1. Dati sfratti/morosità per la città\n"
            f"2. Aggiornamenti normative affitti brevi 2026 (CIN, limiti)\n"
            f"3. Previsioni prezzi zona 2026-2027\n"
            f"4. Piani riqualificazione urbana o nuove infrastrutture\n"
            f"5. Per immobili da ristrutturare: calcola break-even price\n"
            f"   (valore rivendita - costi fissi = prezzo max acquisto)\n"
            f"Valuta ogni rischio: ALTO/MEDIO/BASSO con evidenza."
        ),
        expected_output=(
            "Tabella rischi con livello A/M/B e fonte. "
            "Tabella opportunità con impatto stimato. "
            "Break-even price per immobili da ristrutturare."
        ),
        agent=risk_assessor,
        context=[task_market, task_property],
    )

    # ── Task 4: Raccomandazione finale ────────────────────────────────────
    task_recommendation = Task(
        description=(
            f"Sintetizza tutto in una raccomandazione finale strutturata.\n\n"
            f"QUERY ORIGINALE: {query}\n\n"
            f"Produci OBBLIGATORIAMENTE:\n"
            f"1. Risposta diretta alla query (1-2 frasi con numeri)\n"
            f"2. Tabella comparativa con tutte le metriche per ogni immobile\n"
            f"3. Classifica dal migliore al peggiore con motivazione numerica\n"
            f"4. Strategia dettagliata per il primo classificato\n"
            f"5. 2-3 avvertenze critiche da verificare prima dell'acquisto\n"
            f"6. VERDICT: COMPRA ✓ / VALUTA CON CAUTELA ⚠️ / EVITA ✗\n"
            f"   con motivazione in 3 righe e numeri a supporto"
        ),
        expected_output=(
            "Risposta diretta, tabella comparativa completa, classifica "
            "motivata, strategia con numeri, avvertenze, verdict finale."
        ),
        agent=investment_strategist,
        context=[task_market, task_property, task_risk],
    )

    # ── Lancia crew ───────────────────────────────────────────────────────
    crew = Crew(
        agents=[market_scout, property_analyst, risk_assessor, investment_strategist],
        tasks=[task_market, task_property, task_risk, task_recommendation],
        process=Process.sequential,
        verbose=True,
    )

    logger.info("CrewAI kickoff...")
    result = crew.kickoff()
    logger.info("CrewAI completato")

    task_outputs = result.tasks_output if hasattr(result, "tasks_output") else []

    def get_output(idx: int) -> str:
        try:
            return str(task_outputs[idx].raw) if idx < len(task_outputs) else ""
        except Exception:
            return ""

    return {
        "summary":                   str(result),
        "market_overview":           get_output(0),
        "properties_analysis":       _parse_properties_analysis(get_output(1), properties),
        "risks_opportunities":       get_output(2),
        "investment_recommendation": get_output(3),
        "remaining_usage":           None,
    }


def _format_properties(properties: list[dict]) -> str:
    if not properties:
        return "Nessuna proprietà specificata."
    parts = []
    for i, p in enumerate(properties, 1):
        lines = [f"Proprietà {i}:"]
        if p.get("address"):   lines.append(f"  Indirizzo:  {p['address']}")
        if p.get("price"):     lines.append(f"  Prezzo:     {p['price']:,.0f} €")
        if p.get("size_sqm"):  lines.append(f"  Superficie: {p['size_sqm']} mq")
        if p.get("price") and p.get("size_sqm"):
            lines.append(f"  €/mq:       {p['price'] / p['size_sqm']:,.0f}")
        if p.get("rooms"):     lines.append(f"  Locali:     {p['rooms']}")
        if p.get("condition"): lines.append(f"  Condizioni: {p['condition']}")
        if p.get("notes"):     lines.append(f"  Note:       {p['notes']}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def _parse_properties_analysis(raw_text: str, properties: list[dict]) -> list[dict]:
    if not raw_text:
        return [
            {"address": p.get("address", f"Proprietà {i+1}"),
             "recommendation": "Analisi non disponibile",
             "risks": [], "opportunities": []}
            for i, p in enumerate(properties)
        ]
    return [
        {"address":        p.get("address", f"Proprietà {i+1}"),
         "price_asked":    p.get("price"),
         "size_sqm":       p.get("size_sqm"),
         "recommendation": raw_text,
         "risks":          [],
         "opportunities":  []}
        for i, p in enumerate(properties)
    ]