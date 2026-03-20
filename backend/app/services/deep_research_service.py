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
- USA: zillow.com, realtor.com
- UAE: propertyfinder.ae, bayut.com

STRUTTURA OUTPUT OBBLIGATORIA per ogni citta/zona analizzata:

Indicatore | Valore | Fonte
Prezzo medio vendita | [DATO] euro/mq | [fonte + data]
Prezzo medio affitto | [DATO] euro/mq/mese | [fonte + data]
Variazione YoY | [DATO] % | [fonte + data]
Rendimento lordo | ([affitto]*12)/[vendita]*100 = [DATO] %
Trend | CRESCITA/STABILE/CALO | [motivazione]

Quartieri piu costosi (minimo 2): [nome]: [DATO] euro/mq - [motivazione]
Quartieri piu economici (minimo 2): [nome]: [DATO] euro/mq - [motivazione]

REGOLA CRITICA: cerca SEMPRE il micro-mercato specifico (zona/quartiere),
non la media della citta. Cita URL e data per ogni dato numerico.
Se un dato non e disponibile scrivi 'dato non disponibile'.
"""

_TEMPLATE_PROPERTY_ANALYST = """
Sei un perito immobiliare certificato con esperienza in valutazioni
per investimento. Usi solo dati documentati e formule precise.

FORMULE UNIVERSALI DA APPLICARE SEMPRE:

YIELD LORDO = (affitto mensile * 12) / prezzo acquisto * 100
YIELD NETTO = (affitto annuo * 0,79 - spese condominiali annue) / prezzo acquisto * 100
PAYBACK = prezzo acquisto / reddito netto annuo

CANONE CONCORDATO: se zona alta tensione abitativa -> cedolare 10% invece di 21%

YIELD AIRBNB = (prezzo notte * notti occupate * 0,79 - costi gestione) / prezzo * 100
Costi gestione Airbnb = 28% del ricavo lordo
Cerca tasso occupazione su bnbval.com o airdna.co per la zona specifica.

SCORE INVESTIMENTO 0-100 = media ponderata:
- Yield netto (peso 30%)
- Scostamento prezzo da mercato (peso 25%)
- Liquidita zona (peso 20%)
- Potenziale flipping o rivalutazione (peso 25%)

STRUTTURA OUTPUT per ogni immobile:
Prezzo richiesto: [euro] -> [euro/mq]
Prezzo medio zona: [euro/mq] (fonte: [URL])
Scostamento: [+/-]% [sopra/sotto] mercato
Canone mensile stimato: [euro] (fonte: [URL])
Yield lordo: [%] | Yield netto: [%] | Payback: [anni]
Score investimento: [0-100] - [motivazione con pesi]
Strategia consigliata: buy-to-let lungo / buy-to-let breve / flipping / evita
"""

_TEMPLATE_RISK_ASSESSOR = """
Sei uno specialista in due diligence immobiliare e analisi di rischio.
Valuti ogni fattore con evidenze concrete trovate sul web.

CHECKLIST RISCHI DA VALUTARE (livello ALTO/MEDIO/BASSO):

Per BUY-TO-LET:
- Inquilino moroso: cerca dati sfratti/1000 contratti per la citta
- Normative affitti brevi: cerca aggiornamenti CIN e limiti giorni 2026
- Deprezzamento: YoY prezzi zona
- Costi manutenzione: stima 1% valore immobile/anno

Per FLIPPING:
- Rischio mercato: previsioni prezzi zona 2026-2027
- Rischio cantiere: sforamento medio 10-15% del budget ristrutturazione
- Rischio liquidita: tempo medio vendita ristrutturati in zona
- Vincoli urbanistici: piano regolatore, delibere condominiali

TEMPLATE RISCHI:
Rischio | Evidenza trovata sul web | Livello | Mitigazione

TEMPLATE OPPORTUNITA:
Opportunita | Evidenza | Impatto stimato

Cerca sempre: piani di riqualificazione urbana, nuove infrastrutture metro,
sviluppi residenziali, agevolazioni fiscali specifiche per la zona.
"""

_TEMPLATE_INVESTMENT_STRATEGIST = """
Sei un consulente d'investimento immobiliare senior. Le tue raccomandazioni
includono sempre numeri precisi, orizzonte temporale e strategia di uscita.

STRUTTURA OUTPUT OBBLIGATORIA:

1. RISPOSTA DIRETTA alla query (1-2 frasi con numeri)

