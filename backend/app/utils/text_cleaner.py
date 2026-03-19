"""
utils/text_cleaner.py

Rimuove tutta la formattazione markdown dall'output degli agenti CrewAI.
Restituisce plain text pulito, pronto per il frontend e per il .docx.

Utilizzato da:
    - services/deep_research_service.py
    - services/calculation_service.py
"""

import re


def clean_agent_output(text: str) -> str:
    """
    Rimuove la formattazione markdown dall'output di un agente CrewAI.

    Trasformazioni applicate in ordine:
        1. Rimuove grassetto (**testo** e __testo__)
        2. Rimuove corsivo (*testo* e _testo_)
        3. Rimuove intestazioni (# ## ### ecc.)
        4. Normalizza le tabelle markdown → testo separato da trattini
        5. Rimuove separatori orizzontali (---, ***, ___)
        6. Rimuove bullet points e sostituisce con trattino semplice
        7. Rimuove numerazione markdown (1. 2. 3.)
        8. Rimuove blocchi di codice (``` e `)
        9. Rimuove link markdown [testo](url) → testo
       10. Normalizza righe vuote multiple → massimo una riga vuota

    Args:
        text: Stringa grezza restituita da crew.kickoff() o result.raw

    Returns:
        Stringa plain text pulita
    """
    if not text:
        return ""

    # 1. Grassetto: **testo** oppure __testo__
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)

    # 2. Corsivo: *testo* oppure _testo_
    # Attenzione: non toccare i trattini delle tabelle (---)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text)
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'\1', text)

    # 3. Intestazioni: # Titolo → Titolo
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # 4. Tabelle markdown
    # Rimuove le righe separatore (| --- | --- |)
    text = re.sub(r'^\|[\s\-\|:]+\|$', '', text, flags=re.MULTILINE)
    # Righe di tabella (| col1 | col2 |) → "col1 - col2"
    def format_table_row(match):
        row = match.group(0)
        cells = [cell.strip() for cell in row.split('|') if cell.strip()]
        return ' - '.join(cells)
    text = re.sub(r'^\|.+\|$', format_table_row, text, flags=re.MULTILINE)

    # 5. Separatori orizzontali: --- oppure *** oppure ___
    text = re.sub(r'^[-\*_]{3,}\s*$', '', text, flags=re.MULTILINE)

    # 6. Bullet points: - item oppure * item oppure + item → - item
    # Normalizza tutti i bullet in un trattino semplice
    text = re.sub(r'^[\*\+]\s+', '- ', text, flags=re.MULTILINE)

    # 7. Numerazione: "1. " "2. " ecc. — la lasciamo (è plain text leggibile)
    # Non rimossa intenzionalmente: "1. Primo punto" è plain text valido

    # 8. Blocchi di codice
    # Blocchi multi-riga: ```...```
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Inline: `codice`
    text = re.sub(r'`(.+?)`', r'\1', text)

    # 9. Link markdown: [testo](url) → testo
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)

    # 10. Righe vuote multiple → massimo una riga vuota
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Rimuove spazi trailing su ogni riga
    text = '\n'.join(line.rstrip() for line in text.splitlines())

    return text.strip()


def clean_crew_result(result) -> str:
    """
    Wrapper per l'oggetto CrewOutput restituito da crew.kickoff().
    Estrae il testo grezzo e lo pulisce.

    Args:
        result: Oggetto CrewOutput (ha attributo .raw) oppure stringa

    Returns:
        Plain text pulito
    """
    if hasattr(result, 'raw'):
        raw_text = result.raw
    elif isinstance(result, str):
        raw_text = result
    else:
        raw_text = str(result)

    return clean_agent_output(raw_text)