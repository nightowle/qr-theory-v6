# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Spec für den QR-Automation-CLI-Launcher.

Dieses Skript bündelt `qr_automation.cli` zu einem Windows-Executable,
inklusive Standardkonfiguration und README.
"""
from __future__ import annotations

from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
cli_entry = project_root / "qr_automation" / "cli.py"

if not cli_entry.exists():
    raise FileNotFoundError(f"CLI-Einstiegspunkt wurde nicht gefunden: {cli_entry}")

# Daten (z.B. Beispielkonfiguration) für das Executable verfügbar machen.
extra_data = [
    (project_root / "documentation" / "gateway-config.sample.yaml", "documentation"),
    (project_root / "README.md", "."),
]

datas = [
    (str(source), target)
    for source, target in extra_data
    if source.exists()
]

hidden_imports = [
    "asyncio",
    "fastapi",
    "pydantic",
    "pydantic_core",
    "sqlalchemy",
    "uvicorn",
    "uvicorn.lifespan.on",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "yaml",
]

block_cipher = None


a = Analysis(
    [str(cli_entry)],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="qr-automation",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    version=str(project_root / "deployment" / "pyinstaller" / "qr_automation_cli_version.txt"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="qr-automation",
)
