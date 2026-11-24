"""Testes do núcleo (sem abrir a interface)."""

from __future__ import annotations

import tempfile
import unittest
from collections import Counter
from pathlib import Path

import ezdxf
from ezdxf import bbox

from app import __version__, geometry
from app.cutting import (
    KIND_CUT,
    KIND_TRAVEL,
    OBJECTIVE_BALANCED,
    OBJECTIVE_DISTANCE,
    OBJECTIVE_LIFTS,
    STRATEGY_COLUMNS,
    STRATEGY_PER_LABEL,
    STRATEGY_PROXIMITY,
    STRATEGY_SPIRAL,
    STRATEGY_ZIGZAG,
    build_cut_plan,
    build_imported_cut_plan,
    compare_imported_strategies,
    compare_strategies,
    objective_score,
    start_point,
)
from app.exporters import (
    export_cut_plan_dxf,
    export_cut_plan_pdf,
    export_document_dxf,
    export_document_pdf,
    export_dxf,
    export_pdf,
)
from app.importers import load_dxf, load_pdf, pdf_page_count
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


class StrategyTests(unittest.TestCase):
    def _scene(self):
        sheet = SheetSpec(210, 297)
        label = LabelSpec(50, 30, 2, ShapeType.ROUNDED_RECT, 0.4)
        layout = compute_layout(sheet, label, 2, 2, LayoutSpec(3, 4))
        return sheet, label, layout

    def test_new_strategies_cover_every_label(self) -> None:
        sheet, label, layout = self._scene()
        for strategy in (STRATEGY_COLUMNS, STRATEGY_SPIRAL, STRATEGY_PER_LABEL):
            plan = build_cut_plan(label, layout, sheet=sheet, strategy=strategy)
            self.assertEqual(plan.strategy, strategy)
            self.assertEqual(len(plan.order), layout.count)
            self.assertEqual(set(plan.order), set(range(layout.count)))
            self.assertGreater(plan.cut_length, 0)

    def test_columns_alternate_columns(self) -> None:
        sheet, label, layout = self._scene()
        plan = build_cut_plan(label, layout, sheet=sheet, strategy=STRATEGY_COLUMNS)

        columns: list[list[float]] = []
        current_x: float | None = None
        for index in plan.order:
            x, y = layout.positions[index]
            if current_x is None or abs(x - current_x) > 1e-6:
                columns.append([])
                current_x = x
            columns[-1].append(y)

        self.assertGreater(len(columns), 1)
        for column_number, ys in enumerate(columns):
            self.assertEqual(ys, sorted(ys, reverse=bool(column_number % 2)))

    def test_spiral_differs_from_proximity(self) -> None:
        sheet, label, layout = self._scene()
        proximity = build_cut_plan(label, layout, sheet=sheet)
        spiral = build_cut_plan(label, layout, sheet=sheet, strategy=STRATEGY_SPIRAL)
        self.assertNotEqual(proximity.order, spiral.order)

    def test_per_label_does_not_merge_contours(self) -> None:
        sheet = SheetSpec(210, 297)
        label = LabelSpec(50, 30, 0, ShapeType.ROUNDED_RECT, 0)
        layout = compute_layout(sheet, label, 0, 0, LayoutSpec(2, 2))

        merged = build_cut_plan(label, layout, sheet=sheet, keep_blade_down=True)
        separate = build_cut_plan(
            label,
            layout,
            sheet=sheet,
            strategy=STRATEGY_PER_LABEL,
        )
        merged_cuts = sum(1 for segment in merged.segments if segment.kind == KIND_CUT)
        separate_cuts = sum(
            1 for segment in separate.segments if segment.kind == KIND_CUT
        )
        self.assertEqual(separate_cuts, 4)
        self.assertLess(merged_cuts, separate_cuts)

    def test_start_point_and_first_travel(self) -> None:
        sheet = SheetSpec(210, 297)
        self.assertEqual(start_point(sheet, "top-left"), (0.0, 0.0))
        self.assertEqual(start_point(sheet, "top-right"), (210.0, 0.0))
        self.assertEqual(start_point(sheet, "bottom-left"), (0.0, 297.0))
        self.assertEqual(start_point(sheet, "bottom-right"), (210.0, 297.0))
        self.assertEqual(start_point(sheet, "center"), (105.0, 148.5))

        label = LabelSpec(50, 30)
        layout = compute_layout(sheet, label, 2, 2, LayoutSpec(1, 1))
        plan = build_cut_plan(
            label,
            layout,
            sheet=sheet,
            keep_blade_down=False,
            start="top-right",
        )
        first = plan.segments[0]
        self.assertEqual(first.kind, KIND_TRAVEL)
        self.assertEqual(first.points[0], (210.0, 0.0))

    def test_objective_scores(self) -> None:
        sheet, label, layout = self._scene()
        plan = build_cut_plan(label, layout, sheet=sheet)
        self.assertAlmostEqual(
            objective_score(plan, OBJECTIVE_DISTANCE), plan.total_length
        )
        self.assertGreater(
            objective_score(plan, OBJECTIVE_LIFTS), plan.lift_count * 1000
        )
        self.assertAlmostEqual(
            objective_score(plan, OBJECTIVE_BALANCED),
            plan.total_length + plan.lift_count * 75.0,
        )

    def test_compare_strategies_sorted_by_objective(self) -> None:
        sheet, label, layout = self._scene()
        plans = compare_strategies(label, layout, sheet=sheet)
        self.assertEqual(len(plans), 5)
        scores = [objective_score(plan, OBJECTIVE_DISTANCE) for _key, plan in plans]
        self.assertEqual(scores, sorted(scores))


