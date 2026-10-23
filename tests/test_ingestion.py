"""Unit tests for knowledge base ingestion and chunking."""
import pytest
from pathlib import Path
from src.ingestion import KnowledgeBaseIngestion, DocumentChunk
from src.config import KB_DIR, DATA_DIR, SUPERSEDED_RETURNS_POLICY


def test_parse_frontmatter():
    ing = KnowledgeBaseIngestion()
    content = """---
doc_id: TEST-01
title: Test Document
status: current
effective_from: 2026-08-01
---
# Main Title
## [TEST-SEC1] Section One
This is section one text.
"""
    meta, body = ing.parse_frontmatter(content)
    assert meta["doc_id"] == "TEST-01"
    assert meta["title"] == "Test Document"
    assert meta["status"] == "current"
    assert meta["effective_from"] == "2026-08-01"
    assert "## [TEST-SEC1]" in body


def test_superseded_policy_exclusion():
    ing = KnowledgeBaseIngestion()
    # Ingest with exclusion enabled (default)
    auth_chunks = ing.ingest_kb_documents(exclude_superseded=True)
    for chunk in auth_chunks:
        assert chunk.source_file != SUPERSEDED_RETURNS_POLICY
        assert chunk.status != "superseded"
        assert chunk.is_authoritative is True

    # Ingest with exclusion disabled
    all_chunks = ing.ingest_kb_documents(exclude_superseded=False)
    superseded = [c for c in all_chunks if c.source_file == SUPERSEDED_RETURNS_POLICY]
    assert len(superseded) > 0
    for sc in superseded:
        assert sc.is_authoritative is False


def test_current_returns_policy_v4_included():
    ing = KnowledgeBaseIngestion()
    chunks = ing.ingest_kb_documents(exclude_superseded=True)
    v4_chunks = [c for c in chunks if c.source_file == "pol_returns_v4.md"]
    assert len(v4_chunks) >= 8
    section_ids = {c.section_id for c in v4_chunks}
    assert "RET-2" in section_ids
    assert "RET-3" in section_ids
    assert "RET-6" in section_ids


def test_metadata_preservation():
    ing = KnowledgeBaseIngestion()
    chunks = ing.ingest_all(exclude_superseded=True)
    assert len(chunks) > 100
    for chunk in chunks:
        assert chunk.chunk_id
        assert chunk.source_file
        assert chunk.section_id
        assert chunk.heading
        assert chunk.text
        assert chunk.status == "current"
        assert chunk.is_authoritative is True


def test_malformed_and_empty_document_handling(tmp_path):
    empty_file = tmp_path / "empty.md"
    empty_file.write_text("", encoding="utf-8")

    malformed_file = tmp_path / "malformed.md"
    malformed_file.write_text("No frontmatter header at all here.\nJust random text.", encoding="utf-8")

    ing = KnowledgeBaseIngestion(kb_dir=tmp_path, data_dir=tmp_path)
    chunks = ing.ingest_kb_documents()
    assert len(chunks) == 1  # malformed file ingested as intro chunk
    assert chunks[0].source_file == "malformed.md"
    assert any("Empty document skipped" in err for err in ing.ingestion_errors)
