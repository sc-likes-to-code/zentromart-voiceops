"""Build script to generate official 4-page report.pdf for ZentroMart VoiceOps.

Uses native headless Chrome to render polished HTML/CSS directly to PDF.
Ensures zero third-party PDF dependencies and exact 4-page pagination.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PDF = PROJECT_ROOT / "report.pdf"
TEMP_HTML = PROJECT_ROOT / "outputs" / "evaluation" / "report_temp.html"

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ZentroMart VoiceOps — Capstone Technical Report</title>
<style>
  @page {
    size: A4 portrait;
    margin: 0;
  }
  * {
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
  body {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1e293b;
    background-color: #ffffff;
    font-size: 8.2pt;
    line-height: 1.32;
  }
  .page {
    width: 210mm;
    height: 297mm;
    max-height: 297mm;
    overflow: hidden;
    padding: 12mm 15mm 12mm 15mm;
    page-break-after: always;
    position: relative;
    background: #ffffff;
  }
  .page:last-child {
    page-break-after: avoid;
  }

  /* Header & Footer */
  .page-header {
    border-bottom: 1.5px solid #0284c7;
    padding-bottom: 4px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }
  .page-header .brand {
    font-size: 8pt;
    font-weight: 700;
    color: #0369a1;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .page-header .milestone {
    font-size: 7.5pt;
    color: #64748b;
  }
  .page-footer {
    position: absolute;
    bottom: 8mm;
    left: 15mm;
    right: 15mm;
    border-top: 1px solid #e2e8f0;
    padding-top: 4px;
    display: flex;
    justify-content: space-between;
    font-size: 7pt;
    color: #64748b;
  }

  /* Typography */
  h1 {
    font-size: 15pt;
    margin: 0 0 4px 0;
    color: #0f172a;
    font-weight: 800;
    letter-spacing: -0.3px;
  }
  .sub-title {
    font-size: 9pt;
    color: #475569;
    margin: 0 0 10px 0;
    font-weight: 500;
  }
  h2 {
    font-size: 10.5pt;
    margin: 10px 0 5px 0;
    color: #0369a1;
    font-weight: 700;
    border-bottom: 1px solid #e0f2fe;
    padding-bottom: 2px;
  }
  h3 {
    font-size: 8.8pt;
    margin: 6px 0 3px 0;
    color: #0f172a;
    font-weight: 700;
  }
  p {
    margin: 0 0 5px 0;
    text-align: justify;
  }

  /* Badges & Metadata Box */
  .meta-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 6px 8px;
    margin-bottom: 8px;
    gap: 4px;
  }
  .meta-item {
    font-size: 7.2pt;
  }
  .meta-label {
    font-weight: 700;
    color: #475569;
    text-transform: uppercase;
    display: block;
    font-size: 6.5pt;
  }
  .meta-val {
    color: #0f172a;
    font-weight: 600;
  }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 5px 0 8px 0;
    font-size: 7.6pt;
  }
  th, td {
    padding: 3.5px 6px;
    border: 1px solid #cbd5e1;
    text-align: left;
  }
  th {
    background-color: #f1f5f9;
    color: #1e293b;
    font-weight: 700;
  }
  tr:nth-child(even) td {
    background-color: #f8fafc;
  }
  .text-center { text-align: center; }
  .text-right { text-align: right; }
  .font-mono { font-family: Consolas, monospace; font-size: 7.2pt; }
  .badge-pass {
    display: inline-block;
    background-color: #dcfce7;
    color: #15803d;
    padding: 1px 4px;
    border-radius: 3px;
    font-weight: 700;
    font-size: 7pt;
  }

  /* Visual Architecture Diagram */
  .diag-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
    margin: 5px 0 7px 0;
  }
  .diag-node {
    width: 100%;
    border-radius: 4px;
    padding: 3.5px 8px;
    text-align: center;
    border: 1px solid #cbd5e1;
    background: #ffffff;
  }
  .diag-node .node-title {
    font-weight: 700;
    font-size: 7.6pt;
    letter-spacing: -0.1px;
  }
  .diag-node .node-sub {
    font-size: 6.8pt;
    color: #475569;
    margin-top: 1px;
  }
  .node-input {
    background: #f8fafc;
    border-color: #94a3b8;
  }
  .node-input .node-title { color: #1e293b; }
  .node-speech {
    background: #faf5ff;
    border-color: #d8b4fe;
  }
  .node-speech .node-title { color: #6b21a8; }
  .node-output {
    background: #f0fdfa;
    border-color: #99f6e4;
  }
  .node-output .node-title { color: #0f766e; }

  .diag-arrow {
    text-align: center;
    font-size: 7.5pt;
    font-weight: 700;
    color: #0284c7;
    line-height: 1.15;
    margin: 1px 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
  }
  .diag-arrow span {
    font-size: 6.5pt;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }

  .diag-agent-box {
    width: 100%;
    border: 1.5px solid #0284c7;
    border-radius: 4px;
    background: #ffffff;
    overflow: hidden;
  }
  .agent-header {
    background: #0284c7;
    color: #ffffff;
    padding: 3px 8px;
    font-size: 7.4pt;
    font-weight: 700;
    text-align: center;
    letter-spacing: 0.2px;
  }
  .agent-branches {
    display: flex;
    gap: 6px;
    padding: 5px;
    background: #f8fafc;
  }
  .branch {
    flex: 1;
    padding: 4px 6px;
    border-radius: 3px;
    font-size: 6.9pt;
  }
  .branch-order {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
  }
  .branch-order .branch-title {
    color: #1d4ed8;
  }
  .branch-rag {
    background: #ecfeff;
    border: 1px solid #a5f3fc;
  }
  .branch-rag .branch-title {
    color: #0e7490;
  }
  .branch-title {
    font-weight: 700;
    font-size: 7.2pt;
    margin-bottom: 3px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    border-bottom: 1px solid rgba(0,0,0,0.08);
    padding-bottom: 2px;
  }
  .branch ul {
    margin: 0;
    padding-left: 12px;
  }
  .branch li {
    margin-bottom: 2px;
    line-height: 1.25;
  }

  /* Callout Boxes */
  .callout {
    border-left: 3px solid #0284c7;
    background-color: #f0f9ff;
    padding: 5px 8px;
    margin: 5px 0 7px 0;
    font-size: 7.6pt;
  }
  .callout-warning {
    border-left-color: #f59e0b;
    background-color: #fffbeb;
  }

  /* Two Column Layout */
  .row {
    display: flex;
    gap: 10px;
    margin-bottom: 6px;
  }
  .col-2 {
    flex: 1;
  }
  ul {
    margin: 0 0 5px 0;
    padding-left: 15px;
  }
  li {
    margin-bottom: 2.5px;
  }
</style>
</head>
<body>

<!-- ====================================================================== -->
<!-- PAGE 1: PROJECT OVERVIEW & ARCHITECTURE                                 -->
<!-- ====================================================================== -->
<div class="page">
  <div class="page-header">
    <div class="brand">IIT Guwahati × Gnani.ai TOKENS→TRANSFORMERS Capstone 2026</div>
    <div class="milestone">Final Technical Submission Report</div>
  </div>

  <h1>ZentroMart VoiceOps: Policy-Grounded Voice Support Assistant</h1>
  <div class="sub-title">A Testable, Multi-Turn RAG and Voice Interface with Local Hybrid Retrieval and Gnani.ai Speech</div>

  <div class="meta-grid">
    <div class="meta-item"><span class="meta-label">Project Location</span><span class="meta-val">E:\\MY PROJECTS\\zentromart-voiceops</span></div>
    <div class="meta-item"><span class="meta-label">LLM Reasoning</span><span class="meta-val">gemini-3.5-flash-lite (temp=0.0)</span></div>
    <div class="meta-item"><span class="meta-label">Speech Provider</span><span class="meta-val">Gnani.ai Exclusive (STT/TTS)</span></div>
    <div class="meta-item"><span class="meta-label">Retrieval Engine</span><span class="meta-val">Hybrid FastEmbed BGE + BM25</span></div>
  </div>

  <h2>1. Project Purpose & High-Stakes E-Commerce Context</h2>
  <p>
    Customer support in modern e-commerce demands instant, accurate, and secure resolutions across voice and text channels. While modern Large Language Models (LLMs) excel at conversational fluency, unconstrained zero-shot models pose critical operational risks in production: they hallucinate return deadlines, disclose private customer order details to unauthenticated callers, miss regional policy revisions, and invent refund timelines.
  </p>
  <p>
    The <strong>ZentroMart VoiceOps</strong> capstone resolves these enterprise challenges by establishing an end-to-end customer support voice pipeline for <em>ZentroMart</em>, a synthetic multi-category Indian e-commerce platform. Grounded in the company's 21 authoritative Markdown policy documents, the system is designed to improve factual grounding, enforce caller privacy boundaries, and establish safe escalation pathways across four structured engineering phases:
  </p>
  <ul>
    <li><strong>Phase 1 (Audit & Environment):</strong> Clean environment isolation (Python 3.10), automated dataset integrity checks, strict data type preservation, and policy precedence rules excluding obsolete documents.</li>
    <li><strong>Phase 2 (Grounded RAG Pipeline):</strong> Hybrid lexical (BM25) and dense semantic vector retrieval (FastEmbed <code>BAAI/bge-small-en-v1.5</code>) with structured Gemini answer generation, explicit section-level citation, and strict abstention when evidence is absent.</li>
    <li><strong>Phase 3 (Multi-Turn Agent & Safety Tools):</strong> Deterministic caller identity verification (last 4 phone digits or delivery pincode), stateful multi-turn history tracking, priority escalations for high-value damages (&gt; ₹10,000), and integration with mock database tools (<code>lookup_order</code>, <code>create_ticket</code>).</li>
    <li><strong>Phase 4 (Gnani.ai Voice Integration):</strong> Exclusive speech integration using the official <code>gnani-vachana</code> SDK for Speech-to-Text (STT <code>/stt/v3</code> with Inverse Text Normalization) and Text-to-Speech (TTS <code>timbre-v2.5</code>, <code>Kaveri</code> voice), producing multi-turn voice conversations with complete on-disk artifact persistence.</li>
  </ul>

  <h2>2. End-to-End System Architecture</h2>
  <p>
    The system follows a strict, defensive decoupled architecture where voice processing, state management, retrieval grounding, and database tools interact across verified boundaries:
  </p>

  <div class="diag-wrapper">
    <div class="diag-node node-input">
      <div class="node-title">1. Customer Voice Audio Input</div>
      <div class="node-sub">Supported Formats: <code>.wav</code>, <code>.m4a</code>, <code>.mp3</code>, <code>.aac</code> (up to 25 MB) &bull; Clean near-field telephony/device recording</div>
    </div>

    <div class="diag-arrow">&darr; <span>Customer Audio Stream</span></div>

    <div class="diag-node node-speech">
      <div class="node-title">2. Gnani.ai Speech-to-Text (<code>/stt/v3</code>)</div>
      <div class="node-sub">Inverse Text Normalization (ITN) converts spoken words to numeric Order IDs, pincodes, and phone numbers</div>
    </div>

    <div class="diag-arrow">&darr; <span>Customer Transcript Text</span></div>

    <div class="diag-agent-box">
      <div class="agent-header">
        3. Multi-Turn Controller (VoiceOpsAgent) &bull; Session Isolation &amp; Strict Domain Intent Routing
      </div>
      <div class="agent-branches">
        <div class="branch branch-order">
          <div class="branch-title">[A] Order &amp; Privacy Gateway</div>
          <ul>
            <li><strong>Identity Verification Gate:</strong> Compares last 4 phone digits or delivery pincode before disclosing private order details.</li>
            <li><strong>Mock Support Tools:</strong> Verified access to <code>lookup_order()</code>; permanent lockout after repeated verification failures.</li>
            <li><strong>Supervisor Escalations:</strong> Auto-executes <code>create_ticket()</code> for damages &gt; ₹10,000 or customer agent requests.</li>
          </ul>
        </div>
        <div class="branch branch-rag">
          <div class="branch-title">[B] Grounded Policy RAG Engine</div>
          <ul>
            <li><strong>Hybrid Retrieval:</strong> Sparse BM25 + dense FastEmbed (<code>BAAI/bge-small-en-v1.5</code>) with score fusion.</li>
            <li><strong>Policy Precedence:</strong> Filtered 21 Markdown files (authoritative <code>pol_returns_v4.md</code>; excluded superseded <code>v3</code>).</li>
            <li><strong>Gemini 3.5 Flash Lite:</strong> Strict evidence grounding, explicit section citations (e.g. <code>[RET-2]</code>), and safe abstention.</li>
          </ul>
        </div>
      </div>
    </div>

    <div class="diag-arrow">&darr; <span>Agent Response Text &amp; Cited Evidence Sources</span></div>

    <div class="diag-node node-speech">
      <div class="node-title">4. Gnani.ai Text-to-Speech (<code>/api/v1/tts/inference</code>)</div>
      <div class="node-sub">Model: <code>timbre-v2.5</code> &bull; Voice: <code>Kaveri</code> &bull; Language: <code>en-IN</code> &bull; Output: 16 kHz Mono Linear PCM WAV</div>
    </div>

    <div class="diag-arrow">&darr; <span>Synthesized Audio &amp; Audit Logs</span></div>

    <div class="diag-node node-output">
      <div class="node-title">5. Production Output Artifacts &amp; Persistence</div>
      <div class="node-sub">Saved per turn: Audio <code>turn_XX_output.wav</code>, Transcript <code>turn_XX_transcript.txt</code>, Response <code>.txt</code>, Metadata <code>.json</code></div>
    </div>
  </div>

  <h2>3. Document Precedence & Superseded-Policy Isolation</h2>
  <p>
    Knowledge integrity is maintained through a strict document hierarchy established in <code>00_about_this_knowledge_base.md</code>. Company policies (<code>POL-*</code>) override help guides (<code>HLP-*</code>) and general FAQs. Crucially, the current return policy <code>pol_returns_v4.md</code> (effective 1 August 2026, establishing a 7-day electronics return window) explicitly supersedes <code>pol_returns_v3_superseded.md</code> (which had a 10-day window). During document ingestion, obsolete policies and unstructured human support logs are strictly filtered out from the retrieval index, preventing stale policy contamination.
  </p>

  <div class="page-footer">
    <span>ZentroMart VoiceOps — Capstone Technical Report</span>
    <span>Page 1 of 4</span>
  </div>
</div>

<!-- ====================================================================== -->
<!-- PAGE 2: IMPLEMENTATION DETAILS & SAFETY SAFEGUARDS                      -->
<!-- ====================================================================== -->
<div class="page">
  <div class="page-header">
    <div class="brand">IIT Guwahati × Gnani.ai TOKENS→TRANSFORMERS Capstone 2026</div>
    <div class="milestone">Implementation &amp; Safety Safeguards</div>
  </div>

  <h2>4. Detailed Implementation by Phase</h2>

  <div class="row">
    <div class="col-2">
      <h3>Phase 1: Environment &amp; Schema Integrity</h3>
      <ul>
        <li><strong>Strict Typing:</strong> All relational identifiers (<code>order_id</code>, <code>customer_id</code>, <code>sku</code>, <code>pincode</code>, <code>phone</code>) are enforced as strings (<code>dtype=str</code>) to preserve leading zeros.</li>
        <li><strong>Fixed Operational Date:</strong> Evaluated strictly against the reference anchor date of <strong>20 October 2026</strong>.</li>
        <li><strong>Calendar Exclusions:</strong> Business-day SLA timelines exclude Sundays and the 4 gazetted holidays in <code>holidays.csv</code>.</li>
        <li><strong>Offline Validation:</strong> <code>validate_dataset.py</code> executes offline with zero network dependencies.</li>
      </ul>

      <h3>Phase 2: Hybrid Grounded RAG</h3>
      <ul>
        <li><strong>Chunking:</strong> 21 Markdown files chunked into 69 discrete passages, preserving frontmatter metadata and section IDs.</li>
        <li><strong>Hybrid Fusion:</strong> Combines sparse BM25 scoring with dense embeddings from <code>BAAI/bge-small-en-v1.5</code> via FastEmbed.</li>
        <li><strong>JSON Generation:</strong> Grounded responses structured with decision (<code>answer</code>, <code>clarify</code>, <code>escalate</code>, <code>refuse</code>), citation list, and evidence flag.</li>
      </ul>
    </div>

    <div class="col-2">
      <h3>Phase 3: Multi-Turn Agent &amp; Safety Gates</h3>
      <ul>
        <li><strong>Session Isolation:</strong> Independent <code>ConversationState</code> tracks turn count, verification status, and order data per session.</li>
        <li><strong>Identity Verification Gate:</strong> Unverified callers cannot access order details; must supply registered phone suffix or pincode.</li>
        <li><strong>Automatic Lockout:</strong> Callers exceeding verification attempts are securely locked out and referred to support.</li>
        <li><strong>Ticketing Gateway:</strong> Automatically invokes <code>create_ticket</code> for damaged goods &gt; ₹10,000 or customer agent requests.</li>
      </ul>

      <h3>Phase 4: Exclusive Gnani.ai Voice Pipeline</h3>
      <ul>
        <li><strong>Sole Provider:</strong> Pure Gnani.ai implementation; zero third-party speech engines (Whisper, ElevenLabs, Google Speech).</li>
        <li><strong>Audio Ingestion:</strong> Supports <code>.wav</code>, <code>.mp3</code>, <code>.m4a</code>, <code>.aac</code> up to 25 MB with automatic ITN conversion.</li>
        <li><strong>Synthesis &amp; Logging:</strong> High-quality 16 kHz WAV synthesis via <code>timbre-v2.5</code> (voice: Kaveri), writing JSON metadata per turn.</li>
      </ul>
    </div>
  </div>

  <h2>5. Privacy &amp; Operational Safety Safeguards</h2>
  <p>
    The assistant enforces defense-in-depth safety boundaries to ensure enterprise compliance and data protection:
  </p>
  <ul>
    <li><strong>PII Boundary &amp; No-Leak Policy:</strong> Customer phone numbers, email addresses, and payment credentials are never recited by the model. Under no circumstances are full phone numbers disclosed (e.g. PQ0060 refusal test).</li>
    <li><strong>Pre-Verification Information Gate:</strong> When an unverified caller supplies an order ID, the model confirms receipt of the ID but conceals customer names, items, delivery dates, and amounts until verified.</li>
    <li><strong>High-Value Damage Escalation:</strong> Damaged items exceeding ₹10,000 (such as the Zentro Vista 43" 4K TV) trigger mandatory supervisor ticket creation without premature agent replacement promises.</li>
    <li><strong>Strict Grounded Abstention:</strong> If retrieved document chunks do not explicitly corroborate a policy claim, the model abstains (decision: <code>refuse</code> or <code>escalate</code>) rather than fabricating standard retail practices.</li>
  </ul>

  <h2>6. Automated Test Suite &amp; Dataset Validation Results</h2>
  <p>
    The repository incorporates comprehensive regression and unit testing across every subsystem, executed via <code>pytest</code> and the offline dataset validation harness. All checks pass cleanly:
  </p>

  <table>
    <thead>
      <tr>
        <th>Verification Suite</th>
        <th>Target Component</th>
        <th>Tests / Entities</th>
        <th>Result</th>
        <th>Key Coverage &amp; Safeguards Verified</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>dataset/validate_dataset.py</strong></td>
        <td>Dataset Integrity</td>
        <td>9 CSVs | 21 KBs | 1,000 Orders</td>
        <td><span class="badge-pass">PASS (Exit 0)</span></td>
        <td>Relational foreign keys, order arithmetic, pincode coverage, and document structure.</td>
      </tr>
      <tr>
        <td><strong>tests/test_agent.py</strong></td>
        <td>Agent &amp; Verification</td>
        <td>11 unit tests</td>
        <td><span class="badge-pass">11 / 11 PASS</span></td>
        <td>Caller verification gate, lockout after retries, high-value escalation, ticket logging.</td>
      </tr>
      <tr>
        <td><strong>tests/test_answering.py</strong></td>
        <td>Grounded Answering</td>
        <td>7 unit tests</td>
        <td><span class="badge-pass">7 / 7 PASS</span></td>
        <td>Evidence prompt assembly, JSON fallback resilience, abstention on zero evidence.</td>
      </tr>
      <tr>
        <td><strong>tests/test_baseline.py</strong></td>
        <td>Step 1 Evaluator</td>
        <td>10 unit tests</td>
        <td><span class="badge-pass">10 / 10 PASS</span></td>
        <td>Text normalization, fact matching, prohibited claim detection, mocked Gemini calls.</td>
      </tr>
      <tr>
        <td><strong>tests/test_ingestion.py</strong></td>
        <td>Ingestion &amp; Chunking</td>
        <td>5 unit tests</td>
        <td><span class="badge-pass">5 / 5 PASS</span></td>
        <td>Frontmatter extraction, policy v4 inclusion, explicit exclusion of superseded policy v3.</td>
      </tr>
      <tr>
        <td><strong>tests/test_retrieval.py</strong></td>
        <td>Hybrid Retrieval</td>
        <td>5 unit tests</td>
        <td><span class="badge-pass">5 / 5 PASS</span></td>
        <td>BM25 index persistence, vector search recall, top-k ranking, query sanitation.</td>
      </tr>
      <tr>
        <td><strong>tests/test_voice.py</strong></td>
        <td>Gnani Voice Pipeline</td>
        <td>17 unit tests</td>
        <td><span class="badge-pass">17 / 17 PASS</span></td>
        <td>STT/TTS error handling, multi-turn state preservation, AST exclusivity audit (Gnani only).</td>
      </tr>
      <tr>
        <td><strong>tests/test_cli.py</strong></td>
        <td>CLI Console Interface</td>
        <td>1 unit test</td>
        <td><span class="badge-pass">1 / 1 PASS</span></td>
        <td>One-shot query execution, parameter parsing, stdout rendering.</td>
      </tr>
      <tr>
        <td><strong>Total Automated Test Suite</strong></td>
        <td><strong>Complete Codebase</strong></td>
        <td><strong>56 Pytest Tests</strong></td>
        <td><span class="badge-pass">56 / 56 PASS (2.43s)</span></td>
        <td><strong>Zero failures, zero regressions across all four implementation phases.</strong></td>
      </tr>
    </tbody>
  </table>

  <div class="callout">
    <strong>Static Security AST Audit:</strong> <code>test_exclusive_gnani_speech_provider</code> analyzes the abstract syntax tree of the entire codebase to confirm that no non-Gnani speech packages (such as whisper, elevenlabs, or google-cloud-speech) are imported or referenced.
  </div>

  <div class="page-footer">
    <span>ZentroMart VoiceOps — Capstone Technical Report</span>
    <span>Page 2 of 4</span>
  </div>
</div>

<!-- ====================================================================== -->
<!-- PAGE 3: STEP 1 VS STEP 2 EVALUATION BENCHMARK                           -->
<!-- ====================================================================== -->
<div class="page">
  <div class="page-header">
    <div class="brand">IIT Guwahati × Gnani.ai TOKENS→TRANSFORMERS Capstone 2026</div>
    <div class="milestone">Step 1 vs. Step 2 Empirical Benchmark</div>
  </div>

  <h2>7. Empirical Benchmark: Step 1 Baseline vs. Step 2 Grounded RAG</h2>
  <p>
    To rigorously measure the value of retrieval grounding, both systems were benchmarked against all 52 standardized practice questions in <code>dataset/practice/questions.csv</code>. Both evaluations utilized the exact same model (<code>gemini-3.5-flash-lite</code>), identical decoding parameters (<code>temperature=0.0</code>), and deterministic regex fact scoring.
  </p>

  <table>
    <thead>
      <tr>
        <th>Evaluation Metric</th>
        <th>Step 1: Prompt-Only Baseline</th>
        <th>Step 2: Grounded Hybrid RAG</th>
        <th>Absolute Delta</th>
        <th>Evaluation Role &amp; Significance</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Questions Evaluated</strong></td>
        <td class="text-center"><strong>52 / 52</strong></td>
        <td class="text-center"><strong>52 / 52</strong></td>
        <td class="text-center">0</td>
        <td>Sample completeness across diverse e-commerce intents.</td>
      </tr>
      <tr>
        <td><strong>Execution / API Errors</strong></td>
        <td class="text-center"><strong>0</strong></td>
        <td class="text-center"><strong>0</strong></td>
        <td class="text-center">0</td>
        <td>Execution reliability with exponential rate-limit backoff.</td>
      </tr>
      <tr>
        <td><strong>Retrieval Recall@4 (Any Gold)</strong></td>
        <td class="text-center"><em>N/A (No Retrieval)</em></td>
        <td class="text-center"><strong>82.7%</strong></td>
        <td class="text-center"><em>N/A</em></td>
        <td>Rate at which at least one relevant gold document is retrieved.</td>
      </tr>
      <tr>
        <td><strong>Full Retrieval Accuracy (All Gold)</strong></td>
        <td class="text-center"><em>N/A (No Retrieval)</em></td>
        <td class="text-center"><strong>34.6%</strong></td>
        <td class="text-center"><em>N/A</em></td>
        <td>Multi-hop coverage where 100% of gold sources are retrieved.</td>
      </tr>
      <tr>
        <td><strong>Hard Negative Distractor Hits</strong></td>
        <td class="text-center"><em>N/A (No Retrieval)</em></td>
        <td class="text-center"><strong>1</strong></td>
        <td class="text-center"><em>N/A</em></td>
        <td>Frequency of retrieving superseded policy v3 documents.</td>
      </tr>
      <tr>
        <td><strong>Decision Accuracy</strong></td>
        <td class="text-center"><strong>86.5%</strong></td>
        <td class="text-center"><strong>67.3%</strong></td>
        <td class="text-center"><strong>-19.2 pp</strong></td>
        <td>Categorical alignment: <code>answer</code>, <code>clarify</code>, <code>escalate</code>, <code>refuse</code>.</td>
      </tr>
      <tr>
        <td><strong>Unanswerable Abstention Accuracy</strong></td>
        <td class="text-center"><strong>20.0%</strong></td>
        <td class="text-center"><strong>100.0%</strong></td>
        <td class="text-center"><strong>+80.0 pp</strong></td>
        <td>Clean refusal on out-of-scope queries (e.g. midnight delivery).</td>
      </tr>
      <tr>
        <td><strong>Fact Match Rate (<code>must_include</code>)</strong></td>
        <td class="text-center"><strong>39.7%</strong></td>
        <td class="text-center"><strong>55.2%</strong></td>
        <td class="text-center"><strong>+15.5 pp</strong></td>
        <td>Adherence to company numbers, timelines, and procedures.</td>
      </tr>
      <tr>
        <td><strong>Prohibited Claim Violations (<code>must_not_include</code>)</strong></td>
        <td class="text-center"><strong>0</strong></td>
        <td class="text-center"><strong>0</strong></td>
        <td class="text-center">0</td>
        <td>Explicit violations of forbidden customer guarantees.</td>
      </tr>
    </tbody>
  </table>

  <h2>8. Critical Analysis of Measured Gains and Losses</h2>

  <h3>A. Factual Grounding Gain (+15.5 pp Fact Match Rate)</h3>
  <p>
    In Step 1, the prompt-only baseline achieved only <strong>39.7%</strong> precision on required facts. Lacking access to ZentroMart's internal documents, the baseline was forced to invent generic e-commerce assumptions or omit vital operational details. For example, in <strong>[PQ0002]</strong> (<em>"SKU ELE-0012 pe ZentroMart Assured hai kya? Claim kaise karein?"</em>), the baseline escalated because it lacked catalog data. In contrast, Step 2 Grounded RAG retrieved <code>WAR-2</code> and <code>products.csv:ELE-0012</code>, providing a 100% complete answer citing the 12-month Assured warranty and app claim procedure (+15.5 pp overall).
  </p>

  <h3>B. Hallucination Suppression &amp; Abstention (+80.0 pp Abstention Accuracy)</h3>
  <p>
    On queries outside the knowledge base, the Step 1 baseline exhibited classic ungrounded hallucination, achieving only <strong>20.0%</strong> abstention. For instance, in <strong>[PQ0004]</strong> (<em>"Can I schedule a delivery at midnight?"</em>), the baseline fabricated plausible-sounding operational hours: <em>"Our standard delivery hours are between 8:00 AM and 9:00 PM."</em> In Step 2 Grounded RAG, the model verified that midnight delivery was unsupported by retrieved chunks and cleanly refused (<strong>100.0% abstention</strong>), protecting the business from unfulfillable commitments.
  </p>

  <h3>C. Explaining the Step 2 Decision Accuracy Tradeoff (-19.2 pp)</h3>
  <p>
    The Step 2 system exhibited a measured decrease in categorical decision accuracy (<strong>67.3%</strong> vs. <strong>86.5%</strong> in baseline). Detailed error analysis reveals the architectural cause: the baseline model aggressively defaulted to <code>answer</code> for almost every prompt, which artificially matched the practice dataset's predominantly <code>answer</code>-labeled benchmark. In contrast, Step 2 RAG applied strict evidence-sufficiency gating: whenever retrieval was incomplete, the grounded generator conservatively produced <code>escalate</code> or <code>clarify</code>. While technically safer, this conservative behavior was penalized as a decision mismatch under strict automated evaluation.
  </p>

  <h3>D. Incomplete Multi-Hop Evidence Coverage (34.6% Full Retrieval Accuracy)</h3>
  <p>
    While single-document discovery was strong (<strong>Recall@4 of 82.7%</strong>), <strong>Full Retrieval Accuracy</strong> (capturing 100% of gold sources across multi-hop queries) was <strong>34.6%</strong>. Complex inquiries requiring simultaneous facts from both a specific product row (e.g. <code>products.csv:ELE-0002</code>) and a general policy section (e.g. <code>WAR-2</code>) frequently had one chunk crowded out of the top-4 search window.
  </p>

  <div class="callout callout-warning">
    <strong>Scope of Prohibited Claim Metric:</strong> Both models recorded <strong>0 violations</strong> on the <code>must_not_include</code> test set under temperature 0.0. This metric confirms adherence on the 52 evaluated benchmark scenarios, but should not be misconstrued as a theoretical guarantee of zero hallucinations across arbitrary inputs.
  </div>

  <div class="page-footer">
    <span>ZentroMart VoiceOps — Capstone Technical Report</span>
    <span>Page 3 of 4</span>
  </div>
</div>

<!-- ====================================================================== -->
<!-- PAGE 4: VOICE VALIDATION, LIMITATIONS & ROADMAP                         -->
<!-- ====================================================================== -->
<div class="page">
  <div class="page-header">
    <div class="brand">IIT Guwahati × Gnani.ai TOKENS→TRANSFORMERS Capstone 2026</div>
    <div class="milestone">Voice Validation, Limitations &amp; Roadmap</div>
  </div>

  <h2>9. Live Voice Pipeline Validation with Gnani.ai</h2>
  <p>
    Live voice integration was validated through both a stateful three-turn caller inquiry and a grounded policy query using genuine customer voice recordings, processed exclusively through Gnani.ai STT (<code>/stt/v3</code>) and TTS (<code>timbre-v2.5</code>):
  </p>

  <h3>A. Multi-Turn Order &amp; Identity Verification Flow (Session: <code>order_inquiry_fixed</code>)</h3>
  <ul>
    <li><strong>Turn 1 (Order Identification):</strong> Customer spoke: <em>"hello i want to check the status of my order"</em>. Transcribed accurately via Gnani STT. The agent introduced its role and requested the 8-digit order number (Decision: <code>clarify</code>). Synthesized response audio saved to <code>turn_01_output.wav</code>.</li>
    <li><strong>Turn 2 (Order Lookup &amp; Privacy Gate):</strong> Customer provided the 8-digit order number. The agent executed <code>lookup_order()</code>, located the order record, and safely withheld order details while prompting for identity verification via the last 4 phone digits or delivery pincode (Decision: <code>clarify</code>).</li>
    <li><strong>Turn 3 (Verification &amp; Status Resolution):</strong> Customer provided the delivery pincode: <em>"the delivery pin code associated with my order is 411045"</em>. The agent executed <code>lookup_order()</code> with the verification value, confirmed caller identity, and disclosed the verified delivery status (Decision: <code>answer</code>). Synthesized response audio saved to <code>turn_03_output.wav</code>.</li>
  </ul>

  <h3>B. Policy Question Voice Validation (Session: <code>policy_inquiry</code>)</h3>
  <ul>
    <li><strong>Turn 1 (Grounded Policy Retrieval):</strong> Customer spoke genuine audio recorded to <code>outputs/sample_inputs/policy_question/01_policy_question.m4a</code>: <em>"what is the return window for clothing and footwear"</em>.</li>
    <li><strong>Grounded Resolution:</strong> The agent retrieved Section <code>[RET-2]</code> from <code>pol_returns_v4.md</code> and responded: <em>"The return window for clothing, footwear and bags is 15 days from the delivery date."</em></li>
    <li><strong>Verification &amp; Evidence Citation:</strong> Generated metadata confirms <code>evidence_sources: ["RET-2"]</code>, <code>decision: "answer"</code>, with response synthesized via Gnani TTS to <code>turn_01_output.wav</code> (0 errors, 100% STT/TTS success).</li>
  </ul>

  <h2>10. Verified Project Artifacts &amp; Output Directory Structure</h2>
  <table>
    <thead>
      <tr>
        <th>Artifact Type</th>
        <th>Relative Repository Path</th>
        <th>Contents &amp; Verification Status</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Voice Multi-Turn</strong></td>
        <td><code>outputs/sample_outputs/voice/order_inquiry_fixed/</code></td>
        <td>Turns 01–03: Transcripts (<code>.txt</code>), response audio (<code>.wav</code>), metadata logs (<code>.json</code>).</td>
      </tr>
      <tr>
        <td><strong>Voice Policy Test</strong></td>
        <td><code>outputs/sample_outputs/voice/policy_inquiry/</code></td>
        <td>Turn 01: Audio input, STT transcript, TTS output (<code>.wav</code>), metadata citing <code>RET-2</code>.</td>
      </tr>
      <tr>
        <td><strong>Evaluation Logs</strong></td>
        <td><code>outputs/evaluation/baseline_evaluation_results.json</code></td>
        <td>Raw per-question JSON records for 52 prompt-only baseline runs (0 errors).</td>
      </tr>
      <tr>
        <td><strong>Evaluation Logs</strong></td>
        <td><code>outputs/evaluation/rag_evaluation_results.json</code></td>
        <td>Raw per-question JSON records for 52 grounded RAG runs (82.7% Recall@4).</td>
      </tr>
      <tr>
        <td><strong>Benchmark Reports</strong></td>
        <td><code>outputs/evaluation/step1_vs_step2_comparison.md</code></td>
        <td>Detailed markdown comparison report analyzing percentage-point deltas.</td>
      </tr>
    </tbody>
  </table>

  <h2>11. Limitations &amp; Future Technical Roadmap</h2>
  <p>
    To maintain clear engineering boundaries, completed capstone deliverables are strictly distinguished from identified future enhancements:
  </p>

  <div class="row">
    <div class="col-2">
      <h3>Identified Limitations (Current System)</h3>
      <ul>
        <li><strong>Multi-Hop Coverage (34.6%):</strong> Standard top-4 retrieval occasionally misses secondary product catalog rows when queries require cross-document synthesis.</li>
        <li><strong>Decision Boundary Calibration:</strong> Conservative evidence thresholds reduce categorical decision accuracy against gold labels.</li>
        <li><strong>Acoustic Range:</strong> Tested primarily on clean near-field audio; noisy or high-packet-loss telephony environments require further validation.</li>
      </ul>
    </div>
    <div class="col-2">
      <h3>Future Technical Roadmap (Next Steps)</h3>
      <ul>
        <li><strong>Sub-Query Decomposition:</strong> Implement query planning to fetch catalog metadata and policy documents via parallel independent sub-queries.</li>
        <li><strong>Adaptive Confidence Calibration:</strong> Tune model abstention prompts to dynamically distinguish between minor omissions and critical ungrounded claims.</li>
        <li><strong>Streaming Voice Telephony:</strong> Migrate REST STT/TTS endpoints to full-duplex WebSocket streaming for sub-500ms voice barge-in support.</li>
      </ul>
    </div>
  </div>

  <div class="callout" style="margin-top: 4px;">
    <strong>Submission Sign-Off:</strong> All 56 unit/integration tests pass. Dataset integrity validated offline across 1,000 orders. Live Gnani.ai voice pipeline verified with zero non-Gnani speech dependencies. Ready for final archive packaging.
  </div>

  <div class="page-footer">
    <span>ZentroMart VoiceOps — Capstone Technical Report</span>
    <span>Page 4 of 4</span>
  </div>
</div>

</body>
</html>
"""

