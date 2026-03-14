"""
routers/auth.py
Endpoint autenticazione: registrazione, login, Google OAuth.
"""
import logging
import httpx
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.security import hash_password, verify_password, create_access_token
from app.core.database import (
    get_user_by_email,
    get_user_by_google_id,
    create_user,
    create_google_user,
    link_google_to_existing_user,
)
from app.models import UserRegister, Token, UserPublic
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ─────────────────────────────────────────
# POST /auth/register
# ─────────────────────────────────────────

@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister):
    existing = get_user_by_email(payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email già registrata. Effettua il login.",
        )
    hashed = hash_password(payload.password)
    try:
        user = create_user(email=payload.email, name=payload.name, hashed_password=hashed)
    except Exception as e:
        logger.error(f"Errore creazione utente {payload.email}: {e}")
        raise HTTPException(status_code=500, detail="Errore durante la registrazione. Riprova.")
    logger.info(f"Nuovo utente registrato: {payload.email}")
    return UserPublic(**user)


# ─────────────────────────────────────────
# POST /auth/token
# ─────────────────────────────────────────

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_email(form_data.username)

    # Utente registrato solo con Google (nessuna password)
    if user and not user.get("hashed_password") and user.get("google_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Questo account usa il login con Google. Clicca 'Continua con Google'.",
        )

    if not user or not verify_password(form_data.password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": user["email"]})
    logger.info(f"Login effettuato: {user['email']}")
    return Token(access_token=token)


# ─────────────────────────────────────────
# POST /auth/google
# ─────────────────────────────────────────

class GoogleAuthRequest(BaseModel):
    credential: str  # JWT token restituito da Google


@router.post("/google", response_model=Token)
async def google_auth(payload: GoogleAuthRequest):
    """
    Flusso Google OAuth:
    1. Verifica credential token con API Google
    2. Se utente già registrato con Google ID → login diretto
    3. Se email già registrata con password → collega Google ID e fa login
    4. Altrimenti → crea nuovo utente e fa login
    """
    google_user = await _verify_google_token(payload.credential)
    if not google_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Google non valido o scaduto. Riprova.",
        )

    google_id = google_user["sub"]
    email = google_user["email"].lower()
    name = google_user.get("name") or email.split("@")[0]

    # Caso 1: già registrato con Google
    existing_by_google = get_user_by_google_id(google_id)
    if existing_by_google:
        token = create_access_token(data={"sub": existing_by_google["email"]})
        logger.info(f"Google login: {email}")
        return Token(access_token=token)

    # Caso 2: email già registrata con password → collegamento account
    existing_by_email = get_user_by_email(email)
    if existing_by_email:
        link_google_to_existing_user(email, google_id)
        token = create_access_token(data={"sub": email})
        logger.info(f"Google collegato ad account esistente: {email}")
        return Token(access_token=token)

    # Caso 3: nuovo utente
    try:
        user = create_google_user(email=email, name=name, google_id=google_id)
    except Exception as e:
        logger.error(f"Errore creazione utente Google {email}: {e}")
        raise HTTPException(status_code=500, detail="Errore durante la registrazione. Riprova.")

    token = create_access_token(data={"sub": user["email"]})
    logger.info(f"Nuovo utente Google registrato: {email}")
    return Token(access_token=token)


# ─────────────────────────────────────────
# Helper privato
# ─────────────────────────────────────────

async def _verify_google_token(credential: str) -> dict | None:
    """Verifica il credential token con le API Google."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": credential},
            )
        if response.status_code != 200:
            logger.warning(f"Google tokeninfo fallito: HTTP {response.status_code}")
            return None

        data = response.json()

        # Verifica che il token sia per la nostra app
        if settings.GOOGLE_CLIENT_ID and data.get("aud") != settings.GOOGLE_CLIENT_ID:
            logger.warning(f"Token aud mismatch: {data.get('aud')}")
            return None

        # Verifica email verificata da Google
        if data.get("email_verified") != "true":
            logger.warning(f"Email non verificata da Google: {data.get('email')}")
            return None

        return data

    except Exception as e:
        logger.error(f"Errore verifica token Google: {e}")
        return None
