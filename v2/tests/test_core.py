"""Testes do núcleo (sem abrir a interface)."""

from __future__ import annotations

import tempfile
import unittest
from collections import Counter
from pathlib import Path

import ezdxf
from ezdxf import bbox

from app import geometry
from app.cutting import (
    KIND_CUT,
    KIND_TRAVEL,
    STRATEGY_PROXIMITY,
    STRATEGY_ZIGZAG,
    build_cut_plan,
)
from app.exporters import (
    export_cut_plan_dxf,
    export_cut_plan_pdf,
    export_dxf,
    export_pdf,
)
from app.layout import auto_grid, compute_layout, shape_origin
from app.models import LabelSpec, LayoutSpec, ShapeType, SheetSpec


class AutoGridTests(unittest.TestCase):
    def test_a4_50x30(self) -> None:
        sheet = SheetSpec(210, 297)
        label = LabelSpec(50, 30)
        cols, rows = auto_grid(sheet, label, 2, 2)
        self.assertEqual((cols, rows), (4, 9))

    def test_compensation_does_not_reduce_capacity(self) -> None:
        sheet = SheetSpec(210, 297)
        normal = LabelSpec(50, 30)
        with_overlap = LabelSpec(50, 30, compensation=10)
        self.assertEqual(
            auto_grid(sheet, normal, 2, 2),
            auto_grid(sheet, with_overlap, 2, 2),
        )

    def test_invalid_sheet(self) -> None:
        self.assertEqual(
            auto_grid(SheetSpec(0, 0), LabelSpec(50, 30), 2, 2),
            (0, 0),
        )


class LayoutTests(unittest.TestCase):
    def test_positions_and_fit(self) -> None:
        sheet = SheetSpec(210, 297)
        label = LabelSpec(50, 30)
        layout = compute_layout(sheet, label, 2, 2, LayoutSpec(3, 9))
        self.assertEqual(layout.count, 27)
        self.assertTrue(layout.fits)
        self.assertAlmostEqual(layout.block_width, 3 * 50 + 2 * 2)
        self.assertAlmostEqual(layout.block_height, 9 * 30 + 8 * 2)

    def test_overflow_detected(self) -> None:
        layout = compute_layout(
            SheetSpec(100, 100), LabelSpec(50, 30), 2, 2, LayoutSpec(4, 4)
        )
        self.assertFalse(layout.fits)
        self.assertGreater(layout.overflow_x, 0)

    def test_overlap_keeps_label_cell(self) -> None:
        label = LabelSpec(50, 30, compensation=5)
        layout = compute_layout(
            SheetSpec(210, 297), label, 2, 2, LayoutSpec(1, 1)
        )
        self.assertAlmostEqual(layout.cell_width, 50)
        self.assertAlmostEqual(layout.cell_height, 30)
        x, y = shape_origin(
            label,
            layout.positions[0][0],
            layout.positions[0][1],
            layout.cell_width,
            layout.cell_height,
        )
        self.assertEqual((x, y), layout.positions[0])

    def test_circle_is_square_in_layout(self) -> None:
        label = LabelSpec(40, 40, shape=ShapeType.CIRCLE, compensation=0.5)
        layout = compute_layout(
            SheetSpec(210, 297), label, 0, 0, LayoutSpec(2, 2)
        )
        self.assertAlmostEqual(layout.cell_width, 40)
        self.assertAlmostEqual(layout.cell_height, 40)


