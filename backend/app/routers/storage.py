"""
app/routers/storage.py
Gestione cloud storage per utente:
- GET  /storage/info          → utilizzo storage
- GET  /storage/sessions      → lista sessioni chat
- POST /storage/sessions      → salva sessione
- DELETE /storage/sessions/{id} → elimina sessione
- GET  /storage/download-zip  → zip di tutti i file
- GET  /storage/files/{name}  → scarica singolo file
"""
import json
import logging
import os
import zipfile
from datetime import datetime
from pathlib import Path
from io import BytesIO
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.config import settings
from app.core.security import get_current_user
from app.core.database import (
    get_chat_sessions, save_chat_session,
    delete_chat_session, get_user_storage_bytes,
)
from app.models import STORAGE_MAX_BYTES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storage", tags=["Storage"])

# Directory base storage: una cartella per utente
STORAGE_ROOT = Path(getattr(settings, 'STORAGE_ROOT', './user_storage'))
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

STORAGE_MAX = 2 * 1024 * 1024 * 1024  # 2 GB


def user_dir(user_id: int) -> Path:
    """Percorso cartella dell'utente."""
    p = STORAGE_ROOT / str(user_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def calc_dir_size(path: Path) -> int:
    """Calcola dimensione totale cartella in bytes."""
    return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())


# ─────────────────────────────────────────
# GET /storage/info
# ─────────────────────────────────────────

@router.get("/info", summary="Informazioni utilizzo storage")
async def get_storage_info(current_user: dict = Depends(get_current_user)):
    """Ritorna bytes usati, massimo e percentuale."""
    d = user_dir(current_user["id"])
    used_bytes = calc_dir_size(d)
    return {
        "used_bytes":    used_bytes,
        "max_bytes":     STORAGE_MAX,
        "used_percent":  round((used_bytes / STORAGE_MAX) * 100, 2),
        "files":         [],  # Puoi popolare con lista file se necessario
    }


# ─────────────────────────────────────────
# GET /storage/sessions
# ─────────────────────────────────────────

@router.get("/sessions", summary="Lista sessioni chat dell'utente")
async def list_sessions(current_user: dict = Depends(get_current_user)):
    """Ritorna tutte le sessioni chat salvate per l'utente."""
    sessions = get_chat_sessions(current_user["id"])
    return sessions


# ─────────────────────────────────────────
# POST /storage/sessions
# ─────────────────────────────────────────

@router.post("/sessions", status_code=status.HTTP_201_CREATED, summary="Salva sessione chat")
async def save_session(payload: dict, current_user: dict = Depends(get_current_user)):
    """
    Salva una sessione chat nel DB e su filesystem (come JSON).
    Controlla il limite di 2 GB prima di salvare.
    """
    d = user_dir(current_user["id"])
    used = calc_dir_size(d)

    # Stima dimensione nuova sessione
    content = json.dumps(payload).encode('utf-8')
    if used + len(content) > STORAGE_MAX:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Limite storage 2 GB raggiunto. Elimina alcune sessioni per continuare.",
        )

    session_id = payload.get("id", f"session_{int(datetime.now().timestamp())}")

    # Salva JSON su filesystem
    session_file = d / f"{session_id}.json"
    session_file.write_bytes(content)

    # Salva referenza nel DB
    save_chat_session(
        user_id=current_user["id"],
        session_id=session_id,
        feature=payload.get("feature", "deepresearch"),
        title=payload.get("title", "Sessione"),
        file_path=str(session_file),
        size_bytes=len(content),
    )

    return {"status": "saved", "session_id": session_id, "size_bytes": len(content)}


# ─────────────────────────────────────────
# DELETE /storage/sessions/{session_id}
# ─────────────────────────────────────────

@router.delete("/sessions/{session_id}", summary="Elimina sessione")
async def remove_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """Elimina sessione da DB e filesystem."""
    d = user_dir(current_user["id"])
    session_file = d / f"{session_id}.json"

    if session_file.exists():
        session_file.unlink()

    delete_chat_session(current_user["id"], session_id)
    return {"status": "deleted", "session_id": session_id}


# ─────────────────────────────────────────
# GET /storage/download-zip
# ─────────────────────────────────────────

@router.get("/download-zip", summary="Scarica tutti i dati come .zip")
async def download_zip(current_user: dict = Depends(get_current_user)):
    """
    Crea un archivio .zip con tutti i file dell'utente e lo invia.
    """
    d = user_dir(current_user["id"])
    files = list(d.glob("*.json"))

    if not files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nessun file da scaricare.",
        )

    # Crea zip in memoria
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, arcname=f.name)

    zip_buffer.seek(0)
    filename = f"bighouseai_export_{current_user['email'].split('@')[0]}_{datetime.now().strftime('%Y%m%d')}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
