# ZentroMart VoiceOps — Phase 1: Environment and Dataset Audit Report

**Date:** 23 October 2026  
**Capstone Project:** IIT Guwahati × Gnani.ai TOKENS→TRANSFORMERS VoiceOps 2026  
**Evaluation Milestone:** Phase 1 Workspace Initialization & Integrity Verification  

---

## 1. Project Root and Environment Versions

- **Exact Project Root:** `E:\MY PROJECTS\zentromart-voiceops`
- **Operating System:** Windows (Microsoft Windows, PowerShell)
- **Host Python Version:** `Python 3.10.2`
- **Virtual Environment:** `E:\MY PROJECTS\zentromart-voiceops\.venv`
- **Virtual Environment Python Executable:** `E:\MY PROJECTS\zentromart-voiceops\.venv\Scripts\python.exe` (Python 3.10.2)
- **Git Version:** `git version 2.56.0.windows.2`
- **Git Repository Status:** Not a Git repository (`fatal: not a git repository (or any of the parent directories): .git`). As required by safety guidelines, git was not initialized automatically.

---

## 2. Dataset Validation Result and Exit Code

The supplied offline dataset validation script (`dataset\validate_dataset.py`) was executed against the dataset using both the host Python and the newly provisioned virtual environment Python executable.

- **Execution Command:** `& ".\.venv\Scripts\python.exe" dataset/validate_dataset.py`
- **Exit Code:** `0` (Success)
- **Actual Validator Output:**
  ```text
  PASS — all 9 CSVs, 21 KB documents, primary/foreign keys, order math,
         practice evidence, verification gates and company naming validated.
         1,000 orders | 1,783 items | 244 logs | 52 questions | 23 conversations
  ```

---

## 3. Dataset Inventory, File Counts, and Row Counts

The dataset directory structure is clean with no accidental nested extraction (`dataset/dataset/...`).

### Summary Inventory Table

| Component | Path | File Count | Entity / Row Count | Primary Key / Index | Description |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **Knowledge Base** | `dataset\kb\*.md` | 21 | 21 docs | `doc_id`, `[SECTION-ID]` | Policies, agent guides, help docs, FAQs, and marketing pages |
| **Customers** | `dataset\data\customers.csv` | 1 | 300 rows | `customer_id` | Synthetic customer profile data, phone strings, Plus status |
| **Orders** | `dataset\data\orders.csv` | 1 | 1,000 rows | `order_id` | Full order lifecycle, payments, logistics, refund, and return status |
| **Order Items** | `dataset\data\order_items.csv` | 1 | 1,783 rows | `(order_id, line_no)` | Line-item breakdown linking orders to catalog SKUs |
| **Products** | `dataset\data\products.csv` | 1 | 70 rows | `sku` | Product catalog with return categories, warranty, and seller info |
| **Pincodes** | `dataset\data\pincodes.csv` | 1 | 36 rows | `pincode` | Serviceability, COD coverage, and Express delivery flags |
| **Holidays** | `dataset\data\holidays.csv` | 1 | 4 rows | `date` | Calendar holidays excluded from business-day timeline counts |
| **Support Logs** | `dataset\data\support_logs.csv` | 1 | 244 rows | `log_id` | Historical agent transcripts; imperfect human records (not policy) |
| **Practice Questions** | `dataset\practice\questions.csv` | 1 | 52 rows | `id` | Single-turn benchmarks with expected decisions, evidence, and ASR text |
| **Practice Convs** | `dataset\practice\conversations.csv` | 1 | 96 rows | `(conversation_id, turn)` | Multi-turn customer interactions across 23 conversations |
| **Tools Module** | `dataset\tools\tools.py` | 1 | 2 tools | N/A | Mock identity-gated lookup and ticketing functions |
| **Validation Script** | `dataset\validate_dataset.py` | 1 | 1 script | N/A | Comprehensive integrity validator |

---

## 4. Data Relationships and Field Types

### Relational Entity Graph

```text
customers (customer_id PK) ──(1:N)──> orders (order_id PK, customer_id FK)
                                       │
                                       ├──(1:N)──> order_items (order_id, line_no PK)
                                       │                  │
                                       │                  └──(N:1)──> products (sku PK)
                                       │
                                       └──(N:1)──> pincodes.pincode (PK) [via orders.delivery_pincode]

customers.pincode ──(N:1)──> pincodes.pincode (PK)

support_logs.order_id ──(N:1)──> orders.order_id
support_logs.customer_id ──(N:1)──> customers.customer_id

conversations.order_id ──(N:1)──> orders.order_id
conversations.customer_id ──(N:1)──> customers.customer_id

holidays.date: Standalone reference for business day exclusions.
```

