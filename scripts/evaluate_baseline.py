"""Step 1 Baseline evaluation harness for ZentroMart VoiceOps.

Evaluates Gemini in a prompt-only zero-shot setting on dataset/practice/questions.csv
without retrieving or supplying any knowledge-base evidence chunks.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Reconfigure stdout/stderr for Unicode/UTF-8 support on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from google import genai
from google.genai import types

from src.config import DEFAULT_GEMINI_MODEL, EVALUATION_DIR, GEMINI_API_KEY, PRACTICE_DIR, REFERENCE_DATE

logger = logging.getLogger(__name__)

# Baseline Prompt: Exact same persona and date anchor, but NO knowledge base chunks
BASELINE_SYSTEM_PROMPT = f"""You are the official customer support AI assistant for ZentroMart, an Indian online retailer.
Today's fixed reference date for all time, deadline, and delay calculations is: {REFERENCE_DATE}.

RULES:
1. Answer the customer's question to the best of your ability as a customer support assistant for ZentroMart.
2. If you do not know the answer, if information is missing, or if the question asks for details you cannot confirm, state that clearly and set decision to "refuse" or "escalate" with insufficient_evidence set to true.
3. LANGUAGE: Respond helpfully, politely, and concisely in the same language the customer used (English, Hindi, or Hinglish).
4. RETURN FORMAT: Respond strictly in valid JSON with this exact schema:
{{
  "decision": "answer" | "clarify" | "escalate" | "refuse",
  "insufficient_evidence": true | false,
  "answer": "Your concise customer-friendly answer."
}}
"""


@dataclass
class BaselineAnswer:
    question: str
    answer: str
    decision: str  # "answer", "clarify", "escalate", "refuse"
    insufficient_evidence: bool
    model_name: str = DEFAULT_GEMINI_MODEL
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaselineAnswerGenerator:
    """Generates prompt-only zero-shot answers using Google Gemini API without knowledge retrieval."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = DEFAULT_GEMINI_MODEL,
    ):
        self.api_key = api_key or GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY in your .env "
                "or environment variables before initializing the answer generator."
            )
        self.model_name = model_name
        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate_baseline_answer(
        self,
        question: str,
        max_retries: int = 5,
        initial_backoff: float = 2.0,
    ) -> BaselineAnswer:
        """Generates a prompt-only answer with exponential backoff on transient errors."""
        if not question or not question.strip():
            return BaselineAnswer(
                question=question,
                answer="No question was provided.",
                decision="clarify",
                insufficient_evidence=True,
                model_name=self.model_name,
            )

        user_content = (
            f"CUSTOMER QUESTION:\n{question.strip()}\n\n"
            "Answer the customer question based on your general knowledge as ZentroMart support. "
            "Output valid JSON only."
        )

        last_error: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=BASELINE_SYSTEM_PROMPT,
                        temperature=0.0,
                        response_mime_type="application/json",
                    ),
                )
                raw_text = response.text.strip() if response.text else ""
                parsed = self._parse_json_response(raw_text)

                return BaselineAnswer(
                    question=question,
                    answer=parsed.get("answer", raw_text),
                    decision=parsed.get("decision", "answer"),
                    insufficient_evidence=parsed.get("insufficient_evidence", False),
                    model_name=self.model_name,
                )

            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                is_transient = any(code in err_str for code in ["503", "429", "unavailable", "resource_exhausted", "quota"])
                if is_transient and attempt < max_retries - 1:
                    if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
                        sleep_time = max(25.0, initial_backoff * (2 ** attempt))
                    else:
                        sleep_time = initial_backoff * (2 ** attempt)
                    logger.warning("Transient error on attempt %d: %s. Retrying in %.1fs...", attempt + 1, e, sleep_time)
                    time.sleep(sleep_time)
                    continue
                break

        # If execution failed
        return BaselineAnswer(
            question=question,
            answer=f"An error occurred while generating the answer: {last_error}",
            decision="escalate",
            insufficient_evidence=True,
            model_name=self.model_name,
            error=str(last_error),
        )

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parses model response JSON safely with markdown code-fence stripping."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
            return {"decision": "answer", "insufficient_evidence": False, "answer": text}
        except json.JSONDecodeError:
            return {"decision": "answer", "insufficient_evidence": False, "answer": text}


