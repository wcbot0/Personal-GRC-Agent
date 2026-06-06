"""Qdrant semantic memory with local embedding service."""
from __future__ import annotations

import hashlib
import os
import uuid
from typing import Any

import httpx

from spa.memory.redaction import redact_obj, redact_text
from spa.paths import get_data_dir


class SemanticMemory:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        collection: str | None = None,
        embedding_base: str | None = None,
    ) -> None:
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = port or int(os.getenv("QDRANT_PORT", "6333"))
        self.collection = collection or os.getenv("QDRANT_COLLECTION", "spa_brain")
        self.embedding_base = embedding_base or os.getenv(
            "EMBEDDING_API_BASE", "http://localhost:8080"
        )
        self._client = None
        self._offline_mode = False

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            self._client = QdrantClient(host=self.host, port=self.port)
            collections = [c.name for c in self._client.get_collections().collections]
            if self.collection not in collections:
                self._client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=self._embedding_dim(), distance=Distance.COSINE),
                )
            return self._client
        except Exception:
            self._offline_mode = True
            self._local_index_path = get_data_dir() / "semantic_fallback.jsonl"
            self._local_index_path.parent.mkdir(parents=True, exist_ok=True)
            return None

    def _embedding_dim(self) -> int:
        try:
            vec = self._embed("dimension probe")
            return len(vec)
        except Exception:
            return 768

    def _embed(self, text: str) -> list[float]:
        text = redact_text(text)
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self.embedding_base.rstrip('/')}/embed",
                json={"inputs": text},
            )
            resp.raise_for_status()
            data = resp.json()
        if isinstance(data, list) and data and isinstance(data[0], list):
            return data[0]
        if isinstance(data, dict) and "embeddings" in data:
            return data["embeddings"][0]
        raise ValueError("Unexpected embedding response format")

    def _point_id(self, doc_id: str) -> str:
        return hashlib.sha256(doc_id.encode()).hexdigest()[:32]

    def upsert_document(
        self,
        doc_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        content = redact_text(content)
        metadata = redact_obj(metadata or {})
        client = self._get_client()
        memory_id = str(uuid.uuid5(uuid.NAMESPACE_URL, doc_id))

        if client is None or self._offline_mode:
            import json

            entry = {
                "id": memory_id,
                "doc_id": doc_id,
                "content": content,
                "metadata": metadata,
            }
            with self._local_index_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
            return memory_id

        from qdrant_client.models import PointStruct

        vector = self._embed(content[:8000])
        client.upsert(
            collection_name=self.collection,
            points=[
                PointStruct(
                    id=self._point_id(doc_id),
                    vector=vector,
                    payload={
                        "memory_id": memory_id,
                        "doc_id": doc_id,
                        "content": content[:4000],
                        **metadata,
                    },
                )
            ],
        )
        return memory_id

    def query(self, text: str, limit: int = 5) -> list[dict[str, Any]]:
        client = self._get_client()
        if client is None or self._offline_mode:
            import json

            results = []
            if hasattr(self, "_local_index_path") and self._local_index_path.exists():
                for line in self._local_index_path.read_text(encoding="utf-8").splitlines():
                    entry = json.loads(line)
                    if text.lower() in entry["content"].lower():
                        results.append(entry)
            return results[:limit]

        from qdrant_client.models import Filter

        vector = self._embed(text)
        hits = client.search(
            collection_name=self.collection,
            query_vector=vector,
            limit=limit,
        )
        return [
            {
                "id": hit.payload.get("memory_id"),
                "doc_id": hit.payload.get("doc_id"),
                "content": hit.payload.get("content"),
                "score": hit.score,
                "metadata": {k: v for k, v in hit.payload.items() if k not in {"content"}},
            }
            for hit in hits
        ]

    def forget_by_id(self, memory_id: str) -> bool:
        client = self._get_client()
        if client is None or self._offline_mode:
            if not hasattr(self, "_local_index_path") or not self._local_index_path.exists():
                return False
            import json

            kept = []
            removed = False
            for line in self._local_index_path.read_text(encoding="utf-8").splitlines():
                entry = json.loads(line)
                if entry.get("id") == memory_id or entry.get("doc_id") == memory_id:
                    removed = True
                else:
                    kept.append(line)
            self._local_index_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
            return removed

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[FieldCondition(key="memory_id", match=MatchValue(value=memory_id))]
            ),
        )
        return True

    def forget_by_tag(self, tag: str) -> int:
        client = self._get_client()
        if client is None or self._offline_mode:
            import json

            if not hasattr(self, "_local_index_path") or not self._local_index_path.exists():
                return 0
            kept = []
            removed = 0
            for line in self._local_index_path.read_text(encoding="utf-8").splitlines():
                entry = json.loads(line)
                tags = entry.get("metadata", {}).get("tags", [])
                if tag in tags:
                    removed += 1
                else:
                    kept.append(line)
            self._local_index_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
            return removed

        return 0
