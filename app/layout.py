"""Cálculo de distribuição das etiquetas na folha."""

from __future__ import annotations

import math

from .models import LabelSpec, LayoutResult, LayoutSpec, SheetSpec

EPSILON = 1e-6
MAX_AUTO_LABELS = 4000


def auto_grid(
    sheet: SheetSpec,
    label: LabelSpec,
    spacing_h: float,
    spacing_v: float,
) -> tuple[int, int]:
    """Número máximo de colunas/fileiras que cabem na folha."""

    if not sheet.is_valid or not label.is_valid:
        return 0, 0

    spacing_h = max(0.0, spacing_h)
    spacing_v = max(0.0, spacing_v)
    cell_w = max(label.width, 0.001)
    cell_h = max(label.height, 0.001)

    cols = math.floor((sheet.width + spacing_h) / (cell_w + spacing_h) + EPSILON)
    rows = math.floor((sheet.height + spacing_v) / (cell_h + spacing_v) + EPSILON)
    return max(0, cols), max(0, rows)


def _offset(usable: float, block: float, align: str) -> float:
    if align == "Centro":
        return (usable - block) / 2.0
    if align in ("Direita", "Baixo"):
        return usable - block
    return 0.0


def compute_layout(
    sheet: SheetSpec,
    label: LabelSpec,
    spacing_h: float,
    spacing_v: float,
    spec: LayoutSpec,
) -> LayoutResult:
    """Calcula posições, limites e avisos do layout."""

    result = LayoutResult(columns=max(0, spec.columns), rows=max(0, spec.rows))
    if not sheet.is_valid or not label.is_valid or spec.columns <= 0 or spec.rows <= 0:
        result.warnings.append("Dimensões inválidas ou quantidade de etiquetas igual a zero.")
        return result

    spacing_h = max(0.0, spacing_h)
    spacing_v = max(0.0, spacing_v)

    cell_w = label.width
    cell_h = label.height
    block_w = spec.columns * cell_w + max(0, spec.columns - 1) * spacing_h
    block_h = spec.rows * cell_h + max(0, spec.rows - 1) * spacing_v

    result.cell_width = cell_w
    result.cell_height = cell_h
    result.block_width = block_w
    result.block_height = block_h

    result.overflow_x = max(0.0, block_w - sheet.width)
    result.overflow_y = max(0.0, block_h - sheet.height)
    result.fits = result.overflow_x <= EPSILON and result.overflow_y <= EPSILON

    origin_x = _offset(sheet.width, block_w, spec.align_h)
    origin_y = _offset(sheet.height, block_h, spec.align_v)

    positions: list[tuple[float, float]] = []
    for row in range(spec.rows):
        for col in range(spec.columns):
            positions.append(
                (
                    origin_x + col * (cell_w + spacing_h),
                    origin_y + row * (cell_h + spacing_v),
                )
            )
    result.positions = positions

    if not result.fits:
        parts = []
        if result.overflow_x > EPSILON:
            parts.append(f"{result.overflow_x:.1f} mm na horizontal")
        if result.overflow_y > EPSILON:
            parts.append(f"{result.overflow_y:.1f} mm na vertical")
        result.warnings.append("O layout excede a folha em " + " e ".join(parts) + ".")
    if result.count > MAX_AUTO_LABELS:
        result.warnings.append(
            "Demasiadas etiquetas: a pré-visualização usa um modo simplificado."
        )
    return result


def shape_origin(
    label: LabelSpec, cell_x: float, cell_y: float, cell_w: float, cell_h: float
) -> tuple[float, float]:
    """Origem do caminho dentro da célula.

    A compensação é uma sobreposição de caminho e não altera a caixa da
    etiqueta, por isso a origem coincide com a célula do layout.
    """

    return cell_x, cell_y
