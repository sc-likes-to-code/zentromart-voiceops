"""Root batch execution script for ZentroMart VoiceOps.

Processes a directory of customer audio files sequentially through the
end-to-end voice pipeline: Gnani STT -> VoiceOpsAgent RAG & Tools -> Gnani TTS.
Persists response audio, transcript, response text, and turn metadata with
retrieved chunk IDs.

Required Usage:
    python run.py <audio_folder> [--out-dir <directory>]
"""
import argparse
import logging
import os
import sys
from pathlib import Path

# Configure standard streams for UTF-8 encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import VoiceOpsAgent
from src.answering import GroundedAnswerGenerator
from src.config import (
    DEFAULT_STT_LANGUAGE,
    DEFAULT_TTS_LANGUAGE,
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_VOICE,
    INDEX_DIR,
    VOICE_OUTPUT_DIR,
)
from src.retrieval import KnowledgeBaseRetriever
from src.voice import (
    GnaniVoicePipeline,
    MissingCredentialsError,
    SUPPORTED_EXTENSIONS,
    VoiceTurnResult,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_batch")


def print_turn_banner(res: VoiceTurnResult, current: int, total: int):
    """Prints a clear, structured summary for each processed audio turn."""
    print("\n" + "=" * 70)
    print(f" TURN {current}/{total} (Session: {res.conversation_id}) — DECISION: {res.decision.upper()}")
    print("=" * 70)
    print(f" • Input Audio     : {Path(res.audio_input_path).name}")
    print(f" • STT Transcript  : {res.transcript if res.transcript else '(empty / undetected)'}")
    print(f" • Agent Response  : {res.agent_message}")
    if res.tool_calls:
        print(f" • Tools Executed  : {', '.join(res.tool_calls)}")
    if res.evidence_sources:
        print(f" • Evidence Cited  : {', '.join(res.evidence_sources)}")
    if res.retrieved_chunk_ids:
        print(f" • Chunk IDs Cited : {', '.join(res.retrieved_chunk_ids)}")
    print(f" • Response Audio  : {res.audio_output_path or '(none)'}")
    if res.error:
        print(f" • Notice / Error  : {res.error}")
    print("=" * 70)


def print_batch_summary(results: list, out_dir: Path):
    """Displays a final execution scorecard for the batch."""
    print("\n" + "#" * 70)
    print(" ZENTROMART VOICEOPS — BATCH RUN EXECUTION SUMMARY")
    print("#" * 70)
    total = len(results)
    succeeded = sum(1 for r in results if r.stt_success and r.tts_success and not r.error)
    errors = total - succeeded

    print(f" Total Audio Files Processed : {total}")
    print(f" Successful Turns            : {succeeded}")
    print(f" Failures / Warnings         : {errors}")
    print(f" Output Directory            : {out_dir}")
    print("-" * 70)

    for i, r in enumerate(results, 1):
        status_label = "OK" if (r.stt_success and not r.error) else "ERROR"
        chunks = f" [{len(r.retrieved_chunk_ids)} chunks cited]" if r.retrieved_chunk_ids else ""
        print(f" [{status_label}] Turn {i:02d}: {Path(r.audio_input_path).name} -> {r.decision.upper()}{chunks}")

    print("#" * 70 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ZentroMart VoiceOps Batch Audio Evaluation Runner",
        usage="python run.py <audio_folder> [--out-dir <directory>]",
    )
    parser.add_argument(
        "audio_folder",
        type=str,
        help="Path to folder containing customer audio files (.wav, .m4a, .mp3, .aac)",
    )
    parser.add_argument(
        "--out-dir",
        "-o",
        type=str,
        default=str(VOICE_OUTPUT_DIR / "batch_run"),
        help="Output directory for generated speech, transcripts, and metadata",
    )
    parser.add_argument(
        "--session-id",
        "-s",
        type=str,
        default="batch_session",
        help="Session/conversation ID for stateful context tracking (default: batch_session)",
    )
    parser.add_argument(
        "--separate-sessions",
        action="store_true",
        help="Treat each audio file as an independent caller session rather than a continuous conversation",
    )
    parser.add_argument(
        "--stt-lang",
        type=str,
        default=DEFAULT_STT_LANGUAGE,
        help=f"STT language code (default: {DEFAULT_STT_LANGUAGE})",
    )
    parser.add_argument(
        "--tts-voice",
        type=str,
        default=DEFAULT_TTS_VOICE,
        help=f"TTS voice ID (default: {DEFAULT_TTS_VOICE})",
    )
    parser.add_argument(
        "--tts-model",
        type=str,
        default=DEFAULT_TTS_MODEL,
        help=f"TTS model ID (default: {DEFAULT_TTS_MODEL})",
    )
    parser.add_argument(
        "--tts-lang",
        type=str,
        default=DEFAULT_TTS_LANGUAGE,
        help=f"TTS language code (default: {DEFAULT_TTS_LANGUAGE})",
    )

    args = parser.parse_args()

    audio_dir = Path(args.audio_folder)
    if not audio_dir.exists() or not audio_dir.is_dir():
        print(f"Error: audio folder not found or is not a directory: {audio_dir}", file=sys.stderr)
        return 1

    # Locate audio files
    audio_files = sorted(
        [f for f in audio_dir.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS],
        key=lambda p: p.name.lower(),
    )

    if not audio_files:
        print(f"Error: No supported audio files ({', '.join(SUPPORTED_EXTENSIONS)}) found in {audio_dir}", file=sys.stderr)
        return 1

    print("=" * 70)
    print(" ZENTROMART VOICEOPS — BATCH AUDIO PROCESSING INITIALIZATION")
    print("=" * 70)
    print(f" Source Folder     : {audio_dir} ({len(audio_files)} audio files detected)")
    print(f" Target Output Dir : {args.out_dir}")
    print(f" Session Mode      : {'Isolated Multi-Turn' if not args.separate_sessions else 'Independent Single-Turns'}")
    print("=" * 70)

    # Initialize retriever
    retriever = KnowledgeBaseRetriever()
    if not retriever.load(INDEX_DIR):
        print(f"Warning: Index not found at {INDEX_DIR}. Attempting on-the-fly index build...", file=sys.stderr)
        from src.ingestion import KnowledgeBaseIngestor
        ingestor = KnowledgeBaseIngestor()
        docs = ingestor.ingest_all()
        chunks = ingestor.chunk_documents(docs)
        retriever.build(chunks)
        retriever.save(INDEX_DIR)

    # Initialize answer generator
    try:
        generator = GroundedAnswerGenerator()
    except Exception as e:
        print(f"Error initializing Gemini answer generator: {e}", file=sys.stderr)
        return 1

    # Initialize multi-turn agent
    agent = VoiceOpsAgent(retriever=retriever, answer_generator=generator)

    # Initialize Gnani voice pipeline
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
        print(f"Credentials Error: {e}", file=sys.stderr)
        return 1

    # Run batch processing
    results = pipeline.process_folder(
        audio_dir,
        conversation_id=args.session_id,
        same_session=not args.separate_sessions,
        language_code=args.stt_lang,
    )

    for i, res in enumerate(results, 1):
        print_turn_banner(res, i, len(results))

    print_batch_summary(results, Path(args.out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
