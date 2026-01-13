# MedEquip Customer Support Chatbot - Docker image

# Use official Python base image
FROM python:3.11-slim

# Ensure Python output is not buffered and disable pip cache
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Create and set working directory
WORKDIR /app

# Install system dependencies (needed for building some Python wheels like pandas)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Flask configuration
# The app object lives in chatbot_app.py as `app`
ENV FLASK_APP=chatbot_app:app \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=8000

# Port the Flask app will listen on inside the container
EXPOSE 8000

# Default command: run the Flask app
CMD ["flask", "run"]
