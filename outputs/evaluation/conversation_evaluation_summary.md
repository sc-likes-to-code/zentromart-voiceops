# ZentroMart VoiceOps — Phase 3 Multi-Turn Conversation Evaluation Report

**Evaluation Date:** 23 October 2026  
**Total Conversations Evaluated:** 23  
**Total Turns Evaluated:** 96  
**Evaluation Reference:** `dataset/practice/conversations.csv`  

---

## 1. Executive Summary & Benchmark Metrics

| Metric | Result | Standard / Target |
| :--- | :---: | :--- |
| **Conversations Processed** | **23 / 23** | 100% evaluated |
| **Turns Processed** | **96 / 96** | 100% turns evaluated |
| **Decision Accuracy** | **100.0%** | `answer`, `clarify`, `escalate`, `refuse` |
| **Tool Call Accuracy** | **100.0%** | Verification & ticket gateway adherence |
| **Fact Match Rate (`must_include`)** | **97.6%** | Precision of policy & order facts |
| **Prohibited Claim Violations (`must_not_include`)** | **0** | Zero unauthorized disclosures / promises |

---

## 2. Scenario Highlights

### [PC002] Scenario: `high_value_damage` (4 turns)

- **Turn 1** (Decision: `clarify`, Expected: `clarify`)
  - **Customer:** Hello, mujhe order ke baare mein help chahiye.
  - **Agent:** Hello! I am ZentroMart's AI assistant. I can help you with order updates, returns, refunds, or general policies. Could you please share your 8-digit order number (order ID)?
- **Turn 2** (Decision: `clarify`, Expected: `clarify`)
  - **Customer:** Order number hai 8978 2837.
  - **Agent:** I have located order 89782837. For your privacy and account security, please verify your identity by providing either the last 4 digits of your registered phone number or the delivery pincode for this order.
  - **Tool Executed:** `lookup_order(order_id=89782837)`
- **Turn 3** (Decision: `answer`, Expected: `answer`)
  - **Customer:** Last four digits 4533 hain.
  - **Agent:** Thank you for verifying, Kabir. Your order 89782837 has been verified. It was delivered on 2026-10-15 (status: delivered). How can I assist you with it today?
  - **Tool Executed:** `lookup_order(order_id=89782837, verification_value=4533)`
- **Turn 4** (Decision: `escalate`, Expected: `escalate`)
  - **Customer:** Maine Zentro Vista 43-inch 4K Smart TV damage report kiya tha. Abhi replacement approve kar do na?
  - **Agent:** For damaged items valued over ₹10,000, review is handled by our Priority Resolution team. I have logged ticket TKT37fc5e9fab0c4fb5a812b1267e746fd5 and our colleague will contact you directly.
  - **Tool Executed:** `create_ticket()`

### [PC003] Scenario: `return_eligibility` (5 turns)

- **Turn 1** (Decision: `clarify`, Expected: `clarify`)
  - **Customer:** Hello, mujhe order ke baare mein help chahiye.
  - **Agent:** Hello! I am ZentroMart's AI assistant. I can help you with order updates, returns, refunds, or general policies. Could you please share your 8-digit order number (order ID)?
- **Turn 2** (Decision: `clarify`, Expected: `clarify`)
  - **Customer:** Order number hai 1859 9253.
  - **Agent:** I have located order 18599253. For your privacy and account security, please verify your identity by providing either the last 4 digits of your registered phone number or the delivery pincode for this order.
  - **Tool Executed:** `lookup_order(order_id=18599253)`
- **Turn 3** (Decision: `answer`, Expected: `answer`)
  - **Customer:** Last four digits 4265 hain.
  - **Agent:** Thank you for verifying, Meera. Your order 18599253 has been verified. It was delivered on 2026-10-12 (status: delivered). How can I assist you with it today?
  - **Tool Executed:** `lookup_order(order_id=18599253, verification_value=4265)`
- **Turn 4** (Decision: `answer`, Expected: `answer`)
  - **Customer:** Kya main Kaafi Running Sneakers return kar sakti hoon?
  - **Agent:** Haan, aap ise 27 October 2026 (2026-10-27) tak return kar sakte hain. Plus membership ke chalte reverse pickup fee free hai.
- **Turn 5** (Decision: `answer`, Expected: `answer`)
  - **Customer:** Aur refund kitne din mein aayega?
  - **Agent:** Aapka refund instant, within 2 hours (तुरंत / 2 ghante) mein aapke account mein transfer ho jayega.

### [PC004] Scenario: `return_eligibility` (5 turns)

- **Turn 1** (Decision: `clarify`, Expected: `clarify`)
  - **Customer:** नमस्ते, मुझे अपने ऑर्डर के बारे में मदद चाहिए।
  - **Agent:** नमस्ते! मैं ज़ेंट्रोमार्ट का एआई सहायक (AI assistant) हूँ। मैं आपके ऑर्डर या किसी अन्य सवाल में आपकी क्या मदद कर सकता हूँ? कृपया अपना 8 अंकों का ऑर्डर नंबर (order ID) बताएं।
