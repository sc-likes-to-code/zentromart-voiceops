"""Live smoke test for Gnani.ai STT and TTS integration.

Opt-in test that performs real API calls only if GNANI_API_KEY is configured.
Never logs or prints secret keys.
"""
import math
import os
import struct
import sys
import wave
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import GNANI_API_KEY, VOICE_OUTPUT_DIR
from src.voice import GnaniVoicePipeline


def create_synthetic_wav(output_path: Path, duration_sec: float = 1.5, freq: float = 440.0) -> Path:
    """Generates a clean synthetic PCM WAV file for audio testing."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 16000
    total_samples = int(sample_rate * duration_sec)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        samples = [
            int(32767 * 0.25 * math.sin(2 * math.pi * freq * i / sample_rate))
            for i in range(total_samples)
        ]
        wav_file.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return output_path


def run_smoke_test():
    print("=" * 65)
    print("ZentroMart VoiceOps — Gnani.ai Voice Integration Smoke Test")
    print("=" * 65)

    if not GNANI_API_KEY:
        print("\n[STATUS: BLOCKED / CREDENTIALS REQUIRED]")
        print("GNANI_API_KEY is not configured in .env.")
        print("\nTo test live speech recognition and synthesis against Gnani.ai:")
        print("  1. Add your API key to .env:")
        print("     GNANI_API_KEY=<your_gnani_api_key>")
        print("  2. Re-run this smoke test:")
        print("     python scripts/smoke_test_voice.py\n")
        print("Mocked unit tests and pipeline architecture are validated independently.")
        print("=" * 65)
        return 0

    print(f"\n[CREDENTIAL DETECTED] GNANI_API_KEY is configured (Length: {len(GNANI_API_KEY)} chars).")
    
    # Setup test directories and audio
    smoke_dir = VOICE_OUTPUT_DIR / "smoke_test"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    test_audio = smoke_dir / "smoke_input.wav"
    create_synthetic_wav(test_audio, duration_sec=1.5)
    print(f"Created test audio: {test_audio} ({test_audio.stat().st_size} bytes)")

    pipeline = GnaniVoicePipeline(output_dir=smoke_dir)

    # 1. Test live STT
    print("\n1. Testing Live Gnani STT (REST endpoint /stt/v3)...")
    try:
        transcript = pipeline.transcribe_audio(test_audio)
        print(f"   [SUCCESS] STT API responded.")
        print(f"   Transcript returned: '{transcript}'")
    except Exception as e:
        print(f"   [FAILED] STT API call failed: {e}")
        return 1

    # 2. Test live TTS
    print("\n2. Testing Live Gnani TTS (Model: timbre-v2.5, Voice: Kaveri, Lang: en-IN)...")
    tts_output = smoke_dir / "smoke_output.wav"
    test_text = "Welcome to ZentroMart support. How can I help you with your order today?"
    try:
        audio_bytes = pipeline.synthesize_speech(test_text, output_file=tts_output)
        print(f"   [SUCCESS] TTS API responded.")
        print(f"   Output audio generated: {tts_output}")
        print(f"   Audio size: {len(audio_bytes)} bytes ({tts_output.stat().st_size} bytes on disk)")
    except Exception as e:
        print(f"   [FAILED] TTS API call failed: {e}")
        return 1

    print("\n" + "=" * 65)
    print("LIVE SMOKE TEST COMPLETED SUCCESSFULLY!")
    print("Both Gnani STT and Gnani TTS verified live.")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(run_smoke_test())
