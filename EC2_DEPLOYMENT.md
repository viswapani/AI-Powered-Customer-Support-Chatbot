# MedEquip Chatbot – EC2 Deployment Guide

This document explains how to deploy the MedEquip Customer Support Chatbot to an existing EC2 instance that already runs a MySQL container and a separate banking backend.

Assumptions

- You already have on EC2:
  - A Docker network called `app-net`.
  - A MySQL container named `banking-mysql` running on `app-net` and listening on port `3306`.
  - (Optional) Another app (e.g. `banking-backend`) on the same network.
- You will:
  - Build the chatbot image **on your laptop**.
  - Copy the image to EC2 and load it there.
  - Expose the chatbot on EC2 host port `8001` (container port is `8000`).

---

## 1. Build the Docker image on your laptop

On your laptop, in PowerShell, from the project root:

```bash
cd C:\Pani\AI-Powered-Customer-Support-Chatbot

docker build -t medequip-chatbot:prod .
```

This creates a local image named `medequip-chatbot:prod`.

---

## 2. Save the image to a tarball

Still on your laptop:

```bash
docker save -o medequip-chatbot-prod.tar medequip-chatbot:prod
```

You should now have `medequip-chatbot-prod.tar` in the project directory.

---

## 3. Copy the image tarball to EC2

From your laptop (adjust key path, user, and IP/DNS):

```bash
scp -i C:\path\to\your-key.pem \
    C:\Pani\AI-Powered-Customer-Support-Chatbot\medequip-chatbot-prod.tar \
    ec2-user@YOUR_EC2_PUBLIC_IP:~/
```

Replace:

- `C:\path\to\your-key.pem` with your SSH key path.
- `YOUR_EC2_PUBLIC_IP` with your EC2 public IP or DNS.

---

## 4. Load the image on EC2

SSH into EC2:

```bash
ssh -i /path/to/your-key.pem ec2-user@YOUR_EC2_PUBLIC_IP
```

Then load the image:

```bash
cd ~
docker load -i medequip-chatbot-prod.tar

docker images | grep medequip-chatbot
```

You should see `medequip-chatbot   prod` in the output.

---

## 5. Create a custom `.env` file for EC2

On EC2, create a dedicated env file for the MedEquip chatbot (for example `~/.env-medequip`). This file will be used by `docker run --env-file`.

```bash
cat > ~/.env-medequip << 'EOF'
# ==== OpenAI / LLM ====
# Replace with your real OpenAI API key
OPENAI_API_KEY=sk-REPLACE_ME

# Flask secret key (any long random string, used for session signing)
FLASK_SECRET_KEY=some-long-random-string

# ==== MedEquip MySQL DB (on EC2) ====
# Reuse the existing MySQL container running on Docker network "app-net"
# Container name: banking-mysql
MEDEQUIP_DB_HOST=banking-mysql
MEDEQUIP_DB_PORT=3306

# Use the MySQL root user (must match how banking-mysql was started)
MEDEQUIP_DB_USER=root
MEDEQUIP_DB_PASSWORD=your_root_password
MEDEQUIP_DB_NAME=medequip

# ==== Qdrant (vector store) on EC2 ====
# Qdrant container name on app-net
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Explicit collection name (matches defaults in config.py)
QDRANT_COLLECTION=medequip_kb

# ==== Embeddings (optional; these are the defaults) ====
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
EOF
```

Replace:

- `sk-REPLACE_ME` with your actual OpenAI API key.
- `your_root_password` with the MySQL root password used when creating `banking-mysql`.

> Note: This file is separate from any other `.env` files you use (e.g. for the banking project). You will reference it explicitly with `--env-file ~/.env-medequip`.

---

## 6. Start Qdrant on EC2 (if not already running)

The chatbot uses Qdrant as its vector store. Run Qdrant as a separate container on the shared `app-net` network:

```bash
docker run -d \
  --name qdrant \
  --network app-net \
  -p 6333:6333 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest
```

This makes Qdrant reachable at `qdrant:6333` from other containers on `app-net`.

---

## 7. Initialize the MedEquip MySQL schema and seed data

Use the loaded image and your EC2 env file to create the `medequip` database, tables, and seed demo data inside the existing MySQL server (`banking-mysql`).

```bash
docker run --rm \
  --network app-net \
  --env-file ~/.env-medequip \
  medequip-chatbot:prod \
  python database.py
```

(Optional but recommended) Verify the data with the included script:

```bash
docker run --rm \
  --network app-net \
  --env-file ~/.env-medequip \
  medequip-chatbot:prod \
  python verify_db.py
```

If verification passes, you should see `All DB verification checks passed.` in the output.

---

## 8. Initialize the Qdrant knowledge base (optional but recommended)

Preload core MedEquip documents into Qdrant so the RAG components work immediately:

```bash
docker run --rm \
  --network app-net \
  --env-file ~/.env-medequip \
  medequip-chatbot:prod \
  python rag_pipeline.py
```

You can rerun this later if you want to rebuild the base knowledge base.

---

## 9. Run the MedEquip chatbot container on EC2

Finally, start the chatbot web app as a long-running container. Since port `8000` is already used by the banking backend, we expose the chatbot on host port `8001` and map it to container port `8000`.

```bash
docker run -d \
  --name medequip-chatbot \
  --network app-net \
  -p 8001:8000 \
  --env-file ~/.env-medequip \
  medequip-chatbot:prod
```

Check that it is running:

```bash
docker ps | grep medequip-chatbot
```

View logs if needed:

```bash
docker logs -f medequip-chatbot
```

---

## 10. Access the chatbot from your browser

From your local machine, open this URL in a browser:

```text
http://YOUR_EC2_PUBLIC_IP:8001/
```

Replace `YOUR_EC2_PUBLIC_IP` with your instance's public IP or DNS name.

If the page does not load, check:

- The EC2 security group allows inbound TCP `8001` from your IP.
- The `medequip-chatbot` container is `Up` (`docker ps`).
- There are no fatal errors in `docker logs medequip-chatbot`.

---

## 11. Useful maintenance commands

Stop the chatbot container:

```bash
docker stop medequip-chatbot
```

Start it again:

```bash
docker start medequip-chatbot
```

Rebuild and redeploy (after a new image tarball is copied to EC2):

1. Stop and remove the old container:

   ```bash
   docker stop medequip-chatbot
   docker rm medequip-chatbot
   ```

2. Load the new image tarball:

   ```bash
   docker load -i medequip-chatbot-prod.tar
   ```

3. Start a new container using the same `docker run` command from step 9.
