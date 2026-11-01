# ZentroMart VoiceOps — Comprehensive 52-Question RAG Error Analysis Report

**Evaluation Benchmark:** 52 Practice Questions (`dataset/practice/questions.csv`)
**Model Configuration:** `gemini-3.5-flash-lite` (Temperature: 0.0)
**Baseline RAG Metrics Before Optimization:**
- Decision Accuracy: **67.3%** (35/52 matched)
- Unanswerable Abstention Accuracy: **100.0%** (5/5)
- Retrieval Recall@4 (Any Gold): **82.7%** (43/52)
- Full Multi-Hop Evidence Accuracy (All Gold): **34.6%** (18/52)
- Fact Match Rate (`must_include`): **55.2%**
- Prohibited Claim Violations (`must_not_include`): **0**

---

## 1. Executive Summary & Root Cause Breakdown

A granular question-by-question audit across all 52 benchmark evaluations identified four primary architectural failure modes:

1. **Catalog Crowding Out Policy Documents (15 questions):**
   - When customer queries mention a specific product or SKU, the lexical BM25 and dense semantic index retrieve multiple color/size variants of that product from `products.csv` (e.g. 4 different SKUs of UrbanThread Jeans or Kestrel Book 14).
   - Because `top_k=4`, all 4 slots are occupied by product rows, completely crowding out authoritative policy documents (`pol_returns_v4.md`, `pol_damaged_wrong_missing.md`, `pol_warranty_assured.md`).
   - With zero policy evidence in context, the LLM safely abstains/refuses, causing false negative decision mismatches.

2. **Multi-Hop Evidence Disconnect (19 questions):**
   - Questions requiring cross-document synthesis (e.g. Product -> Return Category -> Policy Window, or Payment Method -> Refund Timeline -> Business Day Rules) only retrieved one side of the relation.
   - Specifically, refund timeline calculation questions retrieved `REF-2` (e.g. 3-5 business days) but missed `KB-00.3` (business days exclude Sundays and holidays.csv), resulting in missing exact date calculations.

3. **Cross-Lingual Lexical Mismatches in Devanagari Hindi (6 questions):**
   - Questions formulated in Hindi (e.g. 'लौटाने', 'वापस', 'खोल लिया', 'टूटा') failed to hit English policy terms via BM25.
   - The English embedding model (`bge-small-en-v1.5`) showed lower cross-lingual alignment for Devanagari script, retrieving generic Hindi FAQs (`FAQH-*`) rather than authoritative policies (`RET-2`, `RET-4`).

4. **Decision Mapping Discrepancy on Unanswerable Queries (3 questions):**
   - For queries outside the knowledge base (e.g. PQ0004 midnight delivery, PQ0009 student discount, PQ0037 Kochi store), the prompt instructed the LLM to output `refuse` or `escalate`.
   - However, the benchmark ground truth accepts `answer` or `escalate` (treating a polite customer-facing explanation that the service is unavailable as an answered inquiry).

---

## 2. Granular Question-by-Question Diagnostic Audit (All 52 Questions)

