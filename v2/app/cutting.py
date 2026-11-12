"""Planeamento do percurso de corte para a simulação de plotter.

O percurso pode ser ordenado de duas formas:

* ``proximity`` - os componentes são visitados por vizinho mais próximo (com
  melhoria 2-opt), minimizando os deslocamentos;
* ``zigzag`` - os componentes são percorridos linha a linha, alternando o
  sentido, para um movimento previsível da cabeça de corte.

Em ambas as estratégias, os contornos são convertidos num grafo de arestas
únicas: arestas coincidentes entre etiquetas vizinhas são cortadas uma só vez
e os contornos que se tocam num ponto são encadeados nesse ponto. O percurso
resultante é um conjunto de trilhos de Euler (um por componente, quando
possível), pelo que a lâmina nunca passa duas vezes sobre a mesma aresta;
pode apenas passar pelo mesmo vértice/ponto.

Quando o encadeamento não é possível, o componente é dividido em vários
trilhos e a lâmina levanta entre eles. Quando o grafo é demasiado grande, o
planeador recorre a um percurso por etiqueta, com deslocamentos em vazio.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import geometry
from .layout import shape_origin
from .models import LabelSpec, LayoutResult

Point = geometry.Point

HOME: Point = (0.0, 0.0)
MAX_PLAN_LABELS = 1500
TWO_OPT_LIMIT = 320
TWO_OPT_PASSES = 12
MAX_GRAPH_EDGES = 60000
SNAP_DECIMALS = 3

KIND_CUT = "cut"
KIND_TRAVEL = "travel"

STRATEGY_PROXIMITY = "proximity"
STRATEGY_ZIGZAG = "zigzag"
STRATEGY_LABELS = {
    STRATEGY_PROXIMITY: "Proximidade",
    STRATEGY_ZIGZAG: "Zigue-zague",
}
STRATEGY_KEYS = {label: key for key, label in STRATEGY_LABELS.items()}


def _distance(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _squared_distance(a: Point, b: Point) -> float:
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    return dx * dx + dy * dy


def _unit(a: Point, b: Point) -> Point:
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    length = math.hypot(dx, dy)
    if length <= 1e-12:
        return (0.0, 0.0)
    return (dx / length, dy / length)


@dataclass(frozen=True)
class CutSegment:
    """Troço do percurso: corte de um trilho ou deslocamento em vazio."""

    points: tuple[Point, ...]
    kind: str
    label_index: int | None = None
    length: float = 0.0
    # Verdadeiro quando este corte continua o anterior sem levantar a lâmina.
    linked: bool = False


@dataclass
class CutPlan:
    """Percurso otimizado, pronto a reproduzir na pré-visualização."""

    segments: list[CutSegment] = field(default_factory=list)
    order: list[int] = field(default_factory=list)
    label_count: int = 0
    truncated: bool = False
    strategy: str = STRATEGY_PROXIMITY
    keep_blade_down: bool = True

    @property
    def cut_length(self) -> float:
        """Comprimento efetivamente cortado."""

        return sum(
            segment.length
            for segment in self.segments
            if segment.kind == KIND_CUT
        )

    @property
    def travel_length(self) -> float:
        """Deslocamentos com a lâmina levantada."""

        return sum(
            segment.length for segment in self.segments if segment.kind == KIND_TRAVEL
        )

    @property
    def lift_count(self) -> int:
        """Elevações da lâmina entre cortes (a posição inicial não conta)."""

        lifts = 0
        seen_cut = False
        for segment in self.segments:
            if segment.kind == KIND_CUT:
                seen_cut = True
            elif segment.kind == KIND_TRAVEL and seen_cut:
                lifts += 1
        return lifts

    @property
    def link_count(self) -> int:
        """Contornos ligados ao anterior sem levantar a lâmina."""

        cut_segments = sum(
            1 for segment in self.segments if segment.kind == KIND_CUT
        )
        return max(0, self.label_count - cut_segments)

    @property
    def total_length(self) -> float:
        return self.cut_length + self.travel_length

    @property
    def is_empty(self) -> bool:
        return not self.segments or self.total_length <= 1e-9

    def estimated_seconds(self, speed_mm_s: float) -> float:
        if speed_mm_s <= 1e-9:
            return 0.0
        return self.total_length / speed_mm_s


@dataclass
class _GraphEdge:
    a: int
    b: int
    p1: Point
    p2: Point
    length: float
    labels: frozenset[int]


@dataclass
class _Component:
    edges: list[int]
    nodes: set[int]
    center: Point
    min_x: float
    max_x: float
    min_y: float
    max_y: float


@dataclass
class _Trail:
    points: list[Point]
    edges: list[int]
    labels: frozenset[int]
    start: Point
    end: Point
    length: float


def _nearest_neighbor(centers: list[Point], home: Point = HOME) -> list[int]:
    """Ordem de visita por vizinho mais próximo, em O(n²)."""

    remaining = list(range(len(centers)))
    order: list[int] = []
    current = home
    while remaining:
        best_position = 0
        best_distance = math.inf
        for position, index in enumerate(remaining):
            distance = _squared_distance(current, centers[index])
            if distance < best_distance:
                best_distance = distance
                best_position = position
        index = remaining.pop(best_position)
        order.append(index)
        current = centers[index]
    return order


def _two_opt(order: list[int], centers: list[Point], home: Point = HOME) -> list[int]:
    """Melhora a ordem com inversões de troços (caminho aberto, início fixo)."""

    if len(order) < 4 or len(order) > TWO_OPT_LIMIT:
        return order

    order = list(order)
    count = len(order)
    for _pass in range(TWO_OPT_PASSES):
        improved = False
        for i in range(count - 1):
            a = home if i == 0 else centers[order[i - 1]]
            b = centers[order[i]]
            for j in range(i + 2, count):
                c = centers[order[j]]
                if j + 1 < count:
                    d = centers[order[j + 1]]
                    before = _distance(a, b) + _distance(c, d)
                    after = _distance(a, c) + _distance(b, d)
                else:
                    before = _distance(a, b)
                    after = _distance(a, c)
                if after + 1e-9 < before:
                    order[i : j + 1] = reversed(order[i : j + 1])
                    improved = True
                    break
            if improved:
                break
        if not improved:
            break
    return order


def _zigzag_order(centers: list[Point], tolerance: float) -> list[int]:
    """Ordena por linhas, alternando o sentido em cada linha."""

    if not centers:
        return []

    indexed = sorted(
        range(len(centers)), key=lambda index: (centers[index][1], centers[index][0])
    )
    rows: list[tuple[float, list[int]]] = []
    for index in indexed:
        y = centers[index][1]
        if not rows or abs(y - rows[-1][0]) > tolerance:
            rows.append((y, [index]))
        else:
            rows[-1][1].append(index)

    order: list[int] = []
    for row_number, (_y, row) in enumerate(rows):
        row.sort(key=lambda index: centers[index][0], reverse=bool(row_number % 2))
        order.extend(row)
    return order


def _node_key(point: Point) -> tuple[float, float]:
    x = round(point[0], SNAP_DECIMALS)
    y = round(point[1], SNAP_DECIMALS)
    return (0.0 if x == 0 else x, 0.0 if y == 0 else y)


def _build_graph(entries: list[tuple[float, float, list[Point]]]):
    """Converte os contornos num grafo de arestas únicas.

    Arestas coincidentes (por exemplo a fronteira partilhada por duas
    etiquetas encostadas) ficam registadas uma só vez, com a lista de
    etiquetas que as usam.
    """

    node_ids: dict[tuple[float, float], int] = {}
    node_points: list[Point] = []
    edges: list[_GraphEdge] = []
    edge_map: dict[tuple[int, int], int] = {}

    def node_id(point: Point) -> int:
        key = _node_key(point)
        existing = node_ids.get(key)
        if existing is not None:
            return existing
        index = len(node_points)
        node_ids[key] = index
        node_points.append(point)
        return index

    for label_index, (_x, _y, contour) in enumerate(entries):
        count = len(contour)
        if count < 3:
            continue
        for step in range(count):
            p1 = contour[step]
            p2 = contour[(step + 1) % count]
            length = _distance(p1, p2)
            if length <= 1e-9:
                continue
            a = node_id(p1)
            b = node_id(p2)
            if a == b:
                continue
            key = (a, b) if a < b else (b, a)
            existing = edge_map.get(key)
            if existing is not None:
                edge = edges[existing]
                edges[existing] = _GraphEdge(
                    edge.a,
                    edge.b,
                    edge.p1,
                    edge.p2,
                    edge.length,
                    edge.labels | {label_index},
                )
            else:
                edge_map[key] = len(edges)
                edges.append(
                    _GraphEdge(
                        a,
                        b,
                        p1,
                        p2,
                        length,
                        frozenset({label_index}),
                    )
                )
    return node_points, edges


def _adjacency(edges: list[_GraphEdge], node_count: int) -> list[list[int]]:
    adjacency: list[list[int]] = [[] for _ in range(node_count)]
    for edge_index, edge in enumerate(edges):
        adjacency[edge.a].append(edge_index)
        adjacency[edge.b].append(edge_index)
    return adjacency


def _components(
    edges: list[_GraphEdge],
    adjacency: list[list[int]],
    node_points: list[Point],
) -> list[_Component]:
    seen: set[int] = set()
    components: list[_Component] = []
    for start in range(len(edges)):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        component_edges: list[int] = []
        component_nodes: set[int] = set()
        while stack:
            edge_index = stack.pop()
            component_edges.append(edge_index)
            edge = edges[edge_index]
            component_nodes.add(edge.a)
            component_nodes.add(edge.b)
            for node in (edge.a, edge.b):
                for neighbour in adjacency[node]:
                    if neighbour not in seen:
                        seen.add(neighbour)
                        stack.append(neighbour)

        points = [node_points[node] for node in component_nodes]
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        components.append(
            _Component(
                component_edges,
                component_nodes,
                ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0),
                min(xs),
                max(xs),
                min(ys),
                max(ys),
            )
        )
    return components


def _pick_edge(
    node: int,
    candidates: list[int],
    incoming: Point,
    edges: list[_GraphEdge],
    node_points: list[Point],
) -> int:
    """Escolhe a aresta que continua mais em frente (percurso em zigue-zague)."""

    best = candidates[0]
    best_key: tuple[float, float, float] | None = None
    for edge_index in candidates:
        edge = edges[edge_index]
        other = edge.b if edge.a == node else edge.a
        direction = _unit(node_points[node], node_points[other])
        dot = incoming[0] * direction[0] + incoming[1] * direction[1]
        dot = max(-1.0, min(1.0, dot))
        angle = math.acos(dot)
        key = (angle, -direction[1], -direction[0])
        if best_key is None or key < best_key:
            best_key = key
            best = edge_index
    return best


def _greedy_trail(
    start: int,
    remaining: set[int],
    adjacency: list[list[int]],
    edges: list[_GraphEdge],
    node_points: list[Point],
    preferred_direction: Point,
) -> list[int]:
    """Trilho máximo a partir de ``start``, sem repetir arestas.

    Não faz backtracking: cada trilho é um caminho contínuo e válido. Quando o
    grafo tem mais de dois vértices ímpares, o componente é dividido em vários
    trilhos, em vez de inventar atalhos que repetiriam arestas.
    """

    node = start
    direction = preferred_direction
    trail: list[int] = []
    while True:
        candidates = [
            edge_index
            for edge_index in adjacency[node]
            if edge_index in remaining
        ]
        if not candidates:
            break
        edge_index = _pick_edge(
            node, candidates, direction, edges, node_points
        )
        remaining.remove(edge_index)
        edge = edges[edge_index]
        other = edge.b if edge.a == node else edge.a
        trail.append(edge_index)
        direction = _unit(node_points[node], node_points[other])
        node = other
    return trail


def _trail_points(
    start: int,
    edge_order: list[int],
    edges: list[_GraphEdge],
    node_points: list[Point],
) -> list[Point]:
    points: list[Point] = [node_points[start]]
    current = start
    for edge_index in edge_order:
        edge = edges[edge_index]
        other = edge.b if edge.a == current else edge.a
        point = node_points[other]
        if _distance(points[-1], point) > 1e-9:
            points.append(point)
        current = other
    return points


def _decompose_trails(
    component: _Component,
    adjacency: list[list[int]],
    edges: list[_GraphEdge],
    node_points: list[Point],
    preferred_point: Point,
    preferred_direction: Point,
) -> list[_Trail]:
    """Divide o componente em trilhos de Euler, sem repetir arestas."""

    remaining = set(component.edges)
    trails: list[_Trail] = []
    preferred = preferred_point
    direction = preferred_direction

    while remaining:
        odd = [
            node
            for node in component.nodes
            if sum(1 for edge in adjacency[node] if edge in remaining) % 2 == 1
        ]
        candidates = [
            node
            for node in component.nodes
            if any(edge in remaining for edge in adjacency[node])
        ]
        if not candidates:
            break
        pool = odd if odd else candidates
        start = min(
            pool, key=lambda node: _squared_distance(node_points[node], preferred)
        )
        if trails:
            heading = _unit(preferred, node_points[start])
            if heading != (0.0, 0.0):
                direction = heading

        edge_order = _greedy_trail(
            start, remaining, adjacency, edges, node_points, direction
        )
        if not edge_order:
            break

        points = _trail_points(start, edge_order, edges, node_points)
        labels: set[int] = set()
        length = 0.0
        for edge_index in edge_order:
            labels.update(edges[edge_index].labels)
            length += edges[edge_index].length

        trails.append(
            _Trail(
                points,
                edge_order,
                frozenset(labels),
                points[0],
                points[-1],
                length,
            )
        )
        preferred = points[-1]
        direction = (1.0, 0.0)
    return trails


def _reverse_trail(trail: _Trail) -> _Trail:
    return _Trail(
        list(reversed(trail.points)),
        list(reversed(trail.edges)),
        trail.labels,
        trail.end,
        trail.start,
        trail.length,
    )


def _order_trails(
    trails: list[_Trail], head: Point
) -> tuple[list[_Trail], Point]:
    """Ordena os trilhos de um componente por proximidade à cabeça."""

    remaining = list(trails)
    ordered: list[_Trail] = []
    while remaining:
        best: _Trail | None = None
        best_key = math.inf
        best_reverse = False
        for trail in remaining:
            start_distance = _distance(head, trail.start)
            end_distance = _distance(head, trail.end)
            if start_distance <= end_distance:
                key = start_distance
                reverse = False
            else:
                key = end_distance
                reverse = True
            if key < best_key:
                best_key = key
                best = trail
                best_reverse = reverse
        if best is None:
            break
        original = best
        if best_reverse:
            best = _reverse_trail(best)
        ordered.append(best)
        head = best.end
        remaining.remove(original)
    return ordered, head


def _polyline_prefix(points: list[Point], length: float) -> list[Point]:
    """Pontos do início da polilinha até percorrer ``length`` mm."""

    if len(points) < 2 or length <= 1e-12:
        return [points[0]] if points else []

    prefix: list[Point] = [points[0]]
    remaining = length
    for index in range(len(points) - 1):
        if remaining <= 1e-12:
            break
        p1 = points[index]
        p2 = points[index + 1]
        segment = _distance(p1, p2)
        if segment <= 1e-12:
            continue
        if remaining >= segment:
            prefix.append(p2)
            remaining -= segment
        else:
            ratio = remaining / segment
            prefix.append(
                (p1[0] + (p2[0] - p1[0]) * ratio, p1[1] + (p2[1] - p1[1]) * ratio)
            )
            remaining = 0.0
    return prefix


def _apply_overlap(points: list[Point], overlap: float) -> list[Point]:
    """Acrescenta a sobreposição inicial, quando definida."""

    if overlap <= 1e-9 or len(points) < 2:
        return points
    prefix = _polyline_prefix(points, overlap)
    if len(prefix) <= 1:
        return points
    return points + prefix[1:]


def _closed_contour_points(contour: list[Point], start_index: int) -> list[Point]:
    count = len(contour)
    return [contour[(start_index + step) % count] for step in range(count + 1)]


def _nearest_index(contour: list[Point], point: Point) -> int:
    return min(
        range(len(contour)),
        key=lambda index: _squared_distance(contour[index], point),
    )


def _entry_contours(
    label: LabelSpec, layout: LayoutResult, quality: str
) -> list[tuple[float, float, list[Point]]]:
    entries: list[tuple[float, float, list[Point]]] = []
    for cell_x, cell_y in layout.positions:
        x, y = shape_origin(label, cell_x, cell_y, layout.cell_width, layout.cell_height)
        contour = geometry.contour_points(label, x, y, quality=quality)
        if len(contour) >= 3:
            entries.append((x, y, contour))
    return entries


def _per_label_plan(
    entries: list[tuple[float, float, list[Point]]],
    label_order: list[int],
    label: LabelSpec,
    *,
    keep_blade_down: bool,
    truncated: bool,
    strategy: str,
) -> CutPlan:
    """Percurso por etiqueta, sem fundir contornos (modo normal)."""

    segments: list[CutSegment] = []
    head = HOME

    for index in label_order:
        contour = entries[index][2]
        start_index = _nearest_index(contour, head)
        points = _closed_contour_points(contour, start_index)
        points = _apply_overlap(points, label.overlap)
        start = points[0]
        travel = _distance(head, start)

        if travel > 1e-9:
            segments.append(
                CutSegment(
                    points=(head, start),
                    kind=KIND_TRAVEL,
                    label_index=index,
                    length=travel,
                )
            )

        segments.append(
            CutSegment(
                points=tuple(points),
                kind=KIND_CUT,
                label_index=index,
                length=geometry.polyline_length(points),
            )
        )
        head = points[-1]

    return CutPlan(
        segments=segments,
        order=list(label_order),
        label_count=len(entries),
        truncated=truncated,
        strategy=strategy,
        keep_blade_down=keep_blade_down,
    )


def build_cut_plan(
    label: LabelSpec,
    layout: LayoutResult,
    *,
    quality: str = "high",
    optimize: bool = True,
    strategy: str = STRATEGY_PROXIMITY,
    keep_blade_down: bool = True,
) -> CutPlan:
    """Constrói o percurso de corte otimizado para o layout atual."""

    strategy = STRATEGY_KEYS.get(strategy, strategy)
    if strategy not in STRATEGY_LABELS:
        strategy = STRATEGY_PROXIMITY

    if not label.is_valid or not layout.positions:
        return CutPlan(strategy=strategy, keep_blade_down=keep_blade_down)

    truncated = len(layout.positions) > MAX_PLAN_LABELS
    if truncated:
        layout = LayoutResult(
            positions=layout.positions[:MAX_PLAN_LABELS],
            columns=layout.columns,
            rows=layout.rows,
            cell_width=layout.cell_width,
            cell_height=layout.cell_height,
            block_width=layout.block_width,
            block_height=layout.block_height,
            fits=layout.fits,
        )

    entries = _entry_contours(label, layout, quality)
    if not entries:
        return CutPlan(
            truncated=truncated,
            strategy=strategy,
            keep_blade_down=keep_blade_down,
        )

    centers = [
        (x + label.width / 2.0, y + label.height / 2.0) for x, y, _contour in entries
    ]
    if strategy == STRATEGY_ZIGZAG:
        label_order = _zigzag_order(centers, max(0.5, label.height / 2.0))
    else:
        label_order = _nearest_neighbor(centers)
        if optimize:
            label_order = _two_opt(label_order, centers)

    if not keep_blade_down:
        return _per_label_plan(
            entries,
            label_order,
            label,
            keep_blade_down=False,
            truncated=truncated,
            strategy=strategy,
        )

    node_points, edges = _build_graph(entries)
    if not edges or len(edges) > MAX_GRAPH_EDGES:
        return _per_label_plan(
            entries,
            label_order,
            label,
            keep_blade_down=True,
            truncated=truncated,
            strategy=strategy,
        )

    adjacency = _adjacency(edges, len(node_points))
    components = _components(edges, adjacency, node_points)
    if not components:
        return _per_label_plan(
            entries,
            label_order,
            label,
            keep_blade_down=True,
            truncated=truncated,
            strategy=strategy,
        )

    component_centers = [component.center for component in components]
    if strategy == STRATEGY_ZIGZAG:
        component_order = _zigzag_order(
            component_centers, max(0.5, label.height / 2.0)
        )
    else:
        component_order = _nearest_neighbor(component_centers)
        if optimize:
            component_order = _two_opt(component_order, component_centers)

    segments: list[CutSegment] = []
    order: list[int] = []
    seen_labels: set[int] = set()
    head = HOME

    for component_index in component_order:
        component = components[component_index]
        trails = _decompose_trails(
            component,
            adjacency,
            edges,
            node_points,
            head,
            (1.0, 0.0),
        )
        trails, _ordered_head = _order_trails(trails, head)

        for trail in trails:
            points = _apply_overlap(trail.points, label.overlap)
            start = points[0]
            travel = _distance(head, start)
            linked = False
            if travel > 1e-9:
                first_label = min(trail.labels) if trail.labels else None
                segments.append(
                    CutSegment(
                        points=(head, start),
                        kind=KIND_TRAVEL,
                        label_index=first_label,
                        length=travel,
                    )
                )
            else:
                linked = bool(segments) and segments[-1].kind == KIND_CUT

            first_label = min(trail.labels) if trail.labels else None
            segments.append(
                CutSegment(
                    points=tuple(points),
                    kind=KIND_CUT,
                    label_index=first_label,
                    length=geometry.polyline_length(points),
                    linked=linked,
                )
            )

            for edge_index in trail.edges:
                for label_index in sorted(edges[edge_index].labels):
                    if label_index not in seen_labels:
                        seen_labels.add(label_index)
                        order.append(label_index)
            head = points[-1]

    for index in range(len(entries)):
        if index not in seen_labels:
            order.append(index)

    return CutPlan(
        segments=segments,
        order=order,
        label_count=len(entries),
        truncated=truncated,
        strategy=strategy,
        keep_blade_down=keep_blade_down,
    )

