"""Pré-visualização 2D/3D com zoom, pan, grelha e margens destacadas."""

from __future__ import annotations

from tkinter import Canvas
from typing import Callable

import customtkinter as ctk

from .. import geometry
from ..models import LabelSpec, LayoutResult, SheetSpec
from . import theme

GRID_STEPS = (1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000, 2000)
THICKNESS_MM = 1.2
LABEL_LIFT_MM = 0.35
Z_FACTOR = 2.6
PADDING_PX = 46
PREVIEW_MAX_LABELS = 1500


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
        self.show_margins = True

        self.scale = 1.0
        self.origin_x = 0.0
        self.origin_y = 0.0
        self.auto_fit = True
        self._pan_last: tuple[int, int] | None = None
        self._width = 1
        self._height = 1

        self.on_zoom: Callable[[int], None] | None = None

        self.canvas.bind("<Configure>", self._on_configure)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<ButtonPress-2>", self._pan_start)
        self.canvas.bind("<B2-Motion>", self._pan_move)
        self.canvas.bind("<ButtonRelease-2>", self._pan_end)
        self.canvas.bind("<ButtonPress-3>", self._pan_start)
        self.canvas.bind("<B3-Motion>", self._pan_move)
        self.canvas.bind("<ButtonRelease-3>", self._pan_end)
        self.canvas.bind("<Double-Button-1>", lambda _e: self.fit())

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

    def set_margins(self, enabled: bool) -> None:
        self.show_margins = enabled
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
        if self.view_mode == "3D":
            x0, y0, x1, y1 = geometry.IsoProjector.raw_bounds(
                sheet.width,
                sheet.height,
                0.0,
                THICKNESS_MM + LABEL_LIFT_MM,
                Z_FACTOR,
            )
        else:
            x0, y0, x1, y1 = 0.0, 0.0, sheet.width, sheet.height

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

        if self.view_mode == "3D":
            self._draw_3d(cw, ch)
        else:
            self._draw_2d(cw, ch)
        self._emit_zoom()

    def _emit_zoom(self) -> None:
        if self.on_zoom:
            self.on_zoom(self.zoom_percent())

    def _fit_scale(self) -> float:
        if not self.sheet or not self.sheet.is_valid:
            return 1.0
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        if self.view_mode == "3D":
            x0, y0, x1, y1 = geometry.IsoProjector.raw_bounds(
                self.sheet.width,
                self.sheet.height,
                0.0,
                THICKNESS_MM + LABEL_LIFT_MM,
                Z_FACTOR,
            )
        else:
            x0, y0, x1, y1 = 0.0, 0.0, self.sheet.width, self.sheet.height
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
    def _draw_2d(self, cw: int, ch: int) -> None:
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

        if self.show_margins:
            self._draw_margins_2d(ox, oy, sw, sh, sc)

        if layout.count > 0:
            self._draw_block_outline_2d(ox, oy, sc)
        self._draw_labels_2d(ox, oy, sc)
        self._clip_outside_sheet_2d(ox, oy, sw, sh)

        # Dimensões e contagem
        info = f"{sheet.width:g} × {sheet.height:g} mm"
        if self.show_margins and sheet.margin > 0:
            info += f"   •   margem {sheet.margin:g} mm"
        if layout.count > PREVIEW_MAX_LABELS:
            info += "   •   pré-visualização parcial"
        if layout.count == 0:
            self.canvas.create_text(
                ox + sw / 2.0,
                oy + sh / 2.0,
                text=self._empty_text(label, layout),
                fill="#b07810" if label.is_valid else theme.MUTED,
                font=theme.font(14, "bold"),
            )
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

    def _draw_margins_2d(self, ox: float, oy: float, sw: float, sh: float, sc: float) -> None:
        if not self.sheet:
            return
        margin = max(0.0, min(self.sheet.margin, self.sheet.width / 2.0, self.sheet.height / 2.0))
        if margin <= 0:
            return
        m = margin * sc
        zones = (
            (ox, oy, ox + sw, oy + m),
            (ox, oy + sh - m, ox + sw, oy + sh),
            (ox, oy + m, ox + m, oy + sh - m),
            (ox + sw - m, oy + m, ox + sw, oy + sh - m),
        )
        for x1, y1, x2, y2 in zones:
            if x2 > x1 and y2 > y1:
                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=theme.AMBER, outline="", stipple="gray12",
                )
        self.canvas.create_rectangle(
            ox + m, oy + m, ox + sw - m, oy + sh - m,
            outline="#c98f1e", width=1, dash=(5, 3),
        )
        if m > 34:
            self.canvas.create_text(
                ox + m + 5,
                oy + m + 4,
                text=f"margem {margin:g} mm",
                anchor="nw",
                fill="#a87512",
                font=theme.font(9),
            )

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

    def _draw_labels_2d(self, ox: float, oy: float, sc: float) -> None:
        if not self.label or not self.layout:
            return
        label = self.label
        layout = self.layout
        count = layout.count
        simplified = count > 400
        quality = "low" if simplified else "high"
        line_width = 2 if count <= 300 else 1
        cw, ch = self._width, self._height

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
                self._polygon(contour, fill="#f8dceb", outline="")

            draw_points = path.points
            if path.closed:
                draw_points = draw_points + [draw_points[0]]
            self._line(
                [(ox + px * sc, oy + py * sc) for px, py in draw_points],
                fill=theme.ACCENT,
                width=line_width,
            )

            if path.overlap:
                self._line(
                    [(ox + px * sc, oy + py * sc) for px, py in path.overlap],
                    fill=theme.CYAN,
                    width=line_width + 1,
                )

    # ---------------------------------------------------------------- 3D
    def _draw_3d(self, cw: int, ch: int) -> None:
        if not self.sheet or not self.label or not self.layout:
            return
        sheet = self.sheet
        label = self.label
        layout = self.layout
        proj = geometry.IsoProjector(self.scale, self.origin_x, self.origin_y, Z_FACTOR)

        top = THICKNESS_MM
        z_max = top + LABEL_LIFT_MM
        corners = [
            (0.0, 0.0, top),
            (sheet.width, 0.0, top),
            (sheet.width, sheet.height, top),
            (0.0, sheet.height, top),
        ]
        projected = [proj.project(*corner) for corner in corners]

        # Faces laterais visíveis (B-C e C-D)
        for a, b in ((1, 2), (2, 3)):
            p1 = proj.project(*corners[a])
            p2 = proj.project(*corners[b])
            p3 = proj.project(corners[b][0], corners[b][1], 0.0)
            p4 = proj.project(corners[a][0], corners[a][1], 0.0)
            self._polygon(
                [p1, p2, p3, p4],
                fill="#d5dae4" if a == 1 else "#c8ceda",
                outline="#b9c0cd",
                width=1,
            )

        self._polygon(projected, fill=theme.SHEET, outline=theme.SHEET_LINE, width=1)

        if self.show_grid:
            self._draw_grid_3d(proj, top)

        if self.show_margins:
            self._draw_margins_3d(proj, top)

        # Etiquetas: longe -> perto para oclusão correta.
        order = sorted(
            layout.positions,
            key=lambda pos: pos[0] + pos[1],
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

            # Sombra / volume
            if not simplified:
                self._polygon(
                    [(x + 2.5, y + 3.5) for x, y in top_points],
                    fill="#b9bfcc",
                    outline="",
                )
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

        info = f"{sheet.width:g} × {sheet.height:g} mm   •   vista isométrica"
        if layout.count > PREVIEW_MAX_LABELS:
            info += "   •   pré-visualização parcial"
        self._draw_info(info, 18, ch - 18)

    def _draw_grid_3d(self, proj: geometry.IsoProjector, z: float) -> None:
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

    def _draw_margins_3d(self, proj: geometry.IsoProjector, z: float) -> None:
        if not self.sheet:
            return
        sheet = self.sheet
        margin = max(
            0.0,
            min(sheet.margin, sheet.width / 2.0, sheet.height / 2.0),
        )
        if margin <= 0:
            return
        w, h, m = sheet.width, sheet.height, margin
        zones = (
            [(0, 0), (w, 0), (w, m), (0, m)],
            [(0, h - m), (w, h - m), (w, h), (0, h)],
            [(0, m), (m, m), (m, h - m), (0, h - m)],
            [(w - m, m), (w, m), (w, h - m), (w - m, h - m)],
        )
        for zone in zones:
            self._polygon(
                [proj.project(x, y, z) for x, y in zone],
                fill=theme.AMBER,
                outline="",
                stipple="gray12",
            )
        inset = [
            (m, m),
            (w - m, m),
            (w - m, h - m),
            (m, h - m),
        ]
        self._polygon(
            [proj.project(x, y, z) for x, y in inset],
            fill="",
            outline="#c98f1e",
            width=1,
            dash=(5, 3),
        )

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
