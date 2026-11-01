"""ZentroMart VoiceOps — High-Visibility Live Demonstration Runner.

Optimized for 1920x1080 OBS Screen Recording with Real-Time Audio Playback.
Executes live through Gnani STT -> VoiceOpsAgent RAG & Tools -> Gnani TTS -> Synchronous Windows Playback.
"""
import argparse
import logging
import os
import sys
import time
import winsound
from pathlib import Path
from typing import Optional

# Configure standard streams for UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Suppress debug/info logging for high-contrast presentation
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("gnani").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import VoiceOpsAgent
from src.answering import GroundedAnswerGenerator
from src.config import INDEX_DIR, VOICE_OUTPUT_DIR
from src.retrieval import KnowledgeBaseRetriever
from src.voice import GnaniVoicePipeline, VoiceTurnResult


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_banner(text: str, width: int = 75, char: str = "="):
    print("\n" + char * width)
    print(f" {text}")
    print(char * width)


def play_audio(audio_path: str):
    if not audio_path or not os.path.exists(audio_path):
        return
    print(f"\n[Playing Gnani.ai Synthesized Voice ({Path(audio_path).name})]...")
    try:
        winsound.PlaySound(str(audio_path), winsound.SND_FILENAME)
        print("[Audio playback complete]")
    except Exception as e:
        print(f"[Playback warning: {e}]")


def run_voice_turn(
    pipeline: GnaniVoicePipeline,
    audio_path: str,
    conversation_id: str,
    turn_num: int,
    total_turns: int,
    play_sound: bool = True,
) -> VoiceTurnResult:
    print_banner(f"TURN {turn_num}/{total_turns} — PROCESSING SPEECH INPUT", char="-")
    print(f" • Input Audio File    : {Path(audio_path).name}")
    print(" • Speech-to-Text      : Contacting Gnani.ai STT (/stt/v3)...")

    start_t = time.time()
    result = pipeline.process_turn(audio_path, conversation_id=conversation_id)
    dur = time.time() - start_t

    print(f" • STT Transcript      : \"{result.transcript}\"")
    print(f" • Decision Gating     : {result.decision.upper()}")
    print(f" • Agent Spoken Answer : {result.agent_message}")

    if result.tool_calls:
        print(f" • Support Tools Run   : {', '.join(result.tool_calls)}")

    if result.evidence_sources:
        print(f" • Policy Sources      : {', '.join(result.evidence_sources)}")

    if result.retrieved_chunk_ids:
        print(f" • Retrieved Chunk IDs :")
        for chunk_id in result.retrieved_chunk_ids:
            print(f"     - {chunk_id}")

    print(f" • Generated Response  : {Path(result.audio_output_path).name if result.audio_output_path else 'None'}")
    print(f" • Turn Latency        : {dur:.2f}s")

    if play_sound and result.audio_output_path:
        play_audio(result.audio_output_path)

    return result


def find_audio_file(folder: Path, stem: str) -> Optional[Path]:
    for ext in [".m4a", ".wav", ".mp3"]:
        cand = folder / f"{stem}{ext}"
        if cand.exists():
            return cand
    return None


def run_scenario_a(pipeline: GnaniVoicePipeline, audio_dir: Path, play_sound: bool = True):
    print_banner("SCENARIO A: GROUNDED MULTI-TURN CONVERSATION WITH FOLLOW-UP", char="=")
    print(" Description: Customer asks about apparel return window; follows up on reverse pickup fee.")
    print(" Objectives : Verify policy grounding (RET-2), multi-turn context retention, and chunk IDs.")

    session_id = f"demo_scenario_a_{int(time.time())}"
    turn1_audio = find_audio_file(audio_dir, "01_return_window")
    turn2_audio = find_audio_file(audio_dir, "02_pickup_fee")

    if not turn1_audio:
        fallback = PROJECT_ROOT / "outputs" / "sample_inputs" / "policy_question" / "01_policy_question.m4a"
        if fallback.exists():
            turn1_audio = fallback

    # Turn 1
    if turn1_audio and turn1_audio.exists():
        run_voice_turn(pipeline, str(turn1_audio), session_id, 1, 2, play_sound=play_sound)
    else:
        print(f"[ERROR] Turn 1 audio not found in {audio_dir}")
        return

    time.sleep(1.0)

    # Turn 2
    if turn2_audio and turn2_audio.exists():
        run_voice_turn(pipeline, str(turn2_audio), session_id, 2, 2, play_sound=play_sound)
    else:
        print("\n" + "-" * 75)
        print(" [Turn 2 Pending] Recording not found at demo/audio/scenario_a/02_pickup_fee.[wav|m4a]")
        print("-" * 75)


def run_scenario_b(pipeline: GnaniVoicePipeline, audio_dir: Path, play_sound: bool = True):
    print_banner("SCENARIO B: SAFETY GATING & HIGH-VALUE ESCALATION", char="=")
    print(" Description: Customer reports broken laptop display (> INR 10,000 threshold).")
    print(" Objectives : Verify policy routing (DWM-3), Priority Resolution handoff, and ticket logging.")

    session_id = f"demo_scenario_b_{int(time.time())}"
    turn1_audio = find_audio_file(audio_dir, "01_damage_escalation")

    if turn1_audio and turn1_audio.exists():
        run_voice_turn(pipeline, str(turn1_audio), session_id, 1, 1, play_sound=play_sound)
    else:
        print("\n" + "-" * 75)
        print(" [Turn 1 Pending] Recording not found at demo/audio/scenario_b/01_damage_escalation.[wav|m4a]")
        print("-" * 75)


def main():
    parser = argparse.ArgumentParser(description="ZentroMart VoiceOps Live Demonstration Runner")
    parser.add_argument("--scenario", choices=["a", "b", "all"], default="all", help="Scenario to execute")
    parser.add_argument("--no-audio", action="store_true", help="Do not play audio through speakers")
    args = parser.parse_args()

    clear_screen()
    print_banner("ZENTROMART VOICEOPS — LIVE DEMONSTRATION RUNNER", char="#")
    print(" IIT Guwahati × Gnani.ai TOKENS→TRANSFORMERS Capstone 2026")
    print(" Live Telephony Pipeline: Gnani STT -> Grounded VoiceOpsAgent -> Gnani TTS\n")

    # Initialize components
    print("Initializing local retrieval index and Gemini answer generator...")
    retriever = KnowledgeBaseRetriever()
    if not retriever.load(INDEX_DIR):
        print(f"[ERROR] Index not found at {INDEX_DIR}. Run 'python scripts/build_index.py' first.")
        return 1

    generator = GroundedAnswerGenerator()
    agent = VoiceOpsAgent(retriever=retriever, answer_generator=generator)
    out_dir = PROJECT_ROOT / "outputs" / "sample_outputs" / "voice" / "demo_run"
    pipeline = GnaniVoicePipeline(agent=agent, output_dir=out_dir)
    print("System initialized successfully. Starting scenarios...\n")

    audio_a_dir = PROJECT_ROOT / "demo" / "audio" / "scenario_a"
    audio_b_dir = PROJECT_ROOT / "demo" / "audio" / "scenario_b"
    play_sound = not args.no_audio

    if args.scenario in ("a", "all"):
        run_scenario_a(pipeline, audio_a_dir, play_sound=play_sound)
        if args.scenario == "all":
            time.sleep(2.0)

    if args.scenario in ("b", "all"):
        run_scenario_b(pipeline, audio_b_dir, play_sound=play_sound)

    print_banner("DEMONSTRATION RUN COMPLETED", char="#")
    print(" All audio artifacts, transcripts, and metadata saved to:")
    print(f" {out_dir}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
