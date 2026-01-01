"""RAG (Retrieval-Augmented Generation) pipeline for MedEquip chatbot.

This module sets up a ChromaDB vector store with OpenAI embeddings and
provides simple helper functions to create the knowledge base, add
documents, and perform semantic search.

The implementation is intentionally minimal but follows the structure
from the project specification so it can be extended later.
"""

from __future__ import annotations

from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

from config import RAG_TOP_K, VECTORSTORE_PATH


_TEXT_SPLITTER = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)


def _get_embeddings() -> OpenAIEmbeddings:
    """Return an OpenAIEmbeddings instance.

    Requires OPENAI_API_KEY to be set in the environment.
    """

    return OpenAIEmbeddings()


def create_knowledge_base() -> Chroma:
    """Initialize ChromaDB with the 10 core MedEquip documents.

    Returns the Chroma vector store instance.
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

    texts = []
    metadatas = []
    for title, content in docs:
        for chunk in _TEXT_SPLITTER.split_text(content):
            texts.append(chunk)
            metadatas.append({"title": title})

    embeddings = _get_embeddings()

    vectorstore = Chroma.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas,
        persist_directory=str(VECTORSTORE_PATH),
    )
    vectorstore.persist()
    return vectorstore


def load_vectorstore() -> Chroma:
    """Load an existing Chroma vector store from disk.

    If it does not exist yet, creates it first.
    """

    embeddings = _get_embeddings()
    try:
        return Chroma(
            embedding_function=embeddings,
            persist_directory=str(VECTORSTORE_PATH),
        )
    except Exception:
        # If loading fails, (re)create the knowledge base
        return create_knowledge_base()


def add_document(title: str, content: str) -> None:
    """Add a new document to the vector store and persist it."""

    vectorstore = load_vectorstore()
    texts = _TEXT_SPLITTER.split_text(content)
    metadatas = [{"title": title} for _ in texts]
    vectorstore.add_texts(texts=texts, metadatas=metadatas)
    vectorstore.persist()


def search_knowledge(query: str, k: int = RAG_TOP_K) -> List[str]:
    """Search the knowledge base and return top-k formatted snippets."""

    vectorstore = load_vectorstore()
    docs = vectorstore.similarity_search(query, k=k)
    results: List[str] = []
    for doc in docs:
        title = doc.metadata.get("title", "Unknown")
        results.append(f"[{title}] {doc.page_content}")
    return results


if __name__ == "__main__":
    # Simple manual test entry point
    vs = create_knowledge_base()
    print("Knowledge base initialized.")
    for snippet in search_knowledge("support hours"):
        print("-", snippet)
