# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common commands and workflows

All commands are intended to be run from the repository root.

### Environment setup

- Create virtual environment (recommended):

  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```

- Install dependencies:

  ```powershell
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  ```

### Required services

- Qdrant (vector database) – must be running before any RAG operations (KB initialization, uploads, chatbot RAG queries):

  ```powershell
  docker run -p 6333:6333 qdrant/qdrant
  ```

- MySQL – `database.py` expects a reachable MySQL instance configured via `config.py` / environment variables. The code will create the `medequip` schema and tables and seed data, but it does **not** start MySQL for you.

  - Connection details come from `MEDEQUIP_DB_HOST`, `MEDEQUIP_DB_PORT`, `MEDEQUIP_DB_USER`, `MEDEQUIP_DB_PASSWORD`, `MEDEQUIP_DB_NAME` (see `config.py` for defaults).

### Environment variables / configuration

- `.env` in the project root (loaded by `rag_pipeline.py` and `database.py`):
  - `OPENAI_API_KEY` – required for embeddings and any RAG-related operations.
  - Optional: `MEDEQUIP_DB_*` variables to override MySQL host/port/user/password/db.
- Process environment (used by Flask apps and Qdrant config):
  - `FLASK_SECRET_KEY` – optional; falls back to `dev-secret-key` for local dev.
  - `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_COLLECTION`, `EMBEDDING_MODEL`, `EMBEDDING_DIM` – override RAG defaults if needed.
- Feature toggles in `config.py`:
  - `ENABLE_RAG` – if `False`, chatbot skips vector search and relies only on SQL + simple fallbacks.

### Database initialization and checks

- One-shot database initialization + integrity checks (recommended entrypoint):

  ```powershell
  python verify_db.py
  ```

  This uses `execute_query` / `get_client_by_credentials` to verify that seeded data is present across core tables.

- Direct schema + seed initialization (if you just want the DB created and populated):

  ```powershell
  python database.py
  ```

  This calls `initialize_database()` under the `__main__` guard.

### Knowledge base (Qdrant) operations

- Initialize core MedEquip knowledge base (10 built-in documents):

  ```powershell
  python rag_pipeline.py
  ```

  This recreates the `medequip_kb` collection and seeds it, then runs a simple test search for "support hours".

### Chatbot entrypoints

- CLI chatbot (good for quick debugging of routing, SQL, and RAG behavior):

  ```powershell
  python chatbot.py
  ```

- Web chatbot UI (Flask; uses the same `MedEquipChatbot` instance as the CLI logic):

  ```powershell
  python chatbot_app.py
  ```

  Then open `http://127.0.0.1:5000/` in a browser.

- Document upload UI for Qdrant (Flask):

  ```powershell
  python upload_app.py
  ```

  Then open `http://127.0.0.1:5000/` and upload `.txt` / `.pdf` files.

### Scripted scenarios / ad hoc tests

There is no formal test framework configured yet (no `pytest`/`unittest` harness). Use the provided scripts as lightweight scenario tests:

- End-to-end chatbot scenarios (auth + order tracking + general support):

  ```powershell
  python test_scenarios.py
  ```

- Database verification across key tables:

  ```powershell
  python verify_db.py
  ```

When adding automated tests, prefer new files alongside `test_scenarios.py` and wire them into a test runner (e.g., pytest) rather than modifying these demo scripts.

### Linting / formatting

There is no project-specific linting or formatting configuration in this repo. If you introduce tools (e.g., Ruff, Black, isort), keep their config alongside this file or in `pyproject.toml`.


## High-level architecture

### Overview

The system is an AI-assisted customer support stack for MedEquip Solutions, composed of three main layers:

1. **Core chatbot orchestration** (`chatbot.py`)
2. **Persistence and business data** (MySQL schema + helpers in `database.py`)
3. **RAG/knowledge base layer** (Qdrant + OpenAI embeddings in `rag_pipeline.py`)

On top of this, there are two Flask apps that expose UIs:

- `chatbot_app.py` – browser-based chat interface over `MedEquipChatbot`.
- `upload_app.py` – document uploader that feeds Qdrant via the RAG pipeline.

Configuration shared across all layers lives in `config.py`.

### Core chatbot (`chatbot.py`)

`MedEquipChatbot` is the central orchestration class and is the main integration point for future enhancements.

Key responsibilities:

