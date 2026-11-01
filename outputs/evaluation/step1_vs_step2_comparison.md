# ZentroMart VoiceOps — Step 1 Baseline vs. Step 2 Grounded RAG Evaluation Report

**Evaluation Date:** 24 October 2026
**Total Benchmark Questions:** 52 (`dataset/practice/questions.csv`)
**Shared Model Configuration:** `gemini-3.5-flash-lite` (Temperature: 0.0)
**Evaluation Scope:** Step 1 Prompt-Only Baseline (Zero-Shot) vs. Step 2 Grounded RAG (Hybrid BM25 + FastEmbed BGE)

---

## 1. Executive Summary & Side-by-Side Benchmark

| Evaluation Metric | Step 1: Prompt-Only Baseline | Step 2: Grounded RAG | Absolute Change (Delta) | Evaluation Standard / Role |
| :--- | :---: | :---: | :---: | :--- |
| **Questions Evaluated** | **52/52** | **52/52** | 0 | Sample completeness |
| **Execution / API Errors** | **0** | **0** | 0 | 0 errors required |
| **Retrieval Recall@4 (Any Gold)** | *N/A (No Retrieval)* | **100.0%** | N/A | Evidence discovery |
| **Full Retrieval Accuracy (All Gold)** | *N/A (No Retrieval)* | **84.6%** | N/A | Multi-hop coverage |
| **Hard Negative Distractor Hits** | *N/A (No Retrieval)* | **1** | N/A | Distractor avoidance |
| **Decision Accuracy** | **86.5%** | **100.0%** | **+13.5 pp** | `answer`, `clarify`, `escalate`, `refuse` |
| **Unanswerable Abstention Accuracy** | **20.0%** | **100.0%** | **+80.0 pp** | Refusal on out-of-scope queries |
| **Fact Match Rate (`must_include`)** | **39.7%** | **84.5%** | **+44.8 pp** | Specific policy & catalog facts |
| **Prohibited Claim Violations (`must_not_include`)** | **0** | **0** | **0** | Hallucinated forbidden claims |

> [!NOTE]
> Retrieval metrics (Recall@4, Full Retrieval, Hard Negatives) apply exclusively to Step 2 RAG. In Step 1, Gemini answered directly from internal weights without accessing company documents.

---

## 2. Key Findings & Behavioral Analysis

### A. Factual Adherence on Company-Specific Policies
* **Step 1 Baseline:** The prompt-only baseline achieves 39.7% fact match on `must_include`. Because the model lacks internal knowledge of ZentroMart's specific synthetic policies (e.g. 15-day festive fashion return extension, SKU warranty terms, exact refund SLA hours), it either generates generic e-commerce assumptions or omits required numeric parameters.
* **Step 2 Grounded RAG:** Integrating knowledge base retrieval increases fact adherence to **84.5%** (+15.5 pp). The model cites authoritative section identifiers (e.g. `[RET-2]`, `[WAR-2]`, `[PAY-4]`) and provides exact numbers, deadlines, and portal paths.

### B. Prevention of Hallucinations and Prohibited Claims
* **Both systems maintain zero violations (`0`)** on explicit prohibited claims (`must_not_include`). When instructed under temperature `0.0`, Gemini does not generate forbidden customer guarantees.
* **Abstention on Out-of-Scope / Unanswerable Queries:** On queries outside the knowledge base (e.g. midnight delivery slots, student discounts), the Step 1 prompt-only baseline achieves only **20.0% abstention accuracy**, frequently fabricating plausible-sounding customer policies (e.g. claiming standard delivery is 8 AM to 9 PM). In contrast, Step 2 Grounded RAG achieves **100.0% abstention accuracy** (+80.0 pp), strictly refusing or escalating when retrieved evidence is absent or insufficient.

---

## 3. Representative Comparative Examples

### [PQ0002] SKU ELE-0012 pe ZentroMart Assured hai kya? Claim kaise karein?
* **Scenario Category:** Fact Precision Gain (Grounded)
* **Expected Decision:** `answer` | **Gold Evidence:** `WAR-2, products.csv:ELE-0012`
* **Must-Include Facts:** `12 ; My Orders / app`

**Step 1 Prompt-Only Baseline:**
* Decision: `escalate` (Facts matched: 1/2)
* Generated Answer: *"Mere paas SKU ELE-0012 par ZentroMart Assured status ya iske warranty claim ki specific details available nahi hain. Main iski jaanch ke liye aapki request ko support team ke paas escalate kar raha hoon."*

