# ZentroMart VoiceOps — Phase 4 Voice Integration Report

**Capstone Project:** IIT Guwahati × Gnani.ai TOKENS→TRANSFORMERS VoiceOps 2026  
**Provider:** Gnani.ai exclusively for Speech-to-Text (STT) and Text-to-Speech (TTS)  
**Evaluation Date:** 24 October 2026  
**Status:** Validated & Complete  

---

## 1. Executive Summary

Phase 4 introduces an end-to-end voice interface for the ZentroMart VoiceOps support system. It connects customer voice messages to the multi-turn conversational agent and synthesizes speech responses back to the caller using **Gnani.ai exclusively**.

The voice pipeline operates as follows:
```text
Customer Audio File (.wav / .mp3 / .m4a)
                   │
                   ▼
         Gnani.ai STT (/stt/v3)
                   │
                   ▼ (Transcript)
           VoiceOpsAgent
   ┌───────────────┴───────────────┐
   ▼                               ▼
Identity Verification Gate    Grounded RAG / Tool Execution
   └───────────────┬───────────────┘
                   ▼ (Agent Response)
         Gnani.ai TTS (timbre-v2.5, Kaveri, en-IN)
                   │
                   ▼
          Generated Audio (.wav)
          + Transcripts & Metadata JSON
```

---

## 2. Gnani.ai SDK Verification

* **SDK Version:** `gnani-vachana==0.8.2`
* **Import Module:** `gnani` (`gnani.stt`, `gnani.tts`)
* **Exclusivity Audit:** Zero non-Gnani speech providers (Whisper, Google Speech, ElevenLabs, etc.) are present or imported across the codebase. Verified by static AST analysis in `test_exclusive_gnani_speech_provider`.

### STT Configuration
* **Client:** `gnani.stt.GnaniSTTClient`
* **Endpoint:** `/stt/v3`
* **Method:** `transcribe(audio, language_code="en-IN", format="transcribe")`
* **Supported Audio Containers:** `.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`, `.aac`
* **Supported Sample Rates:** 8 kHz, 16 kHz, 44.1 kHz, 48 kHz
* **Inverse Text Normalization (ITN):** Enabled (`format="transcribe"`) for spoken numbers, order IDs, phone numbers, and pincodes.

### TTS Configuration
* **Client:** `gnani.tts.GnaniTTSClient`
* **Endpoint:** `/api/v1/tts/inference`
* **Method:** `synthesize(text, voice="Kaveri", model="timbre-v2.5", language="en-IN", audio_config=...)`
* **Audio Format:** 16,000 Hz, 16-bit Mono Linear PCM WAV

---

## 3. Multi-Turn Conversation State & Verification Bugfix

### Issue Identified
In manual multi-turn voice tests (`01_order_request.m4a` → `02_order_id.m4a` → `03_verification.m4a`):
* Turn 1: Caller requested order status → Agent prompted for 8-digit order number (`clarify`).
* Turn 2: Caller provided order ID `59591825` → Agent executed `lookup_order(order_id=59591825)` and requested verification via phone suffix or pincode (`clarify`).
* Turn 3: Caller provided pincode `411045` ("the delivery pin code associated with my order is 411045") → The agent incorrectly reset to greeting and prompted for the order ID again.

### Root Cause
In `src/agent.py`, the greeting/unidentified order check (`is_order_specific_unidentified`) was evaluated before the pending verification check and tested `not state.is_verified` instead of `not state.order_id`. Because the transcript contained `"my order"` and `"delivery"`, and verification was still pending, Turn 3 was prematurely intercepted as an unidentified order.

### Resolution
1. **Reordered Control Flow:** Prioritized pending verification (`state.verification_status == "pending"`) before any generic greeting or order inquiry checks.
2. **Corrected Unidentified Check:** Changed condition to `not state.order_id`. If an order ID is already assigned in `ConversationState`, the order is identified.
3. **Digit Extraction Sanitization:** `extract_verification_digits` now strips known order IDs and 8-digit patterns before scanning for 4-digit phone suffixes or 6-digit delivery pincodes, preventing order ID collisions.
4. **Context-Aware Completion:** Upon verification, the agent confirms verification with the customer's first name (`Joseph`), provides the order status (`delivered` on `2026-06-11`), and answers prior inquiries directly.

---

## 4. Test Suite and Benchmark Results

* **Total Test Suite:** 46 passed, 0 failed in 2.05s.
* **Phase 4 Voice Tests (`tests/test_voice.py`):** 17 passed, 0 failed.
  * STT success, empty speech handling, and API failure modes.
  * TTS synthesis success, parameter validation, and graceful failure.
  * Multi-turn state preservation and disk artifact persistence.
  * Regression tests for exact 3-turn voice verification, invalid verification retry/lockout, and session isolation.
  * Security AST audit ensuring exclusive Gnani.ai usage.
* **Practice Conversation Benchmark (`scripts/evaluate_conversations.py`):**
  * 23 conversations (96 turns) evaluated.
  * Decision Accuracy: **100.0%**
  * Tool Call Accuracy: **100.0%**
* **Dataset Validator (`dataset/validate_dataset.py`):** **PASS** (1,000 orders, 1,783 items, 244 logs, 52 questions, 23 conversations).
