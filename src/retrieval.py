"""Modular local vector and hybrid retrieval engine for ZentroMart VoiceOps."""
import json
import math
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from fastembed import TextEmbedding

from src.config import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_SCORE_THRESHOLD,
    DEFAULT_TOP_K,
    INDEX_DIR,
)
from src.ingestion import DocumentChunk, KnowledgeBaseIngestion


@dataclass
class RetrievalResult:
    chunk_id: str
    source_file: str
    section_id: str
    title: str
    heading: str
    text: str
    score: float
    is_authoritative: bool = True
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class LocalBM25Index:
    """Lightweight in-memory BM25 index for lexical keyword matching."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_len: List[int] = []
        self.avg_dl: float = 0.0
        self.doc_freqs: Dict[str, int] = {}
        self.inverted_index: List[Dict[str, int]] = []
        self.num_docs: int = 0

    def tokenize(self, text: str) -> List[str]:
        """Simple multilingual / alphanumeric tokenizer preserving SKU hyphens."""
        return [tok.lower() for tok in re.findall(r"[A-Za-z0-9\-]+|[\u0900-\u097F]+", text)]

    def fit(self, corpus: List[str]):
        self.num_docs = len(corpus)
        self.doc_len = []
        self.doc_freqs = {}
        self.inverted_index = []

        total_len = 0
        for text in corpus:
            tokens = self.tokenize(text)
            self.doc_len.append(len(tokens))
            total_len += len(tokens)

            tf: Dict[str, int] = {}
            for tok in tokens:
                tf[tok] = tf.get(tok, 0) + 1
            self.inverted_index.append(tf)

            for tok in set(tokens):
                self.doc_freqs[tok] = self.doc_freqs.get(tok, 0) + 1

        self.avg_dl = (total_len / self.num_docs) if self.num_docs > 0 else 1.0

    def score(self, query: str) -> np.ndarray:
        q_tokens = self.tokenize(query)
        scores = np.zeros(self.num_docs, dtype=np.float32)

        for tok in q_tokens:
            if tok not in self.doc_freqs:
                continue
            df = self.doc_freqs[tok]
            idf = math.log(1.0 + (self.num_docs - df + 0.5) / (df + 0.5))

            for i in range(self.num_docs):
                tf = self.inverted_index[i].get(tok, 0)
                if tf > 0:
                    denom = tf + self.k1 * (1.0 - self.b + self.b * (self.doc_len[i] / self.avg_dl))
                    scores[i] += idf * (tf * (self.k1 + 1.0)) / denom

        # Normalize scores to [0, 1] range if max > 0
        max_s = np.max(scores) if self.num_docs > 0 else 0.0
        if max_s > 0:
            scores = scores / max_s
        return scores


class KnowledgeBaseRetriever:
    """Hybrid semantic vector and BM25 retriever with local persistence."""

    def __init__(
        self,
        index_dir: Optional[Path] = None,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        dense_weight: float = 0.65,
    ):
        self.index_dir = Path(index_dir or INDEX_DIR)
        self.model_name = model_name
        self.dense_weight = dense_weight
        self._embed_model: Optional[TextEmbedding] = None
        self.chunks: List[DocumentChunk] = []
        self.embeddings: Optional[np.ndarray] = None
        self.bm25 = LocalBM25Index()

    @property
    def embed_model(self) -> TextEmbedding:
        if self._embed_model is None:
            self._embed_model = TextEmbedding(model_name=self.model_name)
        return self._embed_model

    def build_index(self, chunks: List[DocumentChunk]) -> int:
        """Generates embeddings, builds BM25 index, and prepares chunks for persistence."""
        if not chunks:
            raise ValueError("Cannot build index from empty chunk list.")

        self.chunks = chunks
        corpus = [c.text for c in self.chunks]

        # 1. Generate dense embeddings via fastembed
        raw_embs = list(self.embed_model.embed(corpus))
        embs = np.array(raw_embs, dtype=np.float32)
        # Normalize to unit length for cosine similarity
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        self.embeddings = embs / np.maximum(norms, 1e-9)

        # 2. Fit BM25 lexical index
        self.bm25.fit(corpus)
        return len(self.chunks)

    def save(self, target_dir: Optional[Path] = None):
        """Persists chunks, embeddings, and configuration to disk."""
        save_path = Path(target_dir or self.index_dir)
        save_path.mkdir(parents=True, exist_ok=True)

        # Save metadata and chunks
        chunks_file = save_path / "chunks.json"
        with open(chunks_file, "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in self.chunks], f, indent=2, ensure_ascii=False)

        # Save embeddings
        if self.embeddings is not None:
            np.save(str(save_path / "embeddings.npy"), self.embeddings)

        # Save configuration
        config_file = save_path / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({
                "model_name": self.model_name,
                "dense_weight": self.dense_weight,
                "chunk_count": len(self.chunks),
            }, f, indent=2)

    def load(self, target_dir: Optional[Path] = None) -> bool:
        """Loads index and embeddings from disk if they exist."""
        load_path = Path(target_dir or self.index_dir)
        chunks_file = load_path / "chunks.json"
        embs_file = load_path / "embeddings.npy"

        if not (chunks_file.exists() and embs_file.exists()):
            return False

        with open(chunks_file, "r", encoding="utf-8") as f:
            raw_chunks = json.load(f)
            self.chunks = [DocumentChunk.from_dict(rc) for rc in raw_chunks]

        self.embeddings = np.load(str(embs_file))
        corpus = [c.text for c in self.chunks]
        self.bm25.fit(corpus)
        return True

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        min_score: float = DEFAULT_SCORE_THRESHOLD,
        filter_non_authoritative: bool = True,
    ) -> List[RetrievalResult]:
        """Retrieves top_k most relevant chunks using hybrid dense + BM25 scoring."""
        if not query.strip() or self.embeddings is None or not self.chunks:
            return []

        # 1. Dense query embedding & cosine similarity
        q_raw = list(self.embed_model.embed([query]))[0]
        q_emb = np.array(q_raw, dtype=np.float32)
        q_norm = np.linalg.norm(q_emb)
        q_emb = q_emb / max(q_norm, 1e-9)

        dense_scores = np.dot(self.embeddings, q_emb)

        # 2. BM25 lexical similarity
        bm25_scores = self.bm25.score(query)

        # 3. Hybrid fusion with exact entity matching bonus (e.g., SKU matches)
        combined_scores = self.dense_weight * dense_scores + (1.0 - self.dense_weight) * bm25_scores

        # Check for specific SKU or Section ID mentions in the query
        sku_matches = re.findall(r"\b[A-Z]{3}-\d{4}\b", query)
        section_matches = re.findall(r"\b[A-Z0-9]+-[A-Z0-9]+(?:\.[0-9]+)?\b", query)

        for i, chunk in enumerate(self.chunks):
            # Authoritative filter: exclude superseded content if requested
            if filter_non_authoritative and not chunk.is_authoritative:
                combined_scores[i] = -1.0
                continue

            # SKU exact match bonus
            for sku in sku_matches:
                if sku in chunk.section_id or sku in chunk.text:
                    combined_scores[i] += 0.35

            # Section ID exact match bonus
            for sec in section_matches:
                if sec == chunk.section_id:
                    combined_scores[i] += 0.30

        # 4. Rank and select top_k
        ranked_indices = np.argsort(combined_scores)[::-1]
        results: List[RetrievalResult] = []

        for idx in ranked_indices:
            score = float(combined_scores[idx])
            if score < min_score:
                continue
            chunk = self.chunks[idx]
            results.append(RetrievalResult(
                chunk_id=chunk.chunk_id,
                source_file=chunk.source_file,
                section_id=chunk.section_id,
                title=chunk.title,
                heading=chunk.heading,
                text=chunk.text,
                score=round(score, 4),
                is_authoritative=chunk.is_authoritative,
                metadata=chunk.metadata,
            ))
            if len(results) >= top_k:
                break

        return results
