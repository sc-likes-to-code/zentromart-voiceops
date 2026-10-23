"""Evaluation harness for multi-turn conversations against practice/conversations.csv."""
import csv
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Reconfigure stdout/stderr for Unicode/UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import VoiceOpsAgent
from src.config import EVALUATION_DIR, PRACTICE_DIR


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
        # Match numeric values (e.g., ₹49, 49, 27 October, 2026-10-27)
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


def check_tool_match(actual_calls: List[str], expected_call: str) -> bool:
    """Checks if expected tool call matches actual tool calls."""
    expected = expected_call.strip()
    if not expected:
        return True
    for call in actual_calls:
        # Check tool function name
        if expected.startswith("create_ticket") and "create_ticket" in call:
            return True
        if expected.startswith("lookup_order"):
            if "lookup_order" in call:
                # If expected specifies verification_value, check it
                if "verification_value=" in expected:
                    proof_exp = expected.split("verification_value=")[1].split(")")[0]
                    if f"verification_value={proof_exp}" in call:
                        return True
                elif "verification_value" not in call:
                    return True
    return False


def run_conversation_evaluation() -> Tuple[dict, List[dict]]:
    """Runs all 23 practice conversations from practice/conversations.csv."""
    conv_file = PRACTICE_DIR / "conversations.csv"
    if not conv_file.exists():
        raise FileNotFoundError(f"Conversations file not found: {conv_file}")

    with open(conv_file, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Group rows by conversation_id in turn order
    conversations = defaultdict(list)
    for r in rows:
        conversations[r["conversation_id"]].append(r)

    for cid in conversations:
        conversations[cid].sort(key=lambda x: int(x["turn"]))

    agent = VoiceOpsAgent()

    total_turns = len(rows)
    total_convs = len(conversations)
    print(f"Starting evaluation of {total_convs} conversations ({total_turns} turns)...")

    results = []
    decision_matches = 0
    tool_matches = 0
    must_include_satisfied = 0
    must_include_total = 0
    must_not_include_violations = 0

    for cid, turns in sorted(conversations.items()):
        agent.reset_session(cid)
        scenario = turns[0].get("scenario", "")
        print(f"=== Evaluating {cid} ({scenario}) - {len(turns)} turns ===")

        conv_results = []
        for row in turns:
            turn_num = int(row["turn"])
            msg = row["customer_message"]
            exp_dec = row["expected_decision"].strip()
            exp_tools = row.get("expected_tool_calls", "").strip()
            must_inc = row.get("must_include", "")
            must_not = row.get("must_not_include", "")

            # Execute turn through VoiceOpsAgent
            turn_res = agent.handle_message(msg, conversation_id=cid)

            # 1. Decision match
            dec_match = (turn_res.decision == exp_dec)
            if dec_match:
                decision_matches += 1

            # 2. Tool match
            tool_match = check_tool_match(turn_res.tool_calls, exp_tools)
            if tool_match:
                tool_matches += 1

            # 3. Facts match
            f_matched, f_total, missing = check_must_include(turn_res.agent_message, must_inc)
            must_include_satisfied += f_matched
            must_include_total += f_total

            # 4. Violations
            viols = check_must_not_include(turn_res.agent_message, must_not)
            if viols:
                must_not_include_violations += 1

            print(f"  Turn {turn_num}: [{turn_res.decision.upper()}] (exp: {exp_dec}) | Tool: {turn_res.tool_calls} (exp: {exp_tools}) | Decision Match: {dec_match}")

            conv_results.append({
                "turn": turn_num,
                "user_message": msg,
                "agent_message": turn_res.agent_message,
                "generated_decision": turn_res.decision,
                "expected_decision": exp_dec,
                "decision_match": dec_match,
                "actual_tool_calls": turn_res.tool_calls,
                "expected_tool_calls": exp_tools,
                "tool_match": tool_match,
                "must_include": must_inc,
                "must_include_matched": f_matched,
                "must_include_total": f_total,
                "missing_facts": missing,
                "must_not_include_violations": viols,
            })

        results.append({
            "conversation_id": cid,
            "scenario": scenario,
            "turns": conv_results,
        })

    summary = {
        "total_conversations": total_convs,
        "total_turns": total_turns,
        "decision_accuracy": round(decision_matches / total_turns, 4) if total_turns else 0.0,
        "tool_call_accuracy": round(tool_matches / total_turns, 4) if total_turns else 0.0,
        "must_include_fact_precision": round(must_include_satisfied / must_include_total, 4) if must_include_total else 1.0,
        "prohibited_claim_violations": must_not_include_violations,
    }

    return summary, results


def save_conversation_outputs(summary: dict, results: List[dict]):
    """Writes machine-readable JSON and readable Markdown summary."""
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)

    # 1. JSON output
    json_path = EVALUATION_DIR / "conversation_evaluation_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "conversations": results}, f, indent=2, ensure_ascii=False)
    print(f"\nSaved machine-readable conversation results to {json_path}")

    # 2. Markdown report
    md_path = EVALUATION_DIR / "conversation_evaluation_summary.md"
    md_content = f"""# ZentroMart VoiceOps — Phase 3 Multi-Turn Conversation Evaluation Report

**Evaluation Date:** 23 October 2026  
**Total Conversations Evaluated:** {summary['total_conversations']}  
**Total Turns Evaluated:** {summary['total_turns']}  
**Evaluation Reference:** `dataset/practice/conversations.csv`  

---

## 1. Executive Summary & Benchmark Metrics

| Metric | Result | Standard / Target |
| :--- | :---: | :--- |
| **Conversations Processed** | **{summary['total_conversations']} / {summary['total_conversations']}** | 100% evaluated |
| **Turns Processed** | **{summary['total_turns']} / {summary['total_turns']}** | 100% turns evaluated |
| **Decision Accuracy** | **{summary['decision_accuracy'] * 100:.1f}%** | `answer`, `clarify`, `escalate`, `refuse` |
| **Tool Call Accuracy** | **{summary['tool_call_accuracy'] * 100:.1f}%** | Verification & ticket gateway adherence |
| **Fact Match Rate (`must_include`)** | **{summary['must_include_fact_precision'] * 100:.1f}%** | Precision of policy & order facts |
| **Prohibited Claim Violations (`must_not_include`)** | **{summary['prohibited_claim_violations']}** | Zero unauthorized disclosures / promises |

---

## 2. Scenario Highlights

"""
    for conv in results[:5]:
        md_content += f"""### [{conv['conversation_id']}] Scenario: `{conv['scenario']}` ({len(conv['turns'])} turns)\n\n"""
        for t in conv["turns"]:
            md_content += f"""- **Turn {t['turn']}** (Decision: `{t['generated_decision']}`, Expected: `{t['expected_decision']}`)\n"""
            md_content += f"""  - **Customer:** {t['user_message']}\n"""
            md_content += f"""  - **Agent:** {t['agent_message']}\n"""
            if t['actual_tool_calls']:
                md_content += f"""  - **Tool Executed:** `{', '.join(t['actual_tool_calls'])}`\n"""
        md_content += "\n"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Saved human-readable conversation summary to {md_path}")


def main():
    summary, results = run_conversation_evaluation()
    save_conversation_outputs(summary, results)
    print("\n=== Multi-Turn Conversation Evaluation Completed ===")
    print(f"Conversations: {summary['total_conversations']} | Turns: {summary['total_turns']} | Decision Accuracy: {summary['decision_accuracy']*100:.1f}% | Tool Accuracy: {summary['tool_call_accuracy']*100:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
