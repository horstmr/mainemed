"""Proveniência dos textos de cada consulta.

O que a médica assina/usa é o texto revisado por ela, nunca a saída bruta
do Whisper — mas os dois ficam guardados, com autoria de máquina/humano
marcada, para o caso de discussão sobre erro de transcrição.

Arquivos por consulta:
  audio.wav                 gravação
  transcricao-original.txt  saída bruta do Whisper (nunca sobrescrita)
  transcricao-revisada.txt  texto usado no prontuário, se editado
  prontuario-gerado.txt     saída bruta do modelo de linguagem
  prontuario-final.txt      versão aprovada (copiada/exportada)
  consulta.json             modelos usados e timestamp de cada etapa
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from mainemed import __version__

META = "consulta.json"


def _load(consulta_dir: Path) -> dict:
    try:
        return json.loads((consulta_dir / META).read_text(encoding="utf-8"))
    except Exception:
        return {}


def registrar(consulta_dir: Path, etapa: str, **info) -> None:
    consulta_dir.mkdir(parents=True, exist_ok=True)
    meta = _load(consulta_dir)
    meta.setdefault("app_version", __version__)
    meta.setdefault("etapas", {})[etapa] = {
        "quando": datetime.now().isoformat(timespec="seconds"),
        **info,
    }
    (consulta_dir / META).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )


def salvar_texto(consulta_dir: Path, nome: str, texto: str) -> None:
    consulta_dir.mkdir(parents=True, exist_ok=True)
    (consulta_dir / nome).write_text(texto, encoding="utf-8")


def texto_salvo(consulta_dir: Path | None, nome: str) -> str:
    if consulta_dir is None:
        return ""
    try:
        return (consulta_dir / nome).read_text(encoding="utf-8")
    except OSError:
        return ""
