"""Exportação das dielines para PDF e DXF."""

from __future__ import annotations

import math
from pathlib import Path

import ezdxf
from reportlab.lib.units import mm as mm_unit
from reportlab.pdfgen import canvas as pdf_canvas

from . import geometry
from .cutting import KIND_CUT, CutPlan
from .layout import shape_origin
from .models import LabelSpec, LayoutResult, ShapeType, SheetSpec

ACCENT_RGB = (0.878, 0.251, 0.627)  # #e040a0
DIELINE_LAYER = "DIELINE"
CUT_LAYER = "CORTE"
TRAVEL_LAYER = "DESLOCAMENTO"
BULGE_90 = math.tan(math.radians(90.0) / 4.0)  # 0.4142...


def _pdf_shape(
    c: pdf_canvas.Canvas,
    label: LabelSpec,
    x: float,
    y: float,
    sheet_height: float,
) -> None:
    width = label.width
    height = label.height
    bottom = sheet_height - y - height

    if label.shape is ShapeType.CIRCLE:
        diameter = min(width, height)
        cx = x + width / 2.0
        cy = bottom + height / 2.0
        c.circle(cx * mm_unit, cy * mm_unit, (diameter / 2.0) * mm_unit, stroke=1, fill=0)
        return

    if label.shape is ShapeType.ELLIPSE:
        c.ellipse(
            x * mm_unit,
            bottom * mm_unit,
            (x + width) * mm_unit,
            (bottom + height) * mm_unit,
            stroke=1,
            fill=0,
        )
        return

    radius = label.effective_radius
    c.roundRect(
        x * mm_unit,
        bottom * mm_unit,
        width * mm_unit,
        height * mm_unit,
        radius * mm_unit,
        stroke=1,
        fill=0,
    )


def _pdf_overlap_path(
    c: pdf_canvas.Canvas,
    label: LabelSpec,
    x: float,
    y: float,
    sheet_height: float,
) -> None:
    """Desenha o caminho completo com a sobreposição inicial (overlap)."""

    path = geometry.dieline_path(label, x, y, quality="export")
    if len(path.points) < 2:
        return
    point = c.beginPath()
    first_x, first_y = path.points[0]
    point.moveTo(first_x * mm_unit, (sheet_height - first_y) * mm_unit)
    for px, py in path.points[1:]:
        point.lineTo(px * mm_unit, (sheet_height - py) * mm_unit)
    if path.closed:
        point.close()
    c.drawPath(point, stroke=1, fill=0)


def export_pdf(
    path: str | Path,
    sheet: SheetSpec,
    label: LabelSpec,
    layout: LayoutResult,
) -> None:
    """Gera um PDF vetorial com uma página do tamanho exato da folha."""

    c = pdf_canvas.Canvas(
        str(path), pagesize=(sheet.width * mm_unit, sheet.height * mm_unit)
    )
    c.setTitle("DieCUT Tool v2.2 - Dielines")
    c.setAuthor("DieCUT Tool")
    c.setSubject(f"{layout.columns} x {layout.rows} etiquetas - {label.shape.value}")
    c.setStrokeColorRGB(*ACCENT_RGB)
    c.setLineWidth(0.35 * mm_unit)
    c.setLineJoin(1)

    for cell_x, cell_y in layout.positions:
        x, y = shape_origin(label, cell_x, cell_y, layout.cell_width, layout.cell_height)
        if label.overlap > 1e-9:
            _pdf_overlap_path(c, label, x, y, sheet.height)
        else:
            _pdf_shape(c, label, x, y, sheet.height)

    c.showPage()
    c.save()


def _dxf_rect(
    msp,
    label: LabelSpec,
    x: float,
    y_bottom: float,
) -> None:
    width = label.width
    height = label.height
    radius = label.effective_radius

    if radius <= 1e-9:
        points = [
            (x, y_bottom, 0.0),
            (x + width, y_bottom, 0.0),
            (x + width, y_bottom + height, 0.0),
            (x, y_bottom + height, 0.0),
        ]
    else:
        # Vértices com bulge: cada quarto de círculo tem bulge = tan(90°/4).
        points = [
            (x + radius, y_bottom, 0.0),
            (x + width - radius, y_bottom, BULGE_90),
            (x + width, y_bottom + radius, 0.0),
            (x + width, y_bottom + height - radius, BULGE_90),
            (x + width - radius, y_bottom + height, 0.0),
            (x + radius, y_bottom + height, BULGE_90),
            (x, y_bottom + height - radius, 0.0),
            (x, y_bottom + radius, BULGE_90),
        ]

    msp.add_lwpolyline(
        points,
        format="xyb",
        close=True,
        dxfattribs={"layer": DIELINE_LAYER},
    )


def _dxf_ellipse(
    msp,
    label: LabelSpec,
    x: float,
    y_bottom: float,
) -> None:
    width = label.width
    height = label.height
    cx = x + width / 2.0
    cy = y_bottom + height / 2.0

    if label.shape is ShapeType.CIRCLE:
        diameter = min(width, height)
        msp.add_circle(
            (cx, cy),
            diameter / 2.0,
            dxfattribs={"layer": DIELINE_LAYER},
        )
        return

    if width >= height:
        major_axis = (width / 2.0, 0.0)
        ratio = height / width if width else 1.0
    else:
        major_axis = (0.0, height / 2.0)
        ratio = width / height if height else 1.0

    msp.add_ellipse(
        (cx, cy),
        major_axis=major_axis,
        ratio=max(0.0001, min(1.0, ratio)),
        dxfattribs={"layer": DIELINE_LAYER},
    )


