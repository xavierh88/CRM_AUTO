"""
Dealer AI OS - Voice STT adapter.

Responsibility:
    audio -> text

This module MUST NOT:
- modify Jarvis memory
- write conversation history
- execute Jarvis tools
- alter Jarvis reasoning/context
"""

import os
import tempfile
import threading
from pathlib import Path

from faster_whisper import WhisperModel


MODEL_NAME = os.getenv("DEALER_AI_STT_MODEL", "base")
MAX_AUDIO_BYTES = 8 * 1024 * 1024

_model = None
_model_lock = threading.Lock()
_transcribe_lock = threading.Lock()


def _get_model():
    """Lazy-load the STT model only when Voice is actually used."""
    global _model

    if _model is None:
        with _model_lock:
            if _model is None:
                _model = WhisperModel(
                    MODEL_NAME,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=2,
                    num_workers=1,
                )

    return _model


def transcribe_audio(audio_bytes: bytes, suffix: str = ".webm") -> dict:
    if not audio_bytes:
        raise ValueError("Empty audio")

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ValueError("Audio exceeds 8 MB limit")

    safe_suffix = suffix if suffix in {
        ".webm", ".ogg", ".wav", ".mp3", ".m4a", ".mp4"
    } else ".webm"

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=safe_suffix,
            delete=False,
        ) as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name

        model = _get_model()

        # Serialize transcription on this small 2-vCPU VPS so multiple
        # recordings cannot saturate CPU/RAM simultaneously.
        with _transcribe_lock:
            segments, info = model.transcribe(
                temp_path,
                beam_size=3,
                best_of=3,
                vad_filter=False,
                condition_on_previous_text=False,
            )

            segments = list(segments)

            text = " ".join(
                segment.text.strip()
                for segment in segments
                if segment.text.strip()
            ).strip()

            detected_language = getattr(info, "language", None)
            language_probability = getattr(
                info,
                "language_probability",
                None,
            )

            # Dealer AI Voice is intentionally bilingual (English/Spanish).
            # If automatic detection drifts into another language, retry the
            # same recording as ES and EN and keep the stronger transcription.
            if detected_language not in {"es", "en"}:
                candidates = []

                for forced_language in ("es", "en"):
                    forced_segments, forced_info = model.transcribe(
                        temp_path,
                        language=forced_language,
                        beam_size=1,
                        best_of=1,
                        vad_filter=False,
                        condition_on_previous_text=False,
                    )

                    forced_segments = list(forced_segments)

                    forced_text = " ".join(
                        segment.text.strip()
                        for segment in forced_segments
                        if segment.text.strip()
                    ).strip()

                    avg_logprob_values = [
                        segment.avg_logprob
                        for segment in forced_segments
                        if getattr(segment, "avg_logprob", None) is not None
                    ]

                    avg_logprob = (
                        sum(avg_logprob_values) / len(avg_logprob_values)
                        if avg_logprob_values
                        else float("-inf")
                    )

                    no_speech_values = [
                        segment.no_speech_prob
                        for segment in forced_segments
                        if getattr(segment, "no_speech_prob", None) is not None
                    ]

                    avg_no_speech = (
                        sum(no_speech_values) / len(no_speech_values)
                        if no_speech_values
                        else 1.0
                    )

                    candidates.append({
                        "language": forced_language,
                        "text": forced_text,
                        "avg_logprob": avg_logprob,
                        "avg_no_speech": avg_no_speech,
                    })

                usable_candidates = [
                    candidate
                    for candidate in candidates
                    if candidate["text"]
                ]

                if usable_candidates:
                    best_candidate = max(
                        usable_candidates,
                        key=lambda candidate: (
                            candidate["avg_logprob"],
                            -candidate["avg_no_speech"],
                        ),
                    )

                    text = best_candidate["text"]
                    detected_language = best_candidate["language"]
                    language_probability = None

        return {
            "text": text,
            "language": detected_language,
            "language_probability": language_probability,
            "model": MODEL_NAME,
        }

    finally:
        if temp_path:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass
