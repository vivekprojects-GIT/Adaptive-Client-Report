"""
RagStore — thin wrapper over a persistent ChromaDB collection.

One collection ("ape_kb") holds documents for every domain; each document
carries a `domain` metadata field so retrieval is filtered to a single domain
(cricket / it / movies / travel). Embeddings use Chroma's default local model
(all-MiniLM-L6-v2 via ONNX) — no network call, which keeps the synthesis path
free of external embedding latency.

The store is process-local and lazily initialized. ingest() is idempotent:
it only loads the seed corpus if the collection is empty (or force=True).
"""

from __future__ import annotations

import os
import threading
from typing import Any, Dict, List, Optional

from .corpus import KNOWLEDGE, RAG_DOMAINS

_COLLECTION = "ape_kb"


class RagStore:
    def __init__(self, persist_dir: Optional[str] = None) -> None:
        self.persist_dir = persist_dir or os.getenv("APE_RAG_DIR", "./.chroma")
        self._client = None
        self._col = None
        self._lock = threading.Lock()

    # -- lazy Chroma handles ------------------------------------------------
    def _collection(self):
        if self._col is None:
            with self._lock:
                if self._col is None:
                    import chromadb
                    os.makedirs(self.persist_dir, exist_ok=True)
                    self._client = chromadb.PersistentClient(path=self.persist_dir)
                    self._col = self._client.get_or_create_collection(
                        name=_COLLECTION,
                        metadata={"hnsw:space": "cosine"},
                    )
        return self._col

    # -- ingestion ----------------------------------------------------------
    def count(self, domain: Optional[str] = None) -> int:
        col = self._collection()
        if domain:
            return col.count() and len(
                col.get(where={"domain": domain}).get("ids", [])
            )
        return col.count()

    def ingest(self, force: bool = False) -> Dict[str, int]:
        """Load the seed corpus into the collection. Idempotent unless force."""
        col = self._collection()
        if force and col.count() > 0:
            # wipe and reload
            existing = col.get().get("ids", [])
            if existing:
                col.delete(ids=existing)
        elif col.count() > 0:
            # already populated — report per-domain counts without reloading
            return self._domain_counts()

        ids: List[str] = []
        docs: List[str] = []
        metas: List[Dict[str, Any]] = []
        for domain, entries in KNOWLEDGE.items():
            for e in entries:
                ids.append(e["id"])
                docs.append(e["text"])
                metas.append({"domain": domain, "title": e["title"]})
        if ids:
            col.add(ids=ids, documents=docs, metadatas=metas)
        return self._domain_counts()

    def _domain_counts(self) -> Dict[str, int]:
        col = self._collection()
        out: Dict[str, int] = {}
        for d in RAG_DOMAINS:
            out[d] = len(col.get(where={"domain": d}).get("ids", []))
        return out

    # -- retrieval ----------------------------------------------------------
    def retrieve(self, query: str, domain: str, k: int = 4) -> List[Dict[str, Any]]:
        """Return the top-k passages for a query within one domain.

        Each hit: {id, title, text, distance}. Empty list if domain has no
        docs or the query is blank. Never raises on a cold/empty collection.
        """
        if not query or not domain:
            return []
        col = self._collection()
        try:
            res = col.query(
                query_texts=[query],
                n_results=k,
                where={"domain": domain},
            )
        except Exception:
            return []
        hits: List[Dict[str, Any]] = []
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        for i, _id in enumerate(ids):
            meta = metas[i] if i < len(metas) else {}
            hits.append({
                "id":       _id,
                "title":    (meta or {}).get("title", ""),
                "text":     docs[i] if i < len(docs) else "",
                "distance": dists[i] if i < len(dists) else None,
            })
        return hits


def format_context(hits: List[Dict[str, Any]]) -> str:
    """Render retrieved passages into a compact context block for the prompt."""
    if not hits:
        return ""
    lines = []
    for h in hits:
        title = h.get("title") or h.get("id")
        lines.append(f"- [{title}] {h.get('text', '')}")
    return "\n".join(lines)