class GeometryTests(unittest.TestCase):
    def test_rounded_rect_points_close(self) -> None:
        points = geometry.rounded_rect_points(0, 0, 50, 30, 2)
        self.assertGreater(len(points), 20)
        expected = 50 * 30 - (4 - 3.141592653589793) * 2 ** 2
        self.assertAlmostEqual(geometry.polygon_area(points), expected, delta=1.0)

    def test_contours_inside_label_box(self) -> None:
        for shape in ShapeType:
            label = LabelSpec(40, 30, 2, shape, 5)
            points = geometry.contour_points(label, 10, 20, quality="export")
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            self.assertGreaterEqual(min(xs), 10 - 1e-6, shape)
            self.assertLessEqual(max(xs), 10 + label.width + 1e-6, shape)
            self.assertGreaterEqual(min(ys), 20 - 1e-6, shape)
            self.assertLessEqual(max(ys), 20 + label.height + 1e-6, shape)

    def test_overlap_path_length(self) -> None:
        label = LabelSpec(50, 30, 2, ShapeType.ROUNDED_RECT, 1.5)
        path = geometry.dieline_path(label, 0, 0, quality="export")
        perimeter = geometry.polygon_perimeter(path.contour)
        self.assertFalse(path.closed)
        self.assertAlmostEqual(
            geometry.polyline_length(path.points), perimeter + 1.5, delta=0.05
        )
        self.assertAlmostEqual(
            geometry.polyline_length(path.overlap), 1.5, delta=0.05
        )

    def test_overlap_does_not_change_box(self) -> None:
        for shape in ShapeType:
            label = LabelSpec(40, 30, 2, shape, 4)
            path = geometry.dieline_path(label, 10, 20, quality="export")
            xs = [p[0] for p in path.contour]
            ys = [p[1] for p in path.contour]
            if shape is ShapeType.CIRCLE:
                left, right = 15.0, 45.0
            else:
                left, right = 10.0, 50.0
            self.assertAlmostEqual(min(xs), left, delta=1e-4, msg=shape)
            self.assertAlmostEqual(max(xs), right, delta=1e-4, msg=shape)
            self.assertAlmostEqual(min(ys), 20.0, delta=1e-4, msg=shape)
            self.assertAlmostEqual(max(ys), 50.0, delta=1e-4, msg=shape)

    def test_no_overlap_is_closed(self) -> None:
        label = LabelSpec(50, 30, 2, ShapeType.ROUNDED_RECT, 0)
        path = geometry.dieline_path(label, 0, 0)
        self.assertTrue(path.closed)
        self.assertEqual(path.points, path.contour)
        self.assertFalse(path.overlap)

    def test_negative_compensation_is_ignored(self) -> None:
        label = LabelSpec(50, 30, 2, ShapeType.ROUNDED_RECT, -3)
        self.assertEqual(label.overlap, 0)
        self.assertTrue(geometry.dieline_path(label, 0, 0).closed)

    def test_orbit_bounds(self) -> None:
        x0, y0, x1, y1 = geometry.OrbitProjector.bounds(210, 297, 0, 2)
        self.assertLess(x0, x1)
        self.assertLess(y0, y1)

    def test_orbit_rotates_horizontally(self) -> None:
        first = geometry.OrbitProjector.bounds(210, 297, 0, 2, yaw=45, pitch=35)
        second = geometry.OrbitProjector.bounds(210, 297, 0, 2, yaw=90, pitch=35)
        self.assertNotAlmostEqual(first[0], second[0], places=3)


def _repeated_edges(segments) -> bool:
    """Verdadeiro se algum troço de corte passar duas vezes pela mesma aresta."""

    seen: Counter = Counter()
    for segment in segments:
        points = segment.points
        for first, second in zip(points, points[1:]):
            key = tuple(
                sorted(
                    (
                        (round(first[0], 3), round(first[1], 3)),
                        (round(second[0], 3), round(second[1], 3)),
                    )
                )
            )
            seen[key] += 1
    return any(count > 1 for count in seen.values())


