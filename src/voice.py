"""Voice integration module for ZentroMart VoiceOps.

Exclusively uses Gnani.ai for Speech-to-Text (STT) and Text-to-Speech (TTS).
No alternative speech providers (Whisper, Google Speech, ElevenLabs, etc.) are permitted.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from gnani.stt import (
    APIError as STTAPIError,
    AuthenticationError as STTAuthError,
    GnaniSTTClient,
    InvalidAudioError,
)
from gnani.stt.client import SUPPORTED_EXTENSIONS
from gnani.tts import (
    APIError as TTSAPIError,
    AudioConfig,
    AuthenticationError as TTSAuthError,
    GnaniTTSClient,
)

from src.agent import VoiceOpsAgent
from src.config import (
    DEFAULT_STT_FORMAT,
    DEFAULT_STT_LANGUAGE,
    DEFAULT_TTS_LANGUAGE,
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_VOICE,
    GNANI_API_KEY,
    VOICE_OUTPUT_DIR,
)

logger = logging.getLogger(__name__)

# Maximum recommended audio file size for REST STT endpoint (25 MB)
MAX_AUDIO_FILE_SIZE_BYTES = 25 * 1024 * 1024


class VoicePipelineError(Exception):
    """Base exception for voice pipeline failures."""
    pass


class MissingCredentialsError(VoicePipelineError):
    """Raised when GNANI_API_KEY is not configured."""
    pass


@dataclass
class VoiceTurnResult:
    """Encapsulates the complete result of a voice-driven conversation turn."""
    conversation_id: str
    turn_number: int
    audio_input_path: str
    transcript: str
    agent_message: str
    decision: str
    tool_calls: List[str] = field(default_factory=list)
    evidence_sources: List[str] = field(default_factory=list)
    audio_output_path: Optional[str] = None
    stt_success: bool = True
    tts_success: bool = True
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GnaniVoicePipeline:
    """Orchestrates end-to-end voice conversations using Gnani.ai STT & TTS."""

    def __init__(
        self,
        agent: Optional[VoiceOpsAgent] = None,
        stt_client: Optional[GnaniSTTClient] = None,
        tts_client: Optional[GnaniTTSClient] = None,
        api_key: Optional[str] = None,
        output_dir: Optional[Union[str, Path]] = None,
        tts_model: str = DEFAULT_TTS_MODEL,
        tts_voice: str = DEFAULT_TTS_VOICE,
        tts_language: str = DEFAULT_TTS_LANGUAGE,
        stt_language: str = DEFAULT_STT_LANGUAGE,
        stt_format: str = DEFAULT_STT_FORMAT,
        audio_config: Optional[AudioConfig] = None,
    ):
        self.api_key = api_key or GNANI_API_KEY
        self.agent = agent or VoiceOpsAgent()
        self.output_dir = Path(output_dir or VOICE_OUTPUT_DIR)
        self.tts_model = tts_model
        self.tts_voice = tts_voice
        self.tts_language = tts_language
        self.stt_language = stt_language
        self.stt_format = stt_format
        self.audio_config = audio_config or AudioConfig(
            sample_rate=16000,
            encoding="linear_pcm",
            container="wav",
        )

        # Lazy / injected STT and TTS clients
        self._stt_client = stt_client
        self._tts_client = tts_client

    @property
    def stt_client(self) -> GnaniSTTClient:
        """Returns initialized GnaniSTTClient or raises MissingCredentialsError."""
        if self._stt_client is None:
            if not self.api_key:
                raise MissingCredentialsError(
                    "GNANI_API_KEY is not configured. Set GNANI_API_KEY in your .env "
                    "or pass api_key to GnaniVoicePipeline."
                )
            self._stt_client = GnaniSTTClient(api_key=self.api_key)
        return self._stt_client

    @property
    def tts_client(self) -> GnaniTTSClient:
        """Returns initialized GnaniTTSClient or raises MissingCredentialsError."""
        if self._tts_client is None:
            if not self.api_key:
                raise MissingCredentialsError(
                    "GNANI_API_KEY is not configured. Set GNANI_API_KEY in your .env "
                    "or pass api_key to GnaniVoicePipeline."
                )
            self._tts_client = GnaniTTSClient(api_key=self.api_key)
        return self._tts_client

    def validate_audio_file(self, audio_path: Union[str, Path]) -> Path:
        """Validates that input audio exists, has supported extension and valid size."""
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Input audio file not found: {path}")

        if not path.is_file():
            raise ValueError(f"Path is not a regular file: {path}")

        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise InvalidAudioError(
                f"Unsupported audio format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        file_size = path.stat().st_size
        if file_size == 0:
            raise InvalidAudioError(f"Audio file is empty (0 bytes): {path}")

        if file_size > MAX_AUDIO_FILE_SIZE_BYTES:
            raise InvalidAudioError(
                f"Audio file size ({file_size / (1024 * 1024):.2f} MB) exceeds maximum "
                f"allowed limit of {MAX_AUDIO_FILE_SIZE_BYTES / (1024 * 1024):.0f} MB: {path}"
            )

        return path

    def transcribe_audio(
        self,
        audio_path: Union[str, Path],
        language_code: Optional[str] = None,
        stt_format: Optional[str] = None,
    ) -> str:
        """Transcribes an audio file using Gnani STT.

        Returns:
            The transcribed text. Returns empty string if no speech is detected.
        """
        validated_path = self.validate_audio_file(audio_path)
        lang = language_code or self.stt_language
        fmt = stt_format or self.stt_format

        try:
            resp = self.stt_client.transcribe(
                validated_path,
                language_code=lang,
                format=fmt,
            )
        except (STTAuthError, STTAPIError, InvalidAudioError):
            raise
        except Exception as e:
            raise VoicePipelineError(f"STT transcription failed: {e}") from e

        # Extract transcript safely from Gnani response
        transcript = ""
        if isinstance(resp, dict):
            transcript = str(resp.get("transcript") or "").strip()
        elif isinstance(resp, str):
            transcript = resp.strip()

        return transcript

    def synthesize_speech(
        self,
        text: str,
        output_file: Optional[Union[str, Path]] = None,
        voice: Optional[str] = None,
        model: Optional[str] = None,
        language: Optional[str] = None,
    ) -> bytes:
        """Synthesizes text into speech using Gnani TTS.

        Returns:
            Raw audio bytes, optionally written to output_file.
        """
        if not text or not text.strip():
            raise ValueError("Cannot synthesize speech for empty text.")

        v = voice or self.tts_voice
        m = model or self.tts_model
        lang = language or self.tts_language

        out_path = Path(output_file) if output_file else None
        if out_path:
            out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            audio_bytes = self.tts_client.synthesize(
                text=text.strip(),
                voice=v,
                model=m,
                language=lang,
                audio_config=self.audio_config,
                output_file=out_path,
            )
            return audio_bytes
        except (TTSAuthError, TTSAPIError, ValueError):
            raise
        except Exception as e:
            raise VoicePipelineError(f"TTS synthesis failed: {e}") from e

    def process_turn(
        self,
        audio_input_path: Union[str, Path],
        conversation_id: str = "voice_session",
        language_code: Optional[str] = None,
    ) -> VoiceTurnResult:
        """Executes a single voice turn: STT -> Agent -> TTS -> Save Artifacts.

        Preserves conversation_id across turns to retain verification state.
        """
        input_path = Path(audio_input_path)
        session_dir = self.output_dir / conversation_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Retrieve current turn number for this session
        session_state = self.agent.get_or_create_session(conversation_id)
        turn_number = len(session_state.turns) + 1

        # Step 1: Speech-to-Text via Gnani STT
        try:
            transcript = self.transcribe_audio(input_path, language_code=language_code)
        except Exception as err:
            logger.error("STT failed for %s: %s", input_path, err)
            result = VoiceTurnResult(
                conversation_id=conversation_id,
                turn_number=turn_number,
                audio_input_path=str(input_path),
                transcript="",
                agent_message="",
                decision="stt_error",
                stt_success=False,
                tts_success=False,
                error=f"STT Error: {err}",
            )
            self._save_turn_metadata(result, session_dir)
            return result

        # Handle empty transcript (no speech detected)
        if not transcript:
            agent_msg = (
                "I could not detect any speech in your voice recording. "
                "Please try speaking again or send your message in text."
            )
            out_audio_path = session_dir / f"turn_{turn_number:02d}_output.wav"
            tts_success = True
            error_note = None
            try:
                self.synthesize_speech(agent_msg, output_file=out_audio_path)
            except Exception as tts_err:
                tts_success = False
                out_audio_path = None
                error_note = f"TTS error on empty transcript notice: {tts_err}"

            result = VoiceTurnResult(
                conversation_id=conversation_id,
                turn_number=turn_number,
                audio_input_path=str(input_path),
                transcript="",
                agent_message=agent_msg,
                decision="stt_empty",
                audio_output_path=str(out_audio_path) if out_audio_path else None,
                stt_success=True,
                tts_success=tts_success,
                error=error_note,
            )
            self._save_turn_artifacts(result, session_dir)
            return result

        # Step 2: Agent Response using existing VoiceOpsAgent
        agent_turn = self.agent.handle_message(transcript, conversation_id=conversation_id)
        agent_message = agent_turn.agent_message

        # Step 3: Text-to-Speech via Gnani TTS
        out_audio_path = session_dir / f"turn_{turn_number:02d}_output.wav"
        tts_success = True
        tts_error: Optional[str] = None
        try:
            self.synthesize_speech(agent_message, output_file=out_audio_path)
        except Exception as err:
            logger.error("TTS failed for turn %d: %s", turn_number, err)
            tts_success = False
            out_audio_path = None
            tts_error = f"TTS Synthesis Error: {err}"

        # Step 4: Save artifacts
        result = VoiceTurnResult(
            conversation_id=conversation_id,
            turn_number=turn_number,
            audio_input_path=str(input_path),
            transcript=transcript,
            agent_message=agent_message,
            decision=agent_turn.decision,
            tool_calls=agent_turn.tool_calls,
            evidence_sources=agent_turn.evidence_sources,
            audio_output_path=str(out_audio_path) if out_audio_path else None,
            stt_success=True,
            tts_success=tts_success,
            error=tts_error,
        )
        self._save_turn_artifacts(result, session_dir)
        return result

    def process_folder(
        self,
        folder_path: Union[str, Path],
        conversation_id: Optional[str] = None,
        same_session: bool = True,
        language_code: Optional[str] = None,
    ) -> List[VoiceTurnResult]:
        """Processes a folder of audio files sequentially.

        If same_session is True, all turns share the same conversation_id
        to preserve multi-turn context and caller verification.
        """
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            raise FileNotFoundError(f"Directory not found: {folder}")

        # Find all supported audio files sorted naturally by name
        audio_files = sorted(
            [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS],
            key=lambda p: p.name.lower(),
        )

        if not audio_files:
            logger.warning("No supported audio files found in %s", folder)
            return []

        base_session_id = conversation_id or f"batch_{folder.name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        results: List[VoiceTurnResult] = []

        for idx, audio_file in enumerate(audio_files, 1):
            sess_id = base_session_id if same_session else f"{base_session_id}_turn_{idx}"
            logger.info("Processing [%d/%d]: %s (session=%s)", idx, len(audio_files), audio_file.name, sess_id)
            res = self.process_turn(audio_file, conversation_id=sess_id, language_code=language_code)
            results.append(res)

        return results

    def _save_turn_artifacts(self, result: VoiceTurnResult, session_dir: Path) -> None:
        """Saves transcript text, agent response text, and turn metadata JSON."""
        prefix = f"turn_{result.turn_number:02d}"

        # Save transcript
        transcript_path = session_dir / f"{prefix}_transcript.txt"
        transcript_path.write_text(result.transcript, encoding="utf-8")

        # Save response text
        response_path = session_dir / f"{prefix}_response.txt"
        response_path.write_text(result.agent_message, encoding="utf-8")

        # Save metadata JSON
        self._save_turn_metadata(result, session_dir)

    def _save_turn_metadata(self, result: VoiceTurnResult, session_dir: Path) -> None:
        """Saves turn metadata JSON."""
        meta_path = session_dir / f"turn_{result.turn_number:02d}_metadata.json"
        meta_path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
