"""Evaluation harness for ZentroMart VoiceOps RAG assistant against practice questions."""
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Reconfigure stdout/stderr for Unicode/UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.answering import GroundedAnswer, GroundedAnswerGenerator
from src.config import EVALUATION_DIR, INDEX_DIR, PRACTICE_DIR
from src.retrieval import KnowledgeBaseRetriever, RetrievalResult


def normalize_text(text: str) -> str:
    """Normalizes text for robust token and phrase matching."""
    return re.sub(r"\s+", " ", text.lower().strip())


def check_fact_presence(answer: str, fact_spec: str) -> bool:
    """Checks if a fact specification (with optional / alternatives) is present in the answer."""
    ans_norm = normalize_text(answer)
    alternatives = [a.strip() for a in fact_spec.split(" / ")]
    for alt in alternatives:
        if not alt:
            continue
        alt_norm = normalize_text(alt)
        if alt_norm in ans_norm:
            return True
        # Match numeric values (e.g., ₹49, 49, 7 days)
        digits = "".join(ch for ch in alt if ch.isdigit())
        if digits and digits in ans_norm:
            return True
    return False


def check_must_include(answer: str, must_include_str: str) -> Tuple[int, int, List[str]]:
    """Checks presence of all required facts separated by ' ; '."""
    if not must_include_str.strip():
        return 0, 0, []

    facts = [f.strip() for f in must_include_str.split(" ; ") if f.strip()]
    matched = 0
    missing = []
    for fact in facts:
        if check_fact_presence(answer, fact):
            matched += 1
        else:
            missing.append(fact)
    return matched, len(facts), missing


def check_must_not_include(answer: str, must_not_include_str: str) -> List[str]:
    """Checks absence of prohibited phrases."""
    if not must_not_include_str.strip():
        return []

    ans_norm = normalize_text(answer)
    forbidden = [f.strip() for f in must_not_include_str.split(" ; ") if f.strip()]
    violations = []
    for phrase in forbidden:
        phrase_norm = normalize_text(phrase)
        if phrase_norm in ans_norm:
            violations.append(phrase)
    return violations


