"""Command-line interface for the ZentroMart VoiceOps Grounded RAG Assistant."""
import argparse
import sys
from pathlib import Path
from typing import Optional

# Reconfigure stdout/stderr for Unicode/UTF-8 support on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is on sys.path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.answering import GroundedAnswer, GroundedAnswerGenerator
from src.config import (
    DEFAULT_STT_LANGUAGE,
    DEFAULT_TOP_K,
    DEFAULT_TTS_LANGUAGE,
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_VOICE,
    INDEX_DIR,
    VOICE_OUTPUT_DIR,
)
from src.retrieval import KnowledgeBaseRetriever, RetrievalResult
from src.agent import VoiceOpsAgent
from src.voice import GnaniVoicePipeline, MissingCredentialsError, VoiceTurnResult


def print_formatted_result(result: GroundedAnswer):
    """Displays structured RAG response per Phase 2 requirements."""
    print("\n" + "=" * 60)
    print("1. USER QUESTION:")
    print(f"   {result.question}")
    print("\n2. GROUNDED ANSWER:")
    print(f"   {result.answer}")
    print("\n3. RETRIEVED SOURCES & CHUNK IDENTIFIERS:")
    if result.retrieved_chunks:
        for i, chunk in enumerate(result.retrieved_chunks, 1):
            print(f"   [{i}] Chunk ID : {chunk.chunk_id}")
            print(f"       Source   : {chunk.source_file} (Section: {chunk.section_id})")
            print(f"       Heading  : {chunk.heading}")
            print(f"       Score    : {chunk.score:.4f}")
    else:
        print("   (None retrieved)")

    print("\n4. EVIDENCE PREVIEWS:")
    if result.retrieved_chunks:
        for i, chunk in enumerate(result.retrieved_chunks, 1):
            preview = chunk.text.replace("\n", " ").strip()
            if len(preview) > 180:
                preview = preview[:180] + "..."
            print(f"   [{i}] {preview}")
    else:
        print("   (No evidence chunks available)")

    print("\n5. STATUS:")
    if result.insufficient_evidence:
        print("   DECLINED (Insufficient evidence in knowledge base)")
    else:
        print(f"   ANSWERED (Decision: {result.decision.upper()} | Sources: {', '.join(result.evidence_sources) if result.evidence_sources else 'Knowledge Base'})")
    print("=" * 60 + "\n")


def run_single_query(
    query: str,
    retriever: KnowledgeBaseRetriever,
    generator: GroundedAnswerGenerator,
    top_k: int = DEFAULT_TOP_K,
) -> GroundedAnswer:
    """Executes retrieval and grounded generation for a single user question."""
    chunks = retriever.retrieve(query, top_k=top_k)
    return generator.generate_answer(query, chunks)


