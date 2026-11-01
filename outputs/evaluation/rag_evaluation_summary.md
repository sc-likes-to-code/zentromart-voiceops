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
| **Retrieval Recall@k (Any Gold Evidence)** | **100.0%** | Evidence discovery |
| **Full Retrieval Accuracy (All Evidence)** | **84.6%** | Multi-hop evidence coverage |
| **Hard Negative Avoidance** | **1** distractor hits | Minimal distractor interference |
| **Decision Accuracy** | **100.0%** | `answer`, `clarify`, `escalate`, `refuse` |
| **Abstention Accuracy on Unanswerable** | **100.0%** | Refuses/escalates when info absent |
| **Fact Match Rate (`must_include`)** | **84.5%** | Factual adherence |
| **Prohibited Claim Violations (`must_not_include`)** | **0** | Zero hallucinated forbidden claims |

---

## 2. Sample Evaluations

### Supported Questions (Grounded Accuracy)

#### [PQ0002] SKU ELE-0012 pe ZentroMart Assured hai kya? Claim kaise karein?
- **Intent / Language:** `warranty` (`hi-en`)
- **Retrieved Sections:** `products.csv:ELE-0012, WAR-1, MKS-3, WAR-2`
- **Gold Evidence:** `WAR-2, products.csv:ELE-0012`
- **Decision:** `answer` (Expected: `answer`)
- **Answer:** Haan, SKU ELE-0012 (Kestrel K7 Smartphone) par ZentroMart Assured upalabdh hai! ZentroMart Assured warranty claim karne ke liye, aapko app mein 'My Orders' section mein jaana hoga, jahan ZentroMart pickup aur repair ya replacement ki vyavastha karta hai.
- **Reference Answer:** Haan, 12 mahine ki Assured warranty hai; claim app mein My Orders se karein.

#### [PQ0003] How fast are refunds to the ZentroMart Wallet?
- **Intent / Language:** `refund_timeline` (`en`)
- **Retrieved Sections:** `REF-2, KB-00.1, WAR-2, REF-3`
- **Gold Evidence:** `REF-2, KB-00.1`
- **Decision:** `answer` (Expected: `answer`)
- **Answer:** Refunds to the ZentroMart Wallet are instant and are processed within 2 hours of initiation.
- **Reference Answer:** Instant, within 2 hours of initiation.

#### [PQ0005] SKU ELE-0002 pe ZentroMart Assured hai kya? Claim kaise karein?
- **Intent / Language:** `warranty` (`hi-en`)
- **Retrieved Sections:** `MKS-3, WAR-1, products.csv:ELE-0002, WAR-2`
- **Gold Evidence:** `WAR-2, products.csv:ELE-0002`
- **Decision:** `answer` (Expected: `answer`)
- **Answer:** Haan, SKU ELE-0002 (Nimbus X2 Wireless Earbuds) par ZentroMart Assured uplabdh hai (ZentroMart Assured: Yes). Iske antargat delivery ki date se 12 mahine ki ZentroMart Assured warranty milti hai. Claim karne ke liye aap app mein 'My Orders' section mein jaakar claim raise kar sakte hain, jiske baad ZentroMart pickup arrange karke repair ya replacement ki suvidha deta hai.
- **Reference Answer:** Haan, 12 mahine ki Assured warranty hai; claim app mein My Orders se karein.

### Unanswerable / Out-of-Scope Questions (Abstention Verification)

#### [PQ0004] Can I schedule a delivery at midnight?
- **Intent / Language:** `unsupported` (`en`)
- **Retrieved Sections:** `FAQ-4, CAN-2, DEL-1, FAQ-2`
- **Decision:** `answer` (Abstained: `True`)
- **Answer:** ZentroMart does not offer or support midnight delivery. Standard and Express delivery options are available as per our delivery policy.

#### [PQ0009] Is there a student discount?
- **Intent / Language:** `unsupported` (`en`)
- **Retrieved Sections:** `REF-4, DEL-4, FAQ-3, PAY-4`
- **Decision:** `answer` (Abstained: `True`)
- **Answer:** We're sorry, but ZentroMart does not offer or support a student discount.

