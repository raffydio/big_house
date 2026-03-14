"""
core/security.py
Layer di sicurezza: hashing, JWT, autenticazione, controllo limiti.
Nessuna chiave hardcoded — tutto da config.py.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import settings
from app.models import Plan, TokenData

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# Configurazione
# ─────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
)

# Limiti giornalieri per feature e piano
PLAN_LIMITS: dict[str, dict[str, int]] = {
    Plan.FREE.value:  {"deepresearch": 1, "calcola": 3},
    Plan.PRO.value:   {"deepresearch": 5, "calcola": 20},
    Plan.PLUS.value:  {"deepresearch": 20, "calcola": 100},
}

# Mapping contatori DB → nome feature
FEATURE_COUNTER_MAP: dict[str, str] = {
    "deepresearch": "deepresearch_count",
    "calcola":      "calcola_count",
}


# ─────────────────────────────────────────
# Password Hashing
# ─────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Hash sicuro della password con Argon2id."""
    return _ph.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica password contro hash Argon2.
    Ritorna False senza sollevare eccezioni in caso di mismatch.
    """
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# ─────────────────────────────────────────
# JWT Token
# ─────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un JWT firmato con SECRET_KEY da config.
    Scadenza default: ACCESS_TOKEN_EXPIRE_MINUTES da config.
    """
    payload = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _decode_token(token: str) -> TokenData:
    """Decodifica e valida un JWT. Solleva HTTPException se invalido."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token non valido o scaduto.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
        return TokenData(email=email)
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception


# ─────────────────────────────────────────
# Dependency: get_current_user
# ─────────────────────────────────────────

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    FastAPI dependency: estrae l'utente corrente dal token JWT.
    Importa il DB layer internamente per evitare import circolari.
    """
    from app.core.database import get_user_by_email, reset_usage_if_new_day

    token_data = _decode_token(token)
    user = get_user_by_email(token_data.email)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utente non trovato.",
        )

    # Reset contatori se è un nuovo giorno
    user = reset_usage_if_new_day(user)
    return user


# ─────────────────────────────────────────
# Limite utilizzo per piano
# ─────────────────────────────────────────

def check_limit(user: dict, feature: str) -> int:
    """
    Controlla se l'utente ha ancora utilizzi disponibili per la feature.
    Ritorna il numero di utilizzi rimanenti dopo questo.
    Solleva HTTP 429 se il limite è raggiunto.

    Args:
        user:    dict utente da DB
        feature: 'deepresearch' | 'calcola'

    Returns:
        Utilizzi rimanenti (dopo aver consumato quello corrente)
    """
    plan = user.get("plan", Plan.FREE.value)
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS[Plan.FREE.value])
    max_uses = limits.get(feature, 0)

    counter_col = FEATURE_COUNTER_MAP.get(feature)
    if not counter_col:
        raise ValueError(f"Feature non riconosciuta: {feature}")

    current_count = user.get(counter_col, 0)

    if current_count >= max_uses:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Limite giornaliero raggiunto per '{feature}' "
                f"(piano {plan.upper()}: {max_uses}/giorno). "
                "Effettua l'upgrade per aumentare il limite."
            ),
        )

    remaining = max_uses - current_count - 1  # -1 perché stiamo per usarne uno
    return remaining
