"""
core/database.py
CORRETTO: aggiunta get_db_connection() pubblica — richiesta da storage_manager.py
"""
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime, date
from typing import Optional, Generator

from app.config import settings
from app.models import Plan

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# Schema SQL
# ─────────────────────────────────────────

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    email                   TEXT UNIQUE NOT NULL,
    name                    TEXT NOT NULL,
    hashed_password         TEXT,
    google_id               TEXT UNIQUE,
    plan                    TEXT NOT NULL DEFAULT 'free',
    usage_date              TEXT,
    deepresearch_count      INTEGER NOT NULL DEFAULT 0,
    calcola_count           INTEGER NOT NULL DEFAULT 0,
    created_at              TEXT NOT NULL,
    stripe_customer_id      TEXT,
    stripe_subscription_id  TEXT,
    trial_ends_at           TEXT,
    trial_used              INTEGER NOT NULL DEFAULT 0
);
"""

CREATE_CHAT_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    id          TEXT PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    feature     TEXT NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    file_path   TEXT,
    size_bytes  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""

CREATE_USER_STORAGE_TABLE = """
CREATE TABLE IF NOT EXISTS user_storage (
    user_id     INTEGER PRIMARY KEY,
    used_bytes  INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""

# ─────────────────────────────────────────
# Connessione
# ─────────────────────────────────────────

def _get_connection() -> sqlite3.Connection:
    """Connessione interna — uso diretto per operazioni senza context manager."""
    db_path = settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_db_connection() -> sqlite3.Connection:
    """
    Connessione pubblica — usata da storage_manager.py e altri moduli
    che gestiscono il ciclo di vita della connessione manualmente.
    Il chiamante è responsabile di chiuderla con conn.close().
    """
    return _get_connection()


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager per operazioni DB con commit/rollback automatico."""
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"DB error, rollback eseguito: {e}")
        raise
    finally:
        conn.close()


def init_db() -> None:
    """
    Inizializza tutte le tabelle.
    Esegue anche le migrazioni necessarie su DB esistenti.
    """
    try:
        conn = _get_connection()
        with conn:
            conn.execute(CREATE_USERS_TABLE)
            conn.execute(CREATE_CHAT_SESSIONS_TABLE)
            conn.execute(CREATE_USER_STORAGE_TABLE)

            # ── Migrazione: aggiunge google_id se non esiste ──
            try:
                conn.execute("ALTER TABLE users ADD COLUMN google_id TEXT UNIQUE")
                logger.info("Migrazione DB: colonna google_id aggiunta.")
            except Exception:
                pass

            # ── Migrazione: rende hashed_password nullable ──
            cursor = conn.execute("PRAGMA table_info(users)")
            cols = {row[1]: row[3] for row in cursor.fetchall()}
            if cols.get("hashed_password") == 1:
                logger.info("Migrazione DB: rendendo hashed_password nullable...")
                conn.execute("ALTER TABLE users RENAME TO users_old")
                conn.execute(CREATE_USERS_TABLE)
                conn.execute("""
                    INSERT INTO users
                    (id, email, name, hashed_password, google_id, plan, usage_date,
                     deepresearch_count, calcola_count, created_at)
                    SELECT id, email, name, hashed_password, NULL, plan, usage_date,
                           deepresearch_count, calcola_count, created_at
                    FROM users_old
                """)
                conn.execute("DROP TABLE users_old")
                logger.info("Migrazione DB completata.")

            # ── Migrazioni Stripe ──
            stripe_migrations = [
                "ALTER TABLE users ADD COLUMN stripe_customer_id TEXT",
                "ALTER TABLE users ADD COLUMN stripe_subscription_id TEXT",
                "ALTER TABLE users ADD COLUMN trial_ends_at TEXT",
                "ALTER TABLE users ADD COLUMN trial_used INTEGER NOT NULL DEFAULT 0",
            ]
            for sql in stripe_migrations:
                try:
                    conn.execute(sql)
                    logger.info(f"Migrazione Stripe: {sql[:60]}...")
                except Exception:
                    pass

            conn.commit()
        conn.close()
        logger.info("Database inizializzato correttamente.")
    except Exception as e:
        logger.critical(f"Errore inizializzazione DB: {e}")
        raise


# ─────────────────────────────────────────
# CRUD Users
# ─────────────────────────────────────────

def get_user_by_email(email: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower(),)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_google_id(google_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE google_id = ?", (google_id,)
        ).fetchone()
        return dict(row) if row else None


def create_user(email: str, name: str, hashed_password: str) -> dict:
    now   = datetime.utcnow().isoformat()
    today = date.today().isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO users (email, name, hashed_password, plan, usage_date,
                               deepresearch_count, calcola_count, created_at)
            VALUES (?, ?, ?, ?, ?, 0, 0, ?)
            """,
            (email.lower(), name, hashed_password, Plan.FREE.value, today, now),
        )
    user = get_user_by_email(email)
    if not user:
        raise RuntimeError("Errore nella creazione utente.")
    return user


def create_google_user(email: str, name: str, google_id: str) -> dict:
    now   = datetime.utcnow().isoformat()
    today = date.today().isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO users (email, name, hashed_password, google_id, plan, usage_date,
                               deepresearch_count, calcola_count, created_at)
            VALUES (?, ?, NULL, ?, ?, ?, 0, 0, ?)
            """,
            (email.lower(), name, google_id, Plan.FREE.value, today, now),
        )
    user = get_user_by_email(email)
    if not user:
        raise RuntimeError("Errore creazione utente Google.")
    return user


def link_google_to_existing_user(email: str, google_id: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET google_id = ? WHERE email = ?",
            (google_id, email.lower()),
        )
    logger.info(f"Google ID collegato a: {email}")


def update_user_plan(email: str, new_plan: Plan) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET plan = ? WHERE email = ?",
            (new_plan.value, email.lower()),
        )
    logger.info(f"Piano aggiornato per {email}: {new_plan.value}")


def reset_usage_if_new_day(user: dict) -> dict:
    today = date.today().isoformat()
    if user.get("usage_date") == today:
        return user
    with get_db() as conn:
        conn.execute(
            """
            UPDATE users
            SET usage_date = ?, deepresearch_count = 0, calcola_count = 0
            WHERE email = ?
            """,
            (today, user["email"]),
        )
    logger.info(f"Reset contatori giornalieri per: {user['email']}")
    return get_user_by_email(user["email"])


def increment_usage(email: str, feature: str) -> None:
    column_map = {
        "deepresearch": "deepresearch_count",
        "calcola":      "calcola_count",
    }
    column = column_map.get(feature)
    if not column:
        raise ValueError(f"Feature non valida: {feature}")
    with get_db() as conn:
        conn.execute(
            f"UPDATE users SET {column} = {column} + 1 WHERE email = ?",
            (email.lower(),),
        )


# ─────────────────────────────────────────
# Stripe
# ─────────────────────────────────────────

def update_user_stripe(
    email: str,
    stripe_customer_id: str = None,
    stripe_subscription_id: str = None,
    trial_ends_at: str = None,
) -> None:
    updates, values = [], []
    if stripe_customer_id is not None:
        updates.append("stripe_customer_id = ?"); values.append(stripe_customer_id)
    if stripe_subscription_id is not None:
        updates.append("stripe_subscription_id = ?"); values.append(stripe_subscription_id)
    if trial_ends_at is not None:
        updates.append("trial_ends_at = ?"); values.append(trial_ends_at)
    if not updates:
        return
    values.append(email.lower())
    with get_db() as conn:
        conn.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE email = ?", values
        )


def get_user_by_stripe_customer_id(customer_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE stripe_customer_id = ?", (customer_id,)
        ).fetchone()
        return dict(row) if row else None


def update_user_trial(email: str, trial_used: bool = True) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET trial_used = ? WHERE email = ?",
            (1 if trial_used else 0, email.lower()),
        )


def has_used_trial(email: str) -> bool:
    user = get_user_by_email(email)
    return bool(user and user.get("trial_used", 0))


def is_trial_active(user: dict) -> bool:
    trial_ends_at = user.get("trial_ends_at")
    if not trial_ends_at:
        return False
    try:
        end = datetime.fromisoformat(trial_ends_at)
        return datetime.utcnow() < end
    except Exception:
        return False


# ─────────────────────────────────────────
# Chat sessions + storage
# ─────────────────────────────────────────

def get_chat_sessions(user_id: int) -> list:
    import json, os
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, feature, title, file_path, size_bytes, created_at
            FROM chat_sessions WHERE user_id = ?
            ORDER BY created_at DESC LIMIT 200
            """,
            (user_id,),
        ).fetchall()
    sessions = []
    for row in rows:
        d = dict(row)
        messages = []
        fp = d.get("file_path")
        if fp and os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    messages = json.load(f).get("messages", [])
            except Exception:
                pass
        sessions.append({
            "id":         d["id"],
            "feature":    d["feature"],
            "title":      d["title"],
            "created_at": d["created_at"],
            "messages":   messages,
        })
    return sessions


def save_chat_session(
    user_id: int,
    session_id: str,
    feature: str,
    title: str,
    file_path: str,
    size_bytes: int,
) -> None:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO chat_sessions
            (id, user_id, feature, title, file_path, size_bytes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, user_id, feature, title, file_path, size_bytes, now),
        )
        conn.execute(
            """
            INSERT INTO user_storage (user_id, used_bytes, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                used_bytes = used_bytes + ?, updated_at = ?
            """,
            (user_id, size_bytes, now, size_bytes, now),
        )


def delete_chat_session(user_id: int, session_id: str) -> None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT size_bytes FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if row:
            conn.execute(
                "DELETE FROM chat_sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            )
            conn.execute(
                """
                UPDATE user_storage
                SET used_bytes = MAX(0, used_bytes - ?), updated_at = ?
                WHERE user_id = ?
                """,
                (row["size_bytes"], datetime.utcnow().isoformat(), user_id),
            )


def get_user_storage_bytes(user_id: int) -> int:
    with get_db() as conn:
        row = conn.execute(
            "SELECT used_bytes FROM user_storage WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["used_bytes"] if row else 0