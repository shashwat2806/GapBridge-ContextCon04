from __future__ import annotations

import re

import numpy as np

from .llm import LocalLLM, LocalModelError
from .models import SourceChunk

TOKEN_RE = re.compile(r"[a-z0-9]{2,}")
STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "were",
    "has", "have", "had", "into", "their", "they", "them", "its", "not", "but",
    "all", "any", "who", "what", "when", "where", "how", "why", "does", "must",
    "shall", "will", "can", "may", "should", "policy", "organization",
}


def _tokens(text: str) -> set[str]:
    return {token for token in TOKEN_RE.findall(text.lower()) if token not in STOP_WORDS}


class Retriever:
    def __init__(
        self,
        chunks: list[SourceChunk],
        llm: LocalLLM,
        *,
        use_embeddings: bool = True,
    ):
        self.chunks = chunks
        self.llm = llm
        self.vectors: np.ndarray | None = None
        self.mode = "lexical"
        self.notice = ""
        if use_embeddings:
            try:
                vectors = []
                for start in range(0, len(chunks), 64):
                    vectors.extend(
                        llm.embed([f"{chunk.section}\n{chunk.text}" for chunk in chunks[start : start + 64]])
                    )
                if len(vectors) != len(chunks):
                    raise ValueError("Embedding count did not match the policy passage count.")
                matrix = np.asarray(vectors, dtype=np.float32)
                norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                self.vectors = matrix / np.maximum(norms, 1e-12)
                self.mode = "local embeddings + lexical rerank"
            except (LocalModelError, ValueError, TypeError) as exc:
                self.notice = f"Embedding model unavailable; using local lexical retrieval ({exc})."

    def search(self, query: str, k: int = 4) -> list[SourceChunk]:
        if not self.chunks:
            return []
        query_tokens = _tokens(query)
        lexical = []
        for chunk in self.chunks:
            overlap = len(query_tokens & _tokens(f"{chunk.section} {chunk.text}"))
            lexical.append(overlap / max(1, len(query_tokens)))

        if self.vectors is None:
            scores = np.asarray(lexical, dtype=np.float32)
        else:
            try:
                query_vector = np.asarray(self.llm.embed([query])[0], dtype=np.float32)
                query_vector = query_vector / max(float(np.linalg.norm(query_vector)), 1e-12)
                semantic = np.maximum(self.vectors @ query_vector, 0.0)
                scores = 0.65 * semantic + 0.35 * np.asarray(lexical, dtype=np.float32)
            except (LocalModelError, ValueError, TypeError, IndexError):
                self.vectors = None
                self.mode = "lexical (embedding fallback)"
                self.notice = "Embedding query failed; remaining checks use local lexical retrieval."
                scores = np.asarray(lexical, dtype=np.float32)

        order = np.argsort(-scores, kind="stable")[: min(k, len(self.chunks))]
        return [self.chunks[int(index)] for index in order]
