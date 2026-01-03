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
MYSQL_PASSWORD = os.environ.get("MEDEQUIP_DB_PASSWORD", "medequip123")
MYSQL_DB = os.environ.get("MEDEQUIP_DB_NAME", "medequip")

# Optional SQLAlchemy-style DSN for future use
MYSQL_DSN = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
)

# Vector store / Qdrant configuration
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "medequip_kb")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "1536"))

# LLM configuration (from spec)
OPENAI_MODEL = "gpt-4o-mini"
TEMPERATURE = 0
MAX_HISTORY_TURNS = 10
RAG_TOP_K = 3
SQL_TIMEOUT = 5

# Feature toggles
# When False, the chatbot will not perform RAG lookups and will rely on
# SQL-backed flows and simple fallbacks only.
ENABLE_RAG = True

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
    "QDRANT_HOST",
    "QDRANT_PORT",
    "QDRANT_COLLECTION",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIM",
    "OPENAI_MODEL",
    "TEMPERATURE",
    "MAX_HISTORY_TURNS",
    "RAG_TOP_K",
    "SQL_TIMEOUT",
    "ENABLE_RAG",
]
