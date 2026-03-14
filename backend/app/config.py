"""
config.py — Big House AI con Stripe

⚠️  RINOMINA IL FILE (se non l'hai già fatto):
    backend/app/config_stripe.py  →  backend/app/config.py

Tutti i router fanno `from app.config import settings`

AGGIORNATO: DeepSeek → Google Gemini 2.5 Pro
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──
    APP_NAME: str = "Big House AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    FRONTEND_URL: str = "http://localhost:5173"

    # ── Security ──
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 giorni

    # ── Database ──
    DATABASE_URL: str = "sqlite:///./big_house_ai.db"

    # ── Google Gemini AI ──  (sostituisce DeepSeek)
    GEMINI_API_KEY: str = ""
    # Il prefisso "gemini/" è richiesto da LiteLLM per riconoscere il provider
    GEMINI_MODEL: str = "gemini/gemini-1.5-pro"

    # ── Google OAuth ──
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # ── Stripe ──
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_BASIC: Optional[str] = None
    STRIPE_PRICE_PRO: Optional[str] = None
    STRIPE_PRICE_PLUS: Optional[str] = None

    # ── CORS ──
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY and self.STRIPE_PRICE_PRO)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()