- **Authentication**
  - `authenticate(email, client_id)` delegates to `database.get_client_by_credentials` and stores an `AuthenticatedClient` dataclass on the instance.
  - Several intents are marked `requires_auth`; if a request needs auth and `authenticated_client` is `None`, `chat()` short-circuits with an auth prompt.

- **Intent classification (rule-based placeholder)**
  - `classify_intent(message)` performs keyword-based matching to set:
    - `primary_intent` (e.g., `ORDER_DELIVERY`, `WARRANTY_AMC`, `ISSUE_RESOLUTION`, `FINANCIAL`, `SPARE_PARTS`, `COMPLIANCE`, `PRODUCT_INFO`, `GENERAL_SUPPORT`).
    - `requires_auth` flag.
    - `data_source` – one of `SQL`, `RAG`, or `BOTH`.
  - It also extracts IDs embedded in free text (e.g., `ORD-*`, `TKT-*`, `INV-*`, `ME-*`, and some serial-number patterns) and stores them in `entities` for downstream SQL generation.

- **SQL generation and execution**
  - `generate_sql(request, entities)` maps the high-level intent + entity hints into a small set of canned SQL templates targeting the MedEquip schema:
    - Order + shipment join for `ORDER_DELIVERY`.
    - Ticket + history join for `ISSUE_RESOLUTION`.
    - Invoice lookup, warranty lookup, and parts catalog search.
  - `execute_sql_query(sql, entities)` chooses parameter bindings based on the SQL shape and calls `database.execute_query`, relying on `authenticated_client.client_id` where appropriate.

- **RAG integration**
  - `search_knowledge_base(query)` delegates to `rag_pipeline.search_knowledge` and flattens the list of formatted snippets into a single string.
  - `chat()` uses `ENABLE_RAG` from `config.py` plus the intent’s `data_source` to decide whether to call the vector store.

- **Response formatting (non-LLM placeholder)**
  - `generate_response(...)` contains simple template logic per intent, consuming `sql_results`, `rag_context`, and `entities` to craft textual replies.
  - For RAG-only/general flows it returns the concatenated snippets; otherwise it falls back to a diagnostic JSON dump of the intent structure.

- **Conversation history**
  - A bounded `history` list of `ConversationTurn` dataclasses is maintained (max length `MAX_HISTORY_TURNS` from `config.py`).
  - Both the CLI (`run_cli()`) and web UI (`chatbot_app.py`) rely on this for displaying prior turns.

The `run_cli()` function in this module is the canonical terminal entrypoint: it calls `initialize_database()` (from `database.py`), constructs a `MedEquipChatbot`, and enters a REPL handling `auth`, `history`, and `quit` commands.

### Database layer (`database.py` + `config.py`)

The persistence layer is intentionally explicit and SQL-oriented; there is no ORM in use.

- **Configuration** (`config.py`)
  - Centralizes DB-related settings (`DB_BACKEND`, `MYSQL_*`, `MYSQL_DSN`) and declares that MySQL is the primary backend (`DB_BACKEND = "mysql"`).
  - Also defines vector store and LLM-related settings shared with the RAG layer and chatbot (e.g., `RAG_TOP_K`, `EMBEDDING_MODEL`, `ENABLE_RAG`).

- **Connection and schema management** (`database.py`)
  - `.env` is loaded early so `MEDEQUIP_DB_*` environment variables are available before importing `config`.
  - `ensure_mysql_database_exists()` connects to MySQL without specifying a DB and issues `CREATE DATABASE IF NOT EXISTS` for `MYSQL_DB`.
  - `get_connection()` is a context manager that yields a `mysql.connector` connection and handles commit/rollback.
  - `create_database()` defines the entire MedEquip schema (clients, products, equipment, orders, shipments, service regions, technicians, appointments, warranties, AMCs, coverage claims, support tickets + history, invoices, payments, and parts catalog).

- **Data seeding and helpers**
  - `generate_synthetic_data()` uses Faker to build a baseline set of clients.
  - `populate_sample_data()` inserts deterministic demo records that align with the chatbot’s canned queries (e.g., `ME-10001`, `ORD-2024-0001`, `TKT-2024-0001`, `INV-2024-3456`, and example part numbers).
  - `execute_query()` / `execute_non_query()` are low-level helpers used by both verification scripts and the chatbot.
  - `get_client_by_credentials()` is the only exported auth helper and is used by `MedEquipChatbot.authenticate()` and `verify_db.py`.
  - `initialize_database()` is the high-level entrypoint that calls `ensure_mysql_database_exists()`, `create_database()`, and `populate_sample_data()`.