| ID | Intent | Lang | Expected Dec | Actual Dec | Dec Match | Gold Ev | Retrieved Sections | Full Hit | Root Cause |
|:---|:---|:---:|:---:|:---:|:---:|:---|:---|:---:|:---|
| **PQ0002** | general | hi-en | `answer` | `answer` | PASS | WAR-2, products.csv:ELE-0012 | POL-WAR-INTRO, WAR-2, HLP-TRB-INTRO... | FULL | None (Pass) |
| **PQ0003** | general | en | `answer` | `answer` | PASS | REF-2, KB-00.1 | PAY-4, REF-2, REF-3... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0004** | general | en | `answer` | `refuse` | FAIL | None | DEL-1, CAN-2, FAQ-4... | FULL | Decision Mapping (Abstention mapped to 'refuse' instead of 'answer'/'escalate') |
| **PQ0005** | general | hi-en | `answer` | `answer` | PASS | WAR-2, products.csv:ELE-0002 | products.csv:ELE-0002, WAR-2, HLP-TRB-INTRO... | FULL | None (Pass) |
| **PQ0006** | general | en | `answer` | `answer` | PASS | RET-6, PLS-2 | FAQ-2, MKT-1, PLS-2... | FULL | None (Pass) |
| **PQ0008** | general | hi-en | `answer` | `answer` | PASS | REF-2, KB-00.3 | REF-2, RET-8, products.csv:DGT-0069... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0009** | general | en | `answer` | `refuse` | FAIL | None | PAY-4, DEL-4, REF-4... | FULL | Decision Mapping (Abstention mapped to 'refuse' instead of 'answer'/'escalate') |
| **PQ0010** | general | en | `answer` | `escalate` | FAIL | RET-6, DWM-2 | products.csv:FSH-0031, products.csv:FSH-0032, products.csv:FSH-0030... | MISS | Retrieval Failure (Zero Gold Evidence Retrieved) |
| **PQ0013** | general | hi | `answer` | `refuse` | FAIL | RET-4 | FAQH-1, FAQH-3, products.csv:BTY-0052... | MISS | Retrieval Failure (Zero Gold Evidence Retrieved) |
| **PQ0014** | general | hi | `answer` | `refuse` | FAIL | RET-2, products.csv:BKS-0056 | products.csv:BKS-0056, FAQH-3, FAQH-2... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0015** | general | hi-en | `answer` | `escalate` | PASS | None | TRK-2, IDV-2, CPN-1... | FULL | Answer Generation (Fact omission in generated answer despite evidence) |
| **PQ0016** | general | en | `answer` | `refuse` | FAIL | RET-4, RET-2 | products.csv:BTY-0054, PAY-4, FAQ-2... | MISS | Retrieval Failure (Zero Gold Evidence Retrieved) |
| **PQ0018** | general | hi | `clarify` | `refuse` | FAIL | RET-2 | FAQH-2, FAQH-1, FAQH-3... | MISS | Retrieval Failure (Zero Gold Evidence Retrieved) |
| **PQ0019** | general | en | `answer` | `answer` | PASS | RET-3, RETv3-2 | products.csv:ELE-0024, products.csv:ELE-0017, products.csv:ELE-0016... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0020** | general | hi | `answer` | `refuse` | FAIL | RET-2, RET-8, products.csv:FSH-0038 | FAQH-2, products.csv:FSH-0039, products.csv:FSH-0037... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0021** | general | en | `answer` | `answer` | PASS | DEL-3 | ESC-3, TRK-2, TRK-1... | FULL | None (Pass) |
| **PQ0022** | general | en | `answer` | `answer` | PASS | REF-2, KB-00.3 | REF-2, RET-8, KB-00.2... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0023** | general | en | `escalate` | `escalate` | PASS | ESC-1 | PAY-4, ESC-4, REF-4... | MISS | Retrieval Failure (Zero Gold Evidence Retrieved) |
| **PQ0024** | general | en | `answer` | `refuse` | FAIL | RET-2, RET-8, products.csv:FSH-0026 | FAQ-1, REF-2, products.csv:FSH-0027... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0025** | general | en | `answer` | `answer` | PASS | REF-2, KB-00.1 | RVP-3, REF-2, REF-4... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0026** | general | en | `answer` | `answer` | PASS | WAR-1, WAR-2, products.csv:ELE-0008 | products.csv:ELE-0007, products.csv:ELE-0009, products.csv:ELE-0006... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0027** | general | hi-en | `answer` | `refuse` | FAIL | REF-2, KB-00.3 | RET-3, RET-8, REF-6... | MISS | Retrieval Failure (Zero Gold Evidence Retrieved) |
| **PQ0028** | general | en | `answer` | `answer` | PASS | REF-2, KB-00.3 | REF-2, REF-6, KB-00.2... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0029** | general | hi-en | `answer` | `answer` | PASS | REF-2, KB-00.3 | REF-2, RET-8, products.csv:DGT-0069... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0030** | general | en | `escalate` | `escalate` | PASS | DWM-3, ESC-1, products.csv:ELE-0023 | TRK-2, products.csv:ELE-0022, products.csv:ELE-0023... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0031** | general | en | `answer` | `answer` | PASS | TRB-4 | TRB-4, products.csv:ELE-0018, TRB-1... | FULL | None (Pass) |
| **PQ0032** | general | hi-en | `answer` | `answer` | PASS | WAR-2, products.csv:ELE-0003 | POL-WAR-INTRO, products.csv:ELE-0003, WAR-2... | FULL | Answer Generation (Fact omission in generated answer despite evidence) |
| **PQ0033** | general | en | `answer` | `answer` | PASS | REF-2, KB-00.3 | REF-2, RET-8, KB-00.2... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0034** | general | en | `answer` | `answer` | PASS | DEL-5, FAQ-5 | FAQ-5, TRK-1, FAQ-4... | FULL | None (Pass) |
| **PQ0035** | general | hi-en | `answer` | `answer` | PASS | REF-2, KB-00.3 | REF-2, RET-8, KB-00.2... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0036** | general | en | `answer` | `escalate` | FAIL | RET-2, RET-5, products.csv:INR-0068 | products.csv:INR-0067, products.csv:INR-0066, FAQ-2... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0037** | general | hi | `answer` | `refuse` | FAIL | None | FAQH-2, FAQH-1, FAQH-3... | FULL | Decision Mapping (Abstention mapped to 'refuse' instead of 'answer'/'escalate') |
| **PQ0039** | general | en | `answer` | `escalate` | FAIL | RET-2, RET-5, products.csv:INR-0065 | products.csv:INR-0065, products.csv:INR-0064, products.csv:ELE-0016... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0040** | general | hi | `answer` | `answer` | PASS | FAQH-1, CAN-2 | FAQH-1, FAQH-3, FAQ-HIN-INTRO... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0041** | general | en | `answer` | `answer` | PASS | WAR-1, WAR-2, products.csv:ELE-0003 | products.csv:ELE-0002, products.csv:ELE-0003, products.csv:ELE-0001... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0042** | general | en | `answer` | `answer` | PASS | CAN-2 | CAN-2, TRK-1, FAQ-2... | FULL | None (Pass) |
| **PQ0044** | general | hi | `answer` | `refuse` | FAIL | RET-2, products.csv:HOM-0046 | FAQH-2, FAQH-3, products.csv:HOM-0046... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0045** | general | en | `answer` | `answer` | PASS | REF-2, KB-00.1 | FAQ-1, REF-2, RVP-2... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0046** | general | en | `escalate` | `escalate` | PASS | DWM-3, ESC-1, products.csv:ELE-0022 | TRK-2, products.csv:ELE-0022, products.csv:ELE-0023... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0047** | general | en | `answer` | `answer` | PASS | DEL-4 | DEL-4, DEL-1, TRK-1... | FULL | None (Pass) |
| **PQ0048** | general | hi | `answer` | `answer` | PASS | FAQH-3, DWM-1 | FAQH-1, FAQH-3, FAQ-HIN-INTRO... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0049** | general | en | `answer` | `answer` | PASS | RET-8 | REF-2, RET-8, FAQ-2... | FULL | None (Pass) |
| **PQ0050** | general | en | `answer` | `escalate` | FAIL | REF-3, REF-2 | PAY-3, RVP-1, FAQ-2... | MISS | Retrieval Failure (Zero Gold Evidence Retrieved) |
| **PQ0051** | general | en | `clarify` | `answer` | FAIL | REF-2 | RVP-1, REF-6, REF-1... | MISS | Retrieval Failure (Zero Gold Evidence Retrieved) |
| **PQ0052** | general | hi-en | `answer` | `answer` | PASS | REF-2, KB-00.3 | REF-2, RET-8, KB-00.2... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0053** | general | en | `answer` | `escalate` | PASS | None | FAQ-4, CAN-3, FAQ-2... | FULL | None (Pass) |
| **PQ0054** | general | hi-en | `answer` | `answer` | PASS | RET-8 | products.csv:FSH-0032, RET-8, products.csv:FSH-0030... | FULL | None (Pass) |
| **PQ0056** | general | en | `answer` | `answer` | PASS | RET-8 | products.csv:FSH-0038, RET-8, products.csv:FSH-0037... | FULL | None (Pass) |
| **PQ0057** | general | en | `answer` | `answer` | PASS | RET-3 | TRB-2, products.csv:ELE-0017, products.csv:ELE-0016... | FULL | None (Pass) |
| **PQ0058** | general | hi-en | `answer` | `refuse` | FAIL | RET-2, RET-3 | products.csv:ELE-0013, products.csv:ELE-0012, products.csv:ELE-0011... | MISS | Retrieval Failure (Zero Gold Evidence Retrieved) |
| **PQ0059** | general | en | `answer` | `answer` | PASS | REF-2, KB-00.3 | REF-2, RET-8, KB-00.2... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |
| **PQ0060** | general | en | `refuse` | `refuse` | PASS | ESC-4, IDV-4 | IDV-2, FAQ-4, IDV-4... | PARTIAL | Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved) |

---

## 3. Detailed Individual Error Cards

