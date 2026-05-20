"""Multi-domain RAG package — Chroma-backed knowledge base + retrieval."""

from .corpus import KNOWLEDGE, RAG_DOMAINS
from .store import RagStore, format_context

__all__ = ["KNOWLEDGE", "RAG_DOMAINS", "RagStore", "format_context"]
