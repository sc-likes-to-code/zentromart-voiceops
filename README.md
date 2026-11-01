# ZentroMart VoiceOps — Customer Support AI Agent

[![GitHub Repository](https://img.shields.io/badge/GitHub-sc--likes--to--code%2Fzentromart--voiceops-blue?logo=github)](https://github.com/sc-likes-to-code/zentromart-voiceops)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/tests-64%20passed-brightgreen.svg)]()
[![LLM: Google Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-orange.svg)]()
[![Speech: Gnani.ai](https://img.shields.io/badge/Speech-Gnani.ai%20Exclusive-purple.svg)]()

> **Public GitHub Repository:** [https://github.com/sc-likes-to-code/zentromart-voiceops](https://github.com/sc-likes-to-code/zentromart-voiceops)
> **IIT Guwahati × Gnani.ai TOKENS→TRANSFORMERS VoiceOps 2026 Capstone Project**
> An enterprise-grade, voice-enabled, policy-grounded customer support system for **ZentroMart**, an Indian online retailer.

---

## Architecture & System Overview

```text
               Customer Speech / Audio (.wav, .mp3, .m4a)
                                 │
                                 ▼
                     Gnani.ai STT (/stt/v3)
                                 │
                                 ▼ (Transcript)
                   VoiceOpsAgent (Session State)
             ┌───────────────────┴───────────────────┐
             ▼                                       ▼
    Caller Verification Gate                 Grounded RAG Pipeline
   (Phone last 4 / Pincode)             (Hybrid BM25 + BGE Embeddings)
             │                                       │
             ▼                                       ▼
   Mock Support Tools                       Gemini Answer Generator
   (lookup_order / create_ticket)          (pol_returns_v4 Grounding)
             └───────────────────┬───────────────────┘
                                 ▼ (Agent Response)
                     Gnani.ai TTS (timbre-v2.5)
                     (Voice: Kaveri | Lang: en-IN)
                                 │
                                 ▼
                    Synthesized Output (.wav)
                    + Transcripts & Turn Metadata
```

### Core Capabilities
1. **Grounded Policy Retrieval (RAG):**
   * Hybrid lexical (BM25) and dense semantic (`BAAI/bge-small-en-v1.5` via FastEmbed) retrieval.
   * Grounded generation using Google Gemini (`gemini-3.5-flash-lite`).
   * Explicit citation of source policies, section IDs (`[RET-2]`, `[RET-3]`), and refusal on insufficient evidence.
   * Exclusion of superseded policies (`pol_returns_v3_superseded.md`) and non-authoritative support logs.
2. **Caller Identity Verification & Privacy Guard:**
   * Two-gate verification: requires matching the last 4 digits of the registered phone number or the 6-digit delivery pincode before disclosing private order details.
   * Safe single-retry handling and permanent lockout after repeated verification failures.
   * State boundary guard preventing data leakage to unverified callers.
3. **Multi-Turn Context & Business Logic:**
   * Session-isolated conversation history tracking across successive turns.
   * Automatic escalation triggers for high-value damaged items (> ₹10,000), repeat contacts (≥ 2 in 7 days), and customer requests for human assistance.
   * Integration with offline mock tools (`lookup_order`, `create_ticket`).
4. **Gnani.ai Voice Pipeline (STT & TTS):**
   * Exclusive speech integration using the official `gnani-vachana` SDK.
   * STT transcription with Inverse Text Normalization (ITN) for accurate order IDs and numbers.
   * Neural TTS speech synthesis using `timbre-v2.5` (`Kaveri`, `en-IN`).
   * Turn artifact generation persisting audio, text, transcripts, and JSON metadata.

---

## Directory Structure

```text
zentromart-voiceops/
├── dataset/                         # Local offline capstone dataset (untracked)
│   ├── data/                        # Synthetic CSV records (orders, customers, items, etc.)
│   ├── kb/                          # 21 Markdown knowledge documents & policies
│   ├── practice/                    # Practice evaluation sets (questions.csv, conversations.csv)
│   ├── tools/                       # Mock lookup_order and create_ticket tools
│   └── validate_dataset.py          # Relational and schema validator
├── outputs/
│   ├── evaluation/                  # Evaluation summaries and benchmark results
│   │   ├── phase1_audit.md
│   │   ├── rag_evaluation_summary.md
│   │   ├── rag_evaluation_results.json
│   │   ├── conversation_evaluation_summary.md
│   │   ├── conversation_evaluation_results.json
│   │   └── phase4_voice_summary.md
│   └── sample_outputs/              # Generated audio artifacts and transcript logs
├── run.py                           # Root batch runner for evaluating customer audio folders
├── scripts/
│   ├── build_index.py               # Generates local embeddings & search index
│   ├── evaluate_rag.py              # Evaluates 52 single-turn policy questions
│   ├── evaluate_conversations.py    # Evaluates 23 multi-turn practice conversations
│   └── smoke_test_voice.py          # Opt-in live smoke test for Gnani STT/TTS
├── src/
│   ├── agent.py                     # Multi-turn VoiceOpsAgent & business logic
│   ├── answering.py                 # Gemini grounded answer generator
│   ├── cli.py                       # Unified command-line interface
│   ├── config.py                    # Environment and configuration settings
│   ├── conversation.py              # Session and turn state dataclasses
│   ├── ingestion.py                 # Document parsing, chunking, and metadata extractor
│   ├── retrieval.py                 # Hybrid BM25 & FastEmbed vector index
│   ├── tools_adapter.py             # Safe adapter for dataset mock tools
│   └── voice.py                     # Gnani.ai voice pipeline orchestration
├── tests/
│   ├── test_agent.py                # Agent verification & escalation tests
│   ├── test_answering.py            # Gemini answering & abstention tests
│   ├── test_cli.py                  # CLI query execution tests
│   ├── test_ingestion.py            # Knowledge base chunking & policy filtering tests
│   ├── test_retrieval.py            # Hybrid search retrieval tests
│   └── test_voice.py                # STT, TTS, state preservation, & security tests
├── .env.example                     # Environment template with empty placeholders
├── .gitignore                       # Git ignore rules for virtual environments, secrets, datasets
└── requirements.txt                 # Project dependencies
```

---

## Setup & Installation

### 1. Prerequisites
* Python 3.10 or higher.
* Git.
* PowerShell (Windows) or Bash (macOS/Linux).

### 2. Environment Setup
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Configure API Credentials
Create a `.env` file in the project root based on `.env.example`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GNANI_API_KEY=your_gnani_api_key_here
```

### 4. Build Knowledge Base Index
```powershell
python scripts/build_index.py
```

---

## Batch Audio Evaluation Runner (`run.py`)

As required by the capstone specification for automated testing, the root `run.py` script takes a folder of customer audio files, runs the end-to-end voice pipeline (Gnani STT -> Agent RAG & Tools -> Gnani TTS), and persists speech audio, text transcripts, and turn metadata citing retrieved document chunk IDs:

```powershell
# Execute batch runner on customer audio recordings
python run.py <audio_folder> [--out-dir <directory>]

# Example: Run on policy inquiry sample audio
python run.py outputs/sample_inputs/policy_question --out-dir outputs/sample_outputs/voice/batch_policy

# Example: Run multi-turn order inquiry audio preserving caller verification
python run.py outputs/sample_outputs/voice/manual_test --out-dir outputs/sample_outputs/voice/batch_order
```

### Batch Output Structure
For each turn in the batch, the runner outputs:
* `turn_XX_transcript.txt`: Exact speech-to-text transcript returned by Gnani STT.
* `turn_XX_response.txt`: Grounded agent response text.
* `turn_XX_output.wav`: High-quality 16 kHz WAV speech response synthesized by Gnani TTS (with repaired, fully playable RIFF headers).
* `turn_XX_metadata.json`: Full audit record including decision, tools executed, evidence section IDs (`evidence_sources`), and **exact retrieved document chunk IDs** (`retrieved_chunk_ids` with similarity scores).

---

## Command-Line Interface (CLI) Usage

The unified CLI (`src/cli.py`) also supports one-shot policy inquiries, multi-turn interactive console sessions, and direct voice execution:

### 1. One-Shot Policy Query (Text Mode)
```powershell
python src/cli.py --query "What is the return window for electronics?"
```

### 2. Interactive Multi-Turn Console (Text Mode)
```powershell
python src/cli.py --session-id "support_session_01"
```

### 3. Voice Mode: Single Audio Utterance
```powershell
python src/cli.py --audio "path/to/customer_message.wav" --session-id "voice_call_01"
```

### 4. Live Gnani.ai Voice Smoke Test (Opt-in)
Validates live speech recognition and synthesis against the Gnani.ai API without printing credentials:
```powershell
python scripts/smoke_test_voice.py
```

---

## Verification & Evaluation Scorecard

### Test Suite
Run the full 64-test unit, regression, and batch integration suite:
```powershell
python -m pytest tests/ -v
```
* **Overall Pass Rate:** 64 passed in ~5.3s.
* **Agent Tests (`test_agent.py`):** 11 passed (caller verification, retry limits, lockout, escalation).
* **Baseline Tests (`test_baseline.py`):** 10 passed (zero-shot prompt evaluation, fact matching, regex scoring).
* **RAG & Retrieval Tests (`test_answering.py`, `test_ingestion.py`, `test_retrieval.py`):** 17 passed (grounding, abstention, chunking, BM25).
* **Batch Runner Tests (`test_run_batch.py`):** 3 passed (CLI arguments, directory validation, error handling).
* **Voice Tests (`test_voice.py`):** 22 passed (STT, TTS, WAV header repair, chunk ID propagation, error resilience, AST exclusivity audit).
* **CLI Interface (`test_cli.py`):** 1 passed (parameter handling and formatted output).

### Practice Dataset Validation
```powershell
python dataset/validate_dataset.py
```
* **Status:** PASS (1,000 orders, 1,783 items, 244 logs, 52 questions, 23 conversations validated).

### Multi-Turn Practice Benchmark
```powershell
python scripts/evaluate_conversations.py
```
* **Total Conversations Evaluated:** 23 (96 turns)
* **Decision Accuracy:** 100.0%
* **Tool Call Accuracy:** 100.0%

---

## Security & Compliance
* **Zero Hardcoded Credentials:** All credentials are dynamically resolved via `python-dotenv`. `.env` is ignored by Git and has never been committed.
* **Exclusivity Audit:** Verified by static AST analysis in `test_exclusive_gnani_speech_provider` to guarantee that no third-party speech libraries (Whisper, Google Speech, ElevenLabs, etc.) are imported.
* **Privacy By Design:** Unverified order lookups withhold all private customer and order attributes. Order status and delivery details are only unlocked following proof of identity.