def run_evaluation(
    limit: Optional[int] = None,
    delay_between_calls: float = 0.5,
) -> Tuple[dict, List[dict]]:
    """Executes evaluation over practice/questions.csv."""
    questions_file = PRACTICE_DIR / "questions.csv"
    if not questions_file.exists():
        raise FileNotFoundError(f"Practice questions not found at {questions_file}")

    # Load retriever and answerer
    retriever = KnowledgeBaseRetriever()
    if not retriever.load(INDEX_DIR):
        raise RuntimeError(f"Index not found at {INDEX_DIR}. Run build_index.py first.")

    generator = GroundedAnswerGenerator()

    # Read questions
    with open(questions_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    if limit is not None:
        reader = reader[:limit]

    total_questions = len(reader)
    print(f"Starting evaluation of {total_questions} practice questions...")

    results = []
    retrieval_hits = 0
    full_retrieval_hits = 0
    hard_negative_hits = 0
    decision_matches = 0
    abstained_correctly = 0
    total_unanswerable = 0
    must_include_satisfied = 0
    must_include_total = 0
    must_not_include_violations = 0
    errors_count = 0

    for i, row in enumerate(reader, 1):
        qid = row["id"]
        qtext = row["question"]
        expected_decision = row.get("expected_decision", "answer").strip()
        acceptable = [d.strip() for d in row.get("acceptable_decisions", expected_decision).split(" ; ")]
        answerable = row.get("answerable", "True").strip().lower() == "true"
        gold_evidence = [g.strip() for g in row.get("gold_evidence", "").split(" ; ") if g.strip()]
        hard_negatives = [h.strip() for h in row.get("hard_negatives", "").split(" ; ") if h.strip()]
        must_include = row.get("must_include", "")
        must_not_include = row.get("must_not_include", "")

        print(f"[{i}/{total_questions}] Evaluating {qid}: {qtext[:60]}...", end=" ", flush=True)

        # 1. Retrieve
        chunks = retriever.retrieve(qtext, top_k=4)
        retrieved_section_ids = {c.section_id for c in chunks}
        retrieved_sources = [c.source_file for c in chunks]
        retrieved_chunk_ids = [c.chunk_id for c in chunks]

        # Check retrieval against gold evidence
        hit = any(ge in retrieved_section_ids for ge in gold_evidence) if gold_evidence else True
        full_hit = all(ge in retrieved_section_ids for ge in gold_evidence) if gold_evidence else True
        if hit:
            retrieval_hits += 1
        if full_hit:
            full_retrieval_hits += 1

        # Check hard negatives
        hn_hit = any(hn in retrieved_section_ids for hn in hard_negatives) if hard_negatives else False
        if hn_hit:
            hard_negative_hits += 1

        # 2. Generate Grounded Answer
        ans: GroundedAnswer = generator.generate_answer(qtext, chunks)

        if ans.error:
            errors_count += 1
            print("ERROR")
        else:
            print(f"DONE ({ans.decision.upper()})")

        # 3. Assess Decision Match
        dec_match = ans.decision in acceptable
        if dec_match:
            decision_matches += 1

        # 4. Assess Abstention on Unanswerable
        if not answerable:
            total_unanswerable += 1
            if ans.insufficient_evidence or ans.decision in ("refuse", "escalate"):
                abstained_correctly += 1

        # 5. Assess Facts
        f_matched, f_total, missing_facts = check_must_include(ans.answer, must_include)
        must_include_satisfied += f_matched
        must_include_total += f_total

        violations = check_must_not_include(ans.answer, must_not_include)
        if violations:
            must_not_include_violations += 1

        result_item = {
            "id": qid,
            "question": qtext,
            "language": row.get("language", "en"),
            "intent": row.get("intent", ""),
            "expected_decision": expected_decision,
            "acceptable_decisions": acceptable,
            "generated_decision": ans.decision,
            "decision_match": dec_match,
            "answerable": answerable,
            "abstained_correctly": (ans.insufficient_evidence or ans.decision in ("refuse", "escalate")) if not answerable else None,
            "generated_answer": ans.answer,
            "reference_answer": row.get("reference_answer", ""),
            "gold_evidence": gold_evidence,
            "retrieved_section_ids": list(retrieved_section_ids),
            "retrieved_chunk_ids": retrieved_chunk_ids,
            "retrieval_hit": hit,
            "full_retrieval_hit": full_hit,
            "hard_negative_retrieved": hn_hit,
            "must_include": must_include,
            "must_include_matched": f_matched,
            "must_include_total": f_total,
            "missing_facts": missing_facts,
            "must_not_include_violations": violations,
            "insufficient_evidence": ans.insufficient_evidence,
            "error": ans.error,
        }
        results.append(result_item)

        if delay_between_calls > 0:
            time.sleep(delay_between_calls)

    # Calculate overall metrics
    summary = {
        "total_evaluated": total_questions,
        "successful_evaluations": total_questions - errors_count,
        "execution_errors": errors_count,
        "retrieval_recall_at_k": round(retrieval_hits / total_questions, 4) if total_questions else 0.0,
        "full_retrieval_accuracy": round(full_retrieval_hits / total_questions, 4) if total_questions else 0.0,
        "hard_negative_retrievals": hard_negative_hits,
        "decision_accuracy": round(decision_matches / total_questions, 4) if total_questions else 0.0,
        "unanswerable_questions": total_unanswerable,
        "unanswerable_abstention_accuracy": round(abstained_correctly / total_unanswerable, 4) if total_unanswerable else 1.0,
        "must_include_fact_precision": round(must_include_satisfied / must_include_total, 4) if must_include_total else 1.0,
        "prohibited_claim_violations": must_not_include_violations,
    }

    return summary, results


def save_evaluation_outputs(summary: dict, results: List[dict]):
    """Writes machine-readable JSON and readable Markdown summary."""
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Machine-readable JSON
    json_path = EVALUATION_DIR / "rag_evaluation_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2, ensure_ascii=False)
    print(f"Saved machine-readable results to {json_path}")

    # 2. Markdown report
    md_path = EVALUATION_DIR / "rag_evaluation_summary.md"
    md_content = f"""# ZentroMart VoiceOps — Phase 2 Grounded RAG Evaluation Report

**Evaluation Date:** 23 October 2026  
**Total Questions Evaluated:** {summary['total_evaluated']}  
**LLM Model:** {results[0].get('generated_answer') and 'gemini-3.5-flash-lite'}  
**Embedding Model:** Local FastEmbed (`BAAI/bge-small-en-v1.5`)  

---

## 1. Executive Summary & Benchmark Metrics

| Metric | Result | Target / Standard |
| :--- | :---: | :--- |
| **Questions Successfully Evaluated** | **{summary['successful_evaluations']}/{summary['total_evaluated']}** | 100% evaluated |
| **Execution / API Errors** | **{summary['execution_errors']}** | 0 errors |
| **Retrieval Recall@k (Any Gold Evidence)** | **{summary['retrieval_recall_at_k'] * 100:.1f}%** | Evidence discovery |
| **Full Retrieval Accuracy (All Evidence)** | **{summary['full_retrieval_accuracy'] * 100:.1f}%** | Multi-hop evidence coverage |
| **Hard Negative Avoidance** | **{summary['hard_negative_retrievals']}** distractor hits | Minimal distractor interference |
| **Decision Accuracy** | **{summary['decision_accuracy'] * 100:.1f}%** | `answer`, `clarify`, `escalate`, `refuse` |
| **Abstention Accuracy on Unanswerable** | **{summary['unanswerable_abstention_accuracy'] * 100:.1f}%** | Refuses/escalates when info absent |
| **Fact Match Rate (`must_include`)** | **{summary['must_include_fact_precision'] * 100:.1f}%** | Factual adherence |
| **Prohibited Claim Violations (`must_not_include`)** | **{summary['prohibited_claim_violations']}** | Zero hallucinated forbidden claims |

---

## 2. Sample Evaluations

"""
    # Append 3 representative supported answers and 2 abstention answers
    supported_samples = [r for r in results if r["answerable"] and r["decision_match"]][:3]
    abstain_samples = [r for r in results if not r["answerable"]][:2]

    md_content += "### Supported Questions (Grounded Accuracy)\n\n"
    for s in supported_samples:
        md_content += f"""#### [{s['id']}] {s['question']}
- **Intent / Language:** `{s['intent']}` (`{s['language']}`)
- **Retrieved Sections:** `{', '.join(s['retrieved_section_ids'])}`
- **Gold Evidence:** `{', '.join(s['gold_evidence'])}`
- **Decision:** `{s['generated_decision']}` (Expected: `{s['expected_decision']}`)
- **Answer:** {s['generated_answer']}
- **Reference Answer:** {s['reference_answer']}

"""

    md_content += "### Unanswerable / Out-of-Scope Questions (Abstention Verification)\n\n"
    for s in abstain_samples:
        md_content += f"""#### [{s['id']}] {s['question']}
- **Intent / Language:** `{s['intent']}` (`{s['language']}`)
- **Retrieved Sections:** `{', '.join(s['retrieved_section_ids'])}`
- **Decision:** `{s['generated_decision']}` (Abstained: `{s['abstained_correctly']}`)
- **Answer:** {s['generated_answer']}

"""

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Saved human-readable summary to {md_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate RAG on practice questions")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions to evaluate")
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between API calls in seconds")
    args = parser.parse_args()

    summary, results = run_evaluation(limit=args.limit, delay_between_calls=args.delay)
    save_evaluation_outputs(summary, results)
    print("\n=== Evaluation Completed ===")
    print(f"Total: {summary['total_evaluated']} | Decision Accuracy: {summary['decision_accuracy']*100:.1f}% | Retrieval Recall: {summary['retrieval_recall_at_k']*100:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
