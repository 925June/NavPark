from dotenv import load_dotenv
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")


class Settings:

    ###########################################
    # LLM Configuration
    ###########################################

    LLM_PROVIDER = "deepseek"

    DEEPSEEK_API_KEY = os.getenv(
        "DEEPSEEK_API_KEY",
        ""
    ).strip()

    DEEPSEEK_MODEL = os.getenv(
        "DEEPSEEK_MODEL",
        "deepseek-chat"
    )

    DEEPSEEK_BASE_URL = os.getenv(
        "DEEPSEEK_BASE_URL",
        "https://api.deepseek.com"
    ).rstrip("/")

    DEEPSEEK_TIMEOUT = float(
        os.getenv("DEEPSEEK_TIMEOUT", "60")
    )

    TEMPERATURE = float(
        os.getenv("TEMPERATURE", 0)
    )

    ###########################################
    # AI Workflow
    ###########################################

    AI_CONFIDENCE_THRESHOLD = 0.80

    ###########################################
    # Parking APIs
    ###########################################

    PARKING_API = os.getenv(
        "PARKING_API",
        "http://localhost:9000"
    )

    PAYMENT_API = os.getenv(
        "PAYMENT_API",
        "http://localhost:9001"
    )

    ###########################################
    # Vector Database
    ###########################################

    CHROMA_COLLECTION = "parking_documents"

    ###########################################
    # RAG Configuration
    ###########################################

    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))

    DOCUMENTS_DIR = os.getenv(
        "DOCUMENTS_DIR",
        "documents"
    )

    ENABLE_RAG = os.getenv("ENABLE_RAG", "true").lower() == "true"

    ###########################################
    # Logging
    ###########################################

    LOG_LEVEL = "INFO"

    ###########################################
    # Authentication
    ###########################################

    APP_ENV = os.getenv("APP_ENV", "development").lower()

    DATABASE_PATH = os.getenv(
        "DATABASE_PATH",
        str(PROJECT_ROOT / "data" / "navpark.db")
    )

    AUTH_SECRET = os.getenv(
        "AUTH_SECRET",
        "development-only-change-this-secret"
    )

    AUTH_COOKIE_NAME = "navpark_session"

    AUTH_SESSION_DAYS = int(
        os.getenv("AUTH_SESSION_DAYS", "30")
    )

    COOKIE_SECURE = (
        os.getenv("COOKIE_SECURE", "").lower() == "true"
        or APP_ENV == "production"
    )

    ###########################################
    # SMS
    ###########################################

    SMS_PROVIDER = os.getenv("SMS_PROVIDER", "console").lower()

    SMS_CODE_TTL_SECONDS = int(
        os.getenv("SMS_CODE_TTL_SECONDS", "300")
    )

    SMS_RESEND_COOLDOWN_SECONDS = int(
        os.getenv("SMS_RESEND_COOLDOWN_SECONDS", "60")
    )

    SMS_WEBHOOK_URL = os.getenv("SMS_WEBHOOK_URL", "").strip()

    SMS_WEBHOOK_TOKEN = os.getenv(
        "SMS_WEBHOOK_TOKEN",
        ""
    ).strip()

    ###########################################
    # Mobile Access
    ###########################################

    MOBILE_BASE_URL = os.getenv(
        "MOBILE_BASE_URL",
        ""
    ).strip().rstrip("/")


settings = Settings()
