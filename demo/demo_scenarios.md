# ZentroMart VoiceOps — Demonstration Scenarios Specification

This document details the two real-world demonstration scenarios engineered for the ZentroMart VoiceOps capstone video submission. Both scenarios run through the complete production pipeline:
**Customer Audio (`.m4a`/`.wav`) → Gnani.ai STT (`prisma-v2.5`) → VoiceOpsAgent RAG & Policy Gating → Gnani.ai Streaming TTS (`timbre-v2.5`, Kaveri) → Synchronous Audio Playback (`winsound`)**.

All transcripts, policy citations, retrieved chunk IDs, and agent responses below have been verified with live execution against the ZentroMart policy database.

---

## Scenario A: Grounded Multi-Turn Conversation with Context Retention

- **Domain**: Customer Service / Apparel Return Policies & Logistics Surcharges
- **Demonstration Goal**: Prove accurate knowledge retrieval, strict policy citation (`RET-2`, `RET-8`, `RET-6`), and conversational memory retention across turns without re-asking for product details.
- **Session Duration**: ~50–55 seconds total (2 turns)

### Turn 1 — Initial Return Window Inquiry

#### 1. Input Specification
- **Audio File**: `demo/audio/scenario_a/01_return_window.m4a`
- **Audio Properties**: 16 kHz Mono, 16-bit PCM (M4A container, 167 KB, ~7.5 seconds speech)
- **Spoken Customer Query**: *"What is the return window for clothing and footwear?"*

#### 2. Gnani.ai STT Processing
- **STT Endpoint**: `/stt/v3` (`prisma-v2.5`, Indian English `en-IN`)
- **STT Transcript**: `"what is the return window for clothing and footwear"`
- **Transcription Latency**: 0.35s

#### 3. Agent Decision & Retrieval Gating
- **Decision**: `ANSWER`
- **Category Identified**: `clothing_and_footwear`
- **Policy Rule Triggered**: `RET-2` (Standard 15-day return window) & `RET-8` (Festive sale extension to 30 days)
- **Evidence Sources**: `RET-2`, `RET-8`
- **Retrieved Knowledge Chunks**:
  1. `pol_returns_v4.md:RET-2:2` — Standard Category Return Windows: Clothing, Footwear & Accessories: 15 calendar days from delivery date.
  2. `pol_returns_v4.md:RET-9:9` — Condition Requirements: Must be unworn, unwashed, with all original tags attached in original packaging.
  3. `pol_returns_v4.md:RET-6:6` — Reverse Logistics & Pickup Fee Policy: ₹49 reverse pickup surcharge per order.
  4. `pol_returns_v4.md:RET-8:8` — Festive Season Extended Window: Orders placed during Big Festive Bash (01–15 Oct 2026) receive 30-day return window.

#### 4. Grounded Agent Response
> *"The standard return window for clothing, footwear and bags is 15 days from the delivery date. However, for orders placed during the festive sale between 01 October and 15 October 2026, the return window is extended to 30 days."*

#### 5. Gnani.ai TTS Output & Playback
- **Output File**: `outputs/sample_outputs/voice/demo_run/demo_scenario_a_*/turn_01_output.wav`
- **Voice Model**: `timbre-v2.5` | Voice: `Kaveri` (Indian English female)
- **Header Structure**: Clean RIFF header repaired with exact PCM data length (16 kHz mono 16-bit PCM).
- **Audio Duration**: ~11.5 seconds

---

### Turn 2 — Contextual Follow-Up on Logistics Fees

#### 1. Input Specification
- **Audio File**: `demo/audio/scenario_a/02_pickup_fee.wav`
- **Audio Properties**: 16 kHz Mono WAV (76.8 KB, ~2.4 seconds speech)
- **Spoken Customer Query**: *"Is there any reverse pickup fee for returning it?"*
- **Contextual Dependency**: The customer uses the pronoun *"it"* without mentioning clothing or footwear again. The agent must retain the conversation history from Turn 1 to provide the category-specific policy.

#### 2. Gnani.ai STT Processing
- **STT Endpoint**: `/stt/v3` (`prisma-v2.5`, Indian English `en-IN`)
- **STT Transcript**: `"is there any reverse pickup fee for returning it"`
- **Transcription Latency**: 0.31s

#### 3. Agent Decision & Retrieval Gating
- **Decision**: `ANSWER`
- **Context Retention**: Conversation state preserves `clothing_and_footwear` category from Turn 1.
- **Policy Rule Triggered**: `RET-6` (Reverse logistics fee structure)
- **Evidence Sources**: `RET-6`
- **Retrieved Knowledge Chunks**:
  1. `pol_returns_v4.md:RET-6:6` — Reverse Logistics & Pickup Fee: Standard returns incur a flat ₹49 reverse pickup fee deducted from refund. Waived for ZentroMart Plus members or damaged/incorrect shipments.
  2. `pol_returns_v4.md:RET-2:2` — Category return windows context.

#### 4. Grounded Agent Response
> *"For standard returns of clothing and footwear, a flat reverse pickup fee of ₹49 per order is deducted from the refund amount. However, this pickup fee is completely waived if you are a ZentroMart Plus member, or if the return is due to a damaged or incorrect item delivered by us."*

