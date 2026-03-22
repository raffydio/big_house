"""
backend/app/worker.py
SPRINT 4 — Celery app con 4 code di priorità.

Code (ordine di consumo del worker, dalla più alta alla più bassa):
    q_plus   → piano PLUS
    q_pro    → piano PRO
    q_basic  → piano BASIC
    q_free   → piano FREE

Il worker legge le code nell'ordine specificato in -Q, quindi q_plus viene
sempre controllata prima di q_pro, e così via.

Avvio locale (dopo redis-server attivo):
    cd backend
    celery -A app.worker worker \
        -Q q_plus,q_pro,q_basic,q_free \
        --concurrency=2 \
        --prefetch-multiplier=1 \
        --loglevel=info

Avvio su Render: vedere render.yaml (startCommand del worker service).
"""

import os
from celery import Celery

# ── URL Redis ──────────────────────────────────────────────────────────────────
# In locale: redis://localhost:6379/0 (default dopo apt install redis-server)
# Su Render: iniettata automaticamente da render.yaml come variabile REDIS_URL
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# ── Celery app ────────────────────────────────────────────────────────────────
celery_app = Celery(
    "bighouse",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.ai_tasks"],
)

# ── Configurazione ────────────────────────────────────────────────────────────
celery_app.conf.update(
    # Serializzazione
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Risultati: conservati 2 ore (usiamo Redis job_store per la persistenza reale)
    result_expires=7200,

    # Performance: un task alla volta per queue per rispettare le priorità
    worker_prefetch_multiplier=1,
    task_acks_late=True,               # ACK solo dopo completamento (sicurezza)
    worker_max_tasks_per_child=50,     # restart worker ogni 50 task (memory safety)

    # Timeout hard su singolo task: 10 minuti (le analisi durano 3-5 min)
    task_soft_time_limit=540,          # 9 min → SoftTimeLimitExceeded
    task_time_limit=600,               # 10 min → forza kill

    # Code di priorità (order matters: Celery checks in this order)
    task_queues={
        "q_plus":  {"exchange": "q_plus",  "routing_key": "q_plus"},
        "q_pro":   {"exchange": "q_pro",   "routing_key": "q_pro"},
        "q_basic": {"exchange": "q_basic", "routing_key": "q_basic"},
        "q_free":  {"exchange": "q_free",  "routing_key": "q_free"},
    },
    task_default_queue="q_free",
    task_default_exchange="q_free",
    task_default_routing_key="q_free",
)

# ── Mappa piano → coda ────────────────────────────────────────────────────────
PLAN_QUEUE: dict[str, str] = {
    "plus":  "q_plus",
    "pro":   "q_pro",
    "basic": "q_basic",
    "free":  "q_free",
}


def queue_for_plan(plan: str) -> str:
    """Restituisce la coda Celery corretta per il piano utente."""
    return PLAN_QUEUE.get((plan or "free").lower(), "q_free")