"""Gravação de áudio do microfone (PortAudio via sounddevice).

Grava a 16 kHz mono float32 — o formato que o Whisper consome direto,
sem precisar de ffmpeg para decodificar.
"""

from __future__ import annotations

import threading
import time
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000


class AudioError(RuntimeError):
    pass


class Recorder:
    def __init__(self) -> None:
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream = None
        self._t0: float | None = None
        self.level = 0.0

    def start(self) -> None:
        try:
            import sounddevice as sd
        except Exception as exc:
            raise AudioError("Falha ao carregar o componente de áudio.") from exc

        def callback(indata, frames, _time, _status):
            with self._lock:
                self._chunks.append(indata.copy())
            self.level = float(np.abs(indata).max()) if len(indata) else 0.0

        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback
            )
            self._stream.start()
        except Exception as exc:
            self._stream = None
            raise AudioError(
                "Não foi possível acessar o microfone.\n\n"
                "Verifique em Ajustes do Sistema → Privacidade e Segurança → "
                "Microfone se o MaineMed está autorizado."
            ) from exc
        self._t0 = time.monotonic()

    @property
    def recording(self) -> bool:
        return self._stream is not None

    @property
    def elapsed(self) -> float:
        return 0.0 if self._t0 is None else time.monotonic() - self._t0

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None
        with self._lock:
            if not self._chunks:
                return np.zeros(0, dtype=np.float32)
            data = np.concatenate(self._chunks, axis=0)
        return np.ascontiguousarray(data[:, 0])

    @staticmethod
    def save_wav(path: Path, data: np.ndarray) -> None:
        pcm = (np.clip(data, -1.0, 1.0) * 32767.0).astype("<i2")
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(pcm.tobytes())