- **Verification script** (`verify_db.py`)
  - Encapsulates a set of sanity checks (`check_clients`, `check_auth`, `check_orders_and_shipments`, `check_warranties_and_tickets`, `check_invoices_payments_parts`) to ensure the seeded data matches expectations.
  - `main()` orchestrates these checks and exits non-zero on failure, making this file a good candidate for future CI hooks.

### RAG and vector store (`rag_pipeline.py`)

The RAG layer is a thin wrapper around Qdrant and OpenAI embeddings, designed to be easily replaceable or extensible.

- **Environment and clients**
  - Loads `.env` from the project root to pick up `OPENAI_API_KEY`.
  - Lazily initializes three singletons:
    - `_TEXT_SPLITTER` – a `RecursiveCharacterTextSplitter`, using either `langchain_text_splitters` or legacy `langchain.text_splitter` depending on what is installed.
    - `_QDRANT_CLIENT` – `QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)`.
    - `_OPENAI_CLIENT` – an `openai.OpenAI` client created via `OpenAI(api_key=_get_openai_api_key())`.

- **Collection management**
  - `_ensure_qdrant_collection()` checks for the configured collection and creates it when missing, using `EMBEDDING_DIM` and cosine distance.
  - `create_knowledge_base()` deletes and recreates the collection, embeds a fixed set of 10 MedEquip knowledge snippets, and upserts them as points with `{title, text}` payloads.

- **Embedding and search**
  - `_embed_texts(texts)` is the central embedding helper; both seeding and querying rely on it.
  - `add_document(title, content)` splits arbitrary text into chunks, embeds them, and upserts into the existing collection; this function is used by `upload_app.py`.
  - `search_knowledge(query, k=RAG_TOP_K)` embeds the query, issues a `query_points` call to Qdrant, and formats results as `[title] text` strings; `MedEquipChatbot.search_knowledge_base()` consumes these.

- **Backup implementation**
  - `rag_pipeline_backup_before_rag_debug.py` is an older, functionally similar version that still uses `client.search(...)` instead of `query_points`. Treat it as historical reference—new work should target `rag_pipeline.py`.

### Flask applications

There are two independent Flask apps that sit on top of the core components.

- **Chatbot web UI** (`chatbot_app.py`)
  - Creates a single global `MedEquipChatbot` instance (`bot`) shared across all requests in the process.
    - Conversation history (`bot.history`) is rendered on the main page.
    - This means all browser sessions share the same in-memory chat history and authenticated client; keep that in mind when debugging multi-user behavior.
  - Routes:
    - `GET /` – renders the chat UI (history + optional auth form).
    - `POST /chat` – reads `message` from the form and calls `bot.chat(message)`.
    - `POST /set_auth` – updates session-stored `auth_email`/`auth_client_id` and calls `bot.authenticate(...)` when both fields are provided; empty fields clear authentication on the bot.
  - Uses `FLASK_SECRET_KEY` from the environment (fallback `dev-secret-key`) for session management and runs with `debug=True` under the `__main__` guard.

- **Knowledge base upload UI** (`upload_app.py`)
  - Independent Flask app dedicated to feeding Qdrant via `rag_pipeline.add_document`.
  - Accepts `.txt` and `.pdf` uploads, normalizes filenames via `secure_filename`, and uses a small PDF text extractor built on `PyPDF2`.
  - For `.txt` files it tries UTF-8 first, then falls back to Latin-1 with ignored errors.
  - Exposes two routes:
    - `GET /` – renders a simple upload form.
    - `POST /upload` – validates file type, extracts text, derives a title (explicit form field or sanitized filename), and calls `add_document`; errors are surfaced via Flask `flash()` messages.
  - Also uses `FLASK_SECRET_KEY` with the same debug-mode defaults as `chatbot_app.py`.

### Scripted flows and demos

- **`test_scenarios.py`**
  - Demonstrates two canonical flows:
    - General support question using RAG (`"What are your support hours?"`).
    - Authenticated order-tracking query (`"When will my order ORD-2024-0001 arrive?"`) after authenticating as the demo client.
  - This is the closest thing to an integration test suite at present and is useful for sanity checks after refactors to `MedEquipChatbot`, `database.py`, or `rag_pipeline.py`.

- **`verify_db.py`**
  - Focuses solely on database health and seeded data; useful when touching schema or seed logic.

When making architectural changes, update this file to reflect new cross-module flows (especially anything that changes how intents map to SQL/RAG, or how the Flask apps share state with the core chatbot).