# MedEquip Chatbot – Full Project Setup & Deployment Guide

This guide walks a new developer from an empty machine to:
- Running the MedEquip Customer Support Chatbot locally (CLI and web UI)
- Running Qdrant locally for RAG
- Initializing the MySQL database with sample data
- Building a production Docker image
- Deploying the chatbot to EC2 using Docker (with MySQL + Qdrant in containers)

The examples use **Windows + PowerShell** for local development and a **Linux EC2** instance for deployment, but the concepts are portable.

---

## 1. Prerequisites

### 1.1. Local machine

Install:

- **Python** 3.11+
- **Git**
- **Docker Desktop** (includes Docker CLI)
- A valid **OpenAI API key** (for embeddings and LLM calls)

### 1.2. EC2 instance

On AWS you’ll need:

- A Linux EC2 instance (Amazon Linux or Ubuntu)
- Security group allowing:
  - TCP 22 (SSH)
  - TCP 8001 (chatbot web UI on EC2)
  - TCP 3306 (optional, if you need external DB access – typically keep this internal only)
  - TCP 6333 (optional, if you want to hit Qdrant from outside – often not needed)
- Docker installed on EC2 (we’ll cover basic steps below)

---

## 2. Clone the repository

On your local machine (PowerShell):

```bash
cd C:\Pani

git clone https://github.com/viswapani/AI-Powered-Customer-Support-Chatbot.git
cd AI-Powered-Customer-Support-Chatbot
```

You now have the project code locally.

---

## 3. Local Python environment & dependencies

### 3.1. Create and activate a virtual environment

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

You should see `(.venv)` in your PowerShell prompt.

### 3.2. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

This installs:

- `openai`, `langchain`, `langchain-openai`, `langchain-community`
- `qdrant-client`
- `Flask`, `PyPDF2`
- DB and utility packages: `mysql-connector-python`, `pymysql`, `sqlalchemy`, `pandas`, `python-dotenv`, etc.

---

## 4. Configure environment variables (local)

Create a `.env` file in the project root for local development:

```text
OPENAI_API_KEY=sk-REPLACE_ME

# Optional but recommended for Flask sessions
FLASK_SECRET_KEY=some-long-random-string

# MySQL configuration for local dev (if using Docker MySQL below)
MEDEQUIP_DB_HOST=localhost
MEDEQUIP_DB_PORT=3306
MEDEQUIP_DB_USER=medequip_user
MEDEQUIP_DB_PASSWORD=medequip123
MEDEQUIP_DB_NAME=medequip

# Qdrant configuration for local dev
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=medequip_kb
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
```

Replace `sk-REPLACE_ME` with your real OpenAI API key.

> The code uses `config.py` defaults for many of these values; the `.env` file lets you override them cleanly for local runs.

---

## 5. Run infrastructure locally with Docker

You need two services for the full experience:

1. **MySQL** (for structured customer/account/order data)
2. **Qdrant** (for vector / RAG documents)

### 5.1. Start MySQL in Docker (local)

From any terminal (PowerShell or CMD):

```bash
docker run -d ^
  --name medequip-mysql ^
  -e MYSQL_ROOT_PASSWORD=root_password ^
  -e MYSQL_DATABASE=medequip ^
  -e MYSQL_USER=medequip_user ^
  -e MYSQL_PASSWORD=medequip123 ^
  -v medequip-mysql-data:/var/lib/mysql ^
  -p 3306:3306 ^
  mysql:8.0
```

This will:

- Run MySQL 8.0 on `localhost:3306`
- Create a DB `medequip`
- Create user `medequip_user` / `medequip123` with access to that DB

These values match the defaults we set in `.env`.

### 5.2. Start Qdrant in Docker (local)

In another terminal:

```bash
docker run -d ^
  --name qdrant ^
  -p 6333:6333 ^
  -v qdrant_storage:/qdrant/storage ^
  qdrant/qdrant:latest
```

This exposes Qdrant’s HTTP API at `http://localhost:6333`.

---

## 6. Initialize the MySQL database with sample data (local)

The project includes utilities in `database.py` to create all tables and seed example data.

With your virtualenv active and from the project root:

```bash
python database.py
```

This will:

- Ensure the MySQL database `medequip` exists
- Create all MedEquip tables (clients, orders, shipments, warranties, tickets, invoices, parts, etc.)
- Insert a set of synthetic baseline records

Then run the verification script:

```bash
python verify_db.py
```

If everything is wired correctly, you should see checks for clients, auth, orders/shipments, warranties/tickets, and invoices/payments/parts, ending with a success message.