2. TABELLA COMPARATIVA (se piu immobili):
Metrica | Imm.A | Imm.B | Imm.C
Prezzo (euro) | [DATO] | [DATO] | [DATO]
euro/mq | [DATO] | [DATO] | [DATO]
Scostamento mercato (%) | [DATO] | [DATO] | [DATO]
Yield lordo (%) | [DATO] | [DATO] | [DATO]
Yield netto (%) | [DATO] | [DATO] | [DATO]
Payback (anni) | [DATO] | [DATO] | [DATO]
Score 0-100 | [DATO] | [DATO] | [DATO]
Strategia consigliata | [txt] | [txt] | [txt]

3. CLASSIFICA (dal migliore al peggiore con motivazione numerica)

4. STRATEGIA per il migliore:
- Orizzonte temporale: [anni]
- Rendimento atteso: [%] annuo
- Exit strategy: [rivendita/affitto/altro]
- Prezzo massimo acquisto (break-even): [euro]

5. AVVERTENZE (2-3 punti critici da verificare prima dell'acquisto)

6. VERDICT FINALE:
COMPRA / VALUTA CON CAUTELA / EVITA
con motivazione in 3 righe e numeri.

REGOLA: il verdict deve sempre includere numeri.
"""


# ── Funzione principale ───────────────────────────────────────────────────────

def run_deep_research(
    query: str,
    properties: list[dict],
    plan: str = "free",
    user_id: Optional[int] = None,
) -> dict:
    """
    Deep Research immobiliare con 4 agenti specializzati.
    SPRINT 2: tenta Gemini prima, fallback automatico su Claude se necessario.
    """
    logger.info(
        f"Deep Research START — user={user_id}, plan={plan}, "
        f"properties={len(properties)}, query='{query[:60]}'"
    )

    # ── Tentativo 1: Gemini ──
    try:
        return _run_crew(
            query=query,
            properties=properties,
            plan=plan,
            user_id=user_id,
            llm_type="gemini",
        )
    except Exception as e:
        if should_fallback(e):
            logger.warning(
                f"[deep_research] Gemini fallito ({type(e).__name__}), "
                f"passo a Claude. Errore: {str(e)[:120]}"
            )
        else:
            # Errore non recuperabile (es. bug nel codice) — propaga
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
    )


def _run_crew(
    query: str,
    properties: list[dict],
    plan: str,
    user_id: Optional[int],
    llm_type: str,
    forced_llm=None,
) -> dict:
    """
    Esegue il crew CrewAI con il provider LLM specificato.
    llm_type: "gemini" | "claude"
    forced_llm: se fornito, usa questo LLM invece di chiamare get_llm()
    """
    llm         = forced_llm or get_llm(plan=plan)
    search_mode = get_search_mode(llm_type)
    search_tool = get_search_tool(plan=plan, mode=search_mode)
    props_text  = _format_properties(properties)

    logger.info(f"[deep_research] crew LLM={llm_type}, search_mode={search_mode}")

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
            f"PROPRIETA DA ANALIZZARE:\n{props_text}\n\n"
            "Per ogni proprieta:\n"
            "1. Cerca il micro-mercato SPECIFICO della zona (non la media citta)\n"
            "2. Trova prezzi vendita euro/mq per quella zona su portali locali\n"
            "3. Trova canoni affitto euro/mq/mese per quella zona\n"
            "4. Trova variazione YoY prezzi e trend attuale\n"
            "5. Identifica i quartieri piu costosi e piu economici\n"
            "6. Cita URL e data per ogni dato - mai inventare numeri"
        )
        props_context_property = (
            f"PROPRIETA DA VALUTARE:\n{props_text}\n\n"
            "Per ogni immobile applica le formule esatte:\n"
            "1. Calcola euro/mq e scostamento dal mercato locale (%)\n"
            "2. Trova canone mensile reale per quella zona e tipologia\n"
            "3. Calcola yield lordo, yield netto (*0,79 - spese cond.), payback\n"
            "4. Se da ristrutturare: calcola margine flipping con formula\n"
            "   (notaio 2% + agenzia 3% + IMU 1% + costo ristr. da cronoshare.it)\n"
            "5. Assegna score 0-100 con media ponderata dei 4 fattori\n"
            "6. Indica strategia: buy-to-let lungo/breve/flipping/evita"
        )
        props_context_risk = (
            f"PROPRIETA DA ANALIZZARE:\n{props_text}\n\n"
            "Per ogni zona cerca:\n"
            "1. Dati sfratti/morosita per la citta\n"
            "2. Aggiornamenti normative affitti brevi 2026 (CIN, limiti)\n"
            "3. Previsioni prezzi zona 2026-2027\n"
            "4. Piani riqualificazione urbana o nuove infrastrutture\n"
            "5. Per immobili da ristrutturare: calcola break-even price\n"
            "   (valore rivendita - costi fissi = prezzo max acquisto)\n"
            "Valuta ogni rischio: ALTO/MEDIO/BASSO con evidenza."
        )
    else:
        # Modalità simulazione: nessun immobile fornito dall'utente.
        # Il Market Scout identifica le zone, poi il Property Analyst
        # costruisce 3 profili tipici compatibili con la query e li analizza.
        props_context_market = (
            "L'investitore NON ha fornito immobili specifici.\n"
            "Il tuo compito e analizzare il mercato della zona/citta indicata nella query "
            "e identificare le MIGLIORI AREE dove trovare opportunita compatibili "
            "con i criteri dell'investitore.\n\n"
            "Per ogni area/quartiere trovato:\n"
            "1. Cerca prezzi di vendita euro/mq su portali locali (immobiliare.it, idealista.it)\n"
            "2. Cerca canoni affitto euro/mq/mese\n"
            "3. Cerca variazione YoY e trend\n"
            "4. Identifica quali zone rientrano nel budget indicato nella query\n"
            "5. Cita URL e data per ogni dato - mai inventare numeri\n\n"
            "IMPORTANTE: alla fine elenca le TOP 3 zone/comuni piu promettenti "
            "con i prezzi medi di vendita e affitto trovati."
        )
        props_context_property = (
            "L'investitore NON ha fornito immobili specifici.\n"
            "Basandoti sui dati di mercato trovati dal Market Scout, "
            "COSTRUISCI e ANALIZZA 3 profili di immobile tipico compatibili "
            "con la query dell'investitore. Dai a ciascuno un nome (es. Profilo A, B, C).\n\n"
            f"QUERY INVESTITORE: {query}\n\n"
            "Per OGNI profilo costruito applica le formule esatte:\n"
            "1. Definisci: zona, prezzo acquisto, superficie, condizioni\n"
            "2. Calcola euro/mq e scostamento dal mercato locale (%)\n"
            "3. Calcola yield lordo, yield netto (*0,79 - spese cond.), payback\n"
            "4. Se da ristrutturare: stima costo ristr. da cronoshare.it e calcola\n"
            "   margine flipping (notaio 2% + agenzia 3% + IMU 1% + costo ristr.)\n"
            "5. Assegna score 0-100 con media ponderata dei 4 fattori\n"
            "6. Indica strategia: buy-to-let lungo/breve/flipping/evita\n\n"
            "REGOLA: usa SOLO prezzi e dati reali trovati dal Market Scout. "
            "Non inventare valori. Se mancano dati di affitto per una zona, "
            "usa i dati della citta piu vicina con mercato simile."
        )
        props_context_risk = (
            "L'investitore NON ha fornito immobili specifici.\n"
            "Analizza i rischi e le opportunita per le 3 zone/profili identificati.\n\n"
            f"QUERY INVESTITORE: {query}\n\n"
            "Per ogni zona/profilo cerca:\n"
            "1. Dati sfratti/morosita per la citta o provincia\n"
            "2. Aggiornamenti normative affitti brevi 2026 (CIN, limiti)\n"
            "3. Previsioni prezzi zona 2026-2027\n"
            "4. Piani riqualificazione urbana o nuove infrastrutture\n"
            "5. Per profili da ristrutturare: calcola break-even price\n"
            "   (valore rivendita stimato - costi fissi = prezzo max sostenibile)\n"
            "Valuta ogni rischio: ALTO/MEDIO/BASSO con evidenza e fonte."
        )

    # ── Task ─────────────────────────────────────────────────────────────────
    task_market = Task(
        description=(
            f"QUERY INVESTITORE: {query}\n\n"
            f"{props_context_market}"
        ),
        expected_output=(
            "Per ogni zona: prezzo vendita euro/mq, affitto euro/mq/mese, "
            "YoY%, trend, quartieri costosi/economici. "
            "Ogni dato con fonte URL citata. "
            "Se nessun immobile specifico: TOP 3 zone piu promettenti con prezzi."
        ),
        agent=market_scout,
    )

    task_property = Task(
        description=(
            f"Usando i dati di mercato trovati, procedi con la valutazione:\n\n"
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
    )

    task_risk = Task(
        description=(
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
    )

    task_recommendation = Task(
        description=(
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