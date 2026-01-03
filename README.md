# MedEquip AI-Powered Customer Support Chatbot

This project is an AI-assisted customer support system for MedEquip Solutions. It combines:

- A rule-based chatbot core (authentication, intent routing, SQL queries)
- Retrieval-Augmented Generation (RAG) using Qdrant + OpenAI embeddings
- Flask UIs for:
  - Uploading documents into the Qdrant knowledge base
  - Interacting with the chatbot via a web interface

## 1. Prerequisites

- Python 3.11+ (project has been tested with Python 3.14)
- Git
- Docker (for running Qdrant easily)
- An OpenAI API key

All examples below use **PowerShell on Windows**.

## 2. Clone the repository

```powershell
git clone <your-repo-url> AI-Powered-Customer-Support-Chatbot
cd AI-Powered-Customer-Support-Chatbot
```

## 3. Create and activate a virtual environment (recommended)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

You should see `(.venv)` in your prompt.

## 4. Install dependencies

From the project root with the virtual environment activated:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

This installs:

- `openai`, `langchain`, `langchain-openai`
- `qdrant-client`
- `Flask`, `PyPDF2`
- Database drivers and utilities (`mysql-connector-python`, `pymysql`, `sqlalchemy`, `pandas`, etc.)

## 5. Environment configuration

### 5.1 OpenAI API key

Create a `.env` file in the project root and add:

```text
OPENAI_API_KEY=sk-REPLACE_ME
```

The RAG pipeline (`rag_pipeline.py`) automatically loads this via `python-dotenv`.

### 5.2 Optional: Flask secret key

You can set a Flask secret key (recommended in non-dev environments):

```powershell
$env:FLASK_SECRET_KEY = "some-long-random-string"
```

If not set, the apps fall back to `dev-secret-key`.

## 6. Run Qdrant (vector database)

The project uses [Qdrant](https://qdrant.tech/) as a vector store for embeddings.

The easiest way to run Qdrant locally is via Docker:

```powershell
docker run -p 6333:6333 qdrant/qdrant
```

Leave this container running while you work.

The default configuration in `config.py` assumes:

- `QDRANT_HOST = "localhost"`
- `QDRANT_PORT = 6333`

If you change the host or port, update these in `config.py` or set `QDRANT_HOST` / `QDRANT_PORT` environment variables.

## 7. Initialize the database

The project includes a helper script to create and seed the database.

From the project root:

```powershell
python verify_db.py
```

This will:

- Ensure the schema exists
- Seed example data for orders, tickets, invoices, etc.

(Alternatively, the DB can be initialized indirectly when running the CLI chatbot, which calls `initialize_database()`.)

## 8. Initialize the Qdrant knowledge base

You can preload Qdrant with the built-in MedEquip documents (returns policy, warranty, certifications, etc.).

```powershell
python rag_pipeline.py
```

This will:

- (Re)create the `medequip_kb` collection in Qdrant
- Embed 10 core MedEquip documents using OpenAI embeddings
- Upsert them as points into Qdrant
- Run a simple test search for `"support hours"`

## 9. Run the CLI chatbot

For a quick terminal-based test:

```powershell
python chatbot.py
```

You should see:

```text
============================================================
MedEquip Solutions Customer Support (Dev Demo)
Type 'quit' to exit, 'auth' to authenticate, 'history' to view last turns
============================================================
```

Usage:

- Type any question (e.g. `What are your support hours?`).
- Type `auth` to authenticate:
  - Enter an email and Client ID (`ME-XXXXX`) for account-specific SQL flows.
- Type `history` to view the last 10 conversation turns.
- Type `quit` or `exit` to exit.

RAG is controlled by `ENABLE_RAG` in `config.py` (defaults to `True`).

## 10. Run the document upload UI (Flask)

This Flask app lets you upload `.txt` and `.pdf` files and index them in Qdrant.

From the project root, with the virtual environment activated and Qdrant running:

```powershell
python upload_app.py
```

Open in your browser:

```text
http://127.0.0.1:5000/
```

Features:

- Upload a `.txt` or `.pdf` file.
- Optional **Title** field:
  - If provided, used as the document title.
  - If left empty, the sanitized file name (spaces removed) is used.
- For `.txt` files: content is read as text.
- For `.pdf` files: text is extracted via `PyPDF2`.
- The app calls `add_document(title, content)` from `rag_pipeline.py` to:
  - Split content into chunks
  - Embed via OpenAI
  - Upsert into the configured Qdrant collection

## 11. Run the chatbot web UI (Flask)

This Flask app provides a browser-based chat interface on top of the existing `MedEquipChatbot` logic.

From the project root:

```powershell
python chatbot_app.py
```

Open in your browser:

```text
http://127.0.0.1:5000/
```

Features:

- **Chat history view**: shows the full conversation (`bot.history`).
- **Message input**: send questions about orders, warranties, support hours, etc.
- **Authentication form**:
  - Enter `Email` and `Client ID (ME-XXXXX)` and click **Set Authentication**.
  - Uses the same `authenticate` method as the CLI chatbot; enables SQL-backed flows.
  - Submit empty fields to clear authentication.

Under the hood:

- The web app shares a single `MedEquipChatbot` instance.
- Calls `bot.chat(message)` for each user message.
- RAG and SQL routing behavior is identical to the CLI experience.

## 12. Typical local development workflow

1. Start Qdrant:

   ```powershell
   docker run -p 6333:6333 qdrant/qdrant
   ```

2. In a new terminal, activate your venv and install dependencies (first time or after updates):

   ```powershell
   cd AI-Powered-Customer-Support-Chatbot
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. Initialize the database (first time only):

   ```powershell
   python verify_db.py
   ```

4. Initialize the base knowledge base (optional but recommended):

   ```powershell
   python rag_pipeline.py
   ```

5. Optionally run the document upload UI to add more documents:

   ```powershell
   python upload_app.py
   ```

6. Run the chatbot web UI for interactive testing:

   ```powershell
   python chatbot_app.py
   ```

You can also use the CLI chatbot (`python chatbot.py`) at any time for quick debugging.

## 13. Troubleshooting

- **No RAG answers / generic fallback response**:
  - Ensure Qdrant is running (`docker run -p 6333:6333 qdrant/qdrant`).
  - Ensure `OPENAI_API_KEY` is set in `.env`.
  - Ensure `ENABLE_RAG = True` in `config.py`.
  - Try reinitializing the KB: `python rag_pipeline.py`.

- **Qdrant connection errors**:
  - Check that Qdrant is listening on `localhost:6333`.
  - Verify `QDRANT_HOST` and `QDRANT_PORT` in `config.py`.

- **OpenAI authentication errors**:
  - Double-check `OPENAI_API_KEY` in `.env`.
  - Make sure there are no extra quotes or spaces around the key.

- **Flask app crashes on upload or chat**:
  - Re-run the app in the terminal and watch for the Python traceback.
  - Fix any missing dependencies by re-running `python -m pip install -r requirements.txt`.

---

For more details on the architecture and behavior, see:

- `chatbot.py` – core chatbot logic (authentication, intent routing, SQL + RAG integration)
- `rag_pipeline.py` – Qdrant + OpenAI embeddings pipeline
- `config.py` – configuration for DB, Qdrant, and LLM settings
- `upload_app.py` – document upload Flask UI
- `chatbot_app.py` – chatbot Flask UI
