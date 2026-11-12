"""Ponto de entrada da DieCUT Tool v2.2."""

from __future__ import annotations

import sys
from pathlib import Path

import customtkinter as ctk

from app.exporters import export_dxf, export_pdf
from app.layout import compute_layout
from app.models import LabelSpec, LayoutSpec, ShapeType, SheetSpec
from app.ui.main_window import MainWindow


def _run_selftest() -> int:
    """Verifica a exportação no ambiente atual (útil para o executável)."""

    try:
        index = sys.argv.index("--selftest")
        output = Path(sys.argv[index + 1]) if len(sys.argv) > index + 1 else Path.cwd()
    except ValueError:
        output = Path.cwd()
    output.mkdir(parents=True, exist_ok=True)

    sheet = SheetSpec(210, 297)
    label = LabelSpec(50, 30, 2, ShapeType.ROUNDED_RECT, 0.4)
    layout = compute_layout(sheet, label, 2, 2, LayoutSpec(3, 9, auto=True))
    pdf_path = output / "selftest.pdf"
    dxf_path = output / "selftest.dxf"
    export_pdf(pdf_path, sheet, label, layout)
    export_dxf(dxf_path, sheet, label, layout)
    return 0 if pdf_path.stat().st_size > 0 and dxf_path.stat().st_size > 0 else 1


def main() -> None:
    if "--selftest" in sys.argv:
        raise SystemExit(_run_selftest())
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