---

## 7. Initialize the Qdrant knowledge base (local)

To preload Qdrant with core MedEquip documents (returns policy, warranties, AMC tiers, certifications, support hours, etc.):

```bash
python rag_pipeline.py
```

This script will:

- Ensure the `medequip_kb` collection exists in Qdrant
- Embed the built-in documents using OpenAI embeddings
- Upsert them as points into Qdrant
- Run a simple test query (`"support hours"`) and print results

---

## 8. Run the chatbot locally (CLI and web)

### 8.1. CLI chatbot

For a quick terminal-based test:

```bash
python chatbot.py
```

You’ll see a banner and can:

- Type general questions (e.g. *What are your support hours?*)
- Type `auth` to authenticate with email + Client ID (ME-XXXXX)
- Type `history` to view recent conversation turns
- Type `quit` or `exit` to leave

### 8.2. Web chatbot UI

To run the Flask web UI for the chatbot:

```bash
python chatbot_app.py
```

By default, Flask runs on `http://127.0.0.1:5000/` in development mode.

- Open a browser to `http://127.0.0.1:5000/`
- Use the top form to optionally authenticate (email + Client ID)
- Ask questions in the chat box

> Note: In production/Docker, the web app is configured via `FLASK_APP=chatbot_app:app` and listens on port `8000` inside the container.

### 8.3. Document upload UI (optional)

You can also run the upload UI (if present) to add `.txt` or `.pdf` files into the Qdrant knowledge base:

```bash
python upload_app.py
```

This typically runs at `http://127.0.0.1:5000/` and lets you upload documents, which are then chunked, embedded, and upserted into Qdrant using `add_document` from `rag_pipeline.py`.

---

## 9. Build a production Docker image (locally)

The repository includes a `Dockerfile` that packages the Flask chatbot web app.

From the project root:

```bash
docker build -t medequip-chatbot:prod .
```

This image:

- Uses `python:3.11-slim` as a base
- Installs dependencies from `requirements.txt`
- Copies the application code
- Sets `FLASK_APP=chatbot_app:app` and exposes port `8000`
- Runs `flask run` on container startup

You can test it locally by running:

```bash
docker run -d ^
  --name medequip-chatbot-local ^
  -p 8000:8000 ^
  --env-file .env ^
  medequip-chatbot:prod
```

Then open `http://localhost:8000/` in your browser.

> Ensure your local `.env` points to reachable MySQL and Qdrant instances (for local tests that typically means `localhost` as shown earlier).

---

## 10. Deploying to EC2 with Docker

This section assumes a **fresh** EC2 deployment scenario where the chatbot, MySQL, and Qdrant all run on the same instance and share a Docker network. If you already have other apps running, you can adapt names and ports as needed.

### 10.1. Install Docker on EC2

SSH into your EC2 instance:

```bash
ssh -i /path/to/your-key.pem ec2-user@YOUR_EC2_PUBLIC_IP
```

For Amazon Linux:

```bash
sudo yum update -y
sudo yum install -y docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ec2-user
```

Log out and back in so your user joins the `docker` group.

Verify:

```bash
docker version
```

### 10.2. (Optional) Create a dedicated Docker network

To isolate services, create a network (you can also reuse an existing one):

```bash
docker network create medequip-net
```

We’ll attach MySQL, Qdrant, and the chatbot container to this network.

### 10.3. Run MySQL on EC2

On EC2:

```bash
docker run -d \
  --name medequip-mysql \
  --network medequip-net \
  -e MYSQL_ROOT_PASSWORD=root_password \
  -e MYSQL_DATABASE=medequip \
  -e MYSQL_USER=medequip_user \
  -e MYSQL_PASSWORD=medequip123 \
  -v medequip-mysql-data:/var/lib/mysql \
  -p 3306:3306 \
  mysql:8.0
```

This mirrors the local settings and works well with the code’s defaults.

### 10.4. Run Qdrant on EC2

```bash
docker run -d \
  --name qdrant \
  --network medequip-net \
  -p 6333:6333 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest
```

Now MySQL and Qdrant are reachable from any container on `medequip-net` as `medequip-mysql:3306` and `qdrant:6333`.

### 10.5. Prepare an EC2-specific env file

Create `~/.env-medequip` on EC2:

