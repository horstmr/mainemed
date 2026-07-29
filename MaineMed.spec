# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller --noconfirm mainemed/MaineMed.spec  (em macOS arm64)
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

spec_dir = Path(SPECPATH).resolve()
src_dir = spec_dir / "src"
app_version = os.environ.get("APP_VERSION", "1.0.0")

datas, binaries, hiddenimports = [], [], []
# collect_all garante os artefatos não-Python: mlx.metallib, assets do
# mlx_whisper (mel filters + vocabulários tiktoken), dados do numba/llvmlite.
for pkg in ("mlx", "mlx_whisper", "anthropic", "numba", "llvmlite"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# tiktoken carrega os plugins de encoding por importlib — invisível à análise
# estática do PyInstaller.
hiddenimports += ["tiktoken_ext", "tiktoken_ext.openai_public"]

a = Analysis(
    [str(src_dir / "mainemed" / "main.py")],
    pathex=[str(src_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["torch", "torchaudio", "matplotlib", "PyQt5", "PyQt6", "PySide6", "IPython", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MaineMed",
    console=False,
    target_arch="arm64",
)

coll = COLLECT(exe, a.binaries, a.datas, name="MaineMed")

app = BUNDLE(
    coll,
    name="MaineMed.app",
    icon=None,
    bundle_identifier="com.mainemed.app",
    version=app_version,
    info_plist={
        "CFBundleName": "MaineMed",
        "CFBundleDisplayName": "MaineMed",
        "CFBundleShortVersionString": app_version,
        "CFBundleVersion": app_version,
        # MLX requer macOS 13.5+
        "LSMinimumSystemVersion": "13.5",
        "NSHighResolutionCapable": True,
        # Sem esta chave o macOS não pede permissão e o microfone grava silêncio.
        "NSMicrophoneUsageDescription": (
            "O MaineMed usa o microfone para gravar a consulta e transcrever "
            "o áudio localmente, neste Mac."
        ),
        "LSApplicationCategoryType": "public.app-category.medical",
    },
)