class ImportTests(unittest.TestCase):
    def _export_scene(self, directory: Path, *, overlap: float = 0.0):
        sheet = SheetSpec(210, 297)
        label = LabelSpec(50, 30, 2, ShapeType.ROUNDED_RECT, overlap)
        layout = compute_layout(sheet, label, 2, 2, LayoutSpec(3, 4))
        pdf_path = directory / "dieline.pdf"
        dxf_path = directory / "dieline.dxf"
        export_pdf(pdf_path, sheet, label, layout)
        export_dxf(dxf_path, sheet, label, layout)
        return sheet, label, layout, pdf_path, dxf_path

    def test_pdf_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sheet, _label, layout, pdf_path, _dxf_path = self._export_scene(Path(tmp))
            self.assertEqual(pdf_page_count(pdf_path), 1)
            document = load_pdf(pdf_path)
            self.assertEqual(document.kind, "pdf")
            self.assertEqual(document.path_count, layout.count)
            self.assertTrue(all(path.closed for path in document.paths))
            self.assertAlmostEqual(document.sheet.width, sheet.width, delta=0.1)
            self.assertAlmostEqual(document.sheet.height, sheet.height, delta=0.1)

    def test_pdf_import_keeps_top_origin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _sheet, label, layout, pdf_path, _dxf_path = self._export_scene(
                Path(tmp)
            )
            document = load_pdf(pdf_path)
            ys = [point[1] for path in document.paths for point in path.points]
            xs = [point[0] for path in document.paths for point in path.points]

            expected_top = min(y for _x, y in layout.positions)
            expected_bottom = max(y for _x, y in layout.positions) + label.height
            expected_left = min(x for x, _y in layout.positions)
            expected_right = max(x for x, _y in layout.positions) + label.width

            self.assertAlmostEqual(min(ys), expected_top, delta=0.5)
            self.assertAlmostEqual(max(ys), expected_bottom, delta=0.5)
            self.assertAlmostEqual(min(xs), expected_left, delta=0.5)
            self.assertAlmostEqual(max(xs), expected_right, delta=0.5)

    def test_dxf_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _sheet, _label, layout, _pdf_path, dxf_path = self._export_scene(
                Path(tmp)
            )
            document = load_dxf(dxf_path)
            self.assertEqual(document.kind, "dxf")
            self.assertEqual(document.path_count, layout.count)
            self.assertTrue(all(path.closed for path in document.paths))
            self.assertAlmostEqual(document.sheet.width, layout.block_width, delta=0.5)
            self.assertAlmostEqual(document.sheet.height, layout.block_height, delta=0.5)

    def test_dxf_open_contours_stay_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _sheet, _label, layout, _pdf_path, dxf_path = self._export_scene(
                Path(tmp), overlap=2.0
            )
            document = load_dxf(dxf_path)
            self.assertEqual(document.path_count, layout.count)
            self.assertFalse(any(path.closed for path in document.paths))

            plan = build_imported_cut_plan(document)
            self.assertEqual(plan.label_count, layout.count)
            self.assertGreater(plan.cut_length, 0)

    def test_imported_plan_and_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _sheet, _label, layout, _pdf_path, dxf_path = self._export_scene(
                Path(tmp)
            )
            document = load_dxf(dxf_path)
            plan = build_imported_cut_plan(document)
            self.assertEqual(plan.label_count, document.path_count)
            self.assertGreater(plan.cut_length, 0)

            plans = compare_imported_strategies(document)
            self.assertEqual(len(plans), 5)
            scores = [
                objective_score(plan, OBJECTIVE_DISTANCE) for _key, plan in plans
            ]
            self.assertEqual(scores, sorted(scores))

    def test_export_imported_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _sheet, _label, _layout, pdf_path, _dxf_path = self._export_scene(
                Path(tmp)
            )
            document = load_pdf(pdf_path)
            out_pdf = Path(tmp) / "importado.pdf"
            out_dxf = Path(tmp) / "importado.dxf"
            export_document_pdf(out_pdf, document)
            export_document_dxf(out_dxf, document)

            self.assertEqual(out_pdf.read_bytes()[:4], b"%PDF")
            doc = ezdxf.readfile(out_dxf)
            self.assertIn("IMPORTADO", doc.layers)
            self.assertEqual(len(list(doc.modelspace())), document.path_count)

    def test_pdf_without_vectors(self) -> None:
        from reportlab.lib.units import mm as pdf_mm
        from reportlab.pdfgen import canvas as pdf_canvas

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "texto.pdf"
            c = pdf_canvas.Canvas(str(path), pagesize=(210 * pdf_mm, 297 * pdf_mm))
            c.drawString(20 * pdf_mm, 20 * pdf_mm, "Sem vetores")
            c.showPage()
            c.save()
            with self.assertRaises(ValueError):
                load_pdf(path)

    def test_empty_dxf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vazio.dxf"
            doc = ezdxf.new()
            doc.saveas(str(path))
            with self.assertRaises(ValueError):
                load_dxf(path)


class VersionTests(unittest.TestCase):
    def test_version_metadata(self) -> None:
        from app.ui.about import _version_text

        self.assertEqual(__version__, "4")
        self.assertIn("DieCUT Tool v4", _version_text())


if __name__ == "__main__":
    unittest.main()
