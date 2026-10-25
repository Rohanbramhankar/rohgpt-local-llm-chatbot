# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_dir = Path.cwd()
hiddenimports = []
datas = [
    (str(project_dir / "templates"), "templates"),
    (str(project_dir / "static"), "static"),
    (str(project_dir / "staticfiles"), "staticfiles"),
]

for package in ("chatbot", "config", "webview", "markdown", "pygments", "whitenoise"):
    hiddenimports += collect_submodules(package)
    if package in ("webview", "markdown", "pygments", "whitenoise"):
        datas += collect_data_files(package)

datas += collect_data_files("django")

analysis = Analysis(
    ["desktop.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="RohGPT",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

if sys.platform == "darwin":
    application = BUNDLE(
        executable,
        name="RohGPT.app",
        bundle_identifier="com.rohangpt.desktop",
    )