### Critical Field Type Rules

1. **Identifiers as Strings (`dtype=str`):**
   - IDs must never be loaded as numeric types: `order_id`, `customer_id`, `sku`, `pincode`, `delivery_pincode`, `return_rrn`, `cancellation_rrn`, `rto_rrn`, `phone`.
   - Preserves leading zeros and prevents loss of precision or scientific notation conversion.
2. **Dates and Timelines:**
   - Dates format: `YYYY-MM-DD`. Timestamps format: `YYYY-MM-DDTHH:MM`.
   - **Reference "Today" Date:** **20 October 2026** is the fixed current date for all deadline, delivery delay, and refund calculation logic.
   - Business days exclude Sundays and the 4 calendar holidays in `holidays.csv` (2026-08-15, 2026-10-02, 2026-10-19, 2026-11-09). Return windows are counted in calendar days.
3. **Delimiters:**
   - Short lists inside table cells use ` ; ` (space, semicolon, space).
   - In evaluation schemas (`must_include`), alternative acceptable answers are separated by ` / `.

---

## 5. Policy Precedence and Superseded-Policy Handling

The document hierarchy defined in `dataset\kb\00_about_this_knowledge_base.md` governs all dispute resolution:

1. **Current Policies (`doc_type: policy`, `status: current`)** — Highest authority.
2. **Agent Guides (`doc_type: agent_guide`)** — Operational instructions for verification and handoffs.
3. **Help Articles (`doc_type: help`)** — Practical customer-facing walkthroughs.
4. **FAQs (`doc_type: faq`)** — General answers.
5. **Marketing Pages (`doc_type: marketing`)** — Broad promotional claims; **never override policies**.

### Superseded Document Handling

- `pol_returns_v3_superseded.md` (`doc_id: POL-RET-v3`, `status: superseded`, `effective_from: 2026-03-01`) is superseded by `pol_returns_v4.md` (`doc_id: POL-RET`, `status: current`, `effective_from: 2026-08-01`).
- **Grandfathering Exception:** Electronics delivered **before 1 August 2026** retain the v3 10-day return window. Electronics delivered **on or after 1 August 2026** are bound by the v4 7-day return window.
- **Support Logs (`support_logs.csv`):** Historical logs reflect human agent dialogue and contain acknowledged errors. They serve only as conversational linguistic examples, never as policy authority.

---

## 6. Mock-Tool Signatures and Caller-Verification Requirements

Implemented in `dataset\tools\tools.py`:

### `lookup_order(order_id: str, verification_value: str = None) -> dict`
- **Initial unverified call:** Calling with `order_id` alone yields:
  ```python
  {'verification_required': True, 'order_id': oid, 'message': 'Ask for the registered phone last 4 digits OR delivery pincode.'}
  ```
  It withholds order status, items, amounts, delivery addresses, and personal customer data.
- **Verification check:** Caller must supply either:
  1. Last 4 digits of the registered phone number, OR
  2. 6-digit delivery pincode for that order.
- **On successful verification:** Unlocks full order record, items, customer first name, and Plus membership flag.
- **On failure or mismatch:** Returns `{'verified': False, 'verification_required': True, 'message': 'Verification failed or order not found.'}`.
- **Operational Rules:**
  - Ask for only **one** verification value at a time.
  - Allow at most **one retry** before refusing disclosure.
  - Never read out or hint at the expected phone digits or pincode.
  - Never disclose full phone numbers, emails, or residential addresses even to verified callers.

### `create_ticket(summary: str, order_id: str = None, reason: str = None, intent: str = None) -> dict`
- **Validation:** Enforces a minimum summary length of 20 characters (`issue`, `checks made`, `escalation reason`). Summaries below 20 characters fail with `{'created': False, 'error': 'summary too short: ...'}`.
- **Output:** On success, generates a `ticket_id` (`TKT...`), logs to `dataset\tools\tickets_created.csv`, and returns `{'created': True, 'ticket_id': tid}`.
- **Operational Rule:** Agents must confirm ticket creation to callers **only if** `created == True`.

---

## 7. Practice Question and Conversation Schemas