```bash
cat > ~/.env-medequip << 'EOF'
# ==== OpenAI / LLM ====
OPENAI_API_KEY=sk-REPLACE_ME

# Flask secret key
FLASK_SECRET_KEY=some-long-random-string

# ==== MedEquip MySQL DB (on EC2) ====
MEDEQUIP_DB_HOST=medequip-mysql
MEDEQUIP_DB_PORT=3306
MEDEQUIP_DB_USER=medequip_user
MEDEQUIP_DB_PASSWORD=medequip123
MEDEQUIP_DB_NAME=medequip

# ==== Qdrant (vector store) on EC2 ====
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=medequip_kb

# ==== Embeddings (optional, matches defaults) ====
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536

# Initialize base KB on web app startup (optional)
INIT_QDRANT_KB=true
EOF
```

Replace `sk-REPLACE_ME` with your actual OpenAI key.

### 10.6. Get the Docker image onto EC2

There are two common approaches:

#### Option A – Push to a registry (GitHub Container Registry, ECR, Docker Hub)

1. Tag and push from your local machine:

   ```bash
   docker tag medequip-chatbot:prod YOUR_REGISTRY/medequip-chatbot:prod
   docker push YOUR_REGISTRY/medequip-chatbot:prod
   ```

2. On EC2, log into the registry and pull:

   ```bash
   docker pull YOUR_REGISTRY/medequip-chatbot:prod
   ```

#### Option B – Copy a tarball directly (simple for testing)

On your local machine:

```bash
docker save -o medequip-chatbot-prod.tar medequip-chatbot:prod

scp -i C:\path\to\your-key.pem ^
    C:\Pani\AI-Powered-Customer-Support-Chatbot\medequip-chatbot-prod.tar ^
    ec2-user@YOUR_EC2_PUBLIC_IP:~/
```

On EC2:

```bash
cd ~
docker load -i medequip-chatbot-prod.tar
```

Verify:

```bash
docker images | grep medequip-chatbot
```

You should see `medequip-chatbot   prod`.

### 10.7. Initialize the MySQL schema and sample data on EC2

Use the image and env file to create and seed the DB:

```bash
docker run --rm \
  --network medequip-net \
  --env-file ~/.env-medequip \
  medequip-chatbot:prod \
  python database.py
```

(Optional) Verify with the helper script:

```bash
docker run --rm \
  --network medequip-net \
  --env-file ~/.env-medequip \
  medequip-chatbot:prod \
  python verify_db.py
```

### 10.8. Initialize the Qdrant knowledge base (optional but recommended)

```bash
docker run --rm \
  --network medequip-net \
  --env-file ~/.env-medequip \
  medequip-chatbot:prod \
  python rag_pipeline.py
```

This will preload core MedEquip documents into Qdrant.

### 10.9. Run the chatbot web app on EC2

Finally, start the long-running web container. We’ll expose it on host port `8001` mapped to container port `8000`:

```bash
docker run -d \
  --name medequip-chatbot \
  --network medequip-net \
  -p 8001:8000 \
  --env-file ~/.env-medequip \
  medequip-chatbot:prod
```

Check it’s running:

```bash
docker ps | grep medequip-chatbot
```

View logs if needed:

```bash
docker logs -f medequip-chatbot
```

### 10.10. Access the chatbot from your browser

From your local machine, open:

```text
http://YOUR_EC2_PUBLIC_IP:8001/
```

If the page doesn’t load, check:

- EC2 security group allows inbound TCP `8001` from your IP.
- The `medequip-chatbot` container is `Up` (`docker ps`).
- There are no fatal errors in `docker logs medequip-chatbot`.

---

## 11. Maintenance and redeployments

### 11.1. Stopping/starting the chatbot on EC2

```bash
# Stop
docker stop medequip-chatbot

# Start again
docker start medequip-chatbot
```

### 11.2. Updating the code and redeploying

Typical flow:

1. Make code changes locally and commit/push to Git.
2. Rebuild the Docker image locally:

   ```bash
   docker build -t medequip-chatbot:prod .
   ```

3. Either push to a registry or re-export as a tarball and copy to EC2 (as in 10.6).
4. On EC2, stop/remove the old container and start a new one:

   ```bash
   docker stop medequip-chatbot
   docker rm medequip-chatbot

   # (Load or pull the new image here)

   docker run -d \
     --name medequip-chatbot \
     --network medequip-net \
     -p 8001:8000 \
     --env-file ~/.env-medequip \
     medequip-chatbot:prod
   ```

The DB and Qdrant data are stored in named volumes (`medequip-mysql-data`, `qdrant_storage`), so redeploying the app container does not wipe your data.

---

You now have a complete path from cloning the repo to running the MedEquip chatbot locally and in production on EC2. This guide should be enough for any new developer to reproduce your setup and extend the system.