- **Turn 2** (Decision: `clarify`, Expected: `clarify`)
  - **Customer:** ऑर्डर नंबर है 7936 3550।
  - **Agent:** ऑर्डर संख्या 79363550 मिल गया है। आपकी सुरक्षा और गोपनीयता के लिए, कृपया सत्यापन हेतु अपने पंजीकृत फ़ोन नंबर के आख़िरी 4 अंक (last 4 digits) या इस ऑर्डर का डिलीवरी पिनकोड (delivery pincode) बताएं।
  - **Tool Executed:** `lookup_order(order_id=79363550)`
- **Turn 3** (Decision: `answer`, Expected: `answer`)
  - **Customer:** आख़िरी चार अंक 2949 हैं।
  - **Agent:** सत्यापन सफल रहा, धन्यवाद Harini! आपके ऑर्डर 79363550 की स्थिति delivered है। It was delivered on 2026-10-14 (status: delivered). मैं आपकी क्या सहायता कर सकता हूँ?
  - **Tool Executed:** `lookup_order(order_id=79363550, verification_value=2949)`
- **Turn 4** (Decision: `answer`, Expected: `answer`)
  - **Customer:** क्या मैं UrbanThread Slim Fit Jeans वापस कर सकती हूँ?
  - **Agent:** हाँ, आप इसे 13 November 2026 (2026-11-13) तक वापस कर सकते हैं। रिवर्स पिकअप शुल्क ₹49 लागू होगा।
- **Turn 5** (Decision: `answer`, Expected: `answer`)
  - **Customer:** और रिफ़ंड कितने दिन में आएगा?
  - **Agent:** रिफ़ंड की राशि 1 to 3 business days (1 से 3 कार्यदिवस) में आपके मूल भुगतान खाते में आ जाएगी।

### [PC005] Scenario: `human_requested` (4 turns)

- **Turn 1** (Decision: `clarify`, Expected: `clarify`)
  - **Customer:** नमस्ते, मुझे अपने ऑर्डर के बारे में मदद चाहिए।
  - **Agent:** नमस्ते! मैं ज़ेंट्रोमार्ट का एआई सहायक (AI assistant) हूँ। मैं आपके ऑर्डर या किसी अन्य सवाल में आपकी क्या मदद कर सकता हूँ? कृपया अपना 8 अंकों का ऑर्डर नंबर (order ID) बताएं।
- **Turn 2** (Decision: `clarify`, Expected: `clarify`)
  - **Customer:** ऑर्डर नंबर है 3711 3676।
  - **Agent:** ऑर्डर संख्या 37113676 मिल गया है। आपकी सुरक्षा और गोपनीयता के लिए, कृपया सत्यापन हेतु अपने पंजीकृत फ़ोन नंबर के आख़िरी 4 अंक (last 4 digits) या इस ऑर्डर का डिलीवरी पिनकोड (delivery pincode) बताएं।
  - **Tool Executed:** `lookup_order(order_id=37113676)`
- **Turn 3** (Decision: `answer`, Expected: `answer`)
  - **Customer:** आख़िरी चार अंक 1581 हैं।
  - **Agent:** सत्यापन सफल रहा, धन्यवाद Kavya! आपके ऑर्डर 37113676 की स्थिति delivered है। It was delivered on 2026-06-18 (status: delivered). मैं आपकी क्या सहायता कर सकता हूँ?
  - **Tool Executed:** `lookup_order(order_id=37113676, verification_value=1581)`
- **Turn 4** (Decision: `escalate`, Expected: `escalate`)
  - **Customer:** क्या मैं किसी इंसान से बात कर सकती हूँ?
  - **Agent:** मैंने आपकी सहायता के लिए हमारे सहयोगी (colleague) से बात कराने हेतु टिकट (ticket) TKT950743799b8540cabecfd79e284cf42b बना दिया है। हमारी टीम जल्द ही आपसे जुड़ेगी।
  - **Tool Executed:** `create_ticket()`

### [PC006] Scenario: `human_requested` (4 turns)

- **Turn 1** (Decision: `clarify`, Expected: `clarify`)
  - **Customer:** Hi, I need some help with an order.
  - **Agent:** Hello! I am ZentroMart's AI assistant. I can help you with order updates, returns, refunds, or general policies. Could you please share your 8-digit order number (order ID)?
- **Turn 2** (Decision: `clarify`, Expected: `clarify`)
  - **Customer:** The order number is 6649 2475.
  - **Agent:** I have located order 66492475. For your privacy and account security, please verify your identity by providing either the last 4 digits of your registered phone number or the delivery pincode for this order.
  - **Tool Executed:** `lookup_order(order_id=66492475)`
- **Turn 3** (Decision: `answer`, Expected: `answer`)
  - **Customer:** The last four digits are 6073.
  - **Agent:** Thank you for verifying, Farhan. Your order 66492475 has been verified. It was delivered on 2026-10-06 (status: delivered). How can I assist you with it today?
  - **Tool Executed:** `lookup_order(order_id=66492475, verification_value=6073)`
- **Turn 4** (Decision: `escalate`, Expected: `escalate`)
  - **Customer:** Actually, can I just speak to a person?
  - **Agent:** I have connected you with our human support team under ticket ID TKTd282b1fba8f44e3a82afa969b53e76c9. A colleague will reach out to you shortly.
  - **Tool Executed:** `create_ticket()`

