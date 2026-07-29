"""Ponto de entrada do MaineMed.

`--selfcheck` valida, sem abrir janela, que todos os módulos pesados foram
empacotados corretamente — usado no CI logo após o build do .app.
"""

from __future__ import annotations

import sys


def _selfcheck() -> int:
    import importlib
    from pathlib import Path

    erros: list[str] = []
    modulos = (
        "numpy",
        "sounddevice",
        "tkinter",
        "anthropic",
        "docx",
        "reportlab",
        "huggingface_hub",
        "tiktoken",
        "tiktoken_ext.openai_public",
        "mlx.core",
        "mlx_whisper",
    )
    for mod in modulos:
        try:
            importlib.import_module(mod)
        except Exception as exc:  # noqa: BLE001 - queremos listar qualquer falha
            erros.append(f"{mod}: {exc}")

    if not erros:
        import mlx_whisper

        assets = Path(mlx_whisper.__file__).parent / "assets"
        if not assets.is_dir() or not any(assets.iterdir()):
            erros.append("mlx_whisper/assets ausente do bundle (mel filters/tokenizer)")

    if erros:
        print("SELFCHECK FALHOU:")
        for erro in erros:
            print("  -", erro)
        return 1
    print("SELFCHECK OK")
    return 0


def main() -> int:
    if "--selfcheck" in sys.argv:
        return _selfcheck()

    from mainemed import config

    config.ensure_dirs()
    log = config.setup_logging()
    log.info("MaineMed iniciando")

    def excepthook(tipo, valor, tb):
        log.error("Erro não tratado", exc_info=(tipo, valor, tb))
        try:
            from tkinter import messagebox

            messagebox.showerror(
                "MaineMed",
                f"Erro inesperado:\n{valor}\n\nDetalhes em {config.LOG_DIR}",
            )
        except Exception:
            pass

    sys.excepthook = excepthook

    from mainemed import ui

    ui.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
