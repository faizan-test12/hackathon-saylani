import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(basedir, "instance", "roastco.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- AI / Model config ---
    # Supported list: gemini-3.7-flash, gemini-3.6-flash, gemini-3.5-flash, gemini-3.5-flash-lite, gemini-3.1-flash-lite
    GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
    FALLBACK_MODELS = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.7-flash",
    ]

    # Local embedding model (no API key needed)
    EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
    EMBEDDING_DIM = 384

    # Upload config
    UPLOAD_FOLDER = os.path.join(basedir, "instance", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # --- Token pricing (per 1M tokens, USD) ---
    PRICE_PER_1M_PROMPT_TOKENS = 0.15
    PRICE_PER_1M_COMPLETION_TOKENS = 0.60
