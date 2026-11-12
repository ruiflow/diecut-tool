"""Geometria das dielines: pontos do caminho, área e projeção isométrica."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .models import LabelSpec, ShapeType

Point = tuple[float, float]


def rounded_rect_points(
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float,
    segments_per_corner: int = 8,
) -> list[Point]:
    """Contorno de um retângulo arredondado, por ordem horária (y para baixo)."""

    radius = max(0.0, min(radius, width / 2.0, height / 2.0))
    if radius <= 1e-9:
        return [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]

    points: list[Point] = []
    corners = (
        (x + width - radius, y + radius, 270.0, 360.0),  # canto superior direito
        (x + width - radius, y + height - radius, 0.0, 90.0),  # inferior direito
        (x + radius, y + height - radius, 90.0, 180.0),  # inferior esquerdo
        (x + radius, y + radius, 180.0, 270.0),  # superior esquerdo
    )
    for cx, cy, start, end in corners:
        for index in range(segments_per_corner + 1):
            angle = math.radians(start + (end - start) * index / segments_per_corner)
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def ellipse_points(
    x: float,
    y: float,
    width: float,
    height: float,
    segments: int = 72,
) -> list[Point]:
    """Contorno de uma elipse, por ordem horária (y para baixo)."""

    cx = x + width / 2.0
    cy = y + height / 2.0
    rx = width / 2.0
    ry = height / 2.0
    segments = max(12, segments)
    return [
        (cx + rx * math.cos(2.0 * math.pi * i / segments),
         cy + ry * math.sin(2.0 * math.pi * i / segments))
        for i in range(segments)
    ]


def contour_points(
    label: LabelSpec,
    x: float,
    y: float,
    *,
    quality: str = "high",
) -> list[Point]:
    """Contorno fechado da etiqueta (sem sobreposição), numa posição."""

    width = label.width
    height = label.height
    if width <= 0 or height <= 0:
        return []

    if quality == "export":
        corner_segments, ellipse_segments = 24, 160
    elif quality == "low":
        corner_segments, ellipse_segments = 4, 48
    else:
        corner_segments, ellipse_segments = 10, 96

    if label.shape is ShapeType.CIRCLE:
        diameter = min(width, height)
        cx = x + width / 2.0
        cy = y + height / 2.0
        return ellipse_points(
            cx - diameter / 2.0,
            cy - diameter / 2.0,
            diameter,
            diameter,
            ellipse_segments,
        )

    if label.shape is ShapeType.ELLIPSE:
        return ellipse_points(x, y, width, height, ellipse_segments)

    return rounded_rect_points(
        x,
        y,
        width,
        height,
        label.effective_radius,
        segments_per_corner=corner_segments,
    )


@dataclass(frozen=True)
class DielinePath:
    """Caminho de corte com a sobreposição inicial, quando existe.

    `points` já inclui a volta completa ao contorno e o troço que retraça o
    início. `overlap` contém apenas esse troço, para destaque visual.
    """

    contour: list[Point]
    points: list[Point]
    overlap: list[Point]
    closed: bool


def polyline_length(points: list[Point], *, closed: bool = False) -> float:
    if len(points) < 2:
        return 0.0
    total = 0.0
    for index in range(len(points) - 1):
        x1, y1 = points[index]
        x2, y2 = points[index + 1]
        total += math.hypot(x2 - x1, y2 - y1)
    if closed:
        x1, y1 = points[-1]
        x2, y2 = points[0]
        total += math.hypot(x2 - x1, y2 - y1)
    return total


def polygon_perimeter(points: list[Point]) -> float:
    return polyline_length(points, closed=True)


def _prefix_points(contour: list[Point], length: float) -> list[Point]:
    """Pontos do início do contorno até percorrer `length` mm."""

    if not contour:
        return []
    points: list[Point] = [contour[0]]
    remaining = max(0.0, length)
    if remaining <= 1e-12:
        return points

    count = len(contour)
    for index in range(count):
        if remaining <= 1e-12:
            break
        x1, y1 = contour[index]
        x2, y2 = contour[(index + 1) % count]
        segment = math.hypot(x2 - x1, y2 - y1)
        if segment <= 1e-12:
            continue
        if remaining >= segment:
            points.append((x2, y2))
            remaining -= segment
        else:
            ratio = remaining / segment
            points.append((x1 + (x2 - x1) * ratio, y1 + (y2 - y1) * ratio))
            remaining = 0.0
    return points


def dieline_path(
    label: LabelSpec,
    x: float,
    y: float,
    *,
    quality: str = "high",
) -> DielinePath:
    """Caminho de corte: contorno completo + sobreposição opcional.

    A sobreposição faz o traço regressar sobre o início do caminho, sem
    aumentar a etiqueta, garantindo que a lâmina fecha o corte.
    """

    contour = contour_points(label, x, y, quality=quality)
    if len(contour) < 3:
        return DielinePath(contour, contour, [], True)

    overlap_length = label.overlap
    if overlap_length <= 1e-9:
        return DielinePath(contour, contour, [], True)

    perimeter = polygon_perimeter(contour)
    # Evita voltas completas acidentais com valores muito grandes.
    overlap_length = min(overlap_length, perimeter * 0.5)
    overlap = _prefix_points(contour, overlap_length)
    points = contour + [contour[0]] + overlap[1:]
    return DielinePath(contour, points, overlap, False)



def polygon_area(points: list[Point]) -> float:
    """Área de um polígono (fórmula do laço), em mm²."""

    if len(points) < 3:
        return 0.0
    total = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def shape_area(label: LabelSpec) -> float:
    """Área da etiqueta (a compensação é sobreposição de caminho, não área)."""

    width = label.width
    height = label.height
    if label.shape is ShapeType.CIRCLE:
        diameter = min(width, height)
        return math.pi * (diameter / 2.0) ** 2
    if label.shape is ShapeType.ELLIPSE:
        return math.pi * (width / 2.0) * (height / 2.0)

    radius = label.effective_radius
    return width * height - (4.0 - math.pi) * radius * radius


DEFAULT_YAW = 45.0
DEFAULT_PITCH = 35.0


class OrbitProjector:
    """Projeção 3D com órbita em torno da folha.

    `yaw` roda a folha na horizontal (360° sem limite) e `pitch` inclina a
    câmara entre uma vista quase rasante e uma vista de topo. A escala em Z é
    exagerada para que a espessura da folha e o relevo das etiquetas sejam
    visíveis no ecrã.
    """

    def __init__(
        self,
        scale: float,
        origin_x: float,
        origin_y: float,
        yaw: float = DEFAULT_YAW,
        pitch: float = DEFAULT_PITCH,
        z_factor: float = 2.6,
        pivot: tuple[float, float, float] | None = None,
    ) -> None:
        self.scale = scale
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.yaw = yaw
        self.pitch = pitch
        self.z_factor = z_factor
        self.pivot = pivot or (0.0, 0.0, 0.0)

        yaw_rad = math.radians(yaw)
        pitch_rad = math.radians(pitch)
        cy, sy = math.cos(yaw_rad), math.sin(yaw_rad)
        cp, sp = math.cos(pitch_rad), math.sin(pitch_rad)

        # Base ortonormada da câmara: direita, cima e profundidade.
        self.right = (cy, -sy, 0.0)
        self.up = (-sy * sp, -cy * sp, cp)
        self.forward = (sy * cp, cy * cp, sp)

    def raw(self, x: float, y: float, z: float = 0.0) -> tuple[float, float, float]:
        """Projeta em coordenadas de ecrã (sem escala) e devolve a profundidade."""

        x -= self.pivot[0]
        y -= self.pivot[1]
        z = (z - self.pivot[2]) * self.z_factor
        sx = x * self.right[0] + y * self.right[1]
        sy = -(x * self.up[0] + y * self.up[1] + z * self.up[2])
        depth = x * self.forward[0] + y * self.forward[1] + z * self.forward[2]
        return sx, sy, depth

    def project(self, x: float, y: float, z: float = 0.0) -> Point:
        sx, sy, _depth = self.raw(x, y, z)
        return self.origin_x + sx * self.scale, self.origin_y + sy * self.scale

    def depth(self, x: float, y: float, z: float = 0.0) -> float:
        return self.raw(x, y, z)[2]

    @staticmethod
    def bounds(
        width: float,
        height: float,
        z_min: float,
        z_max: float,
        yaw: float = DEFAULT_YAW,
        pitch: float = DEFAULT_PITCH,
        z_factor: float = 2.6,
        pivot: tuple[float, float, float] | None = None,
    ) -> tuple[float, float, float, float]:
        """Limites em ecrã dos oito cantos da folha, para o auto-ajuste."""

        if pivot is None:
            pivot = (width / 2.0, height / 2.0, (z_min + z_max) / 2.0)
        projector = OrbitProjector(1.0, 0.0, 0.0, yaw, pitch, z_factor, pivot)
        corners = [
            (0.0, 0.0, z_min),
            (width, 0.0, z_min),
            (width, height, z_min),
            (0.0, height, z_min),
            (0.0, 0.0, z_max),
            (width, 0.0, z_max),
            (width, height, z_max),
            (0.0, height, z_max),
        ]
        projected = [projector.project(*corner) for corner in corners]
        xs = [point[0] for point in projected]
        ys = [point[1] for point in projected]
        return min(xs), min(ys), max(xs), max(ys)
