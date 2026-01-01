"""Global configuration for MedEquip AI Customer Support Chatbot."""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"

# Database configuration
# SQLite path (still used by the current database.py implementation)
DB_PATH = DATA_DIR / "medequip.db"

# Primary database backend; set to "mysql" to indicate MySQL should be used
DB_BACKEND = "mysql"  # or "sqlite"

# MySQL connection settings (override via environment variables in production)
MYSQL_HOST = os.environ.get("MEDEQUIP_DB_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MEDEQUIP_DB_PORT", "3306"))
MYSQL_USER = os.environ.get("MEDEQUIP_DB_USER", "medequip_user")
MYSQL_PASSWORD = os.environ.get("MEDEQUIP_DB_PASSWORD", "change-me")
MYSQL_DB = os.environ.get("MEDEQUIP_DB_NAME", "medequip")

# Optional SQLAlchemy-style DSN for future use
MYSQL_DSN = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
)

# Vector store configuration
VECTORSTORE_PATH = VECTORSTORE_DIR / "chroma_db"

# LLM configuration (from spec)
OPENAI_MODEL = "gpt-4o-mini"
TEMPERATURE = 0
MAX_HISTORY_TURNS = 10
RAG_TOP_K = 3
SQL_TIMEOUT = 5

__all__ = [
    "BASE_DIR",
    "DATA_DIR",
    "VECTORSTORE_DIR",
    "DB_PATH",
    "DB_BACKEND",
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DB",
    "MYSQL_DSN",
    "VECTORSTORE_PATH",
    "OPENAI_MODEL",
    "TEMPERATURE",
    "MAX_HISTORY_TURNS",
    "RAG_TOP_K",
    "SQL_TIMEOUT",
]
