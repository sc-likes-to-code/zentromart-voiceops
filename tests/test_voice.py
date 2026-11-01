"""Unit tests for Gnani.ai voice integration (Phase 4).

All tests use mocks to avoid API costs and network dependencies.
Validates STT, TTS, pipeline state preservation, artifact generation,
error handling, and strictly exclusive use of Gnani.ai.
"""
import ast
import json
import math
import struct
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from gnani.stt import APIError as STTAPIError, InvalidAudioError
from gnani.tts import APIError as TTSAPIError

from src.agent import VoiceOpsAgent
from src.conversation import ConversationTurn
from src.voice import (
    GnaniVoicePipeline,
    MissingCredentialsError,
    VoicePipelineError,
    VoiceTurnResult,
    repair_wav_file,
    repair_wav_header,
)


def create_dummy_wav(path: Path, duration_sec: float = 0.5) -> Path:
    """Helper to create a valid minimal PCM WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 16000
    total_samples = int(sample_rate * duration_sec)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        samples = [
            int(32767 * 0.1 * math.sin(2 * math.pi * 440 * i / sample_rate))
            for i in range(total_samples)
        ]
        wav_file.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return path


@pytest.fixture
def dummy_wav(tmp_path: Path) -> Path:
    return create_dummy_wav(tmp_path / "test_input.wav")


@pytest.fixture
def mock_stt_client():
    client = MagicMock()
    client.transcribe.return_value = {
        "success": True,
        "request_id": "req-test-123",
        "transcript": "Where is my order 8978 2837?",
    }
    return client


@pytest.fixture
def mock_tts_client(tmp_path: Path):
    client = MagicMock()
    def fake_synthesize(*args, **kwargs):
        out_file = kwargs.get("output_file")
        audio_content = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        if out_file:
            Path(out_file).parent.mkdir(parents=True, exist_ok=True)
            Path(out_file).write_bytes(audio_content)
        return audio_content
    client.synthesize.side_effect = fake_synthesize
    return client


def test_missing_credentials_raises_error(monkeypatch):
    """Missing GNANI_API_KEY must raise MissingCredentialsError when clients are accessed."""
    monkeypatch.setattr("src.voice.GNANI_API_KEY", None)
    pipeline = GnaniVoicePipeline(api_key=None)

    with pytest.raises(MissingCredentialsError):
        _ = pipeline.stt_client

    with pytest.raises(MissingCredentialsError):
        _ = pipeline.tts_client


def test_audio_file_validation_errors(tmp_path: Path):
    """Pipeline must validate file existence, format extension, and file size."""
    pipeline = GnaniVoicePipeline(api_key="fake-key")

    # 1. Nonexistent file
    with pytest.raises(FileNotFoundError):
        pipeline.validate_audio_file(tmp_path / "does_not_exist.wav")

    # 2. Unsupported extension
    bad_ext = tmp_path / "sample.txt"
    bad_ext.write_text("not audio", encoding="utf-8")
    with pytest.raises(InvalidAudioError, match="Unsupported audio format"):
        pipeline.validate_audio_file(bad_ext)

    # 3. Empty file (0 bytes)
    empty_file = tmp_path / "empty.wav"
    empty_file.touch()
    with pytest.raises(InvalidAudioError, match="empty"):
        pipeline.validate_audio_file(empty_file)


def test_stt_transcribe_success(dummy_wav: Path, mock_stt_client):
    """Verifies STT transcription with valid Gnani response."""
    pipeline = GnaniVoicePipeline(stt_client=mock_stt_client, api_key="fake-key")
    transcript = pipeline.transcribe_audio(dummy_wav)

    assert transcript == "Where is my order 8978 2837?"
    mock_stt_client.transcribe.assert_called_once()
    args, kwargs = mock_stt_client.transcribe.call_args
    assert kwargs.get("language_code") == "en-IN"
    assert kwargs.get("format") == "transcribe"


def test_stt_transcribe_empty_result(dummy_wav: Path, mock_stt_client):
    """Verifies handling when Gnani STT detects no speech."""
    mock_stt_client.transcribe.return_value = {"success": True, "transcript": ""}
    pipeline = GnaniVoicePipeline(stt_client=mock_stt_client, api_key="fake-key")

    transcript = pipeline.transcribe_audio(dummy_wav)
    assert transcript == ""


def test_stt_transcribe_failure(dummy_wav: Path, mock_stt_client):
    """Verifies STT API error raises appropriate exception."""
    mock_stt_client.transcribe.side_effect = STTAPIError(500, "Internal Server Error")
    pipeline = GnaniVoicePipeline(stt_client=mock_stt_client, api_key="fake-key")

    with pytest.raises(STTAPIError):
        pipeline.transcribe_audio(dummy_wav)


def test_tts_synthesize_success(tmp_path: Path, mock_tts_client):
    """Verifies TTS synthesis with valid Gnani parameters."""
    pipeline = GnaniVoicePipeline(tts_client=mock_tts_client, api_key="fake-key")
    out_file = tmp_path / "out.wav"

    audio_bytes = pipeline.synthesize_speech("Hello ZentroMart", output_file=out_file)
    assert len(audio_bytes) > 0
    assert out_file.exists()
    mock_tts_client.synthesize.assert_called_once()
    _, kwargs = mock_tts_client.synthesize.call_args
    assert kwargs.get("model") == "timbre-v2.5"
    assert kwargs.get("voice") == "Kaveri"
    assert kwargs.get("language") == "en-IN"


def test_tts_synthesize_failure(tmp_path: Path, mock_tts_client):
    """Verifies TTS API error handling."""
    mock_tts_client.synthesize.side_effect = TTSAPIError(429, "Rate limit exceeded")
    pipeline = GnaniVoicePipeline(tts_client=mock_tts_client, api_key="fake-key")

    with pytest.raises(TTSAPIError):
        pipeline.synthesize_speech("Hello", output_file=tmp_path / "fail.wav")

    # Empty text validation
    with pytest.raises(ValueError, match="empty text"):
        pipeline.synthesize_speech("   ")


def test_process_turn_end_to_end_and_artifacts(tmp_path: Path, dummy_wav: Path, mock_stt_client, mock_tts_client):
    """Verifies full turn: STT -> Agent -> TTS -> Disk artifacts."""
    out_dir = tmp_path / "voice_outputs"
    agent = MagicMock()
    agent.get_or_create_session.return_value.turns = []
    agent.handle_message.return_value = ConversationTurn(
        turn_number=1,
        user_message="Where is my order 8978 2837?",
        agent_message="To assist with order 89782837, please verify the last 4 digits of your phone or delivery pincode.",
        decision="verify",
        tool_calls=[],
        evidence_sources=[],
    )

    pipeline = GnaniVoicePipeline(
        agent=agent,
        stt_client=mock_stt_client,
        tts_client=mock_tts_client,
        output_dir=out_dir,
        api_key="fake-key",
    )

    result = pipeline.process_turn(dummy_wav, conversation_id="session_test")

    # Verify result structure
    assert isinstance(result, VoiceTurnResult)
    assert result.conversation_id == "session_test"
    assert result.turn_number == 1
    assert result.stt_success is True
    assert result.tts_success is True
    assert result.transcript == "Where is my order 8978 2837?"
    assert result.decision == "verify"
    assert result.audio_output_path is not None
    assert Path(result.audio_output_path).exists()

    # Verify disk artifacts
    session_dir = out_dir / "session_test"
    assert (session_dir / "turn_01_transcript.txt").read_text(encoding="utf-8") == result.transcript
    assert (session_dir / "turn_01_response.txt").read_text(encoding="utf-8") == result.agent_message
    assert (session_dir / "turn_01_output.wav").exists()

    meta_json = json.loads((session_dir / "turn_01_metadata.json").read_text(encoding="utf-8"))
    assert meta_json["turn_number"] == 1
    assert meta_json["decision"] == "verify"


def test_process_turn_empty_speech_detected(tmp_path: Path, dummy_wav: Path, mock_stt_client, mock_tts_client):
    """When no speech is transcribed, pipeline responds politely and generates TTS guidance."""
    mock_stt_client.transcribe.return_value = {"success": True, "transcript": ""}
    out_dir = tmp_path / "voice_outputs"

    pipeline = GnaniVoicePipeline(
        stt_client=mock_stt_client,
        tts_client=mock_tts_client,
        output_dir=out_dir,
        api_key="fake-key",
    )

    result = pipeline.process_turn(dummy_wav, conversation_id="session_empty")

    assert result.decision == "stt_empty"
    assert result.transcript == ""
    assert "could not detect any speech" in result.agent_message
    assert result.stt_success is True
    assert result.tts_success is True
    assert result.audio_output_path is not None


def test_process_turn_stt_failure_graceful_handling(tmp_path: Path, dummy_wav: Path, mock_stt_client, mock_tts_client):
    """When STT crashes, pipeline records stt_error without crashing or faking output audio."""
    mock_stt_client.transcribe.side_effect = STTAPIError(503, "Service Unavailable")
    out_dir = tmp_path / "voice_outputs"

    pipeline = GnaniVoicePipeline(
        stt_client=mock_stt_client,
        tts_client=mock_tts_client,
        output_dir=out_dir,
        api_key="fake-key",
    )

    result = pipeline.process_turn(dummy_wav, conversation_id="session_stt_err")

    assert result.decision == "stt_error"
    assert result.stt_success is False
    assert result.tts_success is False
    assert result.audio_output_path is None
    assert "503" in result.error


def test_process_turn_tts_failure_graceful_handling(tmp_path: Path, dummy_wav: Path, mock_stt_client, mock_tts_client):
    """When TTS fails, agent response text is preserved but audio_output_path is None."""
    mock_tts_client.synthesize.side_effect = TTSAPIError(500, "TTS Synthesizer down")
    out_dir = tmp_path / "voice_outputs"

    agent = MagicMock()
    agent.get_or_create_session.return_value.turns = []
    agent.handle_message.return_value = ConversationTurn(
        turn_number=1,
        user_message="Hello",
        agent_message="Hello! Welcome to ZentroMart.",
        decision="answer",
    )

    pipeline = GnaniVoicePipeline(
        agent=agent,
        stt_client=mock_stt_client,
        tts_client=mock_tts_client,
        output_dir=out_dir,
        api_key="fake-key",
    )

    result = pipeline.process_turn(dummy_wav, conversation_id="session_tts_err")

    assert result.stt_success is True
    assert result.tts_success is False
    assert result.audio_output_path is None
    assert "TTS Synthesis Error" in result.error
    assert result.agent_message == "Hello! Welcome to ZentroMart."


def test_multi_turn_state_preservation(tmp_path: Path, mock_stt_client, mock_tts_client):
    """Verifies that subsequent voice turns preserve conversation context and verification state."""
    wav1 = create_dummy_wav(tmp_path / "turn1.wav")
    wav2 = create_dummy_wav(tmp_path / "turn2.wav")

    # Real VoiceOpsAgent with mocked tools/retriever
    mock_retriever = MagicMock()
    mock_retriever.chunks = [MagicMock()]
    mock_gen = MagicMock()
    mock_tools = MagicMock()
    mock_tools.get_order.return_value = {
        "order_id": "89782837",
        "customer_phone": "9876543210",
        "delivery_pincode": "560001",
        "status": "delivered",
        "delivery_date": "2026-10-18",
        "order_amount": 1499.0,
    }

    agent = VoiceOpsAgent(
        retriever=mock_retriever,
        answer_generator=mock_gen,
        tools_adapter=mock_tools,
    )

    pipeline = GnaniVoicePipeline(
        agent=agent,
        stt_client=mock_stt_client,
        tts_client=mock_tts_client,
        output_dir=tmp_path / "multi_turn_out",
        api_key="fake-key",
    )

    # Turn 1: Caller mentions order -> asks to clarify / verify
    mock_stt_client.transcribe.return_value = {"success": True, "transcript": "Where is my order 8978 2837?"}
    mock_tools.lookup_order.return_value = {"verified": False}
    res1 = pipeline.process_turn(wav1, conversation_id="conv_live_multi")
    assert res1.turn_number == 1
    assert res1.decision == "clarify"
    assert "verify" in res1.agent_message.lower()

    # Turn 2: Caller provides phone last 4 digits
    mock_stt_client.transcribe.return_value = {"success": True, "transcript": "My last four digits are 3210"}
    mock_tools.lookup_order.return_value = {
        "verified": True,
        "customer_first_name": "Rohan",
        "status": "delivered",
        "delivery_date": "2026-10-18",
    }
    res2 = pipeline.process_turn(wav2, conversation_id="conv_live_multi")
    assert res2.turn_number == 2
    assert res2.decision == "answer"
    assert "rohan" in res2.agent_message.lower()


def test_process_folder_batch_mode(tmp_path: Path, mock_stt_client, mock_tts_client):
    """Verifies sequential folder processing with multi-turn preservation."""
    audio_dir = tmp_path / "batch_audios"
    audio_dir.mkdir()
    create_dummy_wav(audio_dir / "01_audio.wav")
    create_dummy_wav(audio_dir / "02_audio.wav")

    mock_stt_client.transcribe.side_effect = [
        {"success": True, "transcript": "Hello ZentroMart"},
        {"success": True, "transcript": "What is your refund policy?"},
    ]

    mock_agent = MagicMock()
    mock_agent.get_or_create_session.side_effect = [
        MagicMock(turns=[]),
        MagicMock(turns=[1]),
    ]
    mock_agent.handle_message.side_effect = [
        ConversationTurn(turn_number=1, user_message="Hello", agent_message="Welcome!", decision="answer"),
        ConversationTurn(turn_number=2, user_message="Policy", agent_message="Policy details", decision="answer"),
    ]

    pipeline = GnaniVoicePipeline(
        agent=mock_agent,
        stt_client=mock_stt_client,
        tts_client=mock_tts_client,
        output_dir=tmp_path / "batch_out",
        api_key="fake-key",
    )

    results = pipeline.process_folder(audio_dir, conversation_id="batch_sess", same_session=True)

    assert len(results) == 2
    assert results[0].turn_number == 1
    assert results[0].conversation_id == "batch_sess"
    assert results[1].turn_number == 2
    assert results[1].conversation_id == "batch_sess"


def test_exclusive_gnani_speech_provider():
    """Security/compliance audit: guarantees NO alternative speech providers are imported or used."""
    prohibited_libraries = {
        "whisper",
        "faster_whisper",
        "gtts",
        "pyttsx3",
        "elevenlabs",
        "google.cloud.speech",
        "azure.cognitiveservices.speech",
        "deepgram",
        "assemblyai",
    }

    source_files = [
        Path("src/voice.py"),
        Path("src/cli.py"),
        Path("src/config.py"),
        Path("src/agent.py"),
    ]

    for src_file in source_files:
        assert src_file.exists(), f"Source file {src_file} missing"
        tree = ast.parse(src_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for prohibited in prohibited_libraries:
                        assert prohibited not in alias.name.lower(), (
                            f"Prohibited speech library '{prohibited}' found in {src_file}"
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for prohibited in prohibited_libraries:
                    assert prohibited not in module.lower(), (
                        f"Prohibited speech library '{prohibited}' found in {src_file}"
                    )


def test_regression_exact_three_turn_voice_verification(tmp_path: Path, mock_stt_client, mock_tts_client):
    """Regression test for the observed three-turn failure in --audio-dir:

    1. 'hello i want to check the status of my order' -> asks for 8-digit order ID
    2. 'my order number is 59591825' -> prompts for phone last 4 or pincode
    3. 'the delivery pin code associated with my order is 411045' -> verifies order and answers
    """
    audio_dir = tmp_path / "voice_session_test"
    audio_dir.mkdir()
    w1 = create_dummy_wav(audio_dir / "01_order_request.wav")
    w2 = create_dummy_wav(audio_dir / "02_order_id.wav")
    w3 = create_dummy_wav(audio_dir / "03_verification.wav")

    mock_retriever = MagicMock()
    mock_retriever.chunks = [MagicMock()]
    mock_gen = MagicMock()
    mock_tools = MagicMock()

    # Turn 2 unverified lookup
    # Turn 3 verified lookup
    def mock_lookup(order_id, verification_value=None):
        if verification_value == "411045":
            return {
                "found": True,
                "verified": True,
                "order_id": order_id,
                "customer_first_name": "Joseph",
                "status": "delivered",
                "delivered_on": "2026-06-11",
                "delivery_pincode": "411045",
            }
        return {
            "found": True,
            "verified": False,
            "order_id": order_id,
        }

    mock_tools.lookup_order.side_effect = mock_lookup

    agent = VoiceOpsAgent(
        retriever=mock_retriever,
        answer_generator=mock_gen,
        tools_adapter=mock_tools,
    )

    pipeline = GnaniVoicePipeline(
        agent=agent,
        stt_client=mock_stt_client,
        tts_client=mock_tts_client,
        output_dir=tmp_path / "voice_out",
        api_key="fake-key",
    )

    mock_stt_client.transcribe.side_effect = [
        {"success": True, "transcript": "hello i want to check the status of my order"},
        {"success": True, "transcript": "my order number is 59591825"},
        {"success": True, "transcript": "the delivery pin code associated with my order is 411045"},
    ]

    results = pipeline.process_folder(audio_dir, conversation_id="order_inquiry_full", same_session=True)
    assert len(results) == 3

    # Turn 1
    assert results[0].turn_number == 1
    assert results[0].decision == "clarify"
    assert "8-digit order number" in results[0].agent_message or "order id" in results[0].agent_message.lower()

    # Turn 2
    assert results[1].turn_number == 2
    assert results[1].decision == "clarify"
    assert "lookup_order(order_id=59591825)" in results[1].tool_calls
    assert "verify" in results[1].agent_message.lower()

    # Turn 3 - MUST NOT be initial greeting or ask for order ID again!
    assert results[2].turn_number == 3
    assert results[2].decision == "answer"
    assert "lookup_order(order_id=59591825, verification_value=411045)" in results[2].tool_calls
    assert "joseph" in results[2].agent_message.lower()
    assert "verified" in results[2].agent_message.lower()
    assert "delivered" in results[2].agent_message.lower()
    assert "could you please share your 8-digit order number" not in results[2].agent_message.lower()

    # Verify artifacts on disk
    session_dir = tmp_path / "voice_out" / "order_inquiry_full"
    for turn_idx in (1, 2, 3):
        assert (session_dir / f"turn_{turn_idx:02d}_transcript.txt").exists()
        assert (session_dir / f"turn_{turn_idx:02d}_response.txt").exists()
        assert (session_dir / f"turn_{turn_idx:02d}_metadata.json").exists()
        assert (session_dir / f"turn_{turn_idx:02d}_output.wav").exists()


def test_regression_invalid_verification_retry_and_lockout(tmp_path: Path, mock_stt_client, mock_tts_client):
    """Regression test ensuring invalid verification triggers retry prompt then lockout."""
    w = create_dummy_wav(tmp_path / "input.wav")

    mock_retriever = MagicMock()
    mock_retriever.chunks = [MagicMock()]
    mock_gen = MagicMock()
    mock_tools = MagicMock()

    mock_tools.lookup_order.return_value = {
        "found": True,
        "verified": False,
        "order_id": "59591825",
    }

    agent = VoiceOpsAgent(
        retriever=mock_retriever,
        answer_generator=mock_gen,
        tools_adapter=mock_tools,
    )

    pipeline = GnaniVoicePipeline(
        agent=agent,
        stt_client=mock_stt_client,
        tts_client=mock_tts_client,
        output_dir=tmp_path / "voice_out_err",
        api_key="fake-key",
    )

    # 1. Provide order ID
    mock_stt_client.transcribe.return_value = {"success": True, "transcript": "my order number is 59591825"}
    r1 = pipeline.process_turn(w, conversation_id="bad_auth_sess")
    assert r1.decision == "clarify"

    # 2. Provide incorrect pincode (Attempt 1) -> retry prompt
    mock_stt_client.transcribe.return_value = {"success": True, "transcript": "the delivery pin code associated with my order is 999999"}
    r2 = pipeline.process_turn(w, conversation_id="bad_auth_sess")
    assert r2.decision == "clarify"
    assert "did not match" in r2.agent_message.lower() or "try again" in r2.agent_message.lower()

    # 3. Provide incorrect pincode (Attempt 2) -> lockout refusal
    mock_stt_client.transcribe.return_value = {"success": True, "transcript": "try 888888"}
    r3 = pipeline.process_turn(w, conversation_id="bad_auth_sess")
    assert r3.decision == "refuse"
    assert "unsuccessful" in r3.agent_message.lower() or "security" in r3.agent_message.lower()

    # 4. Attempt to query order details after lockout -> boundary guard refuse
    mock_stt_client.transcribe.return_value = {"success": True, "transcript": "can you tell me what items are in my order?"}
    r4 = pipeline.process_turn(w, conversation_id="bad_auth_sess")
    assert r4.decision == "refuse"
    assert "cannot share" in r4.agent_message.lower()


def test_regression_voice_session_isolation(tmp_path: Path, mock_stt_client, mock_tts_client):
    """Regression test ensuring multiple conversation sessions remain completely isolated."""
    w = create_dummy_wav(tmp_path / "input.wav")

    mock_retriever = MagicMock()
    mock_retriever.chunks = [MagicMock()]
    mock_gen = MagicMock()
    mock_tools = MagicMock()
    mock_tools.lookup_order.return_value = {"found": True, "verified": False, "order_id": "59591825"}

    agent = VoiceOpsAgent(
        retriever=mock_retriever,
        answer_generator=mock_gen,
        tools_adapter=mock_tools,
    )

    pipeline = GnaniVoicePipeline(
        agent=agent,
        stt_client=mock_stt_client,
        tts_client=mock_tts_client,
        output_dir=tmp_path / "voice_out_iso",
        api_key="fake-key",
    )

    # Session A: In progress order verification
    mock_stt_client.transcribe.return_value = {"success": True, "transcript": "my order is 59591825"}
    rA = pipeline.process_turn(w, conversation_id="session_A")
    assert rA.decision == "clarify"
    assert agent.get_or_create_session("session_A").order_id == "59591825"
    assert agent.get_or_create_session("session_A").verification_status == "pending"

    # Session B: Fresh session asks generic order question
    mock_stt_client.transcribe.return_value = {"success": True, "transcript": "hello i want to check the status of my order"}
    rB = pipeline.process_turn(w, conversation_id="session_B")
    assert rB.decision == "clarify"
    assert agent.get_or_create_session("session_B").order_id is None
    assert agent.get_or_create_session("session_B").verification_status == "none"
    assert "8-digit order number" in rB.agent_message.lower()


def test_repair_wav_header_streaming_sizes():
    """Streaming TTS WAV files with 0xFFFFFFFF sizes must be repaired accurately."""
    sample_rate = 16000
    channels = 1
    bytes_per_sample = 2
    num_samples = int(sample_rate * 1.5)
    raw_pcm = struct.pack(f"<{num_samples}h", *([1000] * num_samples))
    payload_len = len(raw_pcm)

    # Build streaming header with 0xFFFFFFFF
    header = (
        b"RIFF\xff\xff\xff\xffWAVE"
        b"fmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00"
        b"data\xff\xff\xff\xff"
    )
    streaming_wav = header + raw_pcm
    total_len = len(streaming_wav)

    # 1. Repair header
    fixed = repair_wav_header(streaming_wav)

    # 2. Check length is preserved
    assert len(fixed) == total_len

    # 3. Check RIFF size = total_len - 8
    riff_sz = struct.unpack_from("<I", fixed, 4)[0]
    assert riff_sz == total_len - 8

    # 4. Check data size = payload_len
    data_sz = struct.unpack_from("<I", fixed, 40)[0]
    assert data_sz == payload_len

    # 5. Check exact payload preservation (unmodified)
    assert fixed[44:] == raw_pcm

    # 6. Verify wave module opens it and reports exact duration
    import io
    with wave.open(io.BytesIO(fixed), "rb") as wf:
        assert wf.getnchannels() == channels
        assert wf.getsampwidth() == bytes_per_sample
        assert wf.getframerate() == sample_rate
        assert wf.getnframes() == num_samples
        assert pytest.approx(wf.getnframes() / wf.getframerate(), 0.01) == 1.5


def test_repair_wav_header_with_extra_chunks():
    """WAV files with non-standard chunks (e.g. JUNK) must parse correctly to 'data'."""
    raw_pcm = b"\x00\x01\x02\x03" * 100
    junk_payload = b"PADDING_DATA_HERE!"  # 18 bytes
    junk_chunk = b"JUNK" + struct.pack("<I", len(junk_payload)) + junk_payload
    fmt_chunk = b"fmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00"
    data_chunk_header = b"data\xff\xff\xff\xff"
    raw_wav = b"RIFF\xff\xff\xff\xffWAVE" + fmt_chunk + junk_chunk + data_chunk_header + raw_pcm

    fixed = repair_wav_header(raw_wav)
    assert len(fixed) == len(raw_wav)
    assert struct.unpack_from("<I", fixed, 4)[0] == len(raw_wav) - 8
    data_offset = fixed.find(b"data")
    assert data_offset != -1
    data_sz = struct.unpack_from("<I", fixed, data_offset + 4)[0]
    assert data_sz == len(raw_pcm)
    assert fixed[data_offset + 8:] == raw_pcm


def test_repair_wav_file_in_place(tmp_path: Path):
    """File helper repair_wav_file must patch invalid size bytes on disk."""
    raw_pcm = b"\x12\x34" * 500
    header = b"RIFF\xff\xff\xff\xffWAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\xff\xff\xff\xff"
    p = tmp_path / "streaming.wav"
    p.write_bytes(header + raw_pcm)

    modified = repair_wav_file(p)
    assert modified is True
    fixed_bytes = p.read_bytes()
    assert struct.unpack_from("<I", fixed_bytes, 4)[0] == len(fixed_bytes) - 8
    assert struct.unpack_from("<I", fixed_bytes, 40)[0] == len(raw_pcm)
    assert fixed_bytes[44:] == raw_pcm

    # Running again on an already-repaired file returns False (no change)
    assert repair_wav_file(p) is False


def test_retrieved_chunk_ids_propagated_to_turn_and_metadata(tmp_path: Path, mock_stt_client, mock_tts_client):
    """VoiceTurnResult and saved metadata must record both evidence_sources and retrieved_chunk_ids."""
    w = create_dummy_wav(tmp_path / "policy_input.wav")

    mock_retriever = MagicMock()
    mock_retriever.chunks = [MagicMock()]
    mock_chunk = MagicMock(
        chunk_id="pol_returns_v4.md:chunk_002",
        score=0.9123,
        section_id="RET-2",
        source_file="pol_returns_v4.md",
        heading="Return windows by category",
    )
    mock_retriever.retrieve.return_value = [mock_chunk]

    mock_gen = MagicMock()
    mock_gen.generate_answer.return_value = MagicMock(
        question="What is the return window for clothing?",
        answer="Clothing has a 15-day return window under current policy.",
        decision="answer",
        is_grounded=True,
        insufficient_evidence=False,
        evidence_sources=["RET-2"],
        retrieved_chunks=[mock_chunk],
    )

    agent = VoiceOpsAgent(retriever=mock_retriever, answer_generator=mock_gen)
    out_dir = tmp_path / "voice_artifacts_test"
    pipeline = GnaniVoicePipeline(
        agent=agent,
        stt_client=mock_stt_client,
        tts_client=mock_tts_client,
        output_dir=out_dir,
        api_key="fake-key",
    )

    mock_stt_client.transcribe.return_value = {
        "success": True,
        "transcript": "What is the return window for clothing?",
    }

    result = pipeline.process_turn(w, conversation_id="chunk_test_sess")
    assert result.decision == "answer"
    assert result.evidence_sources == ["RET-2"]
    assert result.retrieved_chunk_ids == ["pol_returns_v4.md:chunk_002"]
    assert len(result.retrieved_chunks) == 1
    assert result.retrieved_chunks[0]["chunk_id"] == "pol_returns_v4.md:chunk_002"
    assert result.retrieved_chunks[0]["score"] == 0.9123

    # Inspect persisted metadata JSON file
    meta_path = out_dir / "chunk_test_sess" / "turn_01_metadata.json"
    assert meta_path.exists()
    with open(meta_path, "r", encoding="utf-8") as f:
        meta_json = json.load(f)

    assert meta_json["evidence_sources"] == ["RET-2"]
    assert meta_json["retrieved_chunk_ids"] == ["pol_returns_v4.md:chunk_002"]
    assert meta_json["retrieved_chunks"][0]["section_id"] == "RET-2"


def test_process_folder_error_resilience(tmp_path: Path, mock_stt_client, mock_tts_client):
    """If one audio file fails during STT, process_folder must record error and continue remaining files."""
    audio_dir = tmp_path / "batch_input"
    audio_dir.mkdir()
    create_dummy_wav(audio_dir / "01_valid.wav")
    create_dummy_wav(audio_dir / "02_error.wav")
    create_dummy_wav(audio_dir / "03_valid.wav")

    mock_agent = MagicMock()
    mock_turn = MagicMock()
    mock_turn.decision = "clarify"
    mock_turn.agent_message = "Please share order ID"
    mock_turn.tool_calls = []
    mock_turn.evidence_sources = []
    mock_turn.retrieved_chunk_ids = []
    mock_turn.retrieved_chunks = []
    mock_agent.handle_message.return_value = mock_turn

    def side_effect_transcribe(p, **kwargs):
        if "02_error" in str(p):
            raise InvalidAudioError("Corrupted audio data")
        return {"success": True, "transcript": "valid input"}

    mock_stt_client.transcribe.side_effect = side_effect_transcribe

    out_dir = tmp_path / "batch_out"
    pipeline = GnaniVoicePipeline(
        agent=mock_agent,
        stt_client=mock_stt_client,
        tts_client=mock_tts_client,
        output_dir=out_dir,
        api_key="fake-key",
    )

    results = pipeline.process_folder(audio_dir, conversation_id="batch_err_test", same_session=True)
    assert len(results) == 3
    assert results[0].stt_success is True
    assert results[1].stt_success is False
    assert "Corrupted audio data" in (results[1].error or "") or results[1].decision == "stt_error"
    assert results[2].stt_success is True
