"""
agents/calculation_agents.py
Agenti specializzati per il calcolo ROI e scenari di ristrutturazione.
"""
from crewai import Agent
from app.agents.llm_factory import get_llm


def create_cost_estimator(llm=None) -> Agent:
    """
    Agente specializzato nella stima precisa dei costi di ristrutturazione
    per tre scenari: conservativo, moderato, premium.
    """
    return Agent(
        role="Construction Cost Estimator",
        goal=(
            "Generare stime dettagliate e realistiche dei costi di ristrutturazione "
            "per tre scenari distinti (conservativo, moderato, premium), "
            "specificando categorie di intervento, materiali e manodopera "
            "con prezzi aggiornati al mercato italiano."
        ),
        backstory=(
            "Sei un geometra e quantity surveyor con 14 anni di esperienza "
            "nella stima e computo metrico di opere edili in Italia. "
            "Hai una banca dati aggiornata sui prezzi di tutte le lavorazioni "
            "edili, dai semplici interventi di verniciatura alle ristrutturazioni "
            "integrali con cambio di destinazione d'uso. "
            "Sei preciso, metodico e mai ottimista sui costi: le tue stime "
            "includono sempre contingency del 15% per imprevisti."
        ),
        llm=llm or get_llm(),
        allow_delegation=False,
        verbose=False,
    )


def create_timeline_planner(llm=None) -> Agent:
    """
    Agente specializzato nella pianificazione temporale dei lavori di ristrutturazione.
    """
    return Agent(
        role="Project Timeline Planner",
        goal=(
            "Pianificare le timeline realistiche per ogni scenario di ristrutturazione, "
            "considerando fasi dei lavori, approvvigionamento materiali, "
            "pratiche burocratiche e stagionalità del mercato edilizio italiano."
        ),
        backstory=(
            "Sei un project manager edile con certificazione PMP e 10 anni di esperienza "
            "nella gestione di cantieri residenziali e commerciali in Italia. "
            "Hai gestito progetti in parallelo su tutto il territorio nazionale, "
            "sviluppando un'ottima comprensione dei tempi burocratici (CILA, SCIA, PDC), "
            "dei ritardi tipici nei cantieri e delle strategie per rispettare le scadenze. "
            "La tua pianificazione è sempre realistica, mai ottimistica."
        ),
        llm=llm or get_llm(),
        allow_delegation=False,
        verbose=False,
    )


def create_risk_analyst(llm=None) -> Agent:
    """
    Agente specializzato nell'identificazione e quantificazione dei rischi
    per ogni scenario di investimento immobiliare.
    """
    return Agent(
        role="Real Estate Risk Analyst",
        goal=(
            "Identificare, classificare e quantificare i rischi associati a ogni "
            "scenario di ristrutturazione e investimento, includendo rischi strutturali, "
            "di mercato, regolatori, finanziari e di cantiere. "
            "Fornire un risk score e strategie di mitigazione concrete."
        ),
        backstory=(
            "Sei un analista del rischio specializzato in real estate con background "
            "in ingegneria strutturale e finanza immobiliare. "
            "Hai collaborato con banche e assicurazioni per la valutazione del rischio "
            "su portafogli immobiliari, sviluppando modelli di risk assessment "
            "che integrano dati tecnici, di mercato e regolatori. "
            "La tua analisi è sempre prudente: preferisci sovrastimare i rischi "
            "piuttosto che sorprendere negativamente gli investitori."
        ),
        llm=llm or get_llm(),
        allow_delegation=False,
        verbose=False,
    )