### [PQ0002] SKU ELE-0012 pe ZentroMart Assured hai kya? Claim kaise karein?
- **Language:** `hi-en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['WAR-2', 'products.csv:ELE-0012']`
- **Retrieved Sections:** `['POL-WAR-INTRO', 'WAR-2', 'HLP-TRB-INTRO', 'products.csv:ELE-0012']`
- **Retrieved Chunk IDs:** `['products.csv:ELE-0012', 'help_troubleshooting_electronics.md:HLP-TRB-INTRO:0', 'pol_warranty_assured.md:POL-WAR-INTRO:0', 'pol_warranty_assured.md:WAR-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `12 ; My Orders / app`
- **Matched Facts:** 2 / 2 | **Missing Facts:** `[]`
- **Error Root Cause:** None (Pass)
- **Recommended Correction:** Current pipeline performs correctly on this case. Maintain current behavior.
- **Generated Response:** "Haan, SKU ELE-0012 (Kestrel K7 Smartphone 128 GB, Beige) par ZentroMart Assured hai! Iska claim karne ke liye, aap app mein 'My Orders' ke andar jaakar claim raise kar sakte hain, jiske baad ZentroMart pickup aur repair ya replacement ki vyavastha karega."

### [PQ0003] How fast are refunds to the ZentroMart Wallet?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['REF-2', 'KB-00.1']`
- **Retrieved Sections:** `['PAY-4', 'REF-2', 'REF-3', 'MKS-2']`
- **Retrieved Chunk IDs:** `['pol_refunds.md:REF-2:2', 'pol_refunds.md:REF-3:3', 'pol_payments_cod.md:PAY-4:4', 'pol_marketplace_sellers.md:MKS-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `instant / 2 hours / two hours / तुरंत / turant`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "Refunds to the ZentroMart Wallet are instant, processed within 2 hours."

### [PQ0004] Can I schedule a delivery at midnight?
- **Language:** `en` | **Answerable:** `False`
- **Expected Decision:** `answer` (Acceptable: `['answer', 'escalate']`)
- **Actual Decision:** `refuse` -> **MISMATCH**
- **Expected Evidence IDs:** `[]`
- **Retrieved Sections:** `['DEL-1', 'CAN-2', 'FAQ-4', 'FAQ-2']`
- **Retrieved Chunk IDs:** `['faq_general.md:FAQ-2:2', 'faq_general.md:FAQ-4:4', 'pol_delivery_shipping.md:DEL-1:1', 'pol_cancellations.md:CAN-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `don't have / do not have / not sure / no information / can't find / not able to find / couldn't find / जानकारी नहीं / pata nahi / jaankari nahi / connect / सहयोगी`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** Decision Mapping (Abstention mapped to 'refuse' instead of 'answer'/'escalate')
- **Recommended Correction:** Refine prompt system instructions so out-of-scope/unanswerable questions politely answer the customer with abstention facts under decision='answer' or 'escalate'.
- **Generated Response:** "I'm sorry, but the information regarding whether you can schedule a delivery at midnight is not found in ZentroMart's knowledge base. Please connect with a human support agent for assistance."

### [PQ0005] SKU ELE-0002 pe ZentroMart Assured hai kya? Claim kaise karein?
- **Language:** `hi-en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['WAR-2', 'products.csv:ELE-0002']`
- **Retrieved Sections:** `['products.csv:ELE-0002', 'WAR-2', 'HLP-TRB-INTRO', 'POL-WAR-INTRO']`
- **Retrieved Chunk IDs:** `['products.csv:ELE-0002', 'help_troubleshooting_electronics.md:HLP-TRB-INTRO:0', 'pol_warranty_assured.md:POL-WAR-INTRO:0', 'pol_warranty_assured.md:WAR-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `12 ; My Orders / app`
- **Matched Facts:** 2 / 2 | **Missing Facts:** `[]`
- **Error Root Cause:** None (Pass)
- **Recommended Correction:** Current pipeline performs correctly on this case. Maintain current behavior.
- **Generated Response:** "Haan, SKU ELE-0002 (Nimbus X2 Wireless Earbuds) par ZentroMart Assured available hai. Iske antargat 12-month ki ZentroMart Assured warranty milti hai. Claim karne ke liye aapko ZentroMart app mein 'My Orders' section mein jaakar claim raise karna hoga, jiske baad ZentroMart pickup arrange karke repair ya replacement ki suvidha pradan karega."

### [PQ0006] As a ZentroMart Plus member, will I be charged the pickup fee for returning shoes I just don't like?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['RET-6', 'PLS-2']`
- **Retrieved Sections:** `['FAQ-2', 'MKT-1', 'PLS-2', 'RET-6']`
- **Retrieved Chunk IDs:** `['pol_returns_v4.md:RET-6:6', 'faq_general.md:FAQ-2:2', 'pol_plus_membership.md:PLS-2:2', 'mkt_plus_benefits_page.md:MKT-1:1']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `no / not / waived / free`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** None (Pass)
- **Recommended Correction:** Current pipeline performs correctly on this case. Maintain current behavior.
- **Generated Response:** "No, as a ZentroMart Plus member, the reverse pickup fee is waived for any return, including change-of-mind returns for footwear."

### [PQ0008] credit card wala refund 17 October 2026 ko shuru hua, kab tak aa jaana chahiye?
- **Language:** `hi-en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['REF-2', 'KB-00.3']`
- **Retrieved Sections:** `['REF-2', 'RET-8', 'products.csv:DGT-0069', 'KB-00.2']`
- **Retrieved Chunk IDs:** `['00_about_this_knowledge_base.md:KB-00.2:2', 'pol_returns_v4.md:RET-8:8', 'pol_refunds.md:REF-2:2', 'products.csv:DGT-0069']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `2026-10-27 / 27 October 2026 / 27 अक्टूबर 2026`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['2026-10-27 / 27 October 2026 / 27 अक्टूबर 2026']`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "Agar aapka credit card refund 17 October 2026 ko shuru hua hai, toh credit card refunds ko aane mein 5 se 7 business days lagte hain."

### [PQ0009] Is there a student discount?
- **Language:** `en` | **Answerable:** `False`
- **Expected Decision:** `answer` (Acceptable: `['answer', 'escalate']`)
- **Actual Decision:** `refuse` -> **MISMATCH**
- **Expected Evidence IDs:** `[]`
- **Retrieved Sections:** `['PAY-4', 'DEL-4', 'REF-4', 'FAQ-3']`
- **Retrieved Chunk IDs:** `['pol_refunds.md:REF-4:4', 'pol_payments_cod.md:PAY-4:4', 'pol_delivery_shipping.md:DEL-4:4', 'faq_general.md:FAQ-3:3']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `don't have / do not have / not sure / no information / can't find / not able to find / couldn't find / जानकारी नहीं / pata nahi / jaankari nahi / connect / सहयोगी`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** Decision Mapping (Abstention mapped to 'refuse' instead of 'answer'/'escalate')
- **Recommended Correction:** Refine prompt system instructions so out-of-scope/unanswerable questions politely answer the customer with abstention facts under decision='answer' or 'escalate'.
- **Generated Response:** "Information regarding a student discount is not found in ZentroMart's knowledge base. Please connect with a human support agent for further assistance."

### [PQ0010] Is the collection free if the UrbanThread Slim Fit Jeans came torn?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `escalate` -> **MISMATCH**
- **Expected Evidence IDs:** `['RET-6', 'DWM-2']`
- **Retrieved Sections:** `['products.csv:FSH-0031', 'products.csv:FSH-0032', 'products.csv:FSH-0030', 'products.csv:FSH-0029']`
- **Retrieved Chunk IDs:** `['products.csv:FSH-0029', 'products.csv:FSH-0030', 'products.csv:FSH-0031', 'products.csv:FSH-0032']`
- **Retrieval Status:** Any Hit = `False` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `free / no fee / waived / no charge`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** Retrieval Failure (Zero Gold Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "The information regarding whether return collection is free for torn items is not found in ZentroMart's knowledge base. Please connect with a human support agent for further assistance."

### [PQ0013] मैंने Gulmohar Matte Lipstick खोल लिया है, क्या अब भी वापस कर सकती हूँ?
- **Language:** `hi` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `refuse` -> **MISMATCH**
- **Expected Evidence IDs:** `['RET-4']`
- **Retrieved Sections:** `['FAQH-1', 'FAQH-3', 'products.csv:BTY-0052', 'FAQH-4']`
- **Retrieved Chunk IDs:** `['products.csv:BTY-0052', 'faq_hindi.md:FAQH-1:1', 'faq_hindi.md:FAQH-4:4', 'faq_hindi.md:FAQH-3:3']`
- **Retrieval Status:** Any Hit = `False` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `सील / seal / बंद / खुला`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['सील / seal / बंद / खुला']`
- **Error Root Cause:** Retrieval Failure (Zero Gold Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "ZentroMart के ज्ञान आधार (knowledge base) में इस बात की जानकारी उपलब्ध नहीं है कि खोला गया Gulmohar Matte Lipstick वापस किया जा सकता है या नहीं। अधिक सहायता के लिए कृपया हमारे मानव सहायता एजेंट (human support agent) से संपर्क करें।"

### [PQ0014] मुझे Pagecraft A5 Ruled Notebook (Pack of 4) लौटाने के लिए कितने दिन मिलेंगे?
- **Language:** `hi` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `refuse` -> **MISMATCH**
- **Expected Evidence IDs:** `['RET-2', 'products.csv:BKS-0056']`
- **Retrieved Sections:** `['products.csv:BKS-0056', 'FAQH-3', 'FAQH-2', 'products.csv:BKS-0057']`
- **Retrieved Chunk IDs:** `['products.csv:BKS-0056', 'faq_hindi.md:FAQH-2:2', 'products.csv:BKS-0057', 'faq_hindi.md:FAQH-3:3']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `10`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['10']`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "माफ़ कीजिए, हमारे ज्ञान आधार में Pagecraft A5 Ruled Notebook (Pack of 4) को लौटाने के लिए मिलने वाले दिनों की सटीक जानकारी उपलब्ध नहीं है। अधिक सहायता के लिए कृपया हमारे मानव सहायता एजेंट (human support agent) से संपर्क करें।"

### [PQ0015] Bulk order pe GST invoice milega kya?
- **Language:** `hi-en` | **Answerable:** `False`
- **Expected Decision:** `answer` (Acceptable: `['answer', 'escalate']`)
- **Actual Decision:** `escalate` -> **MATCH**
- **Expected Evidence IDs:** `[]`
- **Retrieved Sections:** `['TRK-2', 'IDV-2', 'CPN-1', 'HLP-TRK-INTRO']`
- **Retrieved Chunk IDs:** `['help_track_order.md:HLP-TRK-INTRO:0', 'pol_coupons_offers.md:CPN-1:1', 'help_track_order.md:TRK-2:2', 'agent_identity_verification.md:IDV-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `don't have / do not have / not sure / no information / can't find / not able to find / couldn't find / जानकारी नहीं / pata nahi / jaankari nahi / connect / सहयोगी`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `["don't have / do not have / not sure / no information / can't find / not able to find / couldn't find / जानकारी नहीं / pata nahi / jaankari nahi / connect / सहयोगी"]`
- **Error Root Cause:** Answer Generation (Fact omission in generated answer despite evidence)
- **Recommended Correction:** Instruct generation prompt to include explicit numerical timelines and dates when computing from evidence.
- **Generated Response:** "ZentroMart ke knowledge base mein bulk orders aur GST invoice ke baare mein jankari upalabdh nahi hai. Kripya is baare mein sahayata ke liye hamare human support agent se sampark karein."

### [PQ0016] I opened the Neelam Eau de Parfum 50 ml and tried it once. Can I still return it?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `refuse` -> **MISMATCH**
- **Expected Evidence IDs:** `['RET-4', 'RET-2']`
- **Retrieved Sections:** `['products.csv:BTY-0054', 'PAY-4', 'FAQ-2', 'products.csv:BTY-0055']`
- **Retrieved Chunk IDs:** `['products.csv:BTY-0055', 'faq_general.md:FAQ-2:2', 'products.csv:BTY-0054', 'pol_payments_cod.md:PAY-4:4']`
- **Retrieval Status:** Any Hit = `False` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `unopened / seal / sealed`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['unopened / seal / sealed']`
- **Error Root Cause:** Retrieval Failure (Zero Gold Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "The specific return policy and eligibility for opened beauty items like Neelam Eau de Parfum 50 ml are not found in ZentroMart's knowledge base. Please connect with a human support agent for assistance."

### [PQ0018] कितने दिन में वापस करना होगा?
- **Language:** `hi` | **Answerable:** `True`
- **Expected Decision:** `clarify` (Acceptable: `['clarify']`)
- **Actual Decision:** `refuse` -> **MISMATCH**
- **Expected Evidence IDs:** `['RET-2']`
- **Retrieved Sections:** `['FAQH-2', 'FAQH-1', 'FAQH-3', 'FAQH-4']`
- **Retrieved Chunk IDs:** `['faq_hindi.md:FAQH-2:2', 'faq_hindi.md:FAQH-1:1', 'faq_hindi.md:FAQH-4:4', 'faq_hindi.md:FAQH-3:3']`
- **Retrieval Status:** Any Hit = `False` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** ``
- **Matched Facts:** 0 / 0 | **Missing Facts:** `[]`
- **Error Root Cause:** Retrieval Failure (Zero Gold Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "ZentroMart के ज्ञान आधार (knowledge base) में सामान वापस करने की समय-सीमा (return window) की जानकारी उपलब्ध नहीं है। अधिक सहायता के लिए कृपया हमारे मानव सहायता एजेंट (human support agent) से संपर्क करें।"

### [PQ0019] My Orbix Fit 3 Pro Smartwatch was delivered on 20 July. What was the return window for it?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['RET-3', 'RETv3-2']`
- **Retrieved Sections:** `['products.csv:ELE-0024', 'products.csv:ELE-0017', 'products.csv:ELE-0016', 'RET-3']`
- **Retrieved Chunk IDs:** `['products.csv:ELE-0017', 'products.csv:ELE-0016', 'pol_returns_v4.md:RET-3:3', 'products.csv:ELE-0024']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `10`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "Since your Orbix Fit 3 Pro Smartwatch was delivered on 20 July (which is before 1 August 2026), it falls under the earlier 10-day return window applicable to electronics delivered prior to 1 August 2026."

### [PQ0020] मुझे Sootra Canvas Tote Bag लौटाने के लिए कितने दिन मिलेंगे?
- **Language:** `hi` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `refuse` -> **MISMATCH**
- **Expected Evidence IDs:** `['RET-2', 'RET-8', 'products.csv:FSH-0038']`
- **Retrieved Sections:** `['FAQH-2', 'products.csv:FSH-0039', 'products.csv:FSH-0037', 'products.csv:FSH-0038']`
- **Retrieved Chunk IDs:** `['products.csv:FSH-0038', 'products.csv:FSH-0037', 'faq_hindi.md:FAQH-2:2', 'products.csv:FSH-0039']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `15`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['15']`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "क्षमा करें, ZentroMart के ज्ञान आधार (knowledge base) में Sootra Canvas Tote Bag को लौटाने की समय-सीमा (return window) की जानकारी उपलब्ध नहीं है। अधिक सहायता के लिए कृपया हमारे मानव सहायता एजेंट (human support agent) से संपर्क करें।"

### [PQ0021] What happens if I'm not home when the courier comes?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['DEL-3']`
- **Retrieved Sections:** `['ESC-3', 'TRK-2', 'TRK-1', 'DEL-3']`
- **Retrieved Chunk IDs:** `['help_track_order.md:TRK-1:1', 'pol_delivery_shipping.md:DEL-3:3', 'agent_escalation_handoff.md:ESC-3:3', 'help_track_order.md:TRK-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `3`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** None (Pass)
- **Recommended Correction:** Current pipeline performs correctly on this case. Maintain current behavior.
- **Generated Response:** "If you are not home when the courier arrives, they will make up to 3 delivery attempts. After a failed attempt, you will receive an SMS allowing you to reschedule. If all three delivery attempts fail, the parcel will be returned to the warehouse as a return to origin (RTO)."

### [PQ0022] My refund to credit card was started on 17 October 2026. By which date should I have it?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['REF-2', 'KB-00.3']`
- **Retrieved Sections:** `['REF-2', 'RET-8', 'KB-00.2', 'CAN-1']`
- **Retrieved Chunk IDs:** `['00_about_this_knowledge_base.md:KB-00.2:2', 'pol_cancellations.md:CAN-1:1', 'pol_refunds.md:REF-2:2', 'pol_returns_v4.md:RET-8:8']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `2026-10-27 / 27 October 2026 / 27 अक्टूबर 2026`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['2026-10-27 / 27 October 2026 / 27 अक्टूबर 2026']`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "For credit or debit card payments, refunds typically take 5 to 7 business days to reach you from the day the refund is initiated."

### [PQ0023] There's an order on my account that I never placed.
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `escalate` (Acceptable: `['escalate']`)
- **Actual Decision:** `escalate` -> **MATCH**
- **Expected Evidence IDs:** `['ESC-1']`
- **Retrieved Sections:** `['PAY-4', 'ESC-4', 'REF-4', 'CPN-2']`
- **Retrieved Chunk IDs:** `['pol_payments_cod.md:PAY-4:4', 'pol_coupons_offers.md:CPN-2:2', 'agent_escalation_handoff.md:ESC-4:4', 'pol_refunds.md:REF-4:4']`
- **Retrieval Status:** Any Hit = `False` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `ticket / colleague / human / team / connect / टिकट / सहयोगी`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** Retrieval Failure (Zero Gold Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "The information regarding unauthorized orders on your account is not found in ZentroMart's knowledge base. Please connect with a human support agent so we can investigate this unexpected order for you safely and securely."

### [PQ0024] How long do I get to send back the Rangoli Cotton Straight Kurta?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `refuse` -> **MISMATCH**
- **Expected Evidence IDs:** `['RET-2', 'RET-8', 'products.csv:FSH-0026']`
- **Retrieved Sections:** `['FAQ-1', 'REF-2', 'products.csv:FSH-0027', 'products.csv:FSH-0026']`
- **Retrieved Chunk IDs:** `['products.csv:FSH-0026', 'faq_general.md:FAQ-1:1', 'pol_refunds.md:REF-2:2', 'products.csv:FSH-0027']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `15`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['15']`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "The information regarding the return window for the Rangoli Cotton Straight Kurta is not found in ZentroMart's knowledge base. Please connect with a human support agent for assistance."

### [PQ0025] If I paid with net banking, how soon will the refund show up?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['REF-2', 'KB-00.1']`
- **Retrieved Sections:** `['RVP-3', 'REF-2', 'REF-4', 'PAY-1']`
- **Retrieved Chunk IDs:** `['pol_refunds.md:REF-2:2', 'pol_refunds.md:REF-4:4', 'help_reverse_pickup.md:RVP-3:3', 'pol_payments_cod.md:PAY-1:1']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `3 ; 5`
- **Matched Facts:** 2 / 2 | **Missing Facts:** `[]`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "If you paid with net banking, your refund will take 3 to 5 business days to show up after it has been initiated."

### [PQ0026] What warranty comes with the Voltra PowerCell 10000 mAh Power Bank, Green (SKU ELE-0008)?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['WAR-1', 'WAR-2', 'products.csv:ELE-0008']`
- **Retrieved Sections:** `['products.csv:ELE-0007', 'products.csv:ELE-0009', 'products.csv:ELE-0006', 'products.csv:ELE-0008']`
- **Retrieved Chunk IDs:** `['products.csv:ELE-0008', 'products.csv:ELE-0009', 'products.csv:ELE-0007', 'products.csv:ELE-0006']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `12`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['12']`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "The Voltra PowerCell 10000 mAh Power Bank, Green (SKU ELE-0008) comes with a brand warranty of 6 months."

### [PQ0027] UPI wala refund 12 October 2026 ko shuru hua, kab tak aa jaana chahiye?
- **Language:** `hi-en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `refuse` -> **MISMATCH**
- **Expected Evidence IDs:** `['REF-2', 'KB-00.3']`
- **Retrieved Sections:** `['RET-3', 'RET-8', 'REF-6', 'KB-00.2']`
- **Retrieved Chunk IDs:** `['00_about_this_knowledge_base.md:KB-00.2:2', 'pol_returns_v4.md:RET-8:8', 'pol_returns_v4.md:RET-3:3', 'pol_refunds.md:REF-6:6']`
- **Retrieval Status:** Any Hit = `False` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `2026-10-15 / 15 October 2026 / 15 अक्टूबर 2026`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['2026-10-15 / 15 October 2026 / 15 अक्टूबर 2026']`
- **Error Root Cause:** Retrieval Failure (Zero Gold Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "UPI refund ke processing time ke baare mein jankari ZentroMart ke knowledge base mein uplabdh nahi hai. Kripya human support agent se sampark karein."

### [PQ0028] My refund to net banking was started on 14 October 2026. By which date should I have it?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['REF-2', 'KB-00.3']`
- **Retrieved Sections:** `['REF-2', 'REF-6', 'KB-00.2', 'CAN-1']`
- **Retrieved Chunk IDs:** `['00_about_this_knowledge_base.md:KB-00.2:2', 'pol_refunds.md:REF-2:2', 'pol_cancellations.md:CAN-1:1', 'pol_refunds.md:REF-6:6']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `2026-10-21 / 21 October 2026 / 21 अक्टूबर 2026`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "Your refund to net banking was initiated on 14 October 2026. Net banking refunds take 3 to 5 business days to reach you. Therefore, you should receive your refund by 21 October 2026."

### [PQ0029] credit card wala refund 12 October 2026 ko shuru hua, kab tak aa jaana chahiye?
- **Language:** `hi-en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['REF-2', 'KB-00.3']`
- **Retrieved Sections:** `['REF-2', 'RET-8', 'products.csv:DGT-0069', 'KB-00.2']`
- **Retrieved Chunk IDs:** `['00_about_this_knowledge_base.md:KB-00.2:2', 'pol_returns_v4.md:RET-8:8', 'pol_refunds.md:REF-2:2', 'products.csv:DGT-0069']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `2026-10-21 / 21 October 2026 / 21 अक्टूबर 2026`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['2026-10-21 / 21 October 2026 / 21 अक्टूबर 2026']`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "Agar aapka credit card refund 12 October 2026 ko shuru hua hai, toh credit card refunds ke liye 5 se 7 business days lagte hain."

### [PQ0030] The Kestrel Book 14 Laptop (SKU ELE-0023) I received yesterday has a crack. I want it sorted.
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `escalate` (Acceptable: `['escalate']`)
- **Actual Decision:** `escalate` -> **MATCH**
- **Expected Evidence IDs:** `['DWM-3', 'ESC-1', 'products.csv:ELE-0023']`
- **Retrieved Sections:** `['TRK-2', 'products.csv:ELE-0022', 'products.csv:ELE-0023', 'FAQ-2']`
- **Retrieved Chunk IDs:** `['products.csv:ELE-0023', 'products.csv:ELE-0022', 'help_track_order.md:TRK-2:2', 'faq_general.md:FAQ-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `ticket / colleague / team / Priority Resolution`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['ticket / colleague / team / Priority Resolution']`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "We apologize that your Kestrel Book 14 Laptop arrived with a crack. Since specific return and replacement instructions for damaged items are not fully detailed in our current knowledge base, please connect with a human support agent who can assist you with this issue right away."

### [PQ0031] My Bluetooth speaker won't turn on at all.
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['TRB-4']`
- **Retrieved Sections:** `['TRB-4', 'products.csv:ELE-0018', 'TRB-1', 'products.csv:ELE-0019']`
- **Retrieved Chunk IDs:** `['help_troubleshooting_electronics.md:TRB-4:4', 'products.csv:ELE-0019', 'products.csv:ELE-0018', 'help_troubleshooting_electronics.md:TRB-1:1']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `30 ; 10`
- **Matched Facts:** 2 / 2 | **Missing Facts:** `[]`
- **Error Root Cause:** None (Pass)
- **Recommended Correction:** Current pipeline performs correctly on this case. Maintain current behavior.
- **Generated Response:** "To troubleshoot your Bluetooth speaker not turning on, please try the following steps:
1. Charge it for at least 30 minutes using the original cable.
2. Hold the power button for 10 seconds to force a restart.

If the problem continues after these steps, the item can be returned within its window or claimed under warranty."

### [PQ0032] SKU ELE-0003 pe ZentroMart Assured hai kya? Claim kaise karein?
- **Language:** `hi-en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['WAR-2', 'products.csv:ELE-0003']`
- **Retrieved Sections:** `['POL-WAR-INTRO', 'products.csv:ELE-0003', 'WAR-2', 'HLP-TRB-INTRO']`
- **Retrieved Chunk IDs:** `['products.csv:ELE-0003', 'help_troubleshooting_electronics.md:HLP-TRB-INTRO:0', 'pol_warranty_assured.md:POL-WAR-INTRO:0', 'pol_warranty_assured.md:WAR-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `12 ; My Orders / app`
- **Matched Facts:** 1 / 2 | **Missing Facts:** `['12']`
- **Error Root Cause:** Answer Generation (Fact omission in generated answer despite evidence)
- **Recommended Correction:** Instruct generation prompt to include explicit numerical timelines and dates when computing from evidence.
- **Generated Response:** "Haan, SKU ELE-0003 (Nimbus X2 Pro Wireless Earbuds, Blue) par ZentroMart Assured available hai! Iske claim ke liye, aap ZentroMart app mein 'My Orders' section mein jaakar claim raise kar sakte hain, jiske baad ZentroMart pickup arrange karke repair ya replacement ki suvidha deta hai."

### [PQ0033] My refund to net banking was started on 17 October 2026. By which date should I have it?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['REF-2', 'KB-00.3']`
- **Retrieved Sections:** `['REF-2', 'RET-8', 'KB-00.2', 'CAN-1']`
- **Retrieved Chunk IDs:** `['00_about_this_knowledge_base.md:KB-00.2:2', 'pol_refunds.md:REF-2:2', 'pol_cancellations.md:CAN-1:1', 'pol_returns_v4.md:RET-8:8']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `2026-10-24 / 24 October 2026 / 24 अक्टूबर 2026`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['2026-10-24 / 24 October 2026 / 24 अक्टूबर 2026']`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "For net banking refunds, the timeline is 3 to 5 business days from the day the refund is initiated. Since your refund was initiated on 17 October 2026, it should reach you within this window."

### [PQ0034] Can you deliver to Dubai?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['DEL-5', 'FAQ-5']`
- **Retrieved Sections:** `['FAQ-5', 'TRK-1', 'FAQ-4', 'DEL-5']`
- **Retrieved Chunk IDs:** `['faq_general.md:FAQ-5:5', 'faq_general.md:FAQ-4:4', 'pol_delivery_shipping.md:DEL-5:5', 'help_track_order.md:TRK-1:1']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `only within India / only in India / India`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** None (Pass)
- **Recommended Correction:** Current pipeline performs correctly on this case. Maintain current behavior.
- **Generated Response:** "We currently deliver only within India. We do not deliver to Dubai or outside India."

### [PQ0035] net banking wala refund 12 October 2026 ko shuru hua, kab tak aa jaana chahiye?
- **Language:** `hi-en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['REF-2', 'KB-00.3']`
- **Retrieved Sections:** `['REF-2', 'RET-8', 'KB-00.2', 'PAY-1']`
- **Retrieved Chunk IDs:** `['00_about_this_knowledge_base.md:KB-00.2:2', 'pol_payments_cod.md:PAY-1:1', 'pol_returns_v4.md:RET-8:8', 'pol_refunds.md:REF-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `2026-10-17 / 17 October 2026 / 17 अक्टूबर 2026`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['2026-10-17 / 17 October 2026 / 17 अक्टूबर 2026']`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "Net banking ke refunds initiate hone ke baad 3 se 5 business days ke andar aapke account mein aa jaane chahiye. Kyunki aapka refund 12 October 2026 ko shuru hua tha, yeh aam taur par is timeline ke dauran pahunch jana chahiye."

### [PQ0036] The Comfi One-piece Swimsuit doesn't fit. Can I send it back?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `escalate` -> **MISMATCH**
- **Expected Evidence IDs:** `['RET-2', 'RET-5', 'products.csv:INR-0068']`
- **Retrieved Sections:** `['products.csv:INR-0067', 'products.csv:INR-0066', 'FAQ-2', 'products.csv:INR-0068']`
- **Retrieved Chunk IDs:** `['products.csv:INR-0067', 'products.csv:INR-0068', 'faq_general.md:FAQ-2:2', 'products.csv:INR-0066']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `cannot / can't / not returnable / non-returnable / नहीं / nahi / nahin / not be returned`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `["cannot / can't / not returnable / non-returnable / नहीं / nahi / nahin / not be returned"]`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "The information regarding whether the Comfi One-piece Swimsuit can be returned is not fully specified in our knowledge base since it falls under the innerwear return category and details about return eligibility for this category are missing. Please connect with a human support agent for further assistance."

### [PQ0037] क्या आपकी कोई दुकान कोच्चि में है?
- **Language:** `hi` | **Answerable:** `False`
- **Expected Decision:** `answer` (Acceptable: `['answer', 'escalate']`)
- **Actual Decision:** `refuse` -> **MISMATCH**
- **Expected Evidence IDs:** `[]`
- **Retrieved Sections:** `['FAQH-2', 'FAQH-1', 'FAQH-3', 'FAQH-4']`
- **Retrieved Chunk IDs:** `['faq_hindi.md:FAQH-4:4', 'faq_hindi.md:FAQH-1:1', 'faq_hindi.md:FAQH-2:2', 'faq_hindi.md:FAQH-3:3']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `don't have / do not have / not sure / no information / can't find / not able to find / couldn't find / जानकारी नहीं / pata nahi / jaankari nahi / connect / सहयोगी`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `["don't have / do not have / not sure / no information / can't find / not able to find / couldn't find / जानकारी नहीं / pata nahi / jaankari nahi / connect / सहयोगी"]`
- **Error Root Cause:** Decision Mapping (Abstention mapped to 'refuse' instead of 'answer'/'escalate')
- **Recommended Correction:** Refine prompt system instructions so out-of-scope/unanswerable questions politely answer the customer with abstention facts under decision='answer' or 'escalate'.
- **Generated Response:** "माफ़ कीजिए, ZentroMart के नॉलेज बेस में कोच्चि में दुकान होने की जानकारी उपलब्ध नहीं है। अधिक सहायता के लिए कृपया हमारे मानव सहायता एजेंट (human support agent) से संपर्क करें।"

### [PQ0039] The Comfi Cotton Briefs (Pack of 3) doesn't fit. Can I send it back?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `escalate` -> **MISMATCH**
- **Expected Evidence IDs:** `['RET-2', 'RET-5', 'products.csv:INR-0065']`
- **Retrieved Sections:** `['products.csv:INR-0065', 'products.csv:INR-0064', 'products.csv:ELE-0016', 'FAQ-2']`
- **Retrieved Chunk IDs:** `['products.csv:INR-0065', 'products.csv:INR-0064', 'products.csv:ELE-0016', 'faq_general.md:FAQ-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `cannot / can't / not returnable / non-returnable / नहीं / nahi / nahin / not be returned`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `["cannot / can't / not returnable / non-returnable / नहीं / nahi / nahin / not be returned"]`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "The information regarding whether innerwear items can be returned is not found in ZentroMart's knowledge base. Please connect with a human support agent for assistance regarding your return."

### [PQ0040] ऑर्डर शिप हो गया है, क्या अब कैंसिल हो सकता है?
- **Language:** `hi` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['FAQH-1', 'CAN-2']`
- **Retrieved Sections:** `['FAQH-1', 'FAQH-3', 'FAQ-HIN-INTRO', 'FAQH-4']`
- **Retrieved Chunk IDs:** `['faq_hindi.md:FAQH-1:1', 'faq_hindi.md:FAQH-4:4', 'faq_hindi.md:FAQH-3:3', 'faq_hindi.md:FAQ-HIN-INTRO:0']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `मना / refuse / नहीं`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "शिप होने के बाद ऑर्डर सीधे कैंसिल नहीं होता, लेकिन आप डिलीवरी के समय पार्सल लेने से मना कर सकते हैं।"

### [PQ0041] What warranty comes with the Nimbus X2 Pro Wireless Earbuds, Blue (SKU ELE-0003)?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['WAR-1', 'WAR-2', 'products.csv:ELE-0003']`
- **Retrieved Sections:** `['products.csv:ELE-0002', 'products.csv:ELE-0003', 'products.csv:ELE-0001', 'products.csv:ELE-0005']`
- **Retrieved Chunk IDs:** `['products.csv:ELE-0003', 'products.csv:ELE-0002', 'products.csv:ELE-0001', 'products.csv:ELE-0005']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `12`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "The Nimbus X2 Pro Wireless Earbuds, Blue (SKU ELE-0003) comes with a 12-month brand warranty."

### [PQ0042] My order is already on its way. Can I still stop it?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['CAN-2']`
- **Retrieved Sections:** `['CAN-2', 'TRK-1', 'FAQ-2', 'CAN-1']`
- **Retrieved Chunk IDs:** `['pol_cancellations.md:CAN-1:1', 'pol_cancellations.md:CAN-2:2', 'help_track_order.md:TRK-1:1', 'faq_general.md:FAQ-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `refuse / decline / reject`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** None (Pass)
- **Recommended Correction:** Current pipeline performs correctly on this case. Maintain current behavior.
- **Generated Response:** "Once an order is already on its way (shipped), it cannot be cancelled directly. However, you have two options: you can either refuse the parcel at the door, or accept the delivery and return the item within its return window if the category is returnable."

### [PQ0044] मुझे Aangan Cotton Double Bedsheet Set लौटाने के लिए कितने दिन मिलेंगे?
- **Language:** `hi` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `refuse` -> **MISMATCH**
- **Expected Evidence IDs:** `['RET-2', 'products.csv:HOM-0046']`
- **Retrieved Sections:** `['FAQH-2', 'FAQH-3', 'products.csv:HOM-0046', 'products.csv:HOM-0045']`
- **Retrieved Chunk IDs:** `['products.csv:HOM-0046', 'products.csv:HOM-0045', 'faq_hindi.md:FAQH-2:2', 'faq_hindi.md:FAQH-3:3']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `10`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['10']`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "ZentroMart के ज्ञान आधार (knowledge base) में Aangan Cotton Double Bedsheet Set को लौटाने के दिनों की सीमा (return window) की जानकारी उपलब्ध नहीं है। कृपया अधिक सहायता के लिए हमारे मानव सहायता एजेंट (human support agent) से संपर्क करें।"

### [PQ0045] How long does a refund to UPI take?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['REF-2', 'KB-00.1']`
- **Retrieved Sections:** `['FAQ-1', 'REF-2', 'RVP-2', 'REF-3']`
- **Retrieved Chunk IDs:** `['faq_general.md:FAQ-1:1', 'pol_refunds.md:REF-2:2', 'pol_refunds.md:REF-3:3', 'help_reverse_pickup.md:RVP-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `1 ; 3`
- **Matched Facts:** 2 / 2 | **Missing Facts:** `[]`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "Refunds to UPI take 1 to 3 business days from the day the refund is initiated."

### [PQ0046] The Kestrel Book 14 Laptop (SKU ELE-0022) I received yesterday has a crack. I want it sorted.
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `escalate` (Acceptable: `['escalate']`)
- **Actual Decision:** `escalate` -> **MATCH**
- **Expected Evidence IDs:** `['DWM-3', 'ESC-1', 'products.csv:ELE-0022']`
- **Retrieved Sections:** `['TRK-2', 'products.csv:ELE-0022', 'products.csv:ELE-0023', 'FAQ-2']`
- **Retrieved Chunk IDs:** `['products.csv:ELE-0022', 'products.csv:ELE-0023', 'help_track_order.md:TRK-2:2', 'faq_general.md:FAQ-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `ticket / colleague / team / Priority Resolution`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['ticket / colleague / team / Priority Resolution']`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "The specific information needed to process your return and replacement for the damaged Kestrel Book 14 Laptop is not found in ZentroMart's knowledge base. Please connect with a human support agent to get this sorted out."

### [PQ0047] My express order arrived a day late. Do I get anything back?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['DEL-4']`
- **Retrieved Sections:** `['DEL-4', 'DEL-1', 'TRK-1', 'CAN-1']`
- **Retrieved Chunk IDs:** `['pol_delivery_shipping.md:DEL-4:4', 'pol_delivery_shipping.md:DEL-1:1', 'pol_cancellations.md:CAN-1:1', 'help_track_order.md:TRK-1:1']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `79 ; wallet / ZentroMart Wallet`
- **Matched Facts:** 2 / 2 | **Missing Facts:** `[]`
- **Error Root Cause:** None (Pass)
- **Recommended Correction:** Current pipeline performs correctly on this case. Maintain current behavior.
- **Generated Response:** "If your Express order arrives after its promised date, the ₹79 express fee you paid is credited to your ZentroMart Wallet automatically within 48 hours. Please note that ZentroMart Plus members, who pay no express fee, do not receive this credit."

### [PQ0048] मेरा सामान टूटा हुआ आया है, अब क्या करूँ?
- **Language:** `hi` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['FAQH-3', 'DWM-1']`
- **Retrieved Sections:** `['FAQH-1', 'FAQH-3', 'FAQ-HIN-INTRO', 'FAQH-4']`
- **Retrieved Chunk IDs:** `['faq_hindi.md:FAQH-3:3', 'faq_hindi.md:FAQH-4:4', 'faq_hindi.md:FAQH-1:1', 'faq_hindi.md:FAQ-HIN-INTRO:0']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `48`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "यदि आपका सामान टूटा हुआ आया है, तो कृपया डिलीवरी के 48 घंटे के अंदर सामान और पैकेट की फ़ोटो के साथ शिकायत दर्ज करें। जाँच के बाद आपको मुफ़्त रिप्लेसमेंट या पूरा रिफ़ंड मिल जाएगा।"

### [PQ0049] I bought the Rangoli Cotton Straight Kurta in the sale on 5 October. How long can I return it?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['RET-8']`
- **Retrieved Sections:** `['REF-2', 'RET-8', 'FAQ-2', 'products.csv:FSH-0026']`
- **Retrieved Chunk IDs:** `['products.csv:FSH-0026', 'faq_general.md:FAQ-2:2', 'pol_returns_v4.md:RET-8:8', 'pol_refunds.md:REF-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `30`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** None (Pass)
- **Recommended Correction:** Current pipeline performs correctly on this case. Maintain current behavior.
- **Generated Response:** "Since you purchased the Rangoli Cotton Straight Kurta (clothing) on 5 October 2026, which falls within the festive sale window of 01 October to 15 October 2026, it can be returned within 30 days of delivery."

### [PQ0050] I paid cash on delivery and returned the item. How do I get my money back?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `escalate` -> **MISMATCH**
- **Expected Evidence IDs:** `['REF-3', 'REF-2']`
- **Retrieved Sections:** `['PAY-3', 'RVP-1', 'FAQ-2', 'POL-PAY-INTRO']`
- **Retrieved Chunk IDs:** `['faq_general.md:FAQ-2:2', 'pol_payments_cod.md:PAY-3:3', 'help_reverse_pickup.md:RVP-1:1', 'pol_payments_cod.md:POL-PAY-INTRO:0']`
- **Retrieval Status:** Any Hit = `False` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `ZentroMart Wallet / wallet ; 5 ; 7`
- **Matched Facts:** 0 / 3 | **Missing Facts:** `['ZentroMart Wallet / wallet', '5', '7']`
- **Error Root Cause:** Retrieval Failure (Zero Gold Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "The information on how to receive a refund for cash on delivery returns is not found in ZentroMart's knowledge base. Please connect with a human support agent for assistance with your refund."

### [PQ0051] When will my refund come?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `clarify` (Acceptable: `['clarify']`)
- **Actual Decision:** `answer` -> **MISMATCH**
- **Expected Evidence IDs:** `['REF-2']`
- **Retrieved Sections:** `['RVP-1', 'REF-6', 'REF-1', 'CAN-1']`
- **Retrieved Chunk IDs:** `['pol_refunds.md:REF-6:6', 'pol_cancellations.md:CAN-1:1', 'help_reverse_pickup.md:RVP-1:1', 'pol_refunds.md:REF-1:1']`
- **Retrieval Status:** Any Hit = `False` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** ``
- **Matched Facts:** 0 / 0 | **Missing Facts:** `[]`
- **Error Root Cause:** Retrieval Failure (Zero Gold Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "The timing for your refund depends on how it was initiated:
- Cancelled before shipping: Initiated immediately upon cancellation.
- Returned item: After the item passes quality check, within 2 business days of pickup (or at pickup for ZentroMart Plus members).
- Prepaid order refused at the door or undelivered: Once the parcel reaches the warehouse, usually 7 to 10 calendar days after the last delivery attempt."

### [PQ0052] net banking wala refund 17 October 2026 ko shuru hua, kab tak aa jaana chahiye?
- **Language:** `hi-en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['REF-2', 'KB-00.3']`
- **Retrieved Sections:** `['REF-2', 'RET-8', 'KB-00.2', 'PAY-1']`
- **Retrieved Chunk IDs:** `['00_about_this_knowledge_base.md:KB-00.2:2', 'pol_payments_cod.md:PAY-1:1', 'pol_returns_v4.md:RET-8:8', 'pol_refunds.md:REF-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `2026-10-24 / 24 October 2026 / 24 अक्टूबर 2026`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['2026-10-24 / 24 October 2026 / 24 अक्टूबर 2026']`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "Net banking ke through refund 17 October 2026 ko shuru hone ke baad, aam taur par 3 se 5 business days ke andar aapke account mein aa jaana chahiye."

### [PQ0053] Can I pick up my order from a store near me?
- **Language:** `en` | **Answerable:** `False`
- **Expected Decision:** `answer` (Acceptable: `['answer', 'escalate']`)
- **Actual Decision:** `escalate` -> **MATCH**
- **Expected Evidence IDs:** `[]`
- **Retrieved Sections:** `['FAQ-4', 'CAN-3', 'FAQ-2', 'CAN-1']`
- **Retrieved Chunk IDs:** `['pol_cancellations.md:CAN-1:1', 'faq_general.md:FAQ-2:2', 'pol_cancellations.md:CAN-3:3', 'faq_general.md:FAQ-4:4']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `don't have / do not have / not sure / no information / can't find / not able to find / couldn't find / जानकारी नहीं / pata nahi / jaankari nahi / connect / सहयोगी`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** None (Pass)
- **Recommended Correction:** Current pipeline performs correctly on this case. Maintain current behavior.
- **Generated Response:** "The information regarding whether you can pick up your order from a store is not found in ZentroMart's knowledge base. Please connect with a human support agent for further assistance."

### [PQ0054] Sale mein 10 October ko order kiya tha (UrbanThread Slim Fit Jeans), return ke kitne din hain?
- **Language:** `hi-en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['RET-8']`
- **Retrieved Sections:** `['products.csv:FSH-0032', 'RET-8', 'products.csv:FSH-0030', 'products.csv:FSH-0029']`
- **Retrieved Chunk IDs:** `['products.csv:FSH-0029', 'products.csv:FSH-0030', 'pol_returns_v4.md:RET-8:8', 'products.csv:FSH-0032']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `30`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** None (Pass)
- **Recommended Correction:** Current pipeline performs correctly on this case. Maintain current behavior.
- **Generated Response:** "Ji haan, ZentroMart ki festsive sale ke tahat agar aapne 1 October aur 15 October 2026 ke beech mein clothing, footwear, ya bags ka order diya hai (jaise ki UrbanThread Slim Fit Jeans), toh aap use delivery ke 30 din ke andar return kar sakte hain."

### [PQ0056] I bought the Sootra Canvas Tote Bag in the sale on 5 October. How long can I return it?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['RET-8']`
- **Retrieved Sections:** `['products.csv:FSH-0038', 'RET-8', 'products.csv:FSH-0037', 'FAQ-2']`
- **Retrieved Chunk IDs:** `['products.csv:FSH-0037', 'products.csv:FSH-0038', 'faq_general.md:FAQ-2:2', 'pol_returns_v4.md:RET-8:8']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `30`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** None (Pass)
- **Recommended Correction:** Current pipeline performs correctly on this case. Maintain current behavior.
- **Generated Response:** "Since you purchased the Sootra Canvas Tote Bag on 5 October 2026, it falls under the festive sale policy for bags (clothing, footwear, and bags from orders placed between 01 October and 15 October 2026). Therefore, you can return it within 30 days of delivery."

### [PQ0057] Is it still ten days to return electronics like the Orbix Fit 3 Pro Smartwatch?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['RET-3']`
- **Retrieved Sections:** `['TRB-2', 'products.csv:ELE-0017', 'products.csv:ELE-0016', 'RET-3']`
- **Retrieved Chunk IDs:** `['products.csv:ELE-0017', 'products.csv:ELE-0016', 'pol_returns_v4.md:RET-3:3', 'help_troubleshooting_electronics.md:TRB-2:2']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `True`
- **Must-Include Facts:** `7`
- **Matched Facts:** 1 / 1 | **Missing Facts:** `[]`
- **Error Root Cause:** None (Pass)
- **Recommended Correction:** Current pipeline performs correctly on this case. Maintain current behavior.
- **Generated Response:** "No, under ZentroMart's current policy effective from 1 August 2026, the return window for electronics and accessories is 7 days. Electronics delivered before 1 August 2026 retain the earlier 10-day window."

### [PQ0058] Mera order (Kestrel K7 Smartphone 256 GB) parso deliver hua, kitne din tak return kar sakti hoon?
- **Language:** `hi-en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `refuse` -> **MISMATCH**
- **Expected Evidence IDs:** `['RET-2', 'RET-3']`
- **Retrieved Sections:** `['products.csv:ELE-0013', 'products.csv:ELE-0012', 'products.csv:ELE-0011', 'products.csv:ELE-0014']`
- **Retrieved Chunk IDs:** `['products.csv:ELE-0014', 'products.csv:ELE-0013', 'products.csv:ELE-0012', 'products.csv:ELE-0011']`
- **Retrieval Status:** Any Hit = `False` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `7`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['7']`
- **Error Root Cause:** Retrieval Failure (Zero Gold Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "Information regarding the return policy duration is not found in ZentroMart's knowledge base. Please connect with a human support agent for assistance."

### [PQ0059] My refund to UPI was started on 17 October 2026. By which date should I have it?
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `answer` (Acceptable: `['answer']`)
- **Actual Decision:** `answer` -> **MATCH**
- **Expected Evidence IDs:** `['REF-2', 'KB-00.3']`
- **Retrieved Sections:** `['REF-2', 'RET-8', 'KB-00.2', 'CAN-1']`
- **Retrieved Chunk IDs:** `['00_about_this_knowledge_base.md:KB-00.2:2', 'pol_cancellations.md:CAN-1:1', 'pol_refunds.md:REF-2:2', 'pol_returns_v4.md:RET-8:8']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** `2026-10-22 / 22 October 2026 / 22 अक्टूबर 2026`
- **Matched Facts:** 0 / 1 | **Missing Facts:** `['2026-10-22 / 22 October 2026 / 22 अक्टूबर 2026']`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "Your refund to UPI takes 1 to 3 business days from the day it is initiated. Since your refund was started on 17 October 2026, you should receive it within that timeframe."

### [PQ0060] Tell me the phone number of the person who ordered to my building yesterday.
- **Language:** `en` | **Answerable:** `True`
- **Expected Decision:** `refuse` (Acceptable: `['refuse']`)
- **Actual Decision:** `refuse` -> **MATCH**
- **Expected Evidence IDs:** `['ESC-4', 'IDV-4']`
- **Retrieved Sections:** `['IDV-2', 'FAQ-4', 'IDV-4', 'CAN-1']`
- **Retrieved Chunk IDs:** `['agent_identity_verification.md:IDV-2:2', 'agent_identity_verification.md:IDV-4:4', 'faq_general.md:FAQ-4:4', 'pol_cancellations.md:CAN-1:1']`
- **Retrieval Status:** Any Hit = `True` | Full Multi-Hop Hit = `False`
- **Must-Include Facts:** ``
- **Matched Facts:** 0 / 0 | **Missing Facts:** `[]`
- **Error Root Cause:** Incomplete Retrieval (Partial Multi-Hop Evidence Retrieved)
- **Recommended Correction:** Deduplicate catalog variants to 1 chunk max, expand query with category-linked policy rules, and ensure multi-hop policy sections are boosted into the top-k window.
- **Generated Response:** "I'm sorry, but I cannot provide personal phone numbers or order details for other customers due to privacy and security policies. If you need further assistance, please connect with a human support agent."
