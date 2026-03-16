# backend/app/core/storage_manager.py
#
# Gestione del ciclo di vita di tutti i dati generati da Big House AI.
#
# RETENTION POLICY PER PIANO:
#   FREE:  sessioni conservate 7 giorni, nessun file DOCX salvato
#   BASIC: sessioni conservate 30 giorni, DOCX conservati 30 giorni, max 500MB
#   PRO:   sessioni conservate 180 giorni, DOCX conservati 180 giorni, max 2GB
#   PLUS:  sessioni conservate 365 giorni, DOCX conservati 365 giorni, max 10GB
#
# COSA VIENE SALVATO:
#   - Testo delle analisi (Deep Research, Calcola ROI) → PostgreSQL (TEXT)
#   - File DOCX generati → filesystem locale (Render) o R2/S3
#   - Metadati sessione → PostgreSQL
#   - Search cache → PostgreSQL con TTL 6h (gestita da search_tool.py)
#
# CLEANUP AUTOMATICO:
#   - Al startup dell'app
#   - Ogni 24h tramite background task FastAPI
#   - On-demand via endpoint admin

import os
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Retention policy per piano ────────────────────────────────────────────────
PLAN_RETENTION = {
    "free": {
        "session_days": 7,        # giorni di conservazione sessioni/testo
        "docx_days":    0,        # 0 = DOCX non vengono salvati su disco
        "storage_mb":   0,        # nessuno storage file
        "max_sessions": 20,       # massimo sessioni totali conservate
    },
    "basic": {
        "session_days": 30,
        "docx_days":    30,
        "storage_mb":   500,
        "max_sessions": 100,
    },
    "pro": {
        "session_days": 180,
        "docx_days":    180,
        "storage_mb":   2048,     # 2 GB in MB
        "max_sessions": 1000,
    },
    "plus": {
        "session_days": 365,
        "docx_days":    365,
        "storage_mb":   10240,    # 10 GB in MB
        "max_sessions": 9999,     # praticamente illimitato
    },
}

# Directory base per i file DOCX
DOCX_BASE_DIR = Path(os.getenv("DOCX_STORAGE_PATH", "/tmp/bighouse_docx"))
DOCX_BASE_DIR.mkdir(parents=True, exist_ok=True)

def get_user_docx_dir(user_id: int) -> Path:
    """Restituisce la directory DOCX per un utente, creandola se non esiste."""
    user_dir = DOCX_BASE_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir

# ── DB helper ─────────────────────────────────────────────────────────────────
def _get_conn():
    try:
        from app.core.database import get_db_connection
        return get_db_connection()
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        return None

# ── Schema setup ──────────────────────────────────────────────────────────────
def ensure_storage_schema():
    """
    Crea le tabelle necessarie se non esistono.
    Da chiamare all'avvio dell'app in main.py.
    """
    conn = _get_conn()
    if not conn:
        return
    try:
        with conn:
            # Sessioni con testo completo delle analisi
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id           TEXT PRIMARY KEY,
                    user_id      INTEGER NOT NULL,
                    feature      TEXT NOT NULL,       -- 'deepresearch' | 'calcola'
                    title        TEXT NOT NULL,
                    result_text  TEXT,                -- testo completo analisi AI
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at   TIMESTAMP,           -- NULL = mai scadere
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user
                ON sessions(user_id, created_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_expires
                ON sessions(expires_at)
            """)

            # File DOCX generati
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stored_files (
                    id           TEXT PRIMARY KEY,
                    user_id      INTEGER NOT NULL,
                    session_id   TEXT,
                    filename     TEXT NOT NULL,
                    filepath     TEXT NOT NULL,       -- path assoluto su disco
                    size_bytes   INTEGER DEFAULT 0,
                    feature      TEXT,
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at   TIMESTAMP,
                    downloaded   INTEGER DEFAULT 0,   -- contatore download
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stored_files_user
                ON stored_files(user_id, created_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stored_files_expires
                ON stored_files(expires_at)
            """)

            # Storage usage per utente (aggiornato ad ogni operazione)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_storage (
                    user_id      INTEGER PRIMARY KEY,
                    used_bytes   INTEGER DEFAULT 0,
                    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

        logger.info("Storage schema OK")
    except Exception as e:
        logger.error(f"ensure_storage_schema error: {e}")
    finally:
        conn.close()

