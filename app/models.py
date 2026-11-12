"""Modelos de domínio da DieCUT Tool v3.

Mantém os cálculos independentes da interface: a UI apenas lê e escreve
nestas estruturas, o que facilita testes e exportação.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ShapeType(str, Enum):
    """Formatos de etiqueta suportados."""

    ROUNDED_RECT = "Retângulo"
    ELLIPSE = "Oval"
    CIRCLE = "Círculo"


ALIGN_H = ("Esquerda", "Centro", "Direita")
ALIGN_V = ("Topo", "Centro", "Baixo")

# Dimensão mínima de uma dieline, para nunca gerar geometria degenerada.
MIN_SIZE_MM = 0.2


@dataclass(frozen=True)
class SheetSpec:
    """Folha onde as etiquetas são distribuídas (medidas em mm).

    A folha é usada por inteiro: não existe margem de segurança, pelo que a
    área útil coincide com a área total.
    """

    width: float
    height: float

    @property
    def is_valid(self) -> bool:
        return self.width > MIN_SIZE_MM and self.height > MIN_SIZE_MM

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)


@dataclass(frozen=True)
class LabelSpec:
    """Etiqueta/dieline.

    `compensation` é o comprimento de sobreposição (mm) no início do caminho,
    para a lâmina fechar o corte. Não altera as dimensões da etiqueta.
    """

    width: float
    height: float
    corner_radius: float = 0.0
    shape: ShapeType = ShapeType.ROUNDED_RECT
    compensation: float = 0.0

    @property
    def is_valid(self) -> bool:
        return self.width > MIN_SIZE_MM and self.height > MIN_SIZE_MM

    @property
    def overlap(self) -> float:
        """Sobreposição efetiva do caminho, em mm (nunca negativa)."""

        return max(0.0, self.compensation)

    @property
    def effective_radius(self) -> float:
        return min(
            max(0.0, self.corner_radius),
            self.width / 2.0,
            self.height / 2.0,
        )


@dataclass(frozen=True)
class LayoutSpec:
    columns: int
    rows: int
    align_h: str = "Centro"
    align_v: str = "Centro"
    auto: bool = False


@dataclass
class LayoutResult:
    positions: list[tuple[float, float]] = field(default_factory=list)
    columns: int = 0
    rows: int = 0
    cell_width: float = 0.0
    cell_height: float = 0.0
    block_width: float = 0.0
    block_height: float = 0.0
    fits: bool = False
    overflow_x: float = 0.0
    overflow_y: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.positions)