class CuttingTests(unittest.TestCase):
    def _scene(self, compensation: float = 0.4):
        sheet = SheetSpec(210, 297)
        label = LabelSpec(50, 30, 2, ShapeType.ROUNDED_RECT, compensation)
        layout = compute_layout(sheet, label, 2, 2, LayoutSpec(3, 4))
        return label, layout

    def test_plan_covers_every_label(self) -> None:
        label, layout = self._scene()
        plan = build_cut_plan(label, layout)
        self.assertEqual(plan.label_count, layout.count)
        self.assertEqual(len(plan.order), layout.count)
        self.assertEqual(len(set(plan.order)), layout.count)
        self.assertEqual(
            sum(1 for segment in plan.segments if segment.kind == KIND_CUT),
            layout.count,
        )
        self.assertGreater(plan.cut_length, 0)
        self.assertGreater(plan.travel_length, 0)
        self.assertAlmostEqual(
            plan.total_length,
            plan.cut_length + plan.travel_length,
        )

    def test_cut_length_matches_perimeter_and_overlap(self) -> None:
        label, layout = self._scene()
        plan = build_cut_plan(label, layout)
        contour = geometry.contour_points(label, 0, 0, quality="high")
        expected = geometry.polygon_perimeter(contour) + label.overlap
        cuts = [segment for segment in plan.segments if segment.kind == KIND_CUT]
        for segment in cuts:
            self.assertAlmostEqual(segment.length, expected, delta=0.02)

    def test_without_overlap_cut_is_exactly_the_perimeter(self) -> None:
        label, layout = self._scene(compensation=0)
        plan = build_cut_plan(label, layout)
        contour = geometry.contour_points(label, 0, 0, quality="high")
        perimeter = geometry.polygon_perimeter(contour)
        cuts = [segment for segment in plan.segments if segment.kind == KIND_CUT]
        for segment in cuts:
            self.assertAlmostEqual(segment.length, perimeter, delta=0.02)

    def test_first_travel_starts_at_home(self) -> None:
        label, layout = self._scene()
        plan = build_cut_plan(label, layout, keep_blade_down=False)
        first = plan.segments[0]
        self.assertEqual(first.kind, KIND_TRAVEL)
        self.assertEqual(first.points[0], (0.0, 0.0))

    def test_zigzag_alternates_rows(self) -> None:
        label, layout = self._scene()
        plan = build_cut_plan(label, layout, strategy=STRATEGY_ZIGZAG)
        self.assertEqual(plan.strategy, STRATEGY_ZIGZAG)
        self.assertEqual(len(plan.order), layout.count)

        rows: list[list[float]] = []
        current_y: float | None = None
        for index in plan.order:
            x, y = layout.positions[index]
            if current_y is None or abs(y - current_y) > 1e-6:
                rows.append([])
                current_y = y
            rows[-1].append(x)

        self.assertGreater(len(rows), 1)
        for row_number, xs in enumerate(rows):
            self.assertEqual(xs, sorted(xs, reverse=bool(row_number % 2)))

    def test_proximity_and_zigzag_differ(self) -> None:
        label, layout = self._scene()
        proximity = build_cut_plan(label, layout, strategy=STRATEGY_PROXIMITY)
        zigzag = build_cut_plan(label, layout, strategy=STRATEGY_ZIGZAG)
        self.assertNotEqual(proximity.order, zigzag.order)

    def test_keep_blade_down_reduces_lifts(self) -> None:
        sheet = SheetSpec(210, 297)
        label = LabelSpec(40, 40, 0, ShapeType.CIRCLE, 0)
        layout = compute_layout(
            sheet, label, 0, 0, LayoutSpec(4, 1, "Esquerda", "Topo")
        )

        down = build_cut_plan(
            label,
            layout,
            strategy=STRATEGY_ZIGZAG,
            keep_blade_down=True,
        )
        lifted = build_cut_plan(
            label,
            layout,
            strategy=STRATEGY_ZIGZAG,
            keep_blade_down=False,
        )

        self.assertEqual(down.lift_count, 0)
        self.assertLess(down.lift_count, lifted.lift_count)
        self.assertEqual(down.link_count, down.label_count - 1)

    def test_estimated_duration(self) -> None:
        label, layout = self._scene()
        plan = build_cut_plan(label, layout)
        self.assertAlmostEqual(
            plan.estimated_seconds(100), plan.total_length / 100.0
        )
        self.assertEqual(plan.estimated_seconds(0), 0.0)

    def test_touching_labels_cut_without_lifting(self) -> None:
        sheet = SheetSpec(210, 297)
        label = LabelSpec(50, 30, 0, ShapeType.ROUNDED_RECT, 0)
        layout = compute_layout(sheet, label, 0, 0, LayoutSpec(2, 2))
        plan = build_cut_plan(
            label,
            layout,
            strategy=STRATEGY_PROXIMITY,
            keep_blade_down=True,
        )

        self.assertEqual(plan.label_count, 4)
        cut_segments = [
            segment for segment in plan.segments if segment.kind == KIND_CUT
        ]
        # A grelha 2x2 tem quatro vértices ímpares: um só trilho repetiria
        # arestas, por isso é dividida em dois trilhos válidos.
        self.assertEqual(len(cut_segments), 2)
        self.assertEqual(plan.lift_count, 1)
        self.assertEqual(plan.link_count, plan.label_count - len(cut_segments))
        self.assertFalse(_repeated_edges(cut_segments))

        with tempfile.TemporaryDirectory() as tmp:
            dxf_path = Path(tmp) / "corte.dxf"
            export_cut_plan_dxf(dxf_path, sheet, plan)
            doc = ezdxf.readfile(dxf_path)
            cut_entities = [
                entity
                for entity in doc.modelspace()
                if entity.dxf.layer == "CORTE"
            ]
            self.assertEqual(len(cut_entities), len(cut_segments))

    def test_touching_circles_form_single_serpentine_trail(self) -> None:
        sheet = SheetSpec(210, 297)
        label = LabelSpec(40, 40, 0, ShapeType.CIRCLE, 0)
        layout = compute_layout(
            sheet, label, 0, 0, LayoutSpec(4, 1, "Esquerda", "Topo")
        )
        plan = build_cut_plan(
            label,
            layout,
            strategy=STRATEGY_ZIGZAG,
            keep_blade_down=True,
        )

        cut_segments = [
            segment for segment in plan.segments if segment.kind == KIND_CUT
        ]
        self.assertEqual(plan.label_count, 4)
        self.assertEqual(len(cut_segments), 1)
        self.assertEqual(plan.lift_count, 0)
        self.assertEqual(plan.link_count, 3)
        self.assertFalse(_repeated_edges(cut_segments))

        contour = geometry.contour_points(label, 0, 0, quality="high")
        expected = 4 * geometry.polygon_perimeter(contour)
        self.assertAlmostEqual(plan.cut_length, expected, delta=0.1)

    def test_shared_edge_is_cut_once(self) -> None:
        sheet = SheetSpec(210, 297)
        label = LabelSpec(50, 30, 0, ShapeType.ROUNDED_RECT, 0)
        layout = compute_layout(
            sheet, label, 0, 0, LayoutSpec(2, 1, "Esquerda", "Topo")
        )
        plan = build_cut_plan(label, layout, strategy=STRATEGY_PROXIMITY)

        cut_segments = [
            segment for segment in plan.segments if segment.kind == KIND_CUT
        ]
        self.assertEqual(len(cut_segments), 1)
        # Dois perímetros de 160 mm menos a aresta partilhada de 30 mm.
        self.assertAlmostEqual(plan.cut_length, 290.0, delta=0.02)
        self.assertFalse(_repeated_edges(cut_segments))

    def test_optimized_plan_dxf_and_pdf(self) -> None:
        label, layout = self._scene()
        sheet = SheetSpec(210, 297)
        plan = build_cut_plan(label, layout)

        with tempfile.TemporaryDirectory() as tmp:
            dxf_path = Path(tmp) / "corte.dxf"
            export_cut_plan_dxf(dxf_path, sheet, plan)
            doc = ezdxf.readfile(dxf_path)
            self.assertEqual(doc.header["$INSUNITS"], 4)
            self.assertIn("CORTE", doc.layers)
            self.assertIn("DESLOCAMENTO", doc.layers)

            cut_entities = [
                entity
                for entity in doc.modelspace()
                if entity.dxf.layer == "CORTE"
            ]
            travel_entities = [
                entity
                for entity in doc.modelspace()
                if entity.dxf.layer == "DESLOCAMENTO"
            ]
            self.assertEqual(
                len(cut_entities), plan.label_count - plan.link_count
            )
            self.assertEqual(
                len(travel_entities),
                sum(
                    1
                    for segment in plan.segments
                    if segment.kind == KIND_TRAVEL
                ),
            )

            pdf_path = Path(tmp) / "corte.pdf"
            export_cut_plan_pdf(pdf_path, sheet, plan)
            self.assertGreater(pdf_path.stat().st_size, 1000)
            self.assertEqual(pdf_path.read_bytes()[:4], b"%PDF")


class ExportTests(unittest.TestCase):
    def _scene(self, compensation: float = 0.4):
        sheet = SheetSpec(210, 297)
        label = LabelSpec(50, 30, 2, ShapeType.ROUNDED_RECT, compensation)
        layout = compute_layout(sheet, label, 2, 2, LayoutSpec(3, 9))
        return sheet, label, layout

    def test_pdf(self) -> None:
        sheet, label, layout = self._scene()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "teste.pdf"
            export_pdf(path, sheet, label, layout)
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 1000)
            self.assertEqual(path.read_bytes()[:4], b"%PDF")

    def test_dxf_with_overlap_is_open_polyline(self) -> None:
        sheet, label, layout = self._scene()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "teste.dxf"
            export_dxf(path, sheet, label, layout)
            self.assertTrue(path.exists())
            doc = ezdxf.readfile(path)
            self.assertEqual(doc.header["$INSUNITS"], 4)
            self.assertIn("DIELINE", doc.layers)
            entities = list(doc.modelspace())
            self.assertEqual(len(entities), layout.count)
            self.assertTrue(all(e.dxf.layer == "DIELINE" for e in entities))
            self.assertTrue(all(e.dxftype() == "LWPOLYLINE" for e in entities))
            self.assertTrue(all(not e.closed for e in entities))

    def test_dxf_overlap_keeps_extents(self) -> None:
        sheet = SheetSpec(210, 297)
        layout = compute_layout(sheet, LabelSpec(50, 30), 2, 2, LayoutSpec(1, 1))
        normal = LabelSpec(50, 30)
        overlap = LabelSpec(50, 30, compensation=2)
        with tempfile.TemporaryDirectory() as tmp:
            path_normal = Path(tmp) / "normal.dxf"
            path_overlap = Path(tmp) / "overlap.dxf"
            export_dxf(path_normal, sheet, normal, layout)
            export_dxf(path_overlap, sheet, overlap, layout)
            box_normal = bbox.extents(ezdxf.readfile(path_normal).modelspace())
            box_overlap = bbox.extents(ezdxf.readfile(path_overlap).modelspace())
            self.assertAlmostEqual(box_normal.extmin.x, box_overlap.extmin.x, places=4)
            self.assertAlmostEqual(box_normal.extmin.y, box_overlap.extmin.y, places=4)
            self.assertAlmostEqual(box_normal.extmax.x, box_overlap.extmax.x, places=4)
            self.assertAlmostEqual(box_normal.extmax.y, box_overlap.extmax.y, places=4)

    def test_dxf_without_overlap_uses_true_entities(self) -> None:
        sheet = SheetSpec(210, 297)
        layout = compute_layout(sheet, LabelSpec(40, 30), 2, 2, LayoutSpec(1, 1))
        expected = {
            ShapeType.ROUNDED_RECT: "LWPOLYLINE",
            ShapeType.ELLIPSE: "ELLIPSE",
            ShapeType.CIRCLE: "CIRCLE",
        }
        with tempfile.TemporaryDirectory() as tmp:
            for shape, entity_type in expected.items():
                label = LabelSpec(40, 30, 4, shape, 0)
                path = Path(tmp) / f"{shape.name}.dxf"
                export_dxf(path, sheet, label, layout)
                entities = list(ezdxf.readfile(path).modelspace())
                self.assertEqual(len(entities), 1, shape)
                self.assertEqual(entities[0].dxftype(), entity_type, shape)

    def test_dxf_all_shapes_with_overlap(self) -> None:
        sheet = SheetSpec(210, 297)
        with tempfile.TemporaryDirectory() as tmp:
            for shape in ShapeType:
                label = LabelSpec(40, 30, 4, shape, 0.2)
                layout = compute_layout(sheet, label, 2, 2, LayoutSpec(2, 2))
                path = Path(tmp) / f"{shape.name}.dxf"
                export_dxf(path, sheet, label, layout)
                entities = list(ezdxf.readfile(path).modelspace())
                self.assertEqual(len(entities), 4)
                self.assertTrue(all(e.dxftype() == "LWPOLYLINE" for e in entities))


if __name__ == "__main__":
    unittest.main()
