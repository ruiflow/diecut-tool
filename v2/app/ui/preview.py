"""Pré-visualização 2D/3D com zoom, pan, órbita e simulação de corte."""

from __future__ import annotations

import bisect
import math
from tkinter import Canvas
from typing import Callable

import customtkinter as ctk

from .. import geometry
from ..cutting import KIND_CUT, STRATEGY_LABELS, CutPlan
from ..models import LabelSpec, LayoutResult, SheetSpec
from . import theme

GRID_STEPS = (1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000, 2000)
THICKNESS_MM = 1.2
LABEL_LIFT_MM = 0.35
Z_FACTOR = 2.6
PADDING_PX = 46
PREVIEW_MAX_LABELS = 1500

SIM_TICK_MS = 33
SIM_DEFAULT_SPEED = 150.0
SIM_MIN_SPEED = 20.0
SIM_MAX_SPEED = 900.0
SIM_PLAN_MAX_LABELS = 500

MIN_PITCH = 5.0
MAX_PITCH = 88.0


def _points_up_to(points: tuple[geometry.Point, ...], distance: float) -> list[geometry.Point]:
    """Pontos de uma polilinha até percorrer `distance` mm."""

    if not points:
        return []
    if distance <= 1e-9:
        return [points[0]]

    result = [points[0]]
    remaining = distance
    for start, end in zip(points, points[1:]):
        segment = math.hypot(end[0] - start[0], end[1] - start[1])
        if segment <= 1e-12:
            continue
        if remaining >= segment:
            result.append(end)
            remaining -= segment
        else:
            ratio = remaining / segment
            result.append(
                (
                    start[0] + (end[0] - start[0]) * ratio,
                    start[1] + (end[1] - start[1]) * ratio,
                )
            )
            break
    return result


