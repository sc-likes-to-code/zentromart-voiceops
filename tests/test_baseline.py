"""Unit tests for Step 1 prompt-only baseline evaluator.

All tests use mocks to ensure no network calls or API costs.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.evaluate_baseline import (
    BaselineAnswer,
    BaselineAnswerGenerator,
    check_fact_presence,
    check_must_include,
    check_must_not_include,
    generate_comparison_report,
    normalize_text,
    run_baseline_evaluation,
)


def test_normalize_text():
    assert normalize_text("  Hello   World!  ") == "hello world!"
    assert normalize_text("Returns\nPolicy\tV4") == "returns policy v4"


def test_check_fact_presence_exact_and_alternatives():
    # Exact phrase
    assert check_fact_presence("The return window is 7 days.", "7 days")
    # Alternative separation with ' / '
    assert check_fact_presence("You have 15 days for fashion items.", "30 days / 15 days")
    assert check_fact_presence("Replacement is available.", "repair / replacement")
    # Numeric extraction
    assert check_fact_presence("Fee is ₹49.", "49")
    assert check_fact_presence("Charge is 49 rupees.", "₹49")
    # Non-presence
    assert not check_fact_presence("Delivery takes 3 days.", "7 days")


def test_check_must_include():
    answer = "Under ZentroMart Assured, there is a 12-month warranty. Claim through My Orders in the app."
    must_include = "12 ; My Orders / app"
    matched, total, missing = check_must_include(answer, must_include)
    assert matched == 2
    assert total == 2
    assert missing == []

    partial_answer = "You get 12 months warranty."
    matched_p, total_p, missing_p = check_must_include(partial_answer, must_include)
    assert matched_p == 1
    assert total_p == 2
    assert "My Orders / app" in missing_p


def test_check_must_not_include():
    answer = "All items have lifetime free replacement and 0 fee."
    forbidden = "lifetime ; 100 days"
    violations = check_must_not_include(answer, forbidden)
    assert violations == ["lifetime"]

    clean_answer = "Standard policy allows 7-day returns."
    assert check_must_not_include(clean_answer, forbidden) == []


def test_baseline_json_parsing():
    gen = BaselineAnswerGenerator(api_key="fake-key")

    # Clean JSON
    res1 = gen._parse_json_response('{"decision": "answer", "insufficient_evidence": false, "answer": "Yes."}')
    assert res1["decision"] == "answer"
    assert res1["answer"] == "Yes."

    # Markdown wrapped JSON
    res2 = gen._parse_json_response('```json\n{"decision": "refuse", "insufficient_evidence": true, "answer": "No."}\n```')
    assert res2["decision"] == "refuse"
    assert res2["insufficient_evidence"] is True

    # Fallback for plain text
    res3 = gen._parse_json_response("This is just plain text.")
    assert res3["decision"] == "answer"
    assert res3["answer"] == "This is just plain text."


def test_baseline_generator_empty_question():
    gen = BaselineAnswerGenerator(api_key="fake-key")
    ans = gen.generate_baseline_answer("   ")
    assert ans.decision == "clarify"
    assert ans.insufficient_evidence is True


def test_baseline_generator_mocked_success():
    gen = BaselineAnswerGenerator(api_key="fake-key")
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({
        "decision": "answer",
        "insufficient_evidence": False,
        "answer": "Returns are accepted within 7 days.",
    })
    mock_client.models.generate_content.return_value = mock_resp
    gen._client = mock_client

    ans = gen.generate_baseline_answer("What is the return window?")
    assert isinstance(ans, BaselineAnswer)
    assert ans.decision == "answer"
    assert ans.answer == "Returns are accepted within 7 days."
    assert ans.insufficient_evidence is False
    assert ans.error is None


def test_baseline_generator_mocked_api_error():
    gen = BaselineAnswerGenerator(api_key="fake-key")
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("API service down")
    gen._client = mock_client

    ans = gen.generate_baseline_answer("What is the return window?", max_retries=1)
    assert ans.decision == "escalate"
    assert ans.insufficient_evidence is True
    assert "API service down" in ans.error


def test_run_baseline_evaluation_mocked(tmp_path: Path):
    mock_gen = MagicMock()
    mock_gen.generate_baseline_answer.return_value = BaselineAnswer(
        question="test",
        answer="You have 7 days to return clothing.",
        decision="answer",
        insufficient_evidence=False,
    )

    summary, results = run_baseline_evaluation(limit=2, delay_between_calls=0.0, generator=mock_gen)
    assert summary["total_evaluated"] == 2
    assert summary["successful_evaluations"] == 2
    assert summary["execution_errors"] == 0
    assert summary["retrieval_recall_at_k"] is None
    assert len(results) == 2
    assert results[0]["id"] == "PQ0002"
    assert results[0]["retrieved_section_ids"] == []


def test_generate_comparison_report(tmp_path: Path):
    rag_json = tmp_path / "rag.json"
    base_json = tmp_path / "baseline.json"
    out_md = tmp_path / "comparison.md"

    rag_data = {
        "summary": {
            "total_evaluated": 52,
            "successful_evaluations": 52,
            "execution_errors": 0,
            "retrieval_recall_at_k": 0.8269,
            "full_retrieval_accuracy": 0.3462,
            "hard_negative_retrievals": 1,
            "decision_accuracy": 0.6731,
            "unanswerable_questions": 5,
            "unanswerable_abstention_accuracy": 1.0,
            "must_include_fact_precision": 0.5517,
            "prohibited_claim_violations": 0,
        },
        "results": [
            {
                "id": "PQ0002",
                "question": "SKU ELE-0012 pe ZentroMart Assured hai kya?",
                "expected_decision": "answer",
                "generated_decision": "answer",
                "answerable": True,
                "gold_evidence": ["WAR-2"],
                "retrieved_section_ids": ["WAR-2"],
                "must_include": "12",
                "must_include_matched": 1,
                "must_include_total": 1,
                "generated_answer": "Haan 12 mahine ki warranty hai.",
            }
        ]
    }

    base_data = {
        "summary": {
            "total_evaluated": 52,
            "successful_evaluations": 52,
            "execution_errors": 0,
            "retrieval_recall_at_k": None,
            "full_retrieval_accuracy": None,
            "hard_negative_retrievals": None,
            "decision_accuracy": 0.5000,
            "unanswerable_questions": 5,
            "unanswerable_abstention_accuracy": 0.8000,
            "must_include_fact_precision": 0.2500,
            "prohibited_claim_violations": 1,
        },
        "results": [
            {
                "id": "PQ0002",
                "question": "SKU ELE-0012 pe ZentroMart Assured hai kya?",
                "expected_decision": "answer",
                "generated_decision": "answer",
                "answerable": True,
                "gold_evidence": ["WAR-2"],
                "must_include": "12",
                "must_include_matched": 0,
                "must_include_total": 1,
                "generated_answer": "ZentroMart offers general warranties on items.",
            }
        ]
    }

    rag_json.write_text(json.dumps(rag_data), encoding="utf-8")
    base_json.write_text(json.dumps(base_data), encoding="utf-8")

    generate_comparison_report(rag_json, base_json, out_md)
    assert out_md.exists()
    content = out_md.read_text(encoding="utf-8")
    assert "Step 1: Prompt-Only Baseline" in content
    assert "Step 2: Grounded RAG" in content
    assert "+17.3 pp" in content or "17.3" in content
