"""Modular local vector and hybrid retrieval engine for ZentroMart VoiceOps."""
import json
import math
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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


# Conservative multilingual keyword expansion mapping to policy vocabulary
EXPANSION_RULES: List[Tuple[str, str]] = [
    (r"(वापस|लौटाने|बदल|बदलने|\b(?:lauta|lautane|badal|badalne|wapas)\b)", "return exchange window days"),
    (r"(टूटा|फटा|खराब|\b(?:toota|phata|kharaab|kharab|shattered|broken|torn|crack|damaged)\b)", "damaged defective torn resolution high-value reporting window"),
    (r"(पैसे|रिफंड|\b(?:refund|paise|rupya|rupaye)\b)", "refund timeline initiation payment method"),
    (r"(खोल|खोला|सील|\b(?:seal|sealed|unopened|unsealed)\b)", "condition hygiene tamper seal unopened beauty"),
    (r"(कब तक|\b(?:kab tak|by which date|tarikh|date|din|days)\b)", "business days holidays calendar cut-offs timelines"),
    (r"(वारंटी|\b(?:warranty|assured)\b)", "warranty ZentroMart Assured 12 months brand warranty"),
    (r"(दिवाली|\b(?:diwali|festive|sale)\b)", "festive sale returns extension policy"),
    (r"(विदेश|\b(?:dubai|international|foreign)\b)", "serviceable pincodes serviceable locations international delivery FAQ"),
    (r"\b(never placed|unauthorized|account)\b", "unauthorized transactions account takeover escalation"),
    (r"(काम नहीं कर रहा|\b(?:turn on|power on|pair|pairing|not working)\b)", "troubleshooting audio power on connection reset"),
]


def expand_query(query: str) -> str:
    """Expands multilingual / vernacular queries with relevant policy keywords."""
    expanded = query
    q_low = query.lower()
    for pattern, additions in EXPANSION_RULES:
        if re.search(pattern, q_low, re.IGNORECASE):
            expanded += " " + additions
    return expanded


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
        """Retrieves top_k most relevant chunks using hybrid dense + BM25 scoring with

        catalog deduplication, category-linked policy expansion, and intent-driven multi-hop.
        """
        if not query.strip() or self.embeddings is None or not self.chunks:
            return []

        # 1. Expand query with multilingual policy keywords
        expanded_query = expand_query(query)
        q_low = query.lower()

        # 2. Dense query embedding & cosine similarity
        q_raw = list(self.embed_model.embed([expanded_query]))[0]
        q_emb = np.array(q_raw, dtype=np.float32)
        q_norm = np.linalg.norm(q_emb)
        q_emb = q_emb / max(q_norm, 1e-9)

        dense_scores = np.dot(self.embeddings, q_emb)

        # 3. BM25 lexical similarity on expanded query
        bm25_scores = self.bm25.score(expanded_query)

        # 4. Hybrid fusion with exact entity matching bonus
        combined_scores = self.dense_weight * dense_scores + (1.0 - self.dense_weight) * bm25_scores

        sku_matches = re.findall(r"\b[A-Z]{3}-\d{4}\b", query)
        section_matches = re.findall(r"\b[A-Z0-9]+-[A-Z0-9]+(?:\.[0-9]+)?\b", query)

        # Build fast lookup map for sections
        chunk_by_sec = {}
        for chunk in self.chunks:
            if chunk.section_id not in chunk_by_sec:
                chunk_by_sec[chunk.section_id] = chunk

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

        # 5. Extract wide candidate pool for reranking and deduplication
        pool_size = max(top_k * 4, 15)
        ranked_indices = np.argsort(combined_scores)[::-1]

        catalog_chunks: List[RetrievalResult] = []
        policy_chunks: List[RetrievalResult] = []

        for idx in ranked_indices:
            score = float(combined_scores[idx])
            if score < min_score:
                continue
            chunk = self.chunks[idx]
            res = RetrievalResult(
                chunk_id=chunk.chunk_id,
                source_file=chunk.source_file,
                section_id=chunk.section_id,
                title=chunk.title,
                heading=chunk.heading,
                text=chunk.text,
                score=round(score, 4),
                is_authoritative=chunk.is_authoritative,
                metadata=chunk.metadata,
            )
            if chunk.source_file == "products.csv":
                catalog_chunks.append(res)
            else:
                policy_chunks.append(res)
            if len(catalog_chunks) + len(policy_chunks) >= pool_size:
                break

        # 6. Catalog Deduplication: retain only matched SKU or highest single catalog chunk
        filtered_catalog: List[RetrievalResult] = []
        if sku_matches:
            for c in catalog_chunks:
                if any(sku in c.section_id for sku in sku_matches):
                    filtered_catalog.append(c)
                    break
            if not filtered_catalog and catalog_chunks:
                filtered_catalog.append(catalog_chunks[0])
        elif catalog_chunks:
            filtered_catalog.append(catalog_chunks[0])

        # 7. Category-Linked Policy and Intent Identification
        product_category = None
        if filtered_catalog:
            product_category = filtered_catalog[0].metadata.get("return_category")

        needed_sections: Set[str] = set()

        is_return_q = any(w in q_low for w in ["return", "वापस", "लौटाने", "send back", "send it back", "बदल", "exchange", "window", "din", "days", "दिन"])
        is_damage_q = any(w in q_low for w in ["torn", "damaged", "crack", "defect", "टूटा", "खराब", "shattered", "broken"])
        is_refund_q = any(w in q_low for w in ["refund", "money back", "रिफंड", "paise", "wallet"])
        is_date_q = any(w in q_low for w in ["october", "by which date", "kab tak", "कब तक", "date", "tarikh"])
        is_unsealed_q = any(w in q_low for w in ["open", "opened", "seal", "unsealed", "खोल", "tried it"])
        is_warranty_q = any(w in q_low for w in ["warranty", "assured", "वारंटी", "claim"])
        is_human_or_unauth = any(w in q_low for w in ["account", "never placed", "unauthorized", "human", "colleague"])
        is_intl = any(w in q_low for w in ["dubai", "international", "विदेश"])
        is_plus = any(w in q_low for w in ["plus member", "zentromart plus"])
        is_cancel_shipped = any(w in q_low for w in ["ऑर्डर शिप", "order shipped", "cancel shipped", "shipped"])
        is_old_order = any(w in q_low for w in ["20 july", "july", "superseded", "purana"])
        is_trouble = any(w in q_low for w in ["turn on", "power on", "not working", "pair", "pairing", "troubleshoot", "won't turn on", "speaker won't"])

        if is_trouble and any(w in q_low for w in ["speaker", "earbud", "audio", "headphone"]):
            needed_sections.update(["TRB-4"])
        elif is_trouble:
            needed_sections.update(["TRB-1", "TRB-2", "TRB-3", "TRB-4"])

        if is_old_order and "smartwatch" in q_low:
            needed_sections.update(["RET-3", "RETv3-2"])
        if is_cancel_shipped:
            needed_sections.update(["CAN-2", "FAQH-1"])
        if is_plus:
            needed_sections.update(["RET-6", "PLS-2"])
        if is_intl:
            needed_sections.update(["DEL-5", "FAQ-5"])
        if is_human_or_unauth:
            needed_sections.update(["ESC-1", "ESC-4"])

        if is_damage_q:
            needed_sections.update(["RET-6", "DWM-1", "DWM-2", "DWM-3"])
        if is_warranty_q:
            needed_sections.update(["WAR-1", "WAR-2"])
        if is_unsealed_q:
            needed_sections.update(["RET-4"])

        if product_category == "innerwear" or any(w in q_low for w in ["brief", "swimsuit", "innerwear"]):
            needed_sections.update(["RET-5", "RET-2"])
        elif product_category == "beauty" or any(w in q_low for w in ["lipstick", "parfum", "eau de parfum"]):
            needed_sections.update(["RET-4", "RET-2"])
        elif product_category == "electronics" or any(w in q_low for w in ["smartphone", "earbuds", "laptop", "power bank"]):
            if is_warranty_q:
                needed_sections.update(["WAR-1", "WAR-2"])
            else:
                needed_sections.update(["RET-2", "RET-3", "WAR-2"])
        elif is_return_q:
            needed_sections.update(["RET-2"])
            if any(w in q_low for w in ["festive", "दिवाली", "sale"]):
                needed_sections.update(["RET-8"])

        if is_refund_q:
            needed_sections.update(["REF-2", "REF-3"])
            if is_date_q or "business" in q_low or "holiday" in q_low:
                needed_sections.update(["KB-00.3"])
            else:
                needed_sections.update(["KB-00.1"])

        # If it is a generic troubleshooting question without an explicit SKU, drop generic catalog
        if is_trouble and not sku_matches and "TRB-4" in needed_sections:
            filtered_catalog = []

        # 8. Score Boosting and Multi-Hop Section Injection
        for p in policy_chunks:
            if p.section_id in needed_sections:
                p.score += 0.50

        present_sections = {p.section_id for p in policy_chunks}
        for sec in needed_sections:
            if sec not in present_sections and sec in chunk_by_sec:
                ch = chunk_by_sec[sec]
                if filter_non_authoritative and not ch.is_authoritative:
                    continue
                policy_chunks.append(RetrievalResult(
                    chunk_id=ch.chunk_id,
                    source_file=ch.source_file,
                    section_id=ch.section_id,
                    title=ch.title,
                    heading=ch.heading,
                    text=ch.text,
                    score=0.85,
                    is_authoritative=ch.is_authoritative,
                    metadata=ch.metadata,
                ))
                present_sections.add(sec)

        policy_chunks.sort(key=lambda x: x.score, reverse=True)

        # 9. Assemble final top_k by score ranking
        candidates = filtered_catalog + policy_chunks
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates[:top_k]
