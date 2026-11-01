# ZentroMart VoiceOps — Demonstration Narration Script

**Total Target Duration**: ~105 – 110 seconds (Strict ceiling: 120 seconds)
**Format**: 1920×1080 High-Definition Screen Recording with Live Spoken Telephony Audio
**Speaker**: Project Presenter / Engineer
**Synthetic Voice**: Gnani.ai `timbre-v2.5` (`Kaveri`, Indian English)

---

## Second-by-Second Production Cue Sheet

| Timestamp | Visual / Screen Action | Spoken Presenter Narration (Voiceover) | Spoken Agent Audio (Kaveri / Gnani.ai) |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:12**<br>*(12s)* | • Show clean terminal screen with ZentroMart VoiceOps banner.<br>• Terminal displays architecture overview: Gnani STT → RAG & Safety Guardrails → Gnani TTS. | *"Welcome to the live demonstration of ZentroMart VoiceOps, built for the IIT Guwahati and Gnani.ai VoiceOps Capstone 2026. VoiceOps provides an autonomous, real-time telephony agent with strict policy grounding, multi-turn memory, and safety escalation."* | *(Silence / Terminal Init)* |
| **0:12 – 0:25**<br>*(13s)* | • Presenter executes command:<br>`python demo/run_live_demo.py`<br>• Terminal shows: `SCENARIO A: GROUNDED MULTI-TURN CONVERSATION`<br>• STT processes `01_return_window.m4a`<br>• Transcript printed: *"what is the return window for clothing and footwear"* | *"In Scenario A, a customer asks about return windows for apparel. Gnani.ai STT transcribes the speech stream with sub-400ms latency. The retriever fetches exact clauses from our indexed policy corpus."* | *(Deepak STT audio plays or transcribes in real time)* |
| **0:25 – 0:38**<br>*(13s)* | • Terminal highlights:<br>`Decision: ANSWER`<br>`Sources: RET-2, RET-8`<br>`Chunks: pol_returns_v4.md:RET-2:2`<br>• Synthetic voice playback begins through system audio. | *(Presenter stays silent while Kaveri speaks)* | **Kaveri (Agent)**:<br>*"The standard return window for clothing, footwear and bags is 15 days from the delivery date. However, for orders placed during the festive sale between 01 October and 15 October 2026, the return window is extended to 30 days."* |
| **0:38 – 0:48**<br>*(10s)* | • Terminal transitions to `TURN 2/2`<br>• STT processes `02_pickup_fee.wav`<br>• Transcript printed: *"is there any reverse pickup fee for returning it"* | *"Next, the customer asks a natural follow-up using the pronoun 'it'. Notice how the agent preserves conversational context without asking the customer to repeat their product category."* | *(Turn 2 STT processes)* |
| **0:48 – 0:59**<br>*(11s)* | • Terminal displays:<br>`Decision: ANSWER`<br>`Sources: RET-6`<br>`Chunks: pol_returns_v4.md:RET-6:6`<br>• Kaveri voice playback executes. | *(Presenter stays silent while Kaveri speaks)* | **Kaveri (Agent)**:<br>*"For standard returns of clothing and footwear, a flat reverse pickup fee of ₹49 per order is deducted from the refund amount. However, this pickup fee is completely waived if you are a ZentroMart Plus member, or if the return is due to a damaged item."* |
| **0:59 – 1:12**<br>*(13s)* | • Terminal transitions to `SCENARIO B: SAFETY GATING & HIGH-VALUE ESCALATION`<br>• STT processes `01_damage_escalation.wav`<br>• Transcript: *"what is the procedure if a delivered electronic product valued above ₹10,000 arrives damaged"* | *"Scenario B demonstrates policy gating and high-value risk control. Here, a customer inquires about a damaged electronic product valued above ₹10,000."* | *(Turn 1 STT processes)* |
| **1:12 – 1:30**<br>*(18s)* | • Terminal displays:<br>`Decision: ESCALATE`<br>`Sources: DWM-1, DWM-2, DWM-3, RET-6`<br>`Chunks: pol_damaged_wrong_missing.md:DWM-3:3`<br>• Kaveri voice speaks policy instructions. | *(Presenter stays silent while Kaveri speaks)* | **Kaveri (Agent)**:<br>*"If a delivered electronic product valued above ₹10,000 arrives damaged, you must report it within 48 hours of delivery along with photos. Because the item value is above ₹10,000, claims are handled by our Priority Resolution team; support agents are required to create a ticket and hand it over for specialist inspection."* |
| **1:30 – 1:48**<br>*(18s)* | • Terminal displays:<br>`DEMONSTRATION RUN COMPLETED`<br>• Display evaluation summary table on screen (or quick cat of benchmark metrics). | *"Our safety guardrails successfully trigger the ESCALATE gate under rule DWM-3, barring direct closure and creating a priority support ticket. Across our 52-question benchmark, ZentroMart VoiceOps achieved 100% decision accuracy, zero prohibited claims, and passed all 67 test suites."* | *(Silence / Terminal Highlights)* |
| **1:48 – 1:55**<br>*(7s)* | • Display sign-off slide / repository info. | *"Thank you. ZentroMart VoiceOps is fully production-ready for automated, compliant e-commerce voice operations."* | *(Silence)* |

---

## Narration Rehearsal Tips

1. **Let the Synthetic Voice Breathe**: Do NOT speak over Kaveri's TTS playback. The OBS audio capture will clearly record both your voice (on your microphone) and Kaveri's voice (on desktop audio output). Pausing while Kaveri speaks highlights the speech synthesis clarity.
2. **Terminal Sizing**: Keep your terminal window maximized or sized to 1920×1080 with 18pt Cascadia Code or Consolas font.
3. **Pacing**: Speak at a steady, professional pace (~130 words per minute). The presenter script above contains approximately 135 words, taking ~60 seconds of presenter speaking time interspersed with ~45 seconds of synthetic audio and STT processing, totaling ~105 seconds.
