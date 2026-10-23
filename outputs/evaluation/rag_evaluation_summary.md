# ZentroMart VoiceOps — Phase 2 Grounded RAG Evaluation Report

**Evaluation Date:** 23 October 2026  
**Total Questions Evaluated:** 52  
**LLM Model:** gemini-3.5-flash-lite  
**Embedding Model:** Local FastEmbed (`BAAI/bge-small-en-v1.5`)  

---

## 1. Executive Summary & Benchmark Metrics

| Metric | Result | Target / Standard |
| :--- | :---: | :--- |
| **Questions Successfully Evaluated** | **52/52** | 100% evaluated |
| **Execution / API Errors** | **0** | 0 errors |
| **Retrieval Recall@k (Any Gold Evidence)** | **82.7%** | Evidence discovery |
| **Full Retrieval Accuracy (All Evidence)** | **34.6%** | Multi-hop evidence coverage |
| **Hard Negative Avoidance** | **1** distractor hits | Minimal distractor interference |
| **Decision Accuracy** | **67.3%** | `answer`, `clarify`, `escalate`, `refuse` |
| **Abstention Accuracy on Unanswerable** | **100.0%** | Refuses/escalates when info absent |
| **Fact Match Rate (`must_include`)** | **55.2%** | Factual adherence |
| **Prohibited Claim Violations (`must_not_include`)** | **0** | Zero hallucinated forbidden claims |

---

## 2. Sample Evaluations

### Supported Questions (Grounded Accuracy)

#### [PQ0002] SKU ELE-0012 pe ZentroMart Assured hai kya? Claim kaise karein?
- **Intent / Language:** `warranty` (`hi-en`)
- **Retrieved Sections:** `POL-WAR-INTRO, WAR-2, HLP-TRB-INTRO, products.csv:ELE-0012`
- **Gold Evidence:** `WAR-2, products.csv:ELE-0012`
- **Decision:** `answer` (Expected: `answer`)
- **Answer:** Haan, SKU ELE-0012 (Kestrel K7 Smartphone 128 GB, Beige) par ZentroMart Assured hai! Iska claim karne ke liye, aap app mein 'My Orders' ke andar jaakar claim raise kar sakte hain, jiske baad ZentroMart pickup aur repair ya replacement ki vyavastha karega.
- **Reference Answer:** Haan, 12 mahine ki Assured warranty hai; claim app mein My Orders se karein.

#### [PQ0003] How fast are refunds to the ZentroMart Wallet?
- **Intent / Language:** `refund_timeline` (`en`)
- **Retrieved Sections:** `PAY-4, REF-2, REF-3, MKS-2`
- **Gold Evidence:** `REF-2, KB-00.1`
- **Decision:** `answer` (Expected: `answer`)
- **Answer:** Refunds to the ZentroMart Wallet are instant, processed within 2 hours.
- **Reference Answer:** Instant, within 2 hours of initiation.

#### [PQ0005] SKU ELE-0002 pe ZentroMart Assured hai kya? Claim kaise karein?
- **Intent / Language:** `warranty` (`hi-en`)
- **Retrieved Sections:** `products.csv:ELE-0002, WAR-2, HLP-TRB-INTRO, POL-WAR-INTRO`
- **Gold Evidence:** `WAR-2, products.csv:ELE-0002`
- **Decision:** `answer` (Expected: `answer`)
- **Answer:** Haan, SKU ELE-0002 (Nimbus X2 Wireless Earbuds) par ZentroMart Assured available hai. Iske antargat 12-month ki ZentroMart Assured warranty milti hai. Claim karne ke liye aapko ZentroMart app mein 'My Orders' section mein jaakar claim raise karna hoga, jiske baad ZentroMart pickup arrange karke repair ya replacement ki suvidha pradan karega.
- **Reference Answer:** Haan, 12 mahine ki Assured warranty hai; claim app mein My Orders se karein.

### Unanswerable / Out-of-Scope Questions (Abstention Verification)

#### [PQ0004] Can I schedule a delivery at midnight?
- **Intent / Language:** `unsupported` (`en`)
- **Retrieved Sections:** `DEL-1, CAN-2, FAQ-4, FAQ-2`
- **Decision:** `refuse` (Abstained: `True`)
- **Answer:** I'm sorry, but the information regarding whether you can schedule a delivery at midnight is not found in ZentroMart's knowledge base. Please connect with a human support agent for assistance.

#### [PQ0009] Is there a student discount?
- **Intent / Language:** `unsupported` (`en`)
- **Retrieved Sections:** `PAY-4, DEL-4, REF-4, FAQ-3`
- **Decision:** `refuse` (Abstained: `True`)
- **Answer:** Information regarding a student discount is not found in ZentroMart's knowledge base. Please connect with a human support agent for further assistance.

