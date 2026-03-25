"""
config.py — Big House AI

AGGIORNAMENTO: gemini-2.0-flash → gemini-2.5-flash-lite
  - 2.0 Flash deprecato, spento 1 Giugno 2026
  - 2.5 Flash-Lite: stesso costo, più potente, reasoning integrato
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

    # ── Google Gemini AI ──
    GEMINI_API_KEY: str = ""
    # MODELLO AGGIORNATO: 2.0 Flash deprecato → 2.5 Flash-Lite
    # Opzioni disponibili:
    #   gemini/gemini-2.5-flash-lite  → più economico, veloce (DEFAULT)
    #   gemini/gemini-2.5-flash       → qualità superiore
    #   gemini/gemini-2.5-pro         → massima qualità (più costoso)
    GEMINI_MODEL: str = "gemini/gemini-2.5-pro"

    # ── Google OAuth ──
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # ── Stripe ──
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_BASIC: Optional[str] = None
    STRIPE_PRICE_PRO: Optional[str] = None
    STRIPE_PRICE_PLUS: Optional[str] = None

    # ── Tavily Search ──
    # Registrati su app.tavily.com — 1.000 crediti/mese gratis
    # Con PAYGO: $0.008/credito, nessun limite mensile
    TAVILY_API_KEY: Optional[str] = None

    # ── CORS ──
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY and self.STRIPE_PRICE_PRO)

    @property
    def search_enabled(self) -> bool:
        return bool(self.TAVILY_API_KEY)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()