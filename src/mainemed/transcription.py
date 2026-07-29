"""Transcrição local com Whisper sobre MLX (GPU dos chips Apple M).

O áudio é passado como array numpy 16 kHz mono float32, o que dispensa
ffmpeg no bundle. O modelo é baixado do Hugging Face na primeira
utilização, para HF_HOME (Application Support), e depois roda offline.
"""

from __future__ import annotations

import numpy as np

from mainemed import config

DEFAULT_REPO = "mlx-community/whisper-large-v3-turbo"


class TranscriptionError(RuntimeError):
    pass


def model_cached(repo: str = DEFAULT_REPO) -> bool:
    safe = "models--" + repo.replace("/", "--")
    snapshot = config.MODELS_DIR / "hub" / safe
    try:
        return snapshot.is_dir() and any(snapshot.rglob("*.json"))
    except OSError:
        return False


def transcrever(audio_f32: np.ndarray, repo: str = DEFAULT_REPO, language: str = "pt") -> str:
    if audio_f32.size < 1600:  # menos de 0,1 s de áudio
        raise TranscriptionError("A gravação ficou vazia. Grave novamente.")
    try:
        import mlx_whisper
    except Exception as exc:
        raise TranscriptionError(
            "Falha ao carregar o mecanismo de transcrição. "
            "Este aplicativo requer um Mac com chip Apple (M1 ou mais novo)."
        ) from exc
    try:
        result = mlx_whisper.transcribe(
            audio_f32, path_or_hf_repo=repo, language=language, task="transcribe"
        )
    except Exception as exc:
        texto = str(exc).lower()
        rede = ("connection", "resolve", "timed out", "timeout", "offline", "http", "ssl", "proxy")
        if any(token in texto for token in rede):
            raise TranscriptionError(
                "Não foi possível baixar o modelo de transcrição.\n\n"
                "Na primeira gravação o MaineMed baixa o modelo (≈1,6 GB) e "
                "precisa de internet. Conecte-se e tente de novo."
            ) from exc
        raise TranscriptionError(f"Erro na transcrição: {exc}") from exc

    text = (result.get("text") or "").strip()
    if not text:
        raise TranscriptionError(
            "Nenhuma fala foi reconhecida na gravação.\n\n"
            "Verifique se o microfone captou áudio (barra de nível durante a "
            "gravação) e a permissão em Ajustes do Sistema → Privacidade e "
            "Segurança → Microfone."
        )
    return text