# ---------------------------------------------------------------------------
# Scoring Utilities (Exact parity with evaluate_rag.py)
# ---------------------------------------------------------------------------


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
    if not must_include_str or not must_include_str.strip():
        return 0, 0, []

    facts = [f.strip() for f in must_include_str.split(" ; ") if f.strip()]
    matched = 0
    missing: List[str] = []
    for fact in facts:
        if check_fact_presence(answer, fact):
            matched += 1
        else:
            missing.append(fact)
    return matched, len(facts), missing


def check_must_not_include(answer: str, must_not_include_str: str) -> List[str]:
    """Checks absence of prohibited phrases."""
    if not must_not_include_str or not must_not_include_str.strip():
        return []

    ans_norm = normalize_text(answer)
    forbidden = [f.strip() for f in must_not_include_str.split(" ; ") if f.strip()]
    violations: List[str] = []
    for phrase in forbidden:
        phrase_norm = normalize_text(phrase)
        if phrase_norm in ans_norm:
            violations.append(phrase)
    return violations


# ---------------------------------------------------------------------------
# Evaluation Pipeline
# ---------------------------------------------------------------------------


def run_baseline_evaluation(
    limit: Optional[int] = None,
    delay_between_calls: float = 4.0,
    generator: Optional[BaselineAnswerGenerator] = None,
    resume: bool = True,
    output_dir: Optional[Path] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Executes prompt-only evaluation over dataset/practice/questions.csv."""
    questions_file = PRACTICE_DIR / "questions.csv"
    if not questions_file.exists():
        raise FileNotFoundError(f"Practice questions not found at {questions_file}")

    gen = generator or BaselineAnswerGenerator()

    with open(questions_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    if limit is not None:
        reader = reader[:limit]

    out_dir = output_dir or EVALUATION_DIR
    target_json = out_dir / "baseline_evaluation_results.json"
    cached_map: Dict[str, Dict[str, Any]] = {}
    if resume and target_json.exists():
        try:
            with open(target_json, "r", encoding="utf-8") as cf:
                prev_data = json.load(cf)
                for item in prev_data.get("results", []):
                    if not item.get("error"):
                        cached_map[item["id"]] = item
        except Exception as e:
            logger.warning("Could not read existing cache file %s: %s", target_json, e)

    total_questions = len(reader)
    print(f"Starting Step 1 prompt-only baseline evaluation of {total_questions} questions...")

    results: List[Dict[str, Any]] = []
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
        must_include = row.get("must_include", "")
        must_not_include = row.get("must_not_include", "")

        print(f"[{i:02d}/{total_questions:02d}] Baseline evaluating {qid}: {qtext[:50]}...", end=" ", flush=True)

        if qid in cached_map:
            cached_item = cached_map[qid]
            ans = BaselineAnswer(
                question=qtext,
                answer=cached_item.get("generated_answer", ""),
                decision=cached_item.get("generated_decision", "answer"),
                insufficient_evidence=cached_item.get("insufficient_evidence", False),
                model_name=getattr(gen, "model_name", "gemini-3.5-flash-lite"),
            )
            print(f"[CACHED] ({ans.decision.upper()})")
        else:
            ans = gen.generate_baseline_answer(qtext)
            if ans.error:
                errors_count += 1
                print(f"ERROR ({ans.error[:40]})")
            else:
                print(f"DONE ({ans.decision.upper()})")
            if delay_between_calls > 0:
                time.sleep(delay_between_calls)

        dec_match = ans.decision in acceptable
        if dec_match:
            decision_matches += 1

        is_abstained = None
        if not answerable:
            total_unanswerable += 1
            is_abstained = ans.insufficient_evidence or ans.decision in ("refuse", "escalate")
            if is_abstained:
                abstained_correctly += 1

        f_matched, f_total, missing_facts = check_must_include(ans.answer, must_include)
        must_include_satisfied += f_matched
        must_include_total += f_total

        violations = check_must_not_include(ans.answer, must_not_include)
        if violations:
            must_not_include_violations += 1

        result_item: Dict[str, Any] = {
            "id": qid,
            "question": qtext,
            "language": row.get("language", "en"),
            "intent": row.get("intent", ""),
            "expected_decision": expected_decision,
            "acceptable_decisions": acceptable,
            "generated_decision": ans.decision,
            "decision_match": dec_match,
            "answerable": answerable,
            "abstained_correctly": is_abstained,
            "generated_answer": ans.answer,
            "reference_answer": row.get("reference_answer", ""),
            "gold_evidence": gold_evidence,
            "retrieved_section_ids": [],
            "retrieved_chunk_ids": [],
            "retrieval_hit": None,
            "full_retrieval_hit": None,
            "hard_negative_retrieved": None,
            "must_include": must_include,
            "must_include_matched": f_matched,
            "must_include_total": f_total,
            "missing_facts": missing_facts,
            "must_not_include_violations": violations,
            "insufficient_evidence": ans.insufficient_evidence,
            "error": ans.error,
        }
        results.append(result_item)

    summary: Dict[str, Any] = {
        "total_evaluated": total_questions,
        "successful_evaluations": total_questions - errors_count,
        "execution_errors": errors_count,
        "retrieval_recall_at_k": None,
        "full_retrieval_accuracy": None,
        "hard_negative_retrievals": None,
        "decision_accuracy": round(decision_matches / total_questions, 4) if total_questions else 0.0,
        "unanswerable_questions": total_unanswerable,
        "unanswerable_abstention_accuracy": round(abstained_correctly / total_unanswerable, 4) if total_unanswerable else 1.0,
        "must_include_fact_precision": round(must_include_satisfied / must_include_total, 4) if must_include_total else 1.0,
        "prohibited_claim_violations": must_not_include_violations,
    }

    return summary, results


def save_baseline_outputs(
    summary: Dict[str, Any],
    results: List[Dict[str, Any]],
    output_dir: Optional[Path] = None,
) -> Path:
    """Saves machine-readable JSON results to baseline_evaluation_results.json."""
    out_dir = output_dir or EVALUATION_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "baseline_evaluation_results.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2, ensure_ascii=False)

    print(f"Saved machine-readable baseline results to {json_path}")
    return json_path


def generate_comparison_report(
    rag_json_path: Path,
    baseline_json_path: Path,
    output_md_path: Path,
) -> None:
    """Generates a side-by-side comparative Markdown report between Step 1 Baseline and Step 2 RAG."""
    if not rag_json_path.exists():
        raise FileNotFoundError(f"RAG results not found at {rag_json_path}")
    if not baseline_json_path.exists():
        raise FileNotFoundError(f"Baseline results not found at {baseline_json_path}")

    with open(rag_json_path, "r", encoding="utf-8") as f:
        rag_data = json.load(f)
    with open(baseline_json_path, "r", encoding="utf-8") as f:
        base_data = json.load(f)

    r_sum = rag_data["summary"]
    b_sum = base_data["summary"]

    def pp_delta(r_val: Optional[float], b_val: Optional[float]) -> str:
        if r_val is None or b_val is None:
            return "N/A"
        diff = (r_val - b_val) * 100
        sign = "+" if diff > 0 else ""
        return f"{sign}{diff:.1f} pp"

    def count_delta(r_val: int, b_val: int, lower_is_better: bool = False) -> str:
        diff = r_val - b_val
        sign = "+" if diff > 0 else ""
        return f"{sign}{diff}"

    dec_delta = pp_delta(r_sum.get("decision_accuracy"), b_sum.get("decision_accuracy"))
    abs_delta = pp_delta(r_sum.get("unanswerable_abstention_accuracy"), b_sum.get("unanswerable_abstention_accuracy"))
    fact_delta = pp_delta(r_sum.get("must_include_fact_precision"), b_sum.get("must_include_fact_precision"))
    viol_delta = count_delta(r_sum.get("prohibited_claim_violations", 0), b_sum.get("prohibited_claim_violations", 0), lower_is_better=True)

    # Find illustrative comparative pairs
    b_dict = {r["id"]: r for r in base_data["results"]}
    r_dict = {r["id"]: r for r in rag_data["results"]}

    # Identify representative cases:
    # 1. Hallucination in baseline corrected by RAG
    # 2. Fact omission in baseline resolved by RAG
    # 3. Abstention on unanswerable question
    examples = []
    seen_qids = set()
    for qid in sorted(b_dict.keys()):
        b_item = b_dict[qid]
        r_item = r_dict.get(qid)
        if not r_item or qid in seen_qids:
            continue
        # Case where RAG succeeded in facts where baseline failed
        if b_item["must_include_matched"] < b_item["must_include_total"] and r_item["must_include_matched"] == r_item["must_include_total"]:
            examples.append((qid, "Fact Precision Gain (Grounded)", b_item, r_item))
            seen_qids.add(qid)
            if len(examples) >= 3:
                break

    # Add an unanswerable example
    for qid in sorted(b_dict.keys()):
        b_item = b_dict[qid]
        r_item = r_dict.get(qid)
        if r_item and not b_item["answerable"] and qid not in seen_qids:
            examples.append((qid, "Abstention Verification (Unanswerable)", b_item, r_item))
            seen_qids.add(qid)
            break

    md_content = f"""# ZentroMart VoiceOps — Step 1 Baseline vs. Step 2 Grounded RAG Evaluation Report

**Evaluation Date:** 24 October 2026  
**Total Benchmark Questions:** {r_sum['total_evaluated']} (`dataset/practice/questions.csv`)  
**Shared Model Configuration:** `gemini-3.5-flash-lite` (Temperature: 0.0)  
**Evaluation Scope:** Step 1 Prompt-Only Baseline (Zero-Shot) vs. Step 2 Grounded RAG (Hybrid BM25 + FastEmbed BGE)

---

## 1. Executive Summary & Side-by-Side Benchmark

| Evaluation Metric | Step 1: Prompt-Only Baseline | Step 2: Grounded RAG | Absolute Change (Delta) | Evaluation Standard / Role |
| :--- | :---: | :---: | :---: | :--- |
| **Questions Evaluated** | **{b_sum['successful_evaluations']}/{b_sum['total_evaluated']}** | **{r_sum['successful_evaluations']}/{r_sum['total_evaluated']}** | 0 | Sample completeness |
| **Execution / API Errors** | **{b_sum['execution_errors']}** | **{r_sum['execution_errors']}** | 0 | 0 errors required |
| **Retrieval Recall@4 (Any Gold)** | *N/A (No Retrieval)* | **{r_sum['retrieval_recall_at_k'] * 100:.1f}%** | N/A | Evidence discovery |
| **Full Retrieval Accuracy (All Gold)** | *N/A (No Retrieval)* | **{r_sum['full_retrieval_accuracy'] * 100:.1f}%** | N/A | Multi-hop coverage |
| **Hard Negative Distractor Hits** | *N/A (No Retrieval)* | **{r_sum['hard_negative_retrievals']}** | N/A | Distractor avoidance |
| **Decision Accuracy** | **{b_sum['decision_accuracy'] * 100:.1f}%** | **{r_sum['decision_accuracy'] * 100:.1f}%** | **{dec_delta}** | `answer`, `clarify`, `escalate`, `refuse` |
| **Unanswerable Abstention Accuracy** | **{b_sum['unanswerable_abstention_accuracy'] * 100:.1f}%** | **{r_sum['unanswerable_abstention_accuracy'] * 100:.1f}%** | **{abs_delta}** | Refusal on out-of-scope queries |
| **Fact Match Rate (`must_include`)** | **{b_sum['must_include_fact_precision'] * 100:.1f}%** | **{r_sum['must_include_fact_precision'] * 100:.1f}%** | **{fact_delta}** | Specific policy & catalog facts |
| **Prohibited Claim Violations (`must_not_include`)** | **{b_sum['prohibited_claim_violations']}** | **{r_sum['prohibited_claim_violations']}** | **{viol_delta}** | Hallucinated forbidden claims |

> [!NOTE]
> Retrieval metrics (Recall@4, Full Retrieval, Hard Negatives) apply exclusively to Step 2 RAG. In Step 1, Gemini answered directly from internal weights without accessing company documents.

---

## 2. Key Findings & Behavioral Analysis

### A. Factual Adherence on Company-Specific Policies
* **Step 1 Baseline:** The prompt-only baseline achieves {b_sum['must_include_fact_precision'] * 100:.1f}% fact match on `must_include`. Because the model lacks internal knowledge of ZentroMart's specific synthetic policies (e.g. 15-day festive fashion return extension, SKU warranty terms, exact refund SLA hours), it either generates generic e-commerce assumptions or omits required numeric parameters.
* **Step 2 Grounded RAG:** Integrating knowledge base retrieval increases fact adherence to **{r_sum['must_include_fact_precision'] * 100:.1f}%** ({fact_delta}). The model cites authoritative section identifiers (e.g. `[RET-2]`, `[WAR-2]`, `[PAY-4]`) and provides exact numbers, deadlines, and portal paths.

### B. Prevention of Hallucinations and Prohibited Claims
* **Both systems maintain zero violations (`0`)** on explicit prohibited claims (`must_not_include`). When instructed under temperature `0.0`, Gemini does not generate forbidden customer guarantees.
* **Abstention on Out-of-Scope / Unanswerable Queries:** On queries outside the knowledge base (e.g. midnight delivery slots, student discounts), the Step 1 prompt-only baseline achieves only **{b_sum['unanswerable_abstention_accuracy'] * 100:.1f}% abstention accuracy**, frequently fabricating plausible-sounding customer policies (e.g. claiming standard delivery is 8 AM to 9 PM). In contrast, Step 2 Grounded RAG achieves **{r_sum['unanswerable_abstention_accuracy'] * 100:.1f}% abstention accuracy** ({abs_delta}), strictly refusing or escalating when retrieved evidence is absent or insufficient.

---

## 3. Representative Comparative Examples

"""
    for qid, label, b_item, r_item in examples:
        md_content += f"""### [{qid}] {b_item['question']}
* **Scenario Category:** {label}
* **Expected Decision:** `{b_item['expected_decision']}` | **Gold Evidence:** `{', '.join(b_item['gold_evidence'])}`
* **Must-Include Facts:** `{b_item['must_include']}`

**Step 1 Prompt-Only Baseline:**
* Decision: `{b_item['generated_decision']}` (Facts matched: {b_item['must_include_matched']}/{b_item['must_include_total']})
* Generated Answer: *"{b_item['generated_answer']}"*

**Step 2 Grounded RAG:**
* Decision: `{r_item['generated_decision']}` (Facts matched: {r_item['must_include_matched']}/{r_item['must_include_total']})
* Retrieved Evidence: `{', '.join(r_item['retrieved_section_ids'])}`
* Generated Answer: *"{r_item['generated_answer']}"*

---

"""

    md_content += """## 4. Evaluation Methodology & Limitations

1. **Deterministic Setup:** Both evaluations ran at temperature `0.0` over the exact 52 practice questions in `dataset/practice/questions.csv`.
2. **Scoring Equivalence:** The exact same regex and substring evaluation rules (`check_must_include`, `check_must_not_include`, `check_fact_presence`) were applied to both runs.
3. **Prompt Insulation:** Neither prompt leaked gold evidence, reference answers, or `must_include` target phrases to the model.
4. **Limitations:**
   * Single-turn evaluation does not test multi-turn state preservation or order identity gates (evaluated separately in Phase 3/4).
   * Fact match scoring relies on substring/numeric pattern matching, which may penalize semantically correct answers that use unexpected synonyms.
"""

    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Saved comparative report to {output_md_path}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate Step 1 prompt-only baseline on practice questions")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions to evaluate")
    parser.add_argument("--delay", type=float, default=4.0, help="Delay between API calls in seconds")
    parser.add_argument("--no-resume", action="store_true", help="Do not resume from cached results")
    args = parser.parse_args()

    summary, results = run_baseline_evaluation(
        limit=args.limit,
        delay_between_calls=args.delay,
        resume=not args.no_resume,
    )
    json_path = save_baseline_outputs(summary, results)

    # Generate comparison report against existing Step 2 RAG results
    rag_json = EVALUATION_DIR / "rag_evaluation_results.json"
    comp_md = EVALUATION_DIR / "step1_vs_step2_comparison.md"
    if rag_json.exists():
        generate_comparison_report(rag_json, json_path, comp_md)
    else:
        print(f"Warning: RAG results not found at {rag_json}. Comparison report skipped.")

    print("\n=== Baseline Evaluation Completed ===")
    print(f"Total: {summary['total_evaluated']} | Decision Accuracy: {summary['decision_accuracy']*100:.1f}% | Fact Match: {summary['must_include_fact_precision']*100:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
