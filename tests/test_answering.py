"""Unit tests for GroundedAnswerGenerator with mocked Gemini API."""
import json
import pytest
from unittest.mock import MagicMock, patch
from src.answering import GroundedAnswerGenerator, GroundedAnswer, SYSTEM_PROMPT
from src.retrieval import RetrievalResult


@pytest.fixture
def sample_result():
    return RetrievalResult(
        chunk_id="pol_returns_v4.md:RET-2:0",
        source_file="pol_returns_v4.md",
        section_id="RET-2",
        title="Returns policy",
        heading="Return windows by category",
        text="Electronics have a 7-day return window from delivery date.",
        score=0.92,
        is_authoritative=True,
    )


def test_missing_api_key_raises_error():
    with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=True):
        with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
            GroundedAnswerGenerator(api_key="")



def test_empty_question_handling():
    gen = GroundedAnswerGenerator(api_key="test-mock-key")
    ans = gen.generate_answer("", [])
    assert ans.decision == "clarify"
    assert ans.insufficient_evidence is True


def test_no_evidence_abstention():
    gen = GroundedAnswerGenerator(api_key="test-mock-key")
    ans = gen.generate_answer("How to fly to the moon?", [])
    assert ans.decision == "escalate"
    assert ans.insufficient_evidence is True
    assert "could not find relevant policy information" in ans.answer


def test_mocked_gemini_grounded_answer(sample_result):
    gen = GroundedAnswerGenerator(api_key="test-mock-key")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "decision": "answer",
        "insufficient_evidence": False,
        "evidence_sources": ["RET-2"],
        "answer": "The return window for electronics is 7 days from delivery."
    })
    mock_client.models.generate_content.return_value = mock_response
    gen._client = mock_client

    ans = gen.generate_answer(
        "What is the return window for electronics?",
        [sample_result]
    )

    assert ans.decision == "answer"
    assert ans.is_grounded is True
    assert ans.insufficient_evidence is False
    assert "7 days" in ans.answer
    assert ans.evidence_sources == ["RET-2"]


def test_mocked_gemini_unanswerable_abstention(sample_result):
    gen = GroundedAnswerGenerator(api_key="test-mock-key")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "decision": "refuse",
        "insufficient_evidence": True,
        "evidence_sources": [],
        "answer": "This information is not covered by ZentroMart policies."
    })
    mock_client.models.generate_content.return_value = mock_response
    gen._client = mock_client

    ans = gen.generate_answer("Can I buy cryptocurrency on ZentroMart?", [sample_result])

    assert ans.decision == "refuse"
    assert ans.insufficient_evidence is True
    assert ans.is_grounded is False


def test_evidence_prompt_formatting(sample_result):
    gen = GroundedAnswerGenerator(api_key="test-mock-key")
    prompt = gen.format_evidence_prompt([sample_result])
    assert "--- EVIDENCE CHUNK 1 ---" in prompt
    assert "Source File: pol_returns_v4.md" in prompt
    assert "Section ID: RET-2" in prompt
    assert "Electronics have a 7-day return window" in prompt


def test_json_parse_fallback():
    gen = GroundedAnswerGenerator(api_key="test-mock-key")
    parsed = gen._parse_json_response("```json\n{\"decision\": \"answer\", \"answer\": \"Yes\"}\n```")
    assert parsed["decision"] == "answer"
    assert parsed["answer"] == "Yes"

    # Non-json plain text fallback
    plain = gen._parse_json_response("Just a plain text response without json.")
    assert plain["decision"] == "answer"
    assert plain["answer"] == "Just a plain text response without json."
