"""
faster-whisper compatibility shim exposing the openai-whisper API.

Drop-in replacement: anywhere that does `import whisper` can use this
module instead and get the same .load_model() / .transcribe() interface.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Any

import numpy as np
from faster_whisper import WhisperModel as _FasterWhisperModel

logger = logging.getLogger(__name__)


class _CompatModel:
    """Wraps faster-whisper to expose openai-whisper's model.transcribe() API."""

    def __init__(self, model_size: str, device: str = "cpu"):
        compute_type = "float32" if device == "cpu" else "float16"
        logger.info("Loading faster-whisper model: %s on %s", model_size, device)
        self._model = _FasterWhisperModel(
            model_size, device=device, compute_type=compute_type
        )
        self.device = device

    def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        task: str = "transcribe",
        word_timestamps: bool = False,
        **kwargs: Any,
    ) -> dict:
        options: dict[str, Any] = {}
        if language and language not in ("auto", ""):
            options["language"] = language
        if task:
            options["task"] = task
        if word_timestamps:
            options["word_timestamps"] = True

        segments_gen, info = self._model.transcribe(audio_path, **options)
        segments = list(segments_gen)
        full_text = " ".join(s.text.strip() for s in segments)

        result_segments = []
        for i, s in enumerate(segments):
            seg: dict[str, Any] = {
                "id": i,
                "start": s.start,
                "end": s.end,
                "text": s.text,
                "avg_logprob": getattr(s, "avg_logprob", -0.5),
                "no_speech_prob": getattr(s, "no_speech_prob", 0.0),
                "compression_ratio": getattr(s, "compression_ratio", 1.0),
                "words": [],
            }
            if word_timestamps and hasattr(s, "words") and s.words:
                seg["words"] = [
                    {
                        "word": w.word,
                        "start": w.start,
                        "end": w.end,
                        "probability": w.probability,
                    }
                    for w in s.words
                ]
            result_segments.append(seg)

        return {
            "text": full_text,
            "segments": result_segments,
            "language": info.language,
        }


def load_model(name: str, device: str | None = None, **kwargs: Any) -> _CompatModel:
    return _CompatModel(name, device=device or "cpu")


def load_audio(file: str, sr: int = 16000) -> np.ndarray:
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-threads",
        "0",
        "-i",
        file,
        "-f",
        "s16le",
        "-ac",
        "1",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(sr),
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, check=True)
    return np.frombuffer(result.stdout, np.int16).flatten().astype(np.float32) / 32768.0


def pad_or_trim(array: np.ndarray, length: int = 480000) -> np.ndarray:
    if array.shape[-1] > length:
        return array[..., :length]
    return np.pad(array, (0, length - array.shape[-1]))