# ── Salvataggio sessione ──────────────────────────────────────────────────────
def save_session(
    session_id: str,
    user_id: int,
    plan: str,
    feature: str,
    title: str,
    result_text: str,
) -> bool:
    """
    Salva il testo di una sessione (Deep Research o Calcola ROI).
    Calcola automaticamente la scadenza in base al piano.
    Verifica il limite max_sessions prima di salvare.
    """
    conn = _get_conn()
    if not conn:
        return False

    retention = PLAN_RETENTION.get(plan, PLAN_RETENTION["free"])
    session_days = retention["session_days"]
    expires_at = (
        datetime.utcnow() + timedelta(days=session_days)
        if session_days > 0
        else None
    )

    try:
        with conn:
            # Controlla limite sessioni per piano
            count = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE user_id = ?",
                (user_id,)
            ).fetchone()[0]

            max_sessions = retention["max_sessions"]
            if count >= max_sessions:
                # Elimina la sessione più vecchia per fare posto
                conn.execute("""
                    DELETE FROM sessions
                    WHERE id = (
                        SELECT id FROM sessions
                        WHERE user_id = ?
                        ORDER BY created_at ASC
                        LIMIT 1
                    )
                """, (user_id,))
                logger.info(f"User {user_id}: rimossa sessione più vecchia (limite {max_sessions})")

            conn.execute("""
                INSERT OR REPLACE INTO sessions
                    (id, user_id, feature, title, result_text, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, user_id, feature, title, result_text,
                  datetime.utcnow(), expires_at))

        logger.info(
            f"Sessione salvata: user={user_id}, plan={plan}, "
            f"feature={feature}, scadenza={expires_at or 'mai'}, "
            f"dimensione={len(result_text.encode())//1024}KB"
        )
        return True
    except Exception as e:
        logger.error(f"save_session error: {e}")
        return False
    finally:
        conn.close()

# ── Salvataggio DOCX ──────────────────────────────────────────────────────────
def save_docx(
    file_id: str,
    user_id: int,
    plan: str,
    session_id: str,
    filename: str,
    file_bytes: bytes,
    feature: str = "deepresearch",
) -> Optional[str]:
    """
    Salva un file DOCX su disco e registra i metadati nel DB.
    Gli utenti FREE non hanno DOCX salvati (docx_days = 0).
    Verifica che l'utente non superi il suo storage limit.
    Restituisce il filepath se OK, None altrimenti.
    """
    retention = PLAN_RETENTION.get(plan, PLAN_RETENTION["free"])

    # FREE: nessun salvataggio file
    if retention["docx_days"] == 0:
        logger.info(f"User {user_id} (FREE): DOCX non salvato su disco")
        return None

    # Controlla quota storage
    used = get_storage_used_bytes(user_id)
    max_bytes = retention["storage_mb"] * 1024 * 1024
    if used + len(file_bytes) > max_bytes:
        logger.warning(
            f"User {user_id}: quota storage superata "
            f"({used//(1024*1024)}MB / {retention['storage_mb']}MB)"
        )
        return None

    conn = _get_conn()
    if not conn:
        return None

    # Salva su disco
    user_dir = get_user_docx_dir(user_id)
    filepath = user_dir / filename
    try:
        filepath.write_bytes(file_bytes)
    except Exception as e:
        logger.error(f"DOCX write error: {e}")
        return None

    expires_at = datetime.utcnow() + timedelta(days=retention["docx_days"])

    try:
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO stored_files
                    (id, user_id, session_id, filename, filepath,
                     size_bytes, feature, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (file_id, user_id, session_id, filename, str(filepath),
                  len(file_bytes), feature, datetime.utcnow(), expires_at))

            # Aggiorna usage
            conn.execute("""
                INSERT INTO user_storage (user_id, used_bytes, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    used_bytes = used_bytes + excluded.used_bytes,
                    updated_at = excluded.updated_at
            """, (user_id, len(file_bytes), datetime.utcnow()))

        logger.info(
            f"DOCX salvato: user={user_id}, file={filename}, "
            f"size={len(file_bytes)//1024}KB, scadenza={expires_at.date()}"
        )
        return str(filepath)
    except Exception as e:
        logger.error(f"save_docx DB error: {e}")
        # rollback file
        filepath.unlink(missing_ok=True)
        return None
    finally:
        conn.close()

# ── Storage info ──────────────────────────────────────────────────────────────
def get_storage_used_bytes(user_id: int) -> int:
    """Ritorna i byte usati dall'utente in stored_files."""
    conn = _get_conn()
    if not conn:
        return 0
    try:
        row = conn.execute(
            "SELECT used_bytes FROM user_storage WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        return row[0] if row else 0
    except Exception:
        return 0
    finally:
        conn.close()

def get_storage_info(user_id: int, plan: str) -> dict:
    """
    Restituisce un riepilogo dello storage per un utente.
    Usato dall'endpoint /storage e dalla dashboard.
    """
    retention = PLAN_RETENTION.get(plan, PLAN_RETENTION["free"])
    max_bytes = retention["storage_mb"] * 1024 * 1024
    used = get_storage_used_bytes(user_id)

    conn = _get_conn()
    files = []
    session_count = 0
    if conn:
        try:
            rows = conn.execute("""
                SELECT id, filename, size_bytes, created_at, feature, session_id
                FROM stored_files
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,)).fetchall()
            files = [
                {
                    "id": r[0], "filename": r[1], "size_bytes": r[2],
                    "created_at": r[3], "feature": r[4], "session_id": r[5],
                }
                for r in rows
            ]
            session_count = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE user_id = ?",
                (user_id,)
            ).fetchone()[0]
        except Exception as e:
            logger.error(f"get_storage_info error: {e}")
        finally:
            conn.close()

    return {
        "used_bytes":     used,
        "max_bytes":      max_bytes,
        "used_percent":   round(used / max_bytes * 100, 1) if max_bytes > 0 else 0,
        "session_count":  session_count,
        "max_sessions":   retention["max_sessions"],
        "retention_days": retention["session_days"],
        "files":          files,
    }

# ── Cleanup ───────────────────────────────────────────────────────────────────
def cleanup_expired_sessions() -> int:
    """Elimina le sessioni scadute dal DB. Restituisce il numero eliminato."""
    conn = _get_conn()
    if not conn:
        return 0
    try:
        with conn:
            result = conn.execute(
                "DELETE FROM sessions WHERE expires_at IS NOT NULL AND expires_at < ?",
                (datetime.utcnow(),)
            )
            deleted = result.rowcount
            if deleted > 0:
                logger.info(f"Cleanup: {deleted} sessioni scadute eliminate")
            return deleted
    except Exception as e:
        logger.error(f"cleanup_expired_sessions error: {e}")
        return 0
    finally:
        conn.close()

def cleanup_expired_files() -> int:
    """
    Elimina i file DOCX scaduti dal disco e dal DB.
    Aggiorna lo storage usage degli utenti coinvolti.
    Restituisce il numero di file eliminati.
    """
    conn = _get_conn()
    if not conn:
        return 0

    deleted = 0
    try:
        rows = conn.execute(
            "SELECT id, user_id, filepath, size_bytes FROM stored_files "
            "WHERE expires_at IS NOT NULL AND expires_at < ?",
            (datetime.utcnow(),)
        ).fetchall()

        for file_id, user_id, filepath, size_bytes in rows:
            # Elimina file da disco
            try:
                Path(filepath).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"File delete error ({filepath}): {e}")

            # Elimina dal DB e aggiorna usage
            with conn:
                conn.execute("DELETE FROM stored_files WHERE id = ?", (file_id,))
                conn.execute("""
                    UPDATE user_storage
                    SET used_bytes = MAX(0, used_bytes - ?), updated_at = ?
                    WHERE user_id = ?
                """, (size_bytes, datetime.utcnow(), user_id))
            deleted += 1

        if deleted > 0:
            logger.info(f"Cleanup: {deleted} file scaduti eliminati")
        return deleted
    except Exception as e:
        logger.error(f"cleanup_expired_files error: {e}")
        return 0
    finally:
        conn.close()

def cleanup_orphan_files() -> int:
    """
    Elimina i file fisici su disco che non hanno più un record in DB
    (es. da crash durante il salvataggio). Pulizia di sicurezza.
    """
    if not DOCX_BASE_DIR.exists():
        return 0

    conn = _get_conn()
    if not conn:
        return 0

    deleted = 0
    try:
        # Raccoglie tutti i filepath registrati nel DB
        rows = conn.execute("SELECT filepath FROM stored_files").fetchall()
        registered = {r[0] for r in rows}

        # Scansiona il filesystem
        for filepath in DOCX_BASE_DIR.rglob("*.docx"):
            if str(filepath) not in registered:
                try:
                    filepath.unlink()
                    deleted += 1
                    logger.info(f"Orfano eliminato: {filepath.name}")
                except Exception as e:
                    logger.warning(f"Orphan delete error: {e}")

        return deleted
    except Exception as e:
        logger.error(f"cleanup_orphan_files error: {e}")
        return 0
    finally:
        conn.close()

def cleanup_search_cache_expired() -> int:
    """Delega alla search_tool per pulizia cache ricerche scadute."""
    try:
        from app.agents.search_tool import cleanup_search_cache
        cleanup_search_cache()
        return 1
    except Exception as e:
        logger.warning(f"cleanup_search_cache: {e}")
        return 0

def run_full_cleanup() -> dict:
    """
    Esegue tutte le operazioni di cleanup.
    Chiamare all'avvio e ogni 24h.
    """
    logger.info("=== CLEANUP START ===")
    result = {
        "sessions_deleted": cleanup_expired_sessions(),
        "files_deleted":    cleanup_expired_files(),
        "orphans_deleted":  cleanup_orphan_files(),
        "cache_cleaned":    cleanup_search_cache_expired(),
        "timestamp":        datetime.utcnow().isoformat(),
    }
    logger.info(f"=== CLEANUP END: {result} ===")
    return result

# ── Eliminazione utente (GDPR) ────────────────────────────────────────────────
def delete_user_data(user_id: int) -> bool:
    """
    Elimina TUTTI i dati di un utente: sessioni, file, storage record.
    Da chiamare quando l'utente cancella il proprio account (GDPR).
    """
    conn = _get_conn()
    if not conn:
        return False

    try:
        # 1. Elimina tutti i file fisici
        user_dir = get_user_docx_dir(user_id)
        if user_dir.exists():
            shutil.rmtree(user_dir, ignore_errors=True)
            logger.info(f"GDPR: cartella utente {user_id} eliminata")

        # 2. Elimina dal DB (CASCADE gestisce stored_files e user_storage)
        with conn:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM stored_files WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM user_storage WHERE user_id = ?", (user_id,))

        logger.info(f"GDPR: tutti i dati dell'utente {user_id} eliminati")
        return True
    except Exception as e:
        logger.error(f"delete_user_data error: {e}")
        return False
    finally:
        conn.close()
