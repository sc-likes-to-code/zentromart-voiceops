"""Unit tests for semantic and lexical retrieval."""
import pytest
import numpy as np
from pathlib import Path
from src.retrieval import KnowledgeBaseRetriever, LocalBM25Index, RetrievalResult
from src.ingestion import DocumentChunk


@pytest.fixture
def sample_chunks():
    return [
        DocumentChunk(
            chunk_id="pol_returns_v4.md:RET-2:0",
            source_file="pol_returns_v4.md",
            doc_id="POL-RET",
            title="Returns policy",
            doc_type="policy",
            status="current",
            effective_from="2026-08-01",
            section_id="RET-2",
            heading="Return windows by category",
            text="Document: Returns policy\nSection: [RET-2] Return windows by category\nElectronics have a 7-day return window.",
            is_authoritative=True,
        ),
        DocumentChunk(
            chunk_id="pol_returns_v4.md:RET-6:1",
            source_file="pol_returns_v4.md",
            doc_id="POL-RET",
            title="Returns policy",
            doc_type="policy",
            status="current",
            effective_from="2026-08-01",
            section_id="RET-6",
            heading="Reverse pickup and fees",
            text="Document: Returns policy\nSection: [RET-6] Reverse pickup and fees\nReverse pickup fee is 49 rupees for fashion.",
            is_authoritative=True,
        ),
        DocumentChunk(
            chunk_id="products.csv:ELE-0012",
            source_file="products.csv",
            doc_id="products.csv",
            title="Kestrel K7 Smartphone",
            doc_type="catalog",
            status="current",
            effective_from="2026-08-01",
            section_id="products.csv:ELE-0012",
            heading="Product SKU ELE-0012: Kestrel K7 Smartphone",
            text="Product Catalog Entry: ELE-0012\nTitle: Kestrel K7 Smartphone\nBrand Warranty: 12 months",
            is_authoritative=True,
        ),
        DocumentChunk(
            chunk_id="pol_returns_v3_superseded.md:RETv3-2:0",
            source_file="pol_returns_v3_superseded.md",
            doc_id="POL-RET-v3",
            title="Returns policy v3",
            doc_type="policy",
            status="superseded",
            effective_from="2026-03-01",
            section_id="RETv3-2",
            heading="Old return windows",
            text="Document: Returns policy v3\nSection: [RETv3-2] Old return windows\nElectronics return window was 10 days.",
            is_authoritative=False,
        ),
    ]


def test_bm25_index():
    bm25 = LocalBM25Index()
    corpus = [
        "Electronics return window is 7 days.",
        "Reverse pickup fee is 49 rupees for fashion items.",
        "Product warranty for smartphone is 12 months.",
    ]
    bm25.fit(corpus)
    scores = bm25.score("pickup fee for fashion")
    assert np.argmax(scores) == 1
    assert scores[1] > scores[0]


def test_retriever_build_and_query(sample_chunks):
    retriever = KnowledgeBaseRetriever()
    retriever.build_index(sample_chunks)
    assert len(retriever.chunks) == 4
    assert retriever.embeddings is not None
    assert retriever.embeddings.shape == (4, 384)

    # Query for pickup fee
    results = retriever.retrieve("What is the pickup fee?", top_k=2)
    assert len(results) > 0
    assert results[0].section_id == "RET-6"
    assert results[0].source_file == "pol_returns_v4.md"


def test_retriever_filters_superseded_by_default(sample_chunks):
    retriever = KnowledgeBaseRetriever()
    retriever.build_index(sample_chunks)

    # Even if query matches old policy terms, non-authoritative chunk is excluded
    results = retriever.retrieve("Electronics return window was 10 days old policy", top_k=5)
    for res in results:
        assert res.is_authoritative is True
        assert res.section_id != "RETv3-2"


def test_retriever_save_and_load(sample_chunks, tmp_path):
    retriever = KnowledgeBaseRetriever(index_dir=tmp_path)
    retriever.build_index(sample_chunks)
    retriever.save(tmp_path)

    loaded_retriever = KnowledgeBaseRetriever(index_dir=tmp_path)
    assert loaded_retriever.load(tmp_path) is True
    assert len(loaded_retriever.chunks) == 4

    results = loaded_retriever.retrieve("Kestrel smartphone warranty", top_k=1)
    assert len(results) == 1
    assert "ELE-0012" in results[0].section_id


def test_retriever_empty_query():
    retriever = KnowledgeBaseRetriever()
    assert retriever.retrieve("") == []
    assert retriever.retrieve("   ") == []