def _dxf_overlap_path(
    msp,
    label: LabelSpec,
    x: float,
    y: float,
    sheet_height: float,
) -> None:
    """LWPOLYLINE aberta com a volta completa e o troço de sobreposição."""

    path = geometry.dieline_path(label, x, y, quality="export")
    points = [(px, sheet_height - py) for px, py in path.points]
    if len(points) < 2:
        return
    msp.add_lwpolyline(
        points,
        format="xy",
        close=False,
        dxfattribs={"layer": DIELINE_LAYER},
    )


def export_dxf(
    path: str | Path,
    sheet: SheetSpec,
    label: LabelSpec,
    layout: LayoutResult,
) -> None:
    """Gera um DXF em milímetros com as dielines no layer DIELINE."""

    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1

    layer = doc.layers.add(DIELINE_LAYER, color=6)
    layer.dxf.linetype = "CONTINUOUS"
    try:
        layer.rgb = (224, 64, 160)
    except (AttributeError, ValueError):
        pass

    msp = doc.modelspace()
    for cell_x, cell_y in layout.positions:
        x, y = shape_origin(label, cell_x, cell_y, layout.cell_width, layout.cell_height)
        y_bottom = sheet.height - y - label.height
        if label.overlap > 1e-9:
            _dxf_overlap_path(msp, label, x, y, sheet.height)
        elif label.shape is ShapeType.ROUNDED_RECT:
            _dxf_rect(msp, label, x, y_bottom)
        else:
            _dxf_ellipse(msp, label, x, y_bottom)

    doc.set_modelspace_vport(
        height=max(sheet.height, 1.0),
        center=(sheet.width / 2.0, sheet.height / 2.0),
    )
    doc.saveas(str(path))


def export_cut_plan_pdf(
    path: str | Path,
    sheet: SheetSpec,
    plan: CutPlan,
) -> None:
    """Gera um PDF com o percurso da simulação, pela ordem calculada."""

    c = pdf_canvas.Canvas(
        str(path), pagesize=(sheet.width * mm_unit, sheet.height * mm_unit)
    )
    c.setTitle("DieCUT Tool v2.2 - Percurso de corte")
    c.setAuthor("DieCUT Tool")
    c.setSubject(
        f"Percurso {plan.strategy} - {plan.label_count} etiquetas - "
        f"{plan.lift_count} elevacoes"
    )
    c.setLineJoin(1)

    for segment in plan.segments:
        if len(segment.points) < 2:
            continue
        point = c.beginPath()
        first_x, first_y = segment.points[0]
        point.moveTo(first_x * mm_unit, (sheet.height - first_y) * mm_unit)
        for px, py in segment.points[1:]:
            point.lineTo(px * mm_unit, (sheet.height - py) * mm_unit)

        if segment.kind == KIND_CUT:
            c.setStrokeColorRGB(*ACCENT_RGB)
            c.setLineWidth(0.35 * mm_unit)
            c.setDash()
        else:
            c.setStrokeColorRGB(0.20, 0.75, 0.86)
            c.setLineWidth(0.25 * mm_unit)
            c.setDash(2, 2)
        c.drawPath(point, stroke=1, fill=0)

    c.showPage()
    c.save()


def export_cut_plan_dxf(
    path: str | Path,
    sheet: SheetSpec,
    plan: CutPlan,
) -> None:
    """Gera um DXF com o percurso otimizado, pela ordem da simulação.

    O layer ``CORTE`` contém os traços com a lâmina em baixo (incluindo os
    contornos encostados cortados num só trilho) e o layer ``DESLOCAMENTO``
    contém os movimentos em vazio. Este último é marcado para não ser plotado,
    mas fica visível em qualquer programa de CAD.
    """

    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1

    cut_layer = doc.layers.add(CUT_LAYER, color=6)
    cut_layer.dxf.linetype = "CONTINUOUS"
    try:
        cut_layer.rgb = (224, 64, 160)
    except (AttributeError, ValueError):
        pass

    travel_layer = doc.layers.add(TRAVEL_LAYER, color=4)
    try:
        travel_layer.dxf.linetype = "DASHED"
    except (AttributeError, ValueError):
        pass
    try:
        travel_layer.dxf.plot = 0
    except (AttributeError, ValueError):
        pass

    msp = doc.modelspace()
    run: list[tuple[float, float]] = []

    def flush_run() -> None:
        nonlocal run
        if len(run) >= 2:
            msp.add_lwpolyline(
                run,
                format="xy",
                close=False,
                dxfattribs={"layer": CUT_LAYER},
            )
        run = []

    for segment in plan.segments:
        if len(segment.points) < 2:
            continue
        points = [(px, sheet.height - py) for px, py in segment.points]
        if segment.kind == KIND_CUT:
            if run and segment.linked:
                # Continua o traço anterior sem levantar a lâmina: uma única
                # polilinha, para a plotter não cortar em dois movimentos.
                run.extend(points[1:])
            else:
                flush_run()
                run = points
        else:
            flush_run()
            msp.add_line(
                points[0],
                points[1],
                dxfattribs={"layer": TRAVEL_LAYER},
            )
    flush_run()

    doc.set_modelspace_vport(
        height=max(sheet.height, 1.0),
        center=(sheet.width / 2.0, sheet.height / 2.0),
    )
    doc.saveas(str(path))
