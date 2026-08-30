"""
Services Package
================
Exports AI RAG retrieval, streaming chat agent dispatchers, and token usage accounting services.
"""

from app.services.rag import retrieve, ingest_document
from app.services.chat_agent import stream_message, process_message
from app.services.usage import calculate_cost

__all__ = [
    "retrieve",
    "ingest_document",
    "stream_message",
    "process_message",
    "calculate_cost",
]
