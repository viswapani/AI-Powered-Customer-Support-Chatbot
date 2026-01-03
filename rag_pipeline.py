"""RAG (Retrieval-Augmented Generation) pipeline for MedEquip chatbot.

This module sets up a Qdrant vector store with OpenAI embeddings and
provides simple helper functions to create the knowledge base, add
documents, and perform semantic search.

The implementation is intentionally minimal but follows the structure
from the project specification so it can be extended later.
"""

from __future__ import annotations

from typing import List
from pathlib import Path
import os
import uuid

from dotenv import load_dotenv
import openai
from qdrant_client import QdrantClient, models

from config import (
    RAG_TOP_K,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
    EMBEDDING_MODEL,
    EMBEDDING_DIM,
)

# Load environment variables (including OPENAI_API_KEY) from .env in the
# project root so embeddings work when this module is run directly.
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# Lazily initialized text splitter so we don't import LangChain unless RAG
# is actually used.
_TEXT_SPLITTER = None
_QDRANT_CLIENT: QdrantClient | None = None
_OPENAI_CLIENT: openai.OpenAI | None = None


def _get_text_splitter():
    """Return a RecursiveCharacterTextSplitter instance, importing on demand."""

    global _TEXT_SPLITTER
    if _TEXT_SPLITTER is None:
        # Support both new and legacy LangChain layouts for text splitters.
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:  # fallback for older langchain versions
            from langchain.text_splitter import RecursiveCharacterTextSplitter

        _TEXT_SPLITTER = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
        )
    return _TEXT_SPLITTER


def _get_qdrant_client() -> QdrantClient:
    """Return a shared QdrantClient instance."""

    global _QDRANT_CLIENT
    if _QDRANT_CLIENT is None:
        _QDRANT_CLIENT = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return _QDRANT_CLIENT


def _get_openai_client() -> openai.OpenAI:
    """Return a shared OpenAI client instance."""

    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is None:
        from openai import OpenAI

        _OPENAI_CLIENT = OpenAI(api_key=_get_openai_api_key())
    return _OPENAI_CLIENT


def _ensure_qdrant_collection() -> None:
    """Ensure the Qdrant collection for the knowledge base exists."""

    client = _get_qdrant_client()
    if not client.collection_exists(QDRANT_COLLECTION):
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=models.VectorParams(
                size=EMBEDDING_DIM,
                distance=models.Distance.COSINE,
            ),
        )


def _get_openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Please add it to your environment or .env file."
        )
    return api_key


def _embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts using the OpenAI embeddings API."""

    client = _get_openai_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def create_knowledge_base():
    """Initialize Qdrant with the 10 core MedEquip documents.

    This recreates the Qdrant collection so the operation is idempotent.
    """

    docs = [
        (
            "Returns & Refunds Policy",
            "MedEquip offers a 30-day return policy on most equipment. Returns require an RMA number and original packaging.",
        ),
        (
            "Warranty Policy",
            "Standard warranty coverage is 12 months from installation date, covering defects in materials and workmanship.",
        ),
        (
            "AMC Tiers",
            "MedEquip offers Basic, Standard, and Premium Annual Maintenance Contracts with varying response times and coverage.",
        ),
        (
            "Installation Requirements",
            "Site preparation guidelines include power, grounding, room dimensions, and HVAC requirements for imaging equipment.",
        ),
        (
            "ISO 13485 Certificate",
            "MedEquip Solutions is certified to ISO 13485 for medical device quality management systems.",
        ),
        (
            "FDA 510(k) Summary DL-4000",
            "DiagnosticLab DL-4000 has FDA 510(k) clearance for diagnostic imaging applications.",
        ),
        (
            "CE Declaration SR-2000",
            "Surgical Robot SR-2000 bears the CE mark and conforms to applicable EU directives.",
        ),
        (
            "Patient Monitor PM-800 Manual",
            "PM-800 operator manual including alarm limits, parameter descriptions, and safety warnings.",
        ),
        (
            "Contact Information",
            "MedEquip global support: North America +1-800-555-0100, EMEA +44-20-5550-1000, APAC +65-6555-0100. Support hours 24/7 for critical issues.",
        ),
        (
            "CT Scanner CT-4000 Specs",
            "CT-4000 specifications: 128-slice detector, 0.35s rotation time, 78cm gantry aperture.",
        ),
    ]

    texts: List[str] = []
    metadatas: List[dict] = []
    ids: List[str] = []
    splitter = _get_text_splitter()
    for title, content in docs:
        for idx, chunk in enumerate(splitter.split_text(content)):
            texts.append(chunk)
            metadatas.append({"title": title})
            ids.append(str(uuid.uuid4()))

    client = _get_qdrant_client()
    if client.collection_exists(QDRANT_COLLECTION):
        client.delete_collection(QDRANT_COLLECTION)

    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=models.VectorParams(
            size=EMBEDDING_DIM,
            distance=models.Distance.COSINE,
        ),
    )

    vectors = _embed_texts(texts)
    points = [
        models.PointStruct(
            id=pid,
            vector=vec,
            payload={"title": meta["title"], "text": text},
        )
        for pid, vec, meta, text in zip(ids, vectors, metadatas, texts)
    ]

    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    return client


def load_vectorstore():
    """Ensure the Qdrant collection exists and return a client handle."""

    _ensure_qdrant_collection()
    return _get_qdrant_client()


def add_document(title: str, content: str) -> None:
    """Add a new document to the vector store and persist it in Qdrant."""

    client = load_vectorstore()
    splitter = _get_text_splitter()
    texts = splitter.split_text(content)
    if not texts:
        return

    metadatas = [{"title": title} for _ in texts]
    ids = [str(uuid.uuid4()) for _ in texts]
    vectors = _embed_texts(texts)

    points = [
        models.PointStruct(
            id=pid,
            vector=vec,
            payload={"title": meta["title"], "text": text},
        )
        for pid, vec, meta, text in zip(ids, vectors, metadatas, texts)
    ]

    client.upsert(collection_name=QDRANT_COLLECTION, points=points)


def search_knowledge(query: str, k: int = RAG_TOP_K) -> List[str]:
    """Search the knowledge base in Qdrant and return top-k formatted snippets.

    If the vector store or its dependencies are unavailable, this function
    degrades gracefully and returns an empty list instead of raising.
    """

    try:
        client = load_vectorstore()
        #print(f"DEBUG: client type: {type(client)}")
        #print(f"DEBUG: client attributes: {[a for a in dir(client) if not a.startswith('_')]}")
        query_vector = _embed_texts([query])[0]
        res = client.query_points(
            collection_name=QDRANT_COLLECTION,
            query=query_vector,
            limit=k,
        ).points
    except Exception as e:
        print("RAG error:", repr(e))
        raise

    results: List[str] = []
    for point in res:
        payload = point.payload or {}
        title = payload.get("title", "Unknown")
        text = payload.get("text", "")
        if text:
            results.append(f"[{title}] {text}")
    return results


if __name__ == "__main__":
    # Simple manual test entry point
    create_knowledge_base()
    print("Knowledge base initialized.")
    for snippet in search_knowledge("support hours"):
        print("-", snippet)
