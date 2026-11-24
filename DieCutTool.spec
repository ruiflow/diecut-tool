# -*- mode: python ; coding: utf-8 -*-

import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("customtkinter")
datas += collect_data_files("pdfplumber")
datas += collect_data_files("pdfminer")
datas += [
    ("assets/icon.ico", "assets"),
    ("assets/icon.png", "assets"),
]

hiddenimports = collect_submodules("pdfminer") + collect_submodules("pdfplumber")

# Em builds free-threaded (abi3t) a extensão Rust do cryptography depende de
# python3t.dll, que vive numa pasta de compatibilidade fora do sys.path.
binaries = []
_compat = os.path.join(sys.base_prefix, "abi3t-compat")
if os.path.isdir(_compat):
    binaries += [
        (os.path.join(_compat, name), ".")
        for name in os.listdir(_compat)
        if name.lower().endswith(".dll")
    ]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DieCutTool v4",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)
