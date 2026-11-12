"""Localização de recursos em execução normal e em executável PyInstaller."""

from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def asset_path(*parts: str) -> str:
    return str(app_root().joinpath("assets", *parts))
