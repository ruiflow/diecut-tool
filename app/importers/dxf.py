"""Leitura de ficheiros DXF para um :class:`ImportedDocument`.

O ``ezdxf`` já é uma dependência da exportação, pelo que a importação usa o
mesmo motor. As entidades vetoriais são convertidas em polilinhas achatadas,
independentemente de serem linhas, arcos, círculos, elipses, splines ou
polilinhas com ``bulge``.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Iterator

import ezdxf
from ezdxf import disassemble
from ezdxf import path as ezpath
from ezdxf import units

from .. import geometry
from ..models import SheetSpec
from .document import ImportedDocument, ImportedPath

Point = geometry.Point

FLATTEN_DISTANCE = 0.25
MM_UNIT = 4


def _conversion_factor(unit_code: int) -> float:
    """Fator de conversão das unidades do DXF para milímetros."""

    if unit_code <= 0:
        return 1.0
    try:
        return float(units.conversion_factor(unit_code, MM_UNIT))
    except Exception:
        return 1.0


def _iter_entities(msp) -> Iterator:
    """Percorre entidades, expandindo blocos inseridos (INSERT)."""

    for entity in msp:
        try:
            yield from disassemble.recursive_decompose([entity])
        except Exception:
            yield entity


def _distance(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _dedupe(points: Iterable[Point]) -> list[Point]:
    cleaned: list[Point] = []
    for point in points:
        if not cleaned or _distance(cleaned[-1], point) > 1e-9:
            cleaned.append((float(point[0]), float(point[1])))
    return cleaned


def _entity_paths(entity, flatten_distance: float) -> list[tuple[list[Point], bool]]:
    try:
        path = ezpath.make_path(entity)
    except Exception:
        return []
    if path is None:
        return []
    try:
        vertices = list(path.flattening(flatten_distance))
    except Exception:
        return []

    points = _dedupe((vertex.x, vertex.y) for vertex in vertices)
    if len(points) < 2:
        return []

    closed = bool(getattr(path, "is_closed", False))
    if closed and _distance(points[0], points[-1]) <= 1e-9:
        points = points[:-1]
    if len(points) < 2:
        return []
    return [(points, closed)]


def _used_layers(msp) -> list[str]:
    layers: set[str] = set()
    for entity in _iter_entities(msp):
        try:
            layers.add(str(entity.dxf.get("layer", "0")))
        except Exception:
            continue
    return sorted(layers)


def dxf_layers(path: str | Path) -> list[str]:
    """Lista as camadas usadas por um DXF."""

    doc = ezdxf.readfile(str(path))
    return _used_layers(doc.modelspace())


def load_dxf(
    path: str | Path,
    *,
    layers: Iterable[str] | None = None,
    flatten_distance: float = FLATTEN_DISTANCE,
) -> ImportedDocument:
    """Lê um DXF e devolve os caminhos normalizados em milímetros."""

    source = Path(path)
    doc = ezdxf.readfile(str(source))
    unit_code = int(doc.header.get("$INSUNITS", 0) or 0)
    factor = _conversion_factor(unit_code)
    msp = doc.modelspace()

    selected = {str(name) for name in layers} if layers is not None else None
    raw_paths: list[tuple[list[Point], bool, str]] = []
    warnings: list[str] = []

    for entity in _iter_entities(msp):
        try:
            layer = str(entity.dxf.get("layer", "0"))
        except Exception:
            layer = "0"
        if selected is not None and layer not in selected:
            continue
        for points, closed in _entity_paths(entity, flatten_distance):
            if len(points) < 2:
                continue
            raw_paths.append((points, closed, layer))

    if not raw_paths:
        raise ValueError(
            "O DXF não contém caminhos vetoriais suportados nas camadas escolhidas."
        )

    xs = [point[0] for points, _closed, _layer in raw_paths for point in points]
    ys = [point[1] for points, _closed, _layer in raw_paths for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = (max_x - min_x) * factor
    height = (max_y - min_y) * factor

    if width <= 1e-6 or height <= 1e-6:
        raise ValueError("O DXF tem dimensões degeneradas (largura ou altura zero).")

    if unit_code not in (0, MM_UNIT):
        warnings.append(
            f"Unidades DXF convertidas para milímetros (código $INSUNITS={unit_code})."
        )

    imported: list[ImportedPath] = []
    for points, closed, layer in raw_paths:
        converted = [
            ((x - min_x) * factor, (max_y - y) * factor) for x, y in points
        ]
        converted = _dedupe(converted)
        if len(converted) < 2:
            continue
        imported.append(ImportedPath(points=converted, closed=closed, layer=layer))

    if not imported:
        raise ValueError("O DXF não contém caminhos válidos após a normalização.")

    used_layers = sorted({path.layer for path in imported})
    return ImportedDocument(
        sheet=SheetSpec(width, height),
        paths=imported,
        source=source,
        kind="dxf",
        layers=used_layers,
        warnings=warnings,
    )
