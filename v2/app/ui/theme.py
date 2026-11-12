"""Paleta e tipografia da interface v2.2."""

from __future__ import annotations

BG = "#0d0f14"
HEADER = "#11141b"
SIDEBAR = "#101319"
CARD = "#171b24"
CARD_ALT = "#1d2230"
BORDER = "#262c3a"
BORDER_SOFT = "#202532"
TEXT = "#e9ecf3"
TEXT_DIM = "#a7afc0"
MUTED = "#7f889b"
ACCENT = "#e040a0"
ACCENT_HOVER = "#f25bb3"
ACCENT_DARK = "#7c2458"
ACCENT_SOFT = "#2a1523"
CYAN = "#35c9e8"
CYAN_DARK = "#123b46"
GREEN = "#3ddc84"
GREEN_DARK = "#153a27"
AMBER = "#f5b942"
AMBER_DARK = "#3d2f14"
RED = "#ff6b81"
RED_DARK = "#3d1a22"
VIEW_BG = "#080a0e"
SHEET = "#f6f7fa"
SHEET_LINE = "#c9cfdb"

FONT = "Segoe UI"
FONT_SEMI = "Segoe UI Semibold"

SHAPE_VALUES = ("Retângulo", "Oval", "Círculo")


def font(size: int = 12, weight: str = "normal") -> tuple[str, int, str]:
    family = FONT_SEMI if weight in ("bold", "semibold") else FONT
    return family, size, weight


def apply_hover(color: str) -> str:
    """Escurece ligeiramente uma cor hex para estados hover."""

    color = color.lstrip("#")
    r, g, b = (int(color[i : i + 2], 16) for i in (0, 2, 4))
    factor = 0.88
    return "#%02x%02x%02x" % (
        int(r * factor),
        int(g * factor),
        int(b * factor),
    )