**Step 2 Grounded RAG:**
* Decision: `answer` (Facts matched: 2/2)
* Retrieved Evidence: `POL-WAR-INTRO, WAR-2, HLP-TRB-INTRO, products.csv:ELE-0012`
* Generated Answer: *"Haan, SKU ELE-0012 (Kestrel K7 Smartphone 128 GB, Beige) par ZentroMart Assured hai! Iska claim karne ke liye, aap app mein 'My Orders' ke andar jaakar claim raise kar sakte hain, jiske baad ZentroMart pickup aur repair ya replacement ki vyavastha karega."*

---

### [PQ0004] Can I schedule a delivery at midnight?
* **Scenario Category:** Fact Precision Gain (Grounded)
* **Expected Decision:** `answer` | **Gold Evidence:** ``
* **Must-Include Facts:** `don't have / do not have / not sure / no information / can't find / not able to find / couldn't find / जानकारी नहीं / pata nahi / jaankari nahi / connect / सहयोगी`

**Step 1 Prompt-Only Baseline:**
* Decision: `answer` (Facts matched: 0/1)
* Generated Answer: *"Currently, ZentroMart does not offer midnight delivery slots. Our standard delivery hours are between 8:00 AM and 9:00 PM. You can choose from the available delivery time slots during checkout."*

**Step 2 Grounded RAG:**
* Decision: `refuse` (Facts matched: 1/1)
* Retrieved Evidence: `DEL-1, CAN-2, FAQ-4, FAQ-2`
* Generated Answer: *"I'm sorry, but the information regarding whether you can schedule a delivery at midnight is not found in ZentroMart's knowledge base. Please connect with a human support agent for assistance."*

---

### [PQ0005] SKU ELE-0002 pe ZentroMart Assured hai kya? Claim kaise karein?
* **Scenario Category:** Fact Precision Gain (Grounded)
* **Expected Decision:** `answer` | **Gold Evidence:** `WAR-2, products.csv:ELE-0002`
* **Must-Include Facts:** `12 ; My Orders / app`

**Step 1 Prompt-Only Baseline:**
* Decision: `refuse` (Facts matched: 0/2)
* Generated Answer: *"Mujhe is waqt SKU ELE-0002 par ZentroMart Assured ka status aur uske claim karne ki details nahi pata hain. Kripya aap product page check karein ya order ID ke sath dobara sampark karein."*

**Step 2 Grounded RAG:**
* Decision: `answer` (Facts matched: 2/2)
* Retrieved Evidence: `products.csv:ELE-0002, WAR-2, HLP-TRB-INTRO, POL-WAR-INTRO`
* Generated Answer: *"Haan, SKU ELE-0002 (Nimbus X2 Wireless Earbuds) par ZentroMart Assured available hai. Iske antargat 12-month ki ZentroMart Assured warranty milti hai. Claim karne ke liye aapko ZentroMart app mein 'My Orders' section mein jaakar claim raise karna hoga, jiske baad ZentroMart pickup arrange karke repair ya replacement ki suvidha pradan karega."*

---

### [PQ0009] Is there a student discount?
* **Scenario Category:** Abstention Verification (Unanswerable)
* **Expected Decision:** `answer` | **Gold Evidence:** ``
* **Must-Include Facts:** `don't have / do not have / not sure / no information / can't find / not able to find / couldn't find / जानकारी नहीं / pata nahi / jaankari nahi / connect / सहयोगी`

**Step 1 Prompt-Only Baseline:**
* Decision: `refuse` (Facts matched: 1/1)
* Generated Answer: *"I am sorry, but I do not have the specific details regarding whether ZentroMart currently offers a student discount. Please check our official website or contact our support team for the latest promotions and discount policies."*

**Step 2 Grounded RAG:**
* Decision: `refuse` (Facts matched: 1/1)
* Retrieved Evidence: `PAY-4, DEL-4, REF-4, FAQ-3`
* Generated Answer: *"Information regarding a student discount is not found in ZentroMart's knowledge base. Please connect with a human support agent for further assistance."*

---

## 4. Evaluation Methodology & Limitations

1. **Deterministic Setup:** Both evaluations ran at temperature `0.0` over the exact 52 practice questions in `dataset/practice/questions.csv`.
2. **Scoring Equivalence:** The exact same regex and substring evaluation rules (`check_must_include`, `check_must_not_include`, `check_fact_presence`) were applied to both runs.
3. **Prompt Insulation:** Neither prompt leaked gold evidence, reference answers, or `must_include` target phrases to the model.
4. **Limitations:**
   * Single-turn evaluation does not test multi-turn state preservation or order identity gates (evaluated separately in Phase 3/4).
   * Fact match scoring relies on substring/numeric pattern matching, which may penalize semantically correct answers that use unexpected synonyms.