def generate_pdf():
    TEMP_HTML.parent.mkdir(parents=True, exist_ok=True)
    with open(TEMP_HTML, "w", encoding="utf-8") as f:
        f.write(HTML_CONTENT)
    print(f"Wrote temporary HTML to {TEMP_HTML}")

    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    browser_bin = None
    for cand in chrome_candidates:
        if os.path.exists(cand):
            browser_bin = cand
            break

    if not browser_bin:
        raise RuntimeError("No compatible Chrome or Edge executable found for PDF generation.")

    print(f"Using browser executable: {browser_bin}")
    cmd = [
        browser_bin,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={OUTPUT_PDF}",
        str(TEMP_HTML),
    ]

    subprocess.run(cmd, check=True)
    print(f"Generated PDF at {OUTPUT_PDF} ({OUTPUT_PDF.stat().st_size} bytes)")

    # Verify page count
    with open(OUTPUT_PDF, "rb") as f:
        pdf_bytes = f.read()

    pages = re.findall(rb"/Type\s*/Page\b", pdf_bytes)
    page_count = len(pages)
    print(f"Verified PDF page count: {page_count}")

    if page_count != 4:
        print(f"WARNING: Expected exactly 4 pages, got {page_count} pages!", file=sys.stderr)
        return False

    print("SUCCESS: report.pdf generated with exactly 4 pages.")
    return True

if __name__ == "__main__":
    success = generate_pdf()
    sys.exit(0 if success else 1)