#### 5. Gnani.ai TTS Output & Playback
- **Output File**: `outputs/sample_outputs/voice/demo_run/demo_scenario_a_*/turn_02_output.wav`
- **Voice Model**: `timbre-v2.5` | Voice: `Kaveri`
- **Audio Duration**: ~9.2 seconds

---

## Scenario B: Safety Gating & High-Value Damage Escalation

- **Domain**: Customer Service / High-Value Damaged Goods Governance
- **Demonstration Goal**: Demonstrate autonomous policy gating, safety boundaries, and the strict requirement that damage claims for items exceeding ₹10,000 cannot be closed by Tier-1 agents and must escalate to the Priority Resolution team (`DWM-3`).
- **Session Duration**: ~30–35 seconds

### Turn 1 — High-Value Damage Inquiry

#### 1. Input Specification
- **Audio File**: `demo/audio/scenario_b/01_damage_escalation.wav`
- **Audio Properties**: 16 kHz Mono WAV (163.8 KB, ~5.1 seconds speech)
- **Spoken Customer Query**: *"What is the procedure if a delivered electronic product valued above 10,000 rupees arrives damaged?"*

#### 2. Gnani.ai STT Processing
- **STT Endpoint**: `/stt/v3` (`prisma-v2.5`, Indian English `en-IN`)
- **STT Transcript**: `"what is the procedure if a delivered electronic product valued above ₹10,000 arrives damaged"`
- **Transcription Latency**: 0.41s

#### 3. Agent Decision & Retrieval Gating
- **Decision**: `ESCALATE`
- **Threshold Gating**: Item value > ₹10,000 triggers strict escalation rule under `DWM-3`.
- **Evidence Sources**: `DWM-1`, `DWM-2`, `DWM-3`, `RET-6`
- **Retrieved Knowledge Chunks**:
  1. `pol_damaged_wrong_missing.md:DWM-3:3` — High-Value Claims (> ₹10,000): Mandatory escalation to Priority Resolution team. Customer support agents must create an internal ticket and transfer the case. Direct refund/replacement without supervisor sign-off is strictly prohibited.
  2. `pol_damaged_wrong_missing.md:DWM-1:1` — Reporting Window: Damaged items must be reported within 48 hours of delivery timestamp.
  3. `pol_damaged_wrong_missing.md:DWM-2:2` — Mandatory Evidence: Customer must provide clear unboxing photos/video showing outer box label and damaged item.
  4. `pol_returns_v4.md:RET-6:6` — Reverse pickup fee waiver for damaged goods.

#### 4. Grounded Agent Response
> *"If a delivered electronic product valued above ₹10,000 arrives damaged, you must report it within 48 hours of delivery along with photos of the item and packaging. Because the item value is above ₹10,000, claims are handled by our Priority Resolution team; support agents are required to create a ticket and hand it over for specialist inspection. After verification, you will receive a free replacement or a full refund including delivery fees, with no reverse pickup fee applied."*

#### 5. Gnani.ai TTS Output & Playback
- **Output File**: `outputs/sample_outputs/voice/demo_run/demo_scenario_b_*/turn_01_output.wav`
- **Voice Model**: `timbre-v2.5` | Voice: `Kaveri`
- **Audio Duration**: ~16.8 seconds

---

### Alternative Scenario B Extension: Live Tool Execution with Customer Order
*(Available in `VoiceOpsAgent` for multi-turn order-bound escalations)*

If an order number (e.g. `59591825`) is provided directly:
1. **Turn 1 (ID Gating)**: Agent runs `lookup_order(59591825)`, detects unverified session, returns `clarify` prompting for pincode or phone digits.
2. **Turn 2 (Verification)**: Customer provides pincode `411045`. Agent confirms identity (*"Thank you for verifying, Joseph..."*).
3. **Turn 3 (Escalation & Ticket Creation)**: Customer states laptop display is shattered (> ₹10,000). Agent returns `escalate`, executes `create_ticket()` logging ticket ID (e.g. `TKT395ac4438a864f63ba8eb0c9225cf023`), and transfers to the Priority Resolution team.

---

## Scenario Summary & Benchmark Alignment

| Scenario | Primary Policy | Key Threshold / Gating | Retrieval Chunk IDs | Decision | Spoken Voice |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A (Turn 1)** | `pol_returns_v4.md` | Standard 15-day vs. 30-day festive window | `RET-2:2`, `RET-8:8`, `RET-6:6`, `RET-9:9` | `ANSWER` | Kaveri (Gnani) |
| **A (Turn 2)** | `pol_returns_v4.md` | ₹49 pickup fee (waived for Plus/damaged) | `RET-6:6`, `RET-2:2` | `ANSWER` | Kaveri (Gnani) |
| **B (Turn 1)** | `pol_damaged_wrong_missing.md` | > ₹10,000 threshold → Priority Resolution | `DWM-3:3`, `DWM-1:1`, `DWM-2:2`, `RET-6:6` | `ESCALATE` | Kaveri (Gnani) |
