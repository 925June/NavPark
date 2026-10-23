from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv(
    Path(__file__).resolve().parent.parent / ".env"
)


class Settings:

    ###########################################
    # LLM Configuration
    ###########################################

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local")

    OPENAI_MODEL = os.getenv(
        "OPENAI_MODEL",
        "gpt-4.1-mini"
    )

    CLAUDE_MODEL = os.getenv(
        "CLAUDE_MODEL",
        "claude-sonnet-4-20250514"
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


settings = Settings()