class PreviewCanvas(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color=theme.VIEW_BG, corner_radius=14, **kwargs)
        self.canvas = Canvas(
            self,
            bg=theme.VIEW_BG,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.sheet: SheetSpec | None = None
        self.label: LabelSpec | None = None
        self.layout: LayoutResult | None = None
        self.spacing_h = 2.0
        self.spacing_v = 2.0
        self.auto_mode = False

        self.view_mode = "2D"
        self.show_grid = True

        self.scale = 1.0
        self.origin_x = 0.0
        self.origin_y = 0.0
        self.auto_fit = True
        self._pan_last: tuple[int, int] | None = None
        self._orbit_last: tuple[int, int] | None = None
        self._width = 1
        self._height = 1

        # Câmara 3D (órbita com o rato).
        self.yaw = geometry.DEFAULT_YAW
        self.pitch = geometry.DEFAULT_PITCH

        # Simulação de corte.
        self.simulation_active = False
        self._sim_plan: CutPlan | None = None
        self._sim_total = 0.0
        self._sim_progress = 0.0
        self._sim_cumulative: list[float] = []
        self._sim_seg_drawn = 0
        self._sim_partial_item: int | None = None
        self._sim_head_item: int | None = None
        self._sim_head_cross: list[int] = []
        self._sim_progress_item: int | None = None
        self._sim_playing = False
        self._sim_job: str | None = None
        self._sim_speed = SIM_DEFAULT_SPEED

        self.on_zoom: Callable[[int], None] | None = None
        self.on_simulation_update: Callable[[float, bool], None] | None = None

        self.canvas.bind("<Configure>", self._on_configure)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<ButtonPress-2>", self._pan_start)
        self.canvas.bind("<B2-Motion>", self._pan_move)
        self.canvas.bind("<ButtonRelease-2>", self._pan_end)
        self.canvas.bind("<ButtonPress-3>", self._pan_start)
        self.canvas.bind("<B3-Motion>", self._pan_move)
        self.canvas.bind("<ButtonRelease-3>", self._pan_end)
        self.canvas.bind("<ButtonPress-1>", self._on_left_press)
        self.canvas.bind("<B1-Motion>", self._on_left_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_release)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)

    # ------------------------------------------------------------------
    #  API
    # ------------------------------------------------------------------
    def update_scene(
        self,
        sheet: SheetSpec,
        label: LabelSpec,
        layout: LayoutResult,
        spacing_h: float,
        spacing_v: float,
        auto: bool = False,
    ) -> None:
        if self.simulation_active:
            self.stop_simulation()
        self.sheet = sheet
        self.label = label
        self.layout = layout
        self.spacing_h = spacing_h
        self.spacing_v = spacing_v
        self.auto_mode = auto
        if self.auto_fit:
            self.fit(redraw=False)
        self.redraw()

    def set_view_mode(self, mode: str) -> None:
        if mode == self.view_mode:
            return
        self.view_mode = mode
        self.auto_fit = True
        self.fit()

    def set_grid(self, enabled: bool) -> None:
        self.show_grid = enabled
        self.redraw()

    def fit(self, redraw: bool = True) -> None:
        self.auto_fit = True
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        if not self.sheet or not self.sheet.is_valid:
            self.scale = 1.0
            self.origin_x = self.origin_y = 0.0
            if redraw:
                self.redraw()
            return

        sheet = self.sheet
        x0, y0, x1, y1 = self._view_bounds(sheet)

        raw_w = max(0.001, x1 - x0)
        raw_h = max(0.001, y1 - y0)
        self.scale = min(
            (cw - 2.0 * PADDING_PX) / raw_w,
            (ch - 2.0 * PADDING_PX) / raw_h,
        )
        self.scale = max(0.0001, self.scale)
        self.origin_x = (cw - raw_w * self.scale) / 2.0 - x0 * self.scale
        self.origin_y = (ch - raw_h * self.scale) / 2.0 - y0 * self.scale
        if redraw:
            self.redraw()

    def reset_view(self) -> None:
        """Repõe a câmara 3D e ajusta a vista à janela."""

        self.yaw = geometry.DEFAULT_YAW
        self.pitch = geometry.DEFAULT_PITCH
        self.fit()

    def zoom_in(self) -> None:
        self._zoom_at(self._width / 2.0, self._height / 2.0, 1.22)

    def zoom_out(self) -> None:
        self._zoom_at(self._width / 2.0, self._height / 2.0, 1.0 / 1.22)

    def zoom_percent(self) -> int:
        fit = self._fit_scale()
        if fit <= 0:
            return 100
        return max(1, int(round(self.scale / fit * 100.0)))

    # ------------------------------------------------------------------
    #  Simulação de corte
    # ------------------------------------------------------------------
    @property
    def simulation_playing(self) -> bool:
        return self._sim_playing

    @property
    def simulation_progress(self) -> float:
        if self._sim_total <= 1e-9:
            return 0.0
        return min(1.0, max(0.0, self._sim_progress / self._sim_total))

    @property
    def simulation_plan(self) -> CutPlan | None:
        return self._sim_plan

    def start_simulation(self, plan: CutPlan) -> None:
        self._cancel_sim_job()
        self._orbit_last = None
        self.canvas.configure(cursor="")
        self.simulation_active = True
        self._sim_plan = plan
        self._sim_total = max(0.0, plan.total_length)
        self._sim_cumulative = [0.0]
        for segment in plan.segments:
            self._sim_cumulative.append(self._sim_cumulative[-1] + segment.length)
        self._sim_progress = 0.0
        self._sim_seg_drawn = 0
        self._sim_partial_item = None
        self._sim_head_item = None
        self._sim_head_cross = []
        self._sim_progress_item = None
        self._sim_playing = self._sim_total > 1e-9
        self.auto_fit = True
        self.fit(redraw=False)
        self.redraw()
        self._emit_sim(False)
        if self._sim_playing:
            self._schedule_sim_tick()

    def stop_simulation(self) -> None:
        self._cancel_sim_job()
        self.simulation_active = False
        self._sim_plan = None
        self._sim_playing = False
        self._sim_progress = 0.0
        self._sim_cumulative = []
        self._sim_seg_drawn = 0
        self._sim_partial_item = None
        self._sim_head_item = None
        self._sim_head_cross = []
        self._sim_progress_item = None
        self.redraw()

    def play_simulation(self) -> None:
        if not self.simulation_active or self._sim_total <= 1e-9:
            return
        if self._sim_progress >= self._sim_total - 1e-9:
            self.restart_simulation()
            return
        self._sim_playing = True
        self._schedule_sim_tick()
        self._emit_sim(False)

    def pause_simulation(self) -> None:
        if not self.simulation_active:
            return
        self._sim_playing = False
        self._cancel_sim_job()
        self._emit_sim(False)

    def toggle_simulation(self) -> None:
        if self._sim_playing:
            self.pause_simulation()
        else:
            self.play_simulation()

    def restart_simulation(self) -> None:
        if not self.simulation_active:
            return
        self._cancel_sim_job()
        self._sim_progress = 0.0
        self._sim_seg_drawn = 0
        self._sim_partial_item = None
        self._sim_head_item = None
        self._sim_head_cross = []
        self._sim_playing = True
        self.redraw()
        self._emit_sim(False)
        if self._sim_total > 1e-9:
            self._schedule_sim_tick()

    def set_simulation_speed(self, speed_mm_s: float) -> None:
        self._sim_speed = max(SIM_MIN_SPEED, min(SIM_MAX_SPEED, speed_mm_s))

    def _schedule_sim_tick(self) -> None:
        if self._sim_job is None and self.simulation_active and self._sim_playing:
            self._sim_job = self.after(SIM_TICK_MS, self._sim_tick)

    def _cancel_sim_job(self) -> None:
        if self._sim_job is not None:
            try:
                self.after_cancel(self._sim_job)
            except Exception:
                pass
            self._sim_job = None

    def _sim_tick(self) -> None:
        self._sim_job = None
        if not self.simulation_active or not self._sim_playing:
            return

        delta = self._sim_speed * (SIM_TICK_MS / 1000.0)
        self._sim_progress = min(self._sim_total, self._sim_progress + delta)
        self._render_sim_progress()

        finished = self._sim_progress >= self._sim_total - 1e-9
        if finished:
            self._sim_playing = False
            self._emit_sim(True)
            return
        self._emit_sim(False)
        self._schedule_sim_tick()

    def _emit_sim(self, finished: bool) -> None:
        if self.on_simulation_update:
            self.on_simulation_update(self.simulation_progress, finished)

    # ------------------------------------------------------------------
    #  Eventos
    # ------------------------------------------------------------------
    def _on_configure(self, event) -> None:
        self._width = max(1, event.width)
        self._height = max(1, event.height)
        if self.auto_fit:
            self.fit(redraw=False)
        self.redraw()

    def _on_wheel(self, event) -> None:
        if event.delta == 0:
            return
        factor = 1.12 if event.delta > 0 else 1.0 / 1.12
        self._zoom_at(event.x, event.y, factor)

    def _zoom_at(self, px: float, py: float, factor: float) -> None:
        if not self.sheet or not self.sheet.is_valid:
            return
        new_scale = max(0.002, min(80.0, self.scale * factor))
        factor = new_scale / self.scale
        self.origin_x = px - (px - self.origin_x) * factor
        self.origin_y = py - (py - self.origin_y) * factor
        self.scale = new_scale
        self.auto_fit = False
        self.redraw()

    def _pan_start(self, event) -> None:
        self._pan_last = (event.x, event.y)
        self.canvas.configure(cursor="fleur")

    def _pan_move(self, event) -> None:
        if self._pan_last is None:
            return
        dx = event.x - self._pan_last[0]
        dy = event.y - self._pan_last[1]
        self._pan_last = (event.x, event.y)
        self.origin_x += dx
        self.origin_y += dy
        self.auto_fit = False
        self.redraw()

    def _pan_end(self, _event) -> None:
        self._pan_last = None
        self.canvas.configure(cursor="")

    def _on_left_press(self, event) -> None:
        if self.view_mode != "3D" or self.simulation_active:
            return
        self._orbit_last = (event.x, event.y)
        self.canvas.configure(cursor="exchange")

    def _on_left_motion(self, event) -> None:
        if self._orbit_last is None:
            return
        dx = event.x - self._orbit_last[0]
        dy = event.y - self._orbit_last[1]
        self._orbit_last = (event.x, event.y)
        self.yaw = (self.yaw - dx * 0.55) % 360.0
        self.pitch = max(MIN_PITCH, min(MAX_PITCH, self.pitch - dy * 0.4))
        if self.auto_fit:
            self.fit(redraw=False)
        self.redraw()

    def _on_left_release(self, _event) -> None:
        if self._orbit_last is None:
            return
        self._orbit_last = None
        self.canvas.configure(cursor="")

    def _on_double_click(self, _event) -> None:
        if self.view_mode == "3D" and not self.simulation_active:
            self.reset_view()
        else:
            self.fit()

    # ------------------------------------------------------------------
    #  Desenho
    # ------------------------------------------------------------------
    def redraw(self) -> None:
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        self._width, self._height = cw, ch
        self.canvas.delete("all")

        if not self.sheet or not self.sheet.is_valid:
            self._placeholder("Sem pré-visualização", "Introduza as medidas da folha.")
            self._emit_zoom()
            return

        if self.simulation_active:
            self._draw_simulation(cw, ch)
        elif self.view_mode == "3D":
            self._draw_3d(cw, ch)
        else:
            self._draw_2d(cw, ch)
        self._emit_zoom()

    def _emit_zoom(self) -> None:
        if self.on_zoom:
            self.on_zoom(self.zoom_percent())

    def _view_bounds(self, sheet: SheetSpec) -> tuple[float, float, float, float]:
        if self.simulation_active or self.view_mode != "3D":
            return 0.0, 0.0, sheet.width, sheet.height
        return geometry.OrbitProjector.bounds(
            sheet.width,
            sheet.height,
            0.0,
            THICKNESS_MM + LABEL_LIFT_MM,
            self.yaw,
            self.pitch,
            Z_FACTOR,
        )

    def _fit_scale(self) -> float:
        if not self.sheet or not self.sheet.is_valid:
            return 1.0
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        x0, y0, x1, y1 = self._view_bounds(self.sheet)
        return min(
            (cw - 2.0 * PADDING_PX) / max(0.001, x1 - x0),
            (ch - 2.0 * PADDING_PX) / max(0.001, y1 - y0),
        )

    def _placeholder(self, title: str, subtitle: str) -> None:
        cx, cy = self.canvas.winfo_width() / 2.0, self.canvas.winfo_height() / 2.0
        self.canvas.create_text(
            cx,
            cy - 12,
            text=title,
            fill=theme.TEXT_DIM,
            font=theme.font(18, "bold"),
        )
        self.canvas.create_text(
            cx,
            cy + 16,
            text=subtitle,
            fill=theme.MUTED,
            font=theme.font(12),
        )

    def _grid_step(self, scale: float) -> int:
        target = 26.0
        for step in GRID_STEPS:
            if step * scale >= target:
                return step
        return GRID_STEPS[-1]

    # ---------------------------------------------------------------- 2D
    def _draw_2d(self, cw: int, ch: int, simulation: bool = False) -> None:
        if not self.sheet or not self.label or not self.layout:
            return
        sheet = self.sheet
        label = self.label
        layout = self.layout
        sc = self.scale
        ox, oy = self.origin_x, self.origin_y
        sw = sheet.width * sc
        sh = sheet.height * sc

        # Sombra suave + folha
        self.canvas.create_rectangle(
            ox + 7, oy + 9, ox + sw + 7, oy + sh + 9,
            fill="#05070a", outline="", stipple="gray50",
        )
        self.canvas.create_rectangle(
            ox, oy, ox + sw, oy + sh,
            fill=theme.SHEET, outline=theme.SHEET_LINE, width=1,
        )

        if self.show_grid:
            self._draw_grid_2d(ox, oy, sw, sh, sc)

        if layout.count > 0:
            self._draw_block_outline_2d(ox, oy, sc)
        self._draw_labels_2d(ox, oy, sc, dim=simulation)

        if simulation:
            self._draw_sim_planned_route()

        self._clip_outside_sheet_2d(ox, oy, sw, sh)

        if layout.count == 0:
            self.canvas.create_text(
                ox + sw / 2.0,
                oy + sh / 2.0,
                text=self._empty_text(label, layout),
                fill="#b07810" if label.is_valid else theme.MUTED,
                font=theme.font(14, "bold"),
            )

        if simulation and self._sim_plan:
            plan = self._sim_plan
            links = (
                f"{plan.link_count} ligaç"
                f"{'ão' if plan.link_count == 1 else 'ões'}"
            )
            lifts = (
                f"{plan.lift_count} elevaç"
                f"{'ão' if plan.lift_count == 1 else 'ões'}"
            )
            info = (
                f"{STRATEGY_LABELS.get(plan.strategy, plan.strategy)}   •   "
                f"Corte {plan.cut_length:,.0f} mm   •   "
                f"{links}   •   "
                f"deslocamento {plan.travel_length:,.0f} mm   •   "
                f"{lifts}"
            )
            if plan.truncated:
                info += "   •   simulação parcial"
        else:
            info = f"{sheet.width:g} × {sheet.height:g} mm"
            if layout.count > PREVIEW_MAX_LABELS:
                info += "   •   pré-visualização parcial"
        self._draw_info(info, ox, min(ch - 14, oy + sh + 16))

    def _draw_grid_2d(self, ox: float, oy: float, sw: float, sh: float, sc: float) -> None:
        step = self._grid_step(sc)
        major = step * 5
        max_x = self.sheet.width if self.sheet else 0.0
        max_y = self.sheet.height if self.sheet else 0.0

        x = step
        while x < max_x:
            px = ox + x * sc
            is_major = abs(x / major - round(x / major)) < 1e-6
            self.canvas.create_line(
                px, oy, px, oy + sh,
                fill="#d6dbe4" if is_major else "#e5e8ee",
                width=1,
            )
            x += step

        y = step
        while y < max_y:
            py = oy + y * sc
            is_major = abs(y / major - round(y / major)) < 1e-6
            self.canvas.create_line(
                ox, py, ox + sw, py,
                fill="#d6dbe4" if is_major else "#e5e8ee",
                width=1,
            )
            y += step

    def _draw_block_outline_2d(self, ox: float, oy: float, sc: float) -> None:
        if not self.layout or not self.layout.positions:
            return
        xs = [p[0] for p in self.layout.positions]
        ys = [p[1] for p in self.layout.positions]
        x1 = min(xs)
        y1 = min(ys)
        x2 = max(xs) + self.layout.cell_width
        y2 = max(ys) + self.layout.cell_height
        self.canvas.create_rectangle(
            ox + x1 * sc, oy + y1 * sc, ox + x2 * sc, oy + y2 * sc,
            outline="#aeb7c8", width=1, dash=(2, 4),
        )

    def _clip_outside_sheet_2d(self, ox: float, oy: float, sw: float, sh: float) -> None:
        """Esconde dielines que saem da folha (o Tk não tem clipping nativo)."""

        cw, ch = self._width, self._height
        zones = (
            (0, 0, cw, oy),
            (0, oy + sh, cw, ch),
            (0, oy, ox, oy + sh),
            (ox + sw, oy, cw, oy + sh),
        )
        for x1, y1, x2, y2 in zones:
            if x2 > x1 and y2 > y1:
                self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=theme.VIEW_BG, outline=""
                )
        self.canvas.create_rectangle(
            ox, oy, ox + sw, oy + sh,
            fill="", outline=theme.SHEET_LINE, width=1,
        )

    def _draw_labels_2d(self, ox: float, oy: float, sc: float, *, dim: bool = False) -> None:
        if not self.label or not self.layout:
            return
        label = self.label
        layout = self.layout
        count = layout.count
        simplified = count > 400
        quality = "low" if simplified else "high"
        line_width = 2 if count <= 300 else 1
        cw, ch = self._width, self._height

        outline_color = "#b6becd" if dim else theme.ACCENT
        fill_color = "#eef1f5" if dim else "#f8dceb"

        for cell_x, cell_y in layout.positions[:PREVIEW_MAX_LABELS]:
            ex, ey = layout_origin(label, layout, cell_x, cell_y)
            path = geometry.dieline_path(label, ex, ey, quality=quality)
            if len(path.contour) < 3:
                continue
            contour = [(ox + px * sc, oy + py * sc) for px, py in path.contour]
            min_x = min(p[0] for p in contour)
            max_x = max(p[0] for p in contour)
            min_y = min(p[1] for p in contour)
            max_y = max(p[1] for p in contour)
            if max_x < -30 or min_x > cw + 30 or max_y < -30 or min_y > ch + 30:
                continue

            if not simplified:
                self._polygon(contour, fill=fill_color, outline="")

            draw_points = path.points
            if path.closed:
                draw_points = draw_points + [draw_points[0]]
            self._line(
                [(ox + px * sc, oy + py * sc) for px, py in draw_points],
                fill=outline_color,
                width=1 if dim else line_width,
            )

            if path.overlap and not dim:
                self._line(
                    [(ox + px * sc, oy + py * sc) for px, py in path.overlap],
                    fill=theme.CYAN,
                    width=line_width + 1,
                )

    # ---------------------------------------------------------------- simulação
    def _draw_simulation(self, cw: int, ch: int) -> None:
        self._sim_seg_drawn = 0
        self._sim_partial_item = None
        self._sim_head_item = None
        self._sim_head_cross = []
        self._sim_progress_item = None

        self._draw_2d(cw, ch, simulation=True)

        self._sim_progress_item = self.canvas.create_text(
            18,
            18,
            text="0%",
            anchor="nw",
            fill=theme.CYAN,
            font=theme.font(16, "bold"),
        )
        self._render_sim_progress()

    def _draw_sim_planned_route(self) -> None:
        if not self._sim_plan:
            return
        if self._sim_plan.label_count > SIM_PLAN_MAX_LABELS:
            return
        for segment in self._sim_plan.segments:
            if len(segment.points) < 2:
                continue
            if segment.kind == KIND_CUT:
                self._line(
                    [self._to_canvas(point) for point in segment.points],
                    fill="#aeb7c8",
                    width=1,
                )
            else:
                self._line(
                    [self._to_canvas(point) for point in segment.points],
                    fill="#c9cfdb",
                    width=1,
                    dash=(2, 4),
                )

    def _render_sim_progress(self) -> None:
        plan = self._sim_plan
        if not plan or not plan.segments or self._sim_total <= 1e-9:
            return

        index = bisect.bisect_right(self._sim_cumulative, self._sim_progress) - 1
        index = max(0, min(index, len(plan.segments) - 1))

        while self._sim_seg_drawn < index:
            self._draw_sim_segment(self._sim_seg_drawn)
            self._sim_seg_drawn += 1

        segment = plan.segments[index]
        local = self._sim_progress - self._sim_cumulative[index]
        local = max(0.0, min(local, segment.length))
        points = _points_up_to(segment.points, local)

        if self._sim_partial_item is not None:
            self.canvas.delete(self._sim_partial_item)
            self._sim_partial_item = None
        if len(points) >= 2:
            if segment.kind == KIND_CUT:
                self._sim_partial_item = self._line(
                    [self._to_canvas(point) for point in points],
                    fill=theme.ACCENT,
                    width=2,
                )
            else:
                self._sim_partial_item = self._line(
                    [self._to_canvas(point) for point in points],
                    fill=theme.CYAN,
                    width=1,
                    dash=(3, 3),
                )

        head = points[-1] if points else segment.points[0]
        self._update_sim_head(head)

        if self._sim_progress_item is not None:
            self.canvas.itemconfigure(
                self._sim_progress_item,
                text=f"{self.simulation_progress * 100.0:.0f}%",
            )

    def _draw_sim_segment(self, index: int) -> None:
        plan = self._sim_plan
        if not plan or index >= len(plan.segments):
            return
        segment = plan.segments[index]
        if len(segment.points) < 2:
            return
        if segment.kind == KIND_CUT:
            self._line(
                [self._to_canvas(point) for point in segment.points],
                fill=theme.ACCENT,
                width=2,
            )
        else:
            self._line(
                [self._to_canvas(point) for point in segment.points],
                fill=theme.CYAN,
                width=1,
                dash=(3, 3),
            )

    def _update_sim_head(self, point: geometry.Point) -> None:
        cx, cy = self._to_canvas(point)
        if self._sim_head_item is None:
            self._sim_head_item = self.canvas.create_oval(
                cx - 5,
                cy - 5,
                cx + 5,
                cy + 5,
                fill=theme.RED,
                outline="#ffffff",
                width=1,
            )
            self._sim_head_cross = [
                self.canvas.create_line(cx - 12, cy, cx - 6, cy, fill=theme.RED, width=1),
                self.canvas.create_line(cx + 6, cy, cx + 12, cy, fill=theme.RED, width=1),
                self.canvas.create_line(cx, cy - 12, cx, cy - 6, fill=theme.RED, width=1),
                self.canvas.create_line(cx, cy + 6, cx, cy + 12, fill=theme.RED, width=1),
            ]
            return

        self.canvas.coords(
            self._sim_head_item, cx - 5, cy - 5, cx + 5, cy + 5
        )
        cross = (
            (cx - 12, cy, cx - 6, cy),
            (cx + 6, cy, cx + 12, cy),
            (cx, cy - 12, cx, cy - 6),
            (cx, cy + 6, cx, cy + 12),
        )
        for item, coords in zip(self._sim_head_cross, cross):
            self.canvas.coords(item, *coords)

    def _to_canvas(self, point: geometry.Point) -> tuple[float, float]:
        return self.origin_x + point[0] * self.scale, self.origin_y + point[1] * self.scale

    # ---------------------------------------------------------------- 3D
    def _draw_3d(self, cw: int, ch: int) -> None:
        if not self.sheet or not self.label or not self.layout:
            return
        sheet = self.sheet
        label = self.label
        layout = self.layout
        top = THICKNESS_MM
        z_max = top + LABEL_LIFT_MM
        pivot = (sheet.width / 2.0, sheet.height / 2.0, (top + z_max) / 2.0)
        proj = geometry.OrbitProjector(
            self.scale,
            self.origin_x,
            self.origin_y,
            self.yaw,
            self.pitch,
            Z_FACTOR,
            pivot,
        )

        # Faces laterais viradas para a câmara.
        if abs(proj.forward[0]) > 1e-6:
            side_x = sheet.width if proj.forward[0] > 0 else 0.0
            self._polygon(
                [
                    proj.project(side_x, 0.0, 0.0),
                    proj.project(side_x, sheet.height, 0.0),
                    proj.project(side_x, sheet.height, top),
                    proj.project(side_x, 0.0, top),
                ],
                fill="#c8ceda",
                outline="#b9c0cd",
                width=1,
            )
        if abs(proj.forward[1]) > 1e-6:
            side_y = sheet.height if proj.forward[1] > 0 else 0.0
            self._polygon(
                [
                    proj.project(0.0, side_y, 0.0),
                    proj.project(sheet.width, side_y, 0.0),
                    proj.project(sheet.width, side_y, top),
                    proj.project(0.0, side_y, top),
                ],
                fill="#d5dae4",
                outline="#b9c0cd",
                width=1,
            )

        corners = [
            (0.0, 0.0, top),
            (sheet.width, 0.0, top),
            (sheet.width, sheet.height, top),
            (0.0, sheet.height, top),
        ]
        self._polygon(
            [proj.project(*corner) for corner in corners],
            fill=theme.SHEET,
            outline=theme.SHEET_LINE,
            width=1,
        )

        if self.show_grid:
            self._draw_grid_3d(proj, top)

        # Etiquetas: longe -> perto para oclusão correta.
        order = sorted(
            layout.positions,
            key=lambda pos: proj.depth(
                pos[0] + label.width / 2.0,
                pos[1] + label.height / 2.0,
                z_max,
            ),
        )[:PREVIEW_MAX_LABELS]
        simplified = layout.count > 350
        for cell_x, cell_y in order:
            ex, ey = layout_origin(label, layout, cell_x, cell_y)
            path = geometry.dieline_path(
                label, ex, ey, quality="low" if simplified else "high"
            )
            if len(path.contour) < 3:
                continue
            top_points = [proj.project(px, py, z_max) for px, py in path.contour]
            if not self._visible(top_points, cw, ch):
                continue
            bottom_points = [proj.project(px, py, top) for px, py in path.contour]

            if not simplified:
                self._polygon(bottom_points, fill="#a72c75", outline="")
                self._polygon(top_points, fill="#f8dceb", outline="")

            draw_points = path.points
            if path.closed:
                draw_points = draw_points + [draw_points[0]]
            self._line(
                [proj.project(px, py, z_max + 0.02) for px, py in draw_points],
                fill=theme.ACCENT,
                width=1,
            )

            if path.overlap:
                self._line(
                    [proj.project(px, py, z_max + 0.03) for px, py in path.overlap],
                    fill=theme.CYAN,
                    width=2,
                )

        if layout.count == 0:
            self.canvas.create_text(
                cw / 2.0,
                ch / 2.0,
                text=self._empty_text(label, layout),
                fill=theme.AMBER if label.is_valid else theme.MUTED,
                font=theme.font(14, "bold"),
            )

        info = (
            f"{sheet.width:g} × {sheet.height:g} mm   •   "
            "arraste com o botão esquerdo para rodar   •   duplo clique repõe"
        )
        if layout.count > PREVIEW_MAX_LABELS:
            info += "   •   pré-visualização parcial"
        self._draw_info(info, 18, ch - 18)

    def _draw_grid_3d(self, proj: geometry.OrbitProjector, z: float) -> None:
        if not self.sheet:
            return
        step = self._grid_step(self.scale)
        major = step * 5
        w, h = self.sheet.width, self.sheet.height

        x = step
        while x < w:
            is_major = abs(x / major - round(x / major)) < 1e-6
            self.canvas.create_line(
                *proj.project(x, 0.0, z),
                *proj.project(x, h, z),
                fill="#d6dbe4" if is_major else "#e5e8ee",
                width=1,
            )
            x += step

        y = step
        while y < h:
            is_major = abs(y / major - round(y / major)) < 1e-6
            self.canvas.create_line(
                *proj.project(0.0, y, z),
                *proj.project(w, y, z),
                fill="#d6dbe4" if is_major else "#e5e8ee",
                width=1,
            )
            y += step

    # ---------------------------------------------------------------- utils
    def _empty_text(self, label: LabelSpec, layout: LayoutResult) -> str:
        if not label.is_valid:
            return "Defina as medidas da etiqueta"
        if not self.auto_mode and (layout.columns <= 0 or layout.rows <= 0):
            return "Indique colunas e fileiras"
        return "A etiqueta não cabe na folha"

    def _visible(self, points: list[tuple[float, float]], cw: int, ch: int) -> bool:
        if not points:
            return False
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return not (max(xs) < -40 or min(xs) > cw + 40 or max(ys) < -40 or min(ys) > ch + 40)

    def _polygon(self, points, **kwargs):
        if not points:
            return None
        flat = [coord for point in points for coord in point]
        return self.canvas.create_polygon(flat, **kwargs)

    def _line(self, points, **kwargs):
        if len(points) < 2:
            return None
        flat = [coord for point in points for coord in point]
        return self.canvas.create_line(flat, **kwargs)

    def _draw_info(self, text: str, x: float, y: float) -> None:
        self.canvas.create_text(
            x,
            y,
            text=text,
            anchor="w",
            fill=theme.MUTED,
            font=theme.font(9),
        )


def layout_origin(
    label: LabelSpec, layout: LayoutResult, cell_x: float, cell_y: float
) -> tuple[float, float]:
    """Origem do caminho compensado dentro da célula (reexportado para a UI)."""

    from ..layout import shape_origin

    return shape_origin(label, cell_x, cell_y, layout.cell_width, layout.cell_height)