def interactive_conversation_loop(agent: VoiceOpsAgent, conversation_id: str = "cli_session"):
    """Runs interactive multi-turn customer support session."""
    print("=" * 65)
    print("ZentroMart VoiceOps — Multi-Turn Customer Support Console")
    print("Type your message and press Enter. Type 'exit' or 'quit' to end.")
    print("=" * 65)

    turn_count = 1
    while True:
        try:
            user_input = input(f"\n[Turn {turn_count}] Customer> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("Ending support session. Have a great day!")
                break

            turn = agent.handle_message(user_input, conversation_id=conversation_id)
            print(f"\n[Turn {turn.turn_number}] Agent ({turn.decision.upper()}):")
            print(f"   {turn.agent_message}")
            if turn.tool_calls:
                print(f"   [Tool Executed: {', '.join(turn.tool_calls)}]")
            if turn.evidence_sources:
                print(f"   [Evidence Cited: {', '.join(turn.evidence_sources)}]")
            turn_count += 1
        except (KeyboardInterrupt, EOFError):
            print("\nSession interrupted. Ending session.")
            break


def print_voice_turn_result(result: VoiceTurnResult):
    """Displays structured result of a voice-driven turn."""
    print("\n" + "=" * 65)
    print(f"VOICE TURN {result.turn_number} [DECISION: {result.decision.upper()}] (Session: {result.conversation_id})")
    print("=" * 65)
    print(f"1. INPUT AUDIO FILE   : {result.audio_input_path}")
    print(f"2. GNANI STT TRANSCRIPT: {result.transcript if result.transcript else '(None / Empty)'}")
    print(f"3. AGENT RESPONSE      : {result.agent_message}")
    if result.tool_calls:
        print(f"4. TOOLS EXECUTED      : {', '.join(result.tool_calls)}")
    if result.evidence_sources:
        print(f"5. EVIDENCE SOURCES    : {', '.join(result.evidence_sources)}")
    print(f"6. GNANI TTS AUDIO     : {result.audio_output_path if result.audio_output_path else '(No audio generated)'}")
    if result.error:
        print(f"7. WARNING / ERROR     : {result.error}")
    print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(description="ZentroMart VoiceOps Assistant (Text & Voice)")
    parser.add_argument("--query", "-q", type=str, help="Single policy query to answer (Phase 2 one-shot text mode)")
    parser.add_argument("--top-k", "-k", type=int, default=DEFAULT_TOP_K, help="Number of evidence chunks to retrieve")
    parser.add_argument("--session-id", "-s", type=str, default="cli_session", help="Session ID for conversation")
    
    # Voice arguments (Phase 4)
    parser.add_argument("--audio", "-a", type=str, help="Single audio file to transcribe with Gnani STT and reply via Gnani TTS")
    parser.add_argument("--audio-dir", "-d", type=str, help="Directory of audio files to process in sequence")
    parser.add_argument("--separate-sessions", action="store_true", help="When using --audio-dir, do not preserve conversation context between files")
    parser.add_argument("--stt-lang", type=str, default=DEFAULT_STT_LANGUAGE, help=f"STT language code (default: {DEFAULT_STT_LANGUAGE})")
    parser.add_argument("--tts-voice", type=str, default=DEFAULT_TTS_VOICE, help=f"TTS voice ID (default: {DEFAULT_TTS_VOICE})")
    parser.add_argument("--tts-model", type=str, default=DEFAULT_TTS_MODEL, help=f"TTS model ID (default: {DEFAULT_TTS_MODEL})")
    parser.add_argument("--tts-lang", type=str, default=DEFAULT_TTS_LANGUAGE, help=f"TTS language code (default: {DEFAULT_TTS_LANGUAGE})")
    parser.add_argument("--out-dir", type=str, default=str(VOICE_OUTPUT_DIR), help="Output directory for voice audio and transcripts")
    args = parser.parse_args()

    # Initialize retriever
    retriever = KnowledgeBaseRetriever()
    if not retriever.load(INDEX_DIR):
        print(f"Error: Index not found at {INDEX_DIR}. Run 'python scripts/build_index.py' first.", file=sys.stderr)
        return 1

    # Initialize answer generator
    try:
        generator = GroundedAnswerGenerator()
    except Exception as e:
        print(f"Error initializing Gemini answer generator: {e}", file=sys.stderr)
        return 1

    # Initialize multi-turn agent
    agent = VoiceOpsAgent(retriever=retriever, answer_generator=generator)

    # 1. Voice pipeline modes
    if args.audio or args.audio_dir:
        try:
            pipeline = GnaniVoicePipeline(
                agent=agent,
                output_dir=args.out_dir,
                tts_model=args.tts_model,
                tts_voice=args.tts_voice,
                tts_language=args.tts_lang,
                stt_language=args.stt_lang,
            )
        except MissingCredentialsError as e:
            print(f"Configuration Error: {e}", file=sys.stderr)
            return 1

        if args.audio:
            try:
                result = pipeline.process_turn(args.audio, conversation_id=args.session_id)
                print_voice_turn_result(result)
            except Exception as e:
                print(f"Error processing audio turn: {e}", file=sys.stderr)
                return 1
            return 0

        if args.audio_dir:
            try:
                results = pipeline.process_folder(
                    args.audio_dir,
                    conversation_id=args.session_id,
                    same_session=not args.separate_sessions,
                )
                print(f"\nProcessed {len(results)} audio file(s) from {args.audio_dir}.")
                for res in results:
                    print_voice_turn_result(res)
            except Exception as e:
                print(f"Error processing audio directory: {e}", file=sys.stderr)
                return 1
            return 0

    # 2. Text one-shot mode (Phase 2 preserved)
    if args.query:
        result = run_single_query(args.query, retriever, generator, top_k=args.top_k)
        print_formatted_result(result)
        return 0

    # 3. Text multi-turn interactive console (Phase 3 preserved)
    interactive_conversation_loop(agent, conversation_id=args.session_id)
    return 0



if __name__ == "__main__":
    sys.exit(main())
