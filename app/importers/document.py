"""Modelos de um documento importado (DXF ou PDF).

Os pontos seguem o mesmo sistema da aplicação: milímetros, origem no canto
superior esquerdo da folha e eixo Y a crescer para baixo. Os leitores tratam
da conversão a partir das unidades originais de cada formato.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .. import geometry
from ..models import SheetSpec

Point = geometry.Point


@dataclass
class ImportedPath:
    """Caminho vetorial lido de um ficheiro importado."""

    points: list[Point] = field(default_factory=list)
    closed: bool = False
    layer: str = ""

    @property
    def length(self) -> float:
        return geometry.polyline_length(self.points)

    @property
    def is_valid(self) -> bool:
        return len(self.points) >= 2 and self.length > 1e-9


@dataclass
class ImportedDocument:
    """Conjunto de caminhos prontos a simular e exportar."""

    sheet: SheetSpec
    paths: list[ImportedPath] = field(default_factory=list)
    source: Path = field(default_factory=Path)
    kind: str = "dxf"
    layers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    page: int = 1
    page_count: int = 1

    @property
    def path_count(self) -> int:
        return len(self.paths)

    @property
    def closed_count(self) -> int:
        return sum(1 for path in self.paths if path.closed)

    @property
    def total_length(self) -> float:
        return sum(path.length for path in self.paths)

    @property
    def is_empty(self) -> bool:
        return not self.paths or self.total_length <= 1e-9

    @property
    def title(self) -> str:
        return self.source.name or "documento importado"

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        points = [point for path in self.paths for point in path.points]
        if not points:
            return (0.0, 0.0, 0.0, 0.0)
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        return (min(xs), min(ys), max(xs), max(ys))
