"""Unit tests for CLI interface."""
import pytest
from unittest.mock import MagicMock, patch
from src.cli import run_single_query
from src.answering import GroundedAnswer
from src.retrieval import RetrievalResult


def test_cli_run_single_query():
    mock_retriever = MagicMock()
    mock_generator = MagicMock()

    mock_chunk = RetrievalResult(
        chunk_id="test.md:T1:0",
        source_file="test.md",
        section_id="T1",
        title="Test",
        heading="Heading",
        text="Sample text",
        score=0.9,
    )
    mock_retriever.retrieve.return_value = [mock_chunk]

    mock_answer = GroundedAnswer(
        question="What is the return fee?",
        answer="The return fee is 49 rupees.",
        decision="answer",
        is_grounded=True,
        insufficient_evidence=False,
        evidence_sources=["T1"],
        retrieved_chunks=[mock_chunk],
    )
    mock_generator.generate_answer.return_value = mock_answer

    result = run_single_query(
        "What is the return fee?",
        mock_retriever,
        mock_generator,
        top_k=2
    )

    mock_retriever.retrieve.assert_called_once_with("What is the return fee?", top_k=2)
    mock_generator.generate_answer.assert_called_once_with("What is the return fee?", [mock_chunk])
    assert result.decision == "answer"
    assert "49 rupees" in result.answer