### `dataset\practice\questions.csv` (52 single-turn questions)
17 attributes:
- `id`: Stable question ID (e.g., `PQ0002`).
- `language`: Query language (`en`, `hi`, `hi-en`, etc.).
- `question`: Customer message text.
- `asr_text`: Phonetic/ASR output simulation (numbers spelled out, missing punctuation, misheard words) for voice robustness testing in Step 4.
- `intent`: Classified query intent (e.g., `returns`, `warranty`, `cancellation`).
- `expected_decision` & `acceptable_decisions`: `answer`, `clarify`, `escalate`, or `refuse`.
- `answerable`: Boolean flag; `False` indicates information is missing from documents, requiring escalation or polite refusal.
- `gold_evidence`: Ground-truth KB section IDs (`[SECTION-ID]`) and product rows (`products.csv:SKU`).
- `hard_negatives`: Deceptive sections likely to distract naive lexical search.
- `must_include` / `must_not_include`: Key facts required (with ` / ` alternatives) or prohibited claims.
- `reference_answer`, `reply_language`, `entities`, `notes`, `needs_native_review`.

### `dataset\practice\conversations.csv` (96 turns across 23 conversations)
13 attributes:
- `conversation_id`: Conversation identifier (e.g., `PC002`).
- `turn`: Sequential 1-based turn number.
- `scenario`: Evaluation scenario description.
- `language`, `order_id`, `customer_id`, `customer_message`.
- `expected_decision`: `answer`, `clarify`, `escalate`, or `refuse`.
- `must_include`, `must_not_include`.
- `expected_tool_calls`: Expected mock tool execution with parameters (e.g., `lookup_order(order_id=46637226)` then `lookup_order(order_id=46637226, verification_value=4533)`).
- `gold_evidence`, `notes`.

---

## 8. Step 1 Baseline and Step 2 RAG Evaluation Plan

### Step 1: Direct LLM Baseline (Zero-Shot)
- **Goal:** Evaluate direct generation performance using the Gemini API against `questions.csv` without document context.
- **Evaluation Criteria:**
  - Decision accuracy against `expected_decision` / `acceptable_decisions`.
  - Hallucination frequency on policy windows, charges, and conditions.
  - Baseline response quality on Hindi and Hinglish inputs.

### Step 2: Knowledge Base Indexing and Policy-Grounded RAG
- **Goal:** Ingest 21 `dataset\kb\*.md` documents, preserving frontmatter metadata (`doc_id`, `doc_type`, `effective_from`, `status`) and `[SECTION-ID]` tags.
- **Retrieval Pipeline:**
  - Multi-stage retrieval combining semantic embeddings and keyword/BM25 retrieval.
  - Section-level chunking preserving section ID tags for evidence citation.
  - Metadata filtering to prioritize `status: current` over `status: superseded` unless grandfathering dates apply.
- **Evaluation Metrics:**
  - **Retrieval Recall@k / Hit Rate:** Checked against `gold_evidence` section IDs.
  - **Hard Negative Resistance:** Verification that distractor sections in `hard_negatives` are filtered.
  - **Fact Adherence:** Validation that generated answers contain all facts in `must_include` and zero phrases in `must_not_include`.

---

## 9. Missing Prerequisites and Blockers

1. **Gnani.ai API Key:**
   - Status: Not yet configured (`GNANI_API_KEY=` placeholder in `.env.example`).
   - Impact: Does not block Step 1 (Baseline), Step 2 (RAG), or Step 3 (Conversation/Tools). Only required for Step 4 (Streaming STT/TTS).
2. **Gemini API Key:**
   - Status: Available in environment.
3. **Python Virtual Environment:**
   - Status: Successfully provisioned at `E:\MY PROJECTS\zentromart-voiceops\.venv`.
4. **Git Repository:**
   - Status: The workspace is not currently a git repository. Preserved as-is without automatic initialization.

---

## 10. Recommended Next PowerShell Commands (Phase 2 Preparation)

To install dependencies within the isolated virtual environment and verify package installation:

```powershell
# 1. Verify virtual environment Python executable
& ".\.venv\Scripts\python.exe" --version

# 2. Upgrade pip inside the virtual environment
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip

# 3. Install core dependencies from requirements.txt
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

# 4. Copy environment template to .env for local configuration (without exposing secrets)
if (-not (Test-Path .env)) { Copy-Item .env.example .env }

# 5. Run initial test suite once created
& ".\.venv\Scripts\python.exe" -m pytest tests/
```
