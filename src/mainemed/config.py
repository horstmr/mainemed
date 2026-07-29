"""Diretórios, configuração e logging do MaineMed.

App assinado não pode escrever dentro do próprio bundle, então tudo
(config, modelos Whisper, consultas, logs) vai para Application Support.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

APP_NAME = "MaineMed"

if sys.platform == "darwin":
    APP_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
else:
    APP_DIR = Path.home() / ".mainemed"

MODELS_DIR = APP_DIR / "models"
CONSULTAS_DIR = APP_DIR / "consultas"
LOG_DIR = APP_DIR / "logs"
CONFIG_PATH = APP_DIR / "config.json"

DEFAULTS = {
    "api_key": "",
    "model": "claude-opus-5",
    "whisper_model": "mlx-community/whisper-large-v3-turbo",
    "language": "pt",
}


def ensure_dirs() -> None:
    for d in (APP_DIR, MODELS_DIR, CONSULTAS_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)
    # HF_HOME precisa apontar para fora do bundle antes de qualquer import
    # do huggingface_hub, senão o download do modelo tenta escrever no .app.
    os.environ.setdefault("HF_HOME", str(MODELS_DIR))
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def load() -> dict:
    ensure_dirs()
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            stored = json.load(fh)
        if isinstance(stored, dict):
            cfg.update({k: v for k, v in stored.items() if k in DEFAULTS})
    except FileNotFoundError:
        pass
    except Exception:
        logging.getLogger(APP_NAME).warning("config.json ilegível; usando padrões", exc_info=True)
    return cfg


def save(cfg: dict) -> None:
    ensure_dirs()
    data = {k: cfg.get(k, DEFAULTS[k]) for k in DEFAULTS}
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass


def setup_logging() -> logging.Logger:
    ensure_dirs()
    logger = logging.getLogger(APP_NAME)
    if not logger.handlers:
        handler = RotatingFileHandler(
            LOG_DIR / "mainemed.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
