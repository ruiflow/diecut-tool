"""Leitura de caminhos vetoriais de um PDF.

O ``pdfplumber`` expõe os comandos originais de cada caminho (``m``, ``l``,
``c`` e ``h``), o que permite achatar as curvas de Bézier em polilinhas. Texto
e imagens são ignorados: a importação é apenas para linework vetorial.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Iterator

from ..models import SheetSpec
from .document import ImportedDocument, ImportedPath

MM_PER_POINT = 25.4 / 72.0
BEZIER_STEPS = 12
Point = tuple[float, float]


def _pdfplumber():
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise RuntimeError(
            "A importação de PDF requer a biblioteca pdfplumber. "
            "Instale com: python -m pip install pdfplumber"
        ) from exc
    return pdfplumber


def _distance(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _dedupe(points: Iterable[Point]) -> list[Point]:
    cleaned: list[Point] = []
    for point in points:
        point = (float(point[0]), float(point[1]))
        if not cleaned or _distance(cleaned[-1], point) > 1e-9:
            cleaned.append(point)
    return cleaned


def _cubic(
    p0: Point, p1: Point, p2: Point, p3: Point, t: float
) -> Point:
    """Ponto de uma curva cúbica de Bézier no parâmetro ``t``."""

    mt = 1.0 - t
    a = mt * mt * mt
    b = 3.0 * mt * mt * t
    c = 3.0 * mt * t * t
    d = t * t * t
    return (
        a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
        a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1],
    )


def _flatten_path(
    commands: list[tuple], steps: int = BEZIER_STEPS
) -> list[tuple[list[Point], bool]]:
    """Converte comandos PDF num ou mais caminhos achatados."""

    subpaths: list[tuple[list[Point], bool]] = []
    current: list[Point] = []
    start: Point | None = None
    closed = False

    def flush() -> None:
        nonlocal current, closed
        if len(current) >= 2:
            if not closed and _distance(current[0], current[-1]) <= 1e-6:
                closed = True
                current = current[:-1]
            subpaths.append((current, closed))
        current = []
        closed = False

    for command in commands:
        if not command:
            continue
        operation = command[0]
        if operation == "m":
            flush()
            start = (float(command[1][0]), float(command[1][1]))
            current = [start]
        elif operation == "l":
            point = (float(command[1][0]), float(command[1][1]))
            if not current:
                start = point
                current = [point]
            else:
                current.append(point)
        elif operation == "c":
            if not current:
                start = (float(command[1][0]), float(command[1][1]))
                current = [start]
            p0 = current[-1]
            p1 = (float(command[1][0]), float(command[1][1]))
            p2 = (float(command[2][0]), float(command[2][1]))
            p3 = (float(command[3][0]), float(command[3][1]))
            for step in range(1, steps + 1):
                current.append(_cubic(p0, p1, p2, p3, step / steps))
        elif operation == "h":
            closed = True
            if current and start and _distance(current[-1], start) > 1e-9:
                current.append(start)

    flush()
    return subpaths


def _line_commands(obj: dict) -> tuple[list[tuple], bool]:
    """Linhas usam coordenadas PDF (origem em baixo)."""

    return (
        [
            ("m", (obj["x0"], obj["y0"])),
            ("l", (obj["x1"], obj["y1"])),
        ],
        True,
    )


def _rect_commands(obj: dict) -> tuple[list[tuple], bool]:
    path = obj.get("path")
    if path:
        # O caminho do pdfplumber já está em coordenadas de ecrã (origem em cima).
        return path, False
    x0, y0, x1, y1 = obj["x0"], obj["y0"], obj["x1"], obj["y1"]
    return (
        [
            ("m", (x0, y0)),
            ("l", (x1, y0)),
            ("l", (x1, y1)),
            ("l", (x0, y1)),
            ("h",),
        ],
        True,
    )


def _curve_commands(obj: dict) -> tuple[list[tuple], bool]:
    path = obj.get("path")
    if path:
        return path, False
    points = obj.get("pts") or []
    if not points:
        return [], False
    commands: list[tuple] = [("m", points[0])]
    commands.extend(("l", point) for point in points[1:])
    if len(points) > 2 and _distance(points[0], points[-1]) <= 1e-9:
        commands.append(("h",))
    return commands, False


def _convert(points: list[Point], page_height: float, flip: bool) -> list[Point]:
    """Converte para a aplicação (origem em cima), em mm."""

    if flip:
        return [
            (x * MM_PER_POINT, (page_height - y) * MM_PER_POINT)
            for x, y in points
        ]
    return [(x * MM_PER_POINT, y * MM_PER_POINT) for x, y in points]


def pdf_page_count(path: str | Path) -> int:
    pdfplumber = _pdfplumber()
    with pdfplumber.open(str(path)) as pdf:
        return len(pdf.pages)


def load_pdf(
    path: str | Path,
    *,
    page: int = 1,
    bezier_steps: int = BEZIER_STEPS,
) -> ImportedDocument:
    """Lê uma página de um PDF vetorial e devolve os caminhos em mm."""

    pdfplumber = _pdfplumber()
    source = Path(path)
    with pdfplumber.open(str(source)) as pdf:
        page_count = len(pdf.pages)
        if page_count == 0:
            raise ValueError("O PDF não tem páginas.")
        if page < 1 or page > page_count:
            raise ValueError(
                f"Página inválida: {page}. O PDF tem {page_count} página(s)."
            )

        pdf_page = pdf.pages[page - 1]
        page_height = float(pdf_page.height)
        sheet = SheetSpec(
            float(pdf_page.width) * MM_PER_POINT,
            page_height * MM_PER_POINT,
        )

        stroked: list[ImportedPath] = []
        filled: list[ImportedPath] = []

        def add_commands(
            commands: list[tuple],
            layer: str,
            is_stroked: bool,
            flip: bool,
        ) -> None:
            target = stroked if is_stroked else filled
            for points, closed in _flatten_path(commands, bezier_steps):
                converted = _dedupe(_convert(points, page_height, flip))
                if len(converted) < 2:
                    continue
                target.append(
                    ImportedPath(points=converted, closed=closed, layer=layer)
                )

        for line in pdf_page.lines:
            commands, flip = _line_commands(line)
            add_commands(commands, "linhas", bool(line.get("stroke")), flip)

        for rect in pdf_page.rects:
            commands, flip = _rect_commands(rect)
            add_commands(commands, "retângulos", bool(rect.get("stroke")), flip)

        for curve in pdf_page.curves:
            commands, flip = _curve_commands(curve)
            add_commands(commands, "curvas", bool(curve.get("stroke")), flip)

        warnings: list[str] = []
        paths = stroked
        if not paths:
            paths = filled
            if paths:
                warnings.append(
                    "O PDF não tem traços vetoriais; foram usados os caminhos preenchidos."
                )

        if not paths:
            raise ValueError(
                "PDF sem caminhos vetoriais. Use um PDF vetorial ou importe um DXF."
            )

        if page_count > 1:
            warnings.append(f"Importada a página {page} de {page_count}.")

        layers = sorted({path.layer for path in paths})
        return ImportedDocument(
            sheet=sheet,
            paths=paths,
            source=source,
            kind="pdf",
            layers=layers,
            warnings=warnings,
            page=page,
            page_count=page_count,
        )
