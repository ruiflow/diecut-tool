"""Ponto de entrada da DieCUT Tool v4."""

from __future__ import annotations

import sys
from pathlib import Path

import customtkinter as ctk

from app.cutting import build_cut_plan, build_imported_cut_plan
from app.exporters import (
    export_cut_plan_dxf,
    export_cut_plan_pdf,
    export_dxf,
    export_pdf,
)
from app.importers import load_dxf, load_pdf
from app.layout import compute_layout
from app.models import LabelSpec, LayoutSpec, ShapeType, SheetSpec
from app.ui.main_window import MainWindow


def _run_selftest() -> int:
    """Verifica exportação, importação e percurso no ambiente atual."""

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

    if pdf_path.stat().st_size <= 0 or dxf_path.stat().st_size <= 0:
        return 1

    try:
        plan = build_cut_plan(label, layout, sheet=sheet)
        build_imported_cut_plan(load_pdf(pdf_path))
        build_imported_cut_plan(load_dxf(dxf_path))
        export_cut_plan_pdf(output / "selftest_corte.pdf", sheet, plan)
        export_cut_plan_dxf(output / "selftest_corte.dxf", sheet, plan)
    except Exception as exc:  # pragma: no cover - diagnóstico do executável
        import traceback

        detail = traceback.format_exc()
        print(f"selftest: {exc}", file=sys.stderr)
        try:
            (output / "selftest-error.txt").write_text(detail, encoding="utf-8")
        except OSError:
            pass
        return 2

    return 0


def main() -> None:
    if "--selftest" in sys.argv:
        raise SystemExit(_run_selftest())
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
