"""Janela principal da DieCUT Tool v3."""

from __future__ import annotations

import re
import tkinter as tk
import unicodedata
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import geometry
from ..cutting import (
    STRATEGY_KEYS,
    STRATEGY_LABELS,
    STRATEGY_PROXIMITY,
    STRATEGY_ZIGZAG,
    CutPlan,
    build_cut_plan,
)
from ..exporters import export_cut_plan_dxf, export_cut_plan_pdf, export_dxf, export_pdf
from ..layout import auto_grid, compute_layout
from ..models import (
    ALIGN_H,
    ALIGN_V,
    LabelSpec,
    LayoutResult,
    LayoutSpec,
    ShapeType,
    SheetSpec,
)
from ..resources import asset_path
from . import theme
from .preview import PreviewCanvas
from .widgets import Card, NumberSpinbox, StatusDot


class MainWindow(ctk.CTk):
    APP_NAME = "DieCUT Tool"
    VERSION = "3"

    def __init__(self) -> None:
        super().__init__(fg_color=theme.BG)
        self.title(f"{self.APP_NAME} v{self.VERSION} - Gerador de cortantes")
        self.geometry("1280x860")
        self.minsize(1060, 700)

        try:
            self.iconbitmap(asset_path("icon.ico"))
        except (tk.TclError, OSError):
            pass

        self._syncing = False
        self._refresh_job: str | None = None
        self._cutting_job: str | None = None
        self._last_export_dir = str(Path.home())
        self._sheet = SheetSpec(0, 0)
        self._label = LabelSpec(0, 0)
        self._layout = LayoutResult()
        self._sim_plan: CutPlan | None = None
        self._previous_view_mode = "2D"

        self._create_variables()
        self._build_layout()
        self._attach_traces()

        self.after(80, self._refresh)

    # ------------------------------------------------------------------
    #  Variáveis
    # ------------------------------------------------------------------
    def _create_variables(self) -> None:
        self.sheet_w = ctk.StringVar(value="210")
        self.sheet_h = ctk.StringVar(value="297")

        self.label_w = ctk.StringVar(value="50")
        self.label_h = ctk.StringVar(value="30")
        self.label_radius = ctk.StringVar(value="2")
        self.compensation = ctk.StringVar(value="0")
        self.shape = ctk.StringVar(value=ShapeType.ROUNDED_RECT.value)

        self.auto_mode = ctk.BooleanVar(value=False)
        self.columns = ctk.StringVar(value="2")
        self.rows = ctk.StringVar(value="4")
        self.spacing_h = ctk.StringVar(value="2")
        self.spacing_v = ctk.StringVar(value="2")

        self.align_h = ctk.StringVar(value="Centro")
        self.align_v = ctk.StringVar(value="Centro")

        self.view_mode = ctk.StringVar(value="2D")
        self.show_grid = ctk.BooleanVar(value=True)
        self.sim_speed = ctk.DoubleVar(value=150.0)
        self.cut_strategy = ctk.StringVar(value=STRATEGY_LABELS[STRATEGY_PROXIMITY])
        self.keep_blade_down = ctk.BooleanVar(value=True)

    # ------------------------------------------------------------------
    #  Construção da interface
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_sidebar()
        self._build_workspace()
        self._build_statusbar()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=theme.HEADER, corner_radius=0, height=76)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(2, weight=1)

        logo = ctk.CTkFrame(header, width=42, height=42, corner_radius=12, fg_color=theme.ACCENT)
        logo.grid(row=0, column=0, padx=(18, 12), pady=17)
        logo.grid_propagate(False)
        ctk.CTkLabel(
            logo,
            text="D",
            font=theme.font(22, "bold"),
            text_color="#ffffff",
        ).place(relx=0.5, rely=0.5, anchor="center")

        text_frame = ctk.CTkFrame(header, fg_color="transparent")
        text_frame.grid(row=0, column=1, sticky="w")
        title_row = ctk.CTkFrame(text_frame, fg_color="transparent")
        title_row.pack(anchor="w")
        ctk.CTkLabel(
            title_row,
            text=self.APP_NAME,
            font=theme.font(19, "bold"),
            text_color=theme.TEXT,
        ).pack(side="left")
        ctk.CTkLabel(
            title_row,
            text=f"  v{self.VERSION}",
            font=theme.font(11, "bold"),
            text_color=theme.ACCENT,
            fg_color=theme.ACCENT_SOFT,
            corner_radius=7,
            width=48,
            height=22,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(
            text_frame,
            text="Gerador de cortantes • pré-visualização 2D/3D • simulação de corte • PDF e DXF",
            font=theme.font(11),
            text_color=theme.MUTED,
        ).pack(anchor="w", pady=(2, 0))

        self.header_info = ctk.CTkLabel(
            header,
            text="",
            font=theme.font(12, "bold"),
            text_color=theme.TEXT_DIM,
        )
        self.header_info.grid(row=0, column=3, padx=24, sticky="e")

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkScrollableFrame(
            self,
            width=356,
            fg_color=theme.SIDEBAR,
            corner_radius=0,
            scrollbar_button_color=theme.BORDER,
            scrollbar_button_hover_color=theme.BORDER_SOFT,
        )
        sidebar.grid(row=1, column=0, sticky="nsew")
        self.sidebar = sidebar

        self._build_sheet_card(sidebar)
        self._build_label_card(sidebar)
        self._build_cutting_card(sidebar)
        self._build_distribution_card(sidebar)
        self._build_alignment_card(sidebar)
        self._build_export_card(sidebar)

        ctk.CTkLabel(
            sidebar,
            text="Atalhos: Ctrl+P PDF • Ctrl+D DXF • Ctrl+0 ajustar • F5 simulação",
            font=theme.font(9),
            text_color=theme.MUTED,
            wraplength=310,
        ).pack(pady=(2, 16), padx=20)

    def _build_sheet_card(self, parent) -> None:
        card = Card(parent, "Formato da folha", icon="▤")
        card.pack(fill="x", padx=12, pady=(12, 8))
        self._add_field(card.body, "Largura da folha (mm)", self.sheet_w, step=10, minimum=1)
        self._add_field(card.body, "Altura da folha (mm)", self.sheet_h, step=10, minimum=1)

    def _build_label_card(self, parent) -> None:
        card = Card(parent, "Etiqueta e dieline", icon="◈")
        card.pack(fill="x", padx=12, pady=8)

        self.shape_segment = ctk.CTkSegmentedButton(
            card.body,
            values=list(theme.SHAPE_VALUES),
            variable=self.shape,
            height=30,
            corner_radius=8,
            border_width=2,
            fg_color=theme.BG,
            selected_color=theme.ACCENT,
            selected_hover_color=theme.ACCENT_HOVER,
            unselected_color=theme.CARD_ALT,
            unselected_hover_color=theme.BORDER,
            text_color=theme.TEXT,
            font=theme.font(11, "bold"),
        )
        self.shape_segment.pack(fill="x", pady=(2, 8))

        self.label_w_spin = self._add_field(
            card.body, "Largura / diâmetro (mm)", self.label_w, step=1, minimum=1
        )
        self.label_h_spin = self._add_field(
            card.body, "Altura (mm)", self.label_h, step=1, minimum=1
        )
        self.radius_spin = self._add_field(
            card.body, "Raio do canto (mm)", self.label_radius, step=0.5, minimum=0
        )
        self._add_field(
            card.body,
            "Over-compensate (mm)",
            self.compensation,
            step=0.1,
            decimals=2,
            minimum=0,
            maximum=50,
        )
        ctk.CTkLabel(
            card.body,
            text=(
                "Sobreposição no início do caminho para a lâmina fechar o corte. "
                "Não altera as dimensões da etiqueta; o troço sobreposto aparece em ciano."
            ),
            font=theme.font(9),
            text_color=theme.MUTED,
            anchor="w",
            justify="left",
            wraplength=300,
        ).pack(fill="x", pady=(4, 0))

    def _build_distribution_card(self, parent) -> None:
        card = Card(parent, "Distribuição", icon="▦")
        card.pack(fill="x", padx=12, pady=8)

        auto_row = ctk.CTkFrame(card.body, fg_color="transparent")
        auto_row.pack(fill="x", pady=(2, 6))
        ctk.CTkLabel(
            auto_row,
            text="Modo automático",
            font=theme.font(12, "bold"),
            text_color=theme.TEXT,
        ).pack(side="left")
        self.auto_switch = ctk.CTkSwitch(
            auto_row,
            text="",
            width=44,
            switch_width=40,
            switch_height=20,
            variable=self.auto_mode,
            onvalue=True,
            offvalue=False,
            fg_color=theme.BORDER,
            progress_color=theme.ACCENT,
            button_color=theme.TEXT,
            button_hover_color="#ffffff",
            command=self._on_auto_toggle,
        )
        self.auto_switch.pack(side="right")
        ctk.CTkLabel(
            card.body,
            text="Calcula o número máximo de etiquetas que cabem na folha.",
            font=theme.font(9),
            text_color=theme.MUTED,
            anchor="w",
            justify="left",
            wraplength=300,
        ).pack(fill="x", pady=(0, 6))

        self.col_spin = self._add_field(
            card.body, "Colunas", self.columns, step=1, integer=True, minimum=0
        )
        self.row_spin = self._add_field(
            card.body, "Fileiras", self.rows, step=1, integer=True, minimum=0
        )
        self._add_field(
            card.body, "Espaço horizontal (mm)", self.spacing_h, step=0.5, minimum=0
        )
        self._add_field(
            card.body, "Espaço vertical (mm)", self.spacing_v, step=0.5, minimum=0
        )

    def _build_alignment_card(self, parent) -> None:
        card = Card(parent, "Alinhamento", icon="⌗")
        card.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(
            card.body, text="Horizontal", font=theme.font(11), text_color=theme.TEXT_DIM
        ).pack(anchor="w", pady=(2, 2))
        ctk.CTkComboBox(
            card.body,
            values=list(ALIGN_H),
            variable=self.align_h,
            state="readonly",
            height=30,
            corner_radius=8,
            fg_color=theme.BG,
            border_color=theme.BORDER,
            button_color=theme.CARD_ALT,
            button_hover_color=theme.BORDER,
            dropdown_fg_color=theme.CARD_ALT,
            dropdown_hover_color=theme.BORDER,
            dropdown_text_color=theme.TEXT,
            text_color=theme.TEXT,
            font=theme.font(11),
            dropdown_font=theme.font(11),
        ).pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            card.body, text="Vertical", font=theme.font(11), text_color=theme.TEXT_DIM
        ).pack(anchor="w", pady=(2, 2))
        ctk.CTkComboBox(
            card.body,
            values=list(ALIGN_V),
            variable=self.align_v,
            state="readonly",
            height=30,
            corner_radius=8,
            fg_color=theme.BG,
            border_color=theme.BORDER,
            button_color=theme.CARD_ALT,
            button_hover_color=theme.BORDER,
            dropdown_fg_color=theme.CARD_ALT,
            dropdown_hover_color=theme.BORDER,
            dropdown_text_color=theme.TEXT,
            text_color=theme.TEXT,
            font=theme.font(11),
            dropdown_font=theme.font(11),
        ).pack(fill="x")

    def _build_cutting_card(self, parent) -> None:
        card = Card(parent, "Percurso de corte", icon="✂")
        card.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(
            card.body,
            text="Estratégia",
            font=theme.font(11),
            text_color=theme.TEXT_DIM,
        ).pack(anchor="w", pady=(2, 2))
        self.strategy_segment = ctk.CTkSegmentedButton(
            card.body,
            values=list(STRATEGY_LABELS.values()),
            variable=self.cut_strategy,
            height=30,
            corner_radius=8,
            border_width=2,
            fg_color=theme.BG,
            selected_color=theme.ACCENT,
            selected_hover_color=theme.ACCENT_HOVER,
            unselected_color=theme.CARD_ALT,
            unselected_hover_color=theme.BORDER,
            text_color=theme.TEXT,
            font=theme.font(11, "bold"),
            command=self._on_cutting_option_change,
        )
        self.strategy_segment.pack(fill="x", pady=(0, 8))

        self.blade_switch = ctk.CTkSwitch(
            card.body,
            text="Manter lâmina em baixo",
            variable=self.keep_blade_down,
            onvalue=True,
            offvalue=False,
            fg_color=theme.BORDER,
            progress_color=theme.ACCENT,
            button_color=theme.TEXT,
            button_hover_color="#ffffff",
            text_color=theme.TEXT_DIM,
            font=theme.font(11),
            command=self._on_cutting_option_change,
        )
        self.blade_switch.pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(
            card.body,
            text=(
                "Proximidade encurta os deslocamentos; zigue-zague percorre a "
                "folha linha a linha. Os contornos que se tocam são cortados "
                "num só percurso, sem levantar a lâmina e sem passar duas vezes "
                "sobre a mesma aresta."
            ),
            font=theme.font(9),
            text_color=theme.MUTED,
            anchor="w",
            justify="left",
            wraplength=300,
        ).pack(fill="x", pady=(4, 0))

    def _build_export_card(self, parent) -> None:
        card = Card(parent, "Exportar", icon="⇩")
        card.pack(fill="x", padx=12, pady=8)

        self.pdf_button = ctk.CTkButton(
            card.body,
            text="Exportar PDF",
            height=38,
            corner_radius=9,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color="#ffffff",
            font=theme.font(12, "bold"),
            command=self._export_pdf,
        )
        self.pdf_button.pack(fill="x", pady=(2, 6))

        self.dxf_button = ctk.CTkButton(
            card.body,
            text="Exportar DXF",
            height=38,
            corner_radius=9,
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            border_width=1,
            border_color=theme.CYAN,
            text_color=theme.CYAN,
            font=theme.font(12, "bold"),
            command=self._export_dxf,
        )
        self.dxf_button.pack(fill="x")
        ctk.CTkLabel(
            card.body,
            text="PDF vetorial no tamanho da folha • DXF em mm, layer DIELINE.",
            font=theme.font(9),
            text_color=theme.MUTED,
            anchor="w",
            justify="left",
            wraplength=300,
        ).pack(fill="x", pady=(6, 0))

    def _build_workspace(self) -> None:
        workspace = ctk.CTkFrame(self, fg_color="transparent")
        workspace.grid(row=1, column=1, sticky="nsew", padx=(0, 12), pady=12)
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(
            workspace,
            fg_color=theme.CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER,
            height=52,
        )
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_propagate(False)

        ctk.CTkLabel(
            toolbar,
            text="PRÉ-VISUALIZAÇÃO",
            font=theme.font(10, "bold"),
            text_color=theme.MUTED,
        ).pack(side="left", padx=(16, 12))

        self.view_segment = ctk.CTkSegmentedButton(
            toolbar,
            values=["2D", "3D"],
            variable=self.view_mode,
            width=104,
            height=30,
            corner_radius=8,
            border_width=2,
            fg_color=theme.BG,
            selected_color=theme.ACCENT,
            selected_hover_color=theme.ACCENT_HOVER,
            unselected_color=theme.CARD_ALT,
            unselected_hover_color=theme.BORDER,
            text_color=theme.TEXT,
            font=theme.font(11, "bold"),
            command=self._on_view_mode,
        )
        self.view_segment.pack(side="left")

        self.grid_switch = ctk.CTkSwitch(
            toolbar,
            text="Grelha",
            width=82,
            switch_width=34,
            switch_height=18,
            variable=self.show_grid,
            onvalue=True,
            offvalue=False,
            fg_color=theme.BORDER,
            progress_color=theme.ACCENT,
            button_color=theme.TEXT,
            button_hover_color="#ffffff",
            text_color=theme.TEXT_DIM,
            font=theme.font(10),
            command=lambda: self.preview.set_grid(self.show_grid.get()),
        )
        self.grid_switch.pack(side="left", padx=(16, 0))

        self.sim_button = ctk.CTkButton(
            toolbar,
            text="▶  Simulação",
            width=108,
            height=30,
            corner_radius=8,
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            border_width=1,
            border_color=theme.CYAN,
            text_color=theme.CYAN,
            font=theme.font(10, "bold"),
            command=self._toggle_simulation,
        )
        self.sim_button.pack(side="left", padx=(14, 0))

        # Controlos de zoom à direita
        self.fit_button = ctk.CTkButton(
            toolbar,
            text="Ajustar",
            width=66,
            height=30,
            corner_radius=8,
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            text_color=theme.TEXT_DIM,
            font=theme.font(10, "bold"),
            command=lambda: self.preview.fit(),
        )
        self.fit_button.pack(side="right", padx=(0, 14))

        self.zoom_label = ctk.CTkLabel(
            toolbar,
            text="100%",
            width=48,
            font=theme.font(10, "bold"),
            text_color=theme.TEXT_DIM,
        )
        self.zoom_label.pack(side="right")

        self.zoom_in_button = ctk.CTkButton(
            toolbar,
            text="+",
            width=30,
            height=30,
            corner_radius=8,
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            text_color=theme.TEXT_DIM,
            font=theme.font(14, "bold"),
            command=lambda: self.preview.zoom_in(),
        )
        self.zoom_in_button.pack(side="right", padx=(4, 0))

        self.zoom_out_button = ctk.CTkButton(
            toolbar,
            text="−",
            width=30,
            height=30,
            corner_radius=8,
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            text_color=theme.TEXT_DIM,
            font=theme.font(14, "bold"),
            command=lambda: self.preview.zoom_out(),
        )
        self.zoom_out_button.pack(side="right", padx=(10, 0))

        self.preview = PreviewCanvas(workspace)
        self.preview.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.preview.on_zoom = self._on_zoom
        self.preview.on_simulation_update = self._on_simulation_update

        self._build_simulation_bar(workspace)

        self.bind("<Control-p>", lambda _e: self._export_pdf())
        self.bind("<Control-d>", lambda _e: self._export_dxf())
        self.bind("<Control-0>", lambda _e: self.preview.fit())
        self.bind("<Control-plus>", lambda _e: self.preview.zoom_in())
        self.bind("<Control-equal>", lambda _e: self.preview.zoom_in())
        self.bind("<Control-minus>", lambda _e: self.preview.zoom_out())
        self.bind("<F5>", lambda _e: self._toggle_simulation())

    def _build_simulation_bar(self, workspace) -> None:
        self.sim_bar = ctk.CTkFrame(
            workspace,
            fg_color=theme.CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER,
            height=58,
        )
        self.sim_bar.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.sim_bar.grid_propagate(False)
        self.sim_bar.grid_remove()

        ctk.CTkLabel(
            self.sim_bar,
            text="SIMULAÇÃO DE CORTE",
            font=theme.font(10, "bold"),
            text_color=theme.MUTED,
        ).pack(side="left", padx=(16, 12), pady=11)

        self.sim_play_button = ctk.CTkButton(
            self.sim_bar,
            text="⏸  Pausar",
            width=104,
            height=34,
            corner_radius=8,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color="#ffffff",
            font=theme.font(11, "bold"),
            command=lambda: self.preview.toggle_simulation(),
        )
        self.sim_play_button.pack(side="left", padx=(0, 6), pady=11)

        self.sim_restart_button = ctk.CTkButton(
            self.sim_bar,
            text="⟲  Reiniciar",
            width=98,
            height=34,
            corner_radius=8,
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            text_color=theme.TEXT_DIM,
            font=theme.font(11, "bold"),
            command=lambda: self.preview.restart_simulation(),
        )
        self.sim_restart_button.pack(side="left", padx=(0, 10), pady=11)

        self.sim_save_button = ctk.CTkButton(
            self.sim_bar,
            text="⤓  Guardar",
            width=104,
            height=34,
            corner_radius=8,
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            border_width=1,
            border_color=theme.GREEN,
            text_color=theme.GREEN,
            font=theme.font(11, "bold"),
            command=self._open_save_menu,
        )
        self.sim_save_button.pack(side="left", padx=(0, 16), pady=11)

        speed_frame = ctk.CTkFrame(self.sim_bar, fg_color="transparent")
        speed_frame.pack(side="left", pady=11)
        ctk.CTkLabel(
            speed_frame,
            text="Velocidade",
            font=theme.font(10),
            text_color=theme.TEXT_DIM,
        ).pack(side="left", padx=(0, 6))
        self.sim_speed_slider = ctk.CTkSlider(
            speed_frame,
            from_=20,
            to=900,
            number_of_steps=88,
            width=150,
            height=18,
            variable=self.sim_speed,
            button_color=theme.CYAN,
            button_hover_color="#7fe2f5",
            progress_color=theme.CYAN,
            fg_color=theme.BORDER,
            command=self._on_sim_speed,
        )
        self.sim_speed_slider.pack(side="left")
        self.sim_speed_label = ctk.CTkLabel(
            speed_frame,
            text="150 mm/s",
            width=64,
            font=theme.font(10, "bold"),
            text_color=theme.TEXT_DIM,
        )
        self.sim_speed_label.pack(side="left", padx=(8, 0))

        self.sim_progress_label = ctk.CTkLabel(
            self.sim_bar,
            text="0%",
            width=54,
            font=theme.font(12, "bold"),
            text_color=theme.CYAN,
        )
        self.sim_progress_label.pack(side="right", padx=(0, 12))

        self.sim_close_button = ctk.CTkButton(
            self.sim_bar,
            text="Fechar",
            width=74,
            height=34,
            corner_radius=8,
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            text_color=theme.TEXT_DIM,
            font=theme.font(11, "bold"),
            command=self._stop_simulation,
        )
        self.sim_close_button.pack(side="right", padx=(0, 14), pady=11)

    def _build_statusbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=theme.HEADER, corner_radius=0, height=36)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)

        self.status_dot = StatusDot(bar, color=theme.GREEN)
        self.status_dot.pack(side="left", padx=(18, 4))
        self.status_label = ctk.CTkLabel(
            bar,
            text="A calcular…",
            font=theme.font(10),
            text_color=theme.TEXT_DIM,
        )
        self.status_label.pack(side="left")

        self.occupancy_label = ctk.CTkLabel(
            bar,
            text="",
            font=theme.font(10),
            text_color=theme.MUTED,
        )
        self.occupancy_label.pack(side="right", padx=(10, 18))

        self.count_label = ctk.CTkLabel(
            bar,
            text="",
            font=theme.font(10, "bold"),
            text_color=theme.TEXT_DIM,
        )
        self.count_label.pack(side="right")

    # ------------------------------------------------------------------
    #  Helpers de UI
    # ------------------------------------------------------------------
    def _add_field(
        self,
        parent,
        label: str,
        variable: ctk.StringVar,
        *,
        step: float = 1.0,
        integer: bool = False,
        minimum: float | None = None,
        maximum: float | None = None,
        decimals: int = 2,
    ) -> NumberSpinbox:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=3)
        ctk.CTkLabel(
            row,
            text=label,
            font=theme.font(11),
            text_color=theme.TEXT_DIM,
            anchor="w",
        ).pack(side="left")
        spinbox = NumberSpinbox(
            row,
            variable,
            step=step,
            integer=integer,
            minimum=minimum,
            maximum=maximum,
            decimals=decimals,
        )
        spinbox.pack(side="right")
        return spinbox

    # ------------------------------------------------------------------
    #  Eventos e estado
    # ------------------------------------------------------------------
    def _attach_traces(self) -> None:
        for variable in (
            self.sheet_w,
            self.sheet_h,
            self.label_h,
            self.label_radius,
            self.compensation,
            self.columns,
            self.rows,
            self.spacing_h,
            self.spacing_v,
            self.align_h,
            self.align_v,
        ):
            variable.trace_add("write", self._on_variable_change)

        self.label_w.trace_add("write", self._on_width_change)
        self.shape.trace_add("write", self._on_shape_change)
        self.auto_mode.trace_add("write", self._on_variable_change)

    def _set_variable(self, variable: ctk.Variable, value: str) -> None:
        if variable.get() == value:
            return
        self._syncing = True
        try:
            variable.set(value)
        finally:
            self._syncing = False

    def _on_variable_change(self, *_args) -> None:
        if self._syncing:
            return
        self._schedule_refresh()

    def _on_width_change(self, *_args) -> None:
        if self._syncing:
            return
        if self.shape.get() == ShapeType.CIRCLE.value:
            self._set_variable(self.label_h, self.label_w.get())
        self._schedule_refresh()

    def _on_shape_change(self, *_args) -> None:
        if self._syncing:
            return
        if self.shape.get() == ShapeType.CIRCLE.value:
            self._set_variable(self.label_h, self.label_w.get())
        self._refresh_states()
        self._schedule_refresh()

    def _on_auto_toggle(self) -> None:
        self._refresh_states()
        self._schedule_refresh()

    def _on_view_mode(self, value: str) -> None:
        self.preview.set_view_mode(value)

    def _on_zoom(self, percent: int) -> None:
        self.zoom_label.configure(text=f"{percent}%")

    # ------------------------------------------------------------------
    #  Simulação de corte
    # ------------------------------------------------------------------
    def _on_cutting_text_change(self, *_args) -> None:
        if self._syncing:
            return
        if self._cutting_job is not None:
            try:
                self.after_cancel(self._cutting_job)
            except Exception:
                pass
        self._cutting_job = self.after(300, self._apply_cutting_text_change)

    def _apply_cutting_text_change(self) -> None:
        self._cutting_job = None
        self._on_cutting_option_change()

    def _on_cutting_option_change(self, _value: str | None = None) -> None:
        """Recalcula o percurso se a simulação estiver a decorrer."""

        if self.preview.simulation_active:
            self._replan_simulation()

    def _cut_plan_options(self) -> dict:
        return {
            "strategy": STRATEGY_KEYS.get(
                self.cut_strategy.get(), STRATEGY_PROXIMITY
            ),
            "keep_blade_down": bool(self.keep_blade_down.get()),
        }

    def _replan_simulation(self) -> None:
        if not self._simulation_ready():
            return
        plan = build_cut_plan(
            self._label,
            self._layout,
            quality="high",
            **self._cut_plan_options(),
        )
        if plan.is_empty:
            return
        self._sim_plan = plan
        self.sim_progress_label.configure(text="0%")
        self.preview.start_simulation(plan)
        self._show_plan_status(plan, finished=False)

    def _toggle_simulation(self) -> None:
        if self.preview.simulation_active:
            self._stop_simulation()
        else:
            self._start_simulation()

    def _simulation_ready(self) -> bool:
        if not self._sheet.is_valid:
            messagebox.showwarning(
                "Dimensões inválidas",
                "Introduza as dimensões da folha antes de simular o corte.",
                parent=self,
            )
            return False
        if not self._label.is_valid:
            messagebox.showwarning(
                "Dimensões inválidas",
                "Introduza as dimensões da etiqueta antes de simular o corte.",
                parent=self,
            )
            return False
        if self._layout.count == 0:
            messagebox.showwarning(
                "Nada para cortar",
                "A etiqueta não cabe na folha com os valores atuais.",
                parent=self,
            )
            return False
        if not self._layout.fits:
            messagebox.showwarning(
                "Layout excede a folha",
                self._layout.warnings[0]
                + "\n\nReduza a quantidade de etiquetas ou o espaçamento.",
                parent=self,
            )
            return False
        return True

    def _start_simulation(self) -> None:
        if not self._simulation_ready():
            return

        self.status_label.configure(
            text="A calcular o percurso mais curto…", text_color=theme.TEXT_DIM
        )
        self.update_idletasks()

        plan = build_cut_plan(
            self._label,
            self._layout,
            quality="high",
            **self._cut_plan_options(),
        )
        if plan.is_empty:
            messagebox.showwarning(
                "Simulação de corte",
                "Não foi possível gerar o percurso de corte para este layout.",
                parent=self,
            )
            return

        self._sim_plan = plan
        self._previous_view_mode = self.view_mode.get()
        self.view_segment.set("2D")
        self.preview.set_view_mode("2D")
        self.view_segment.configure(state="disabled")

        self.sim_bar.grid()
        self.sim_button.configure(
            text="■  Parar",
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            border_color=theme.ACCENT,
            text_color="#ffffff",
        )
        self.sim_play_button.configure(text="⏸  Pausar")
        self.sim_progress_label.configure(text="0%")
        self.preview.start_simulation(plan)
        self._show_plan_status(plan, finished=False)

    def _show_plan_status(self, plan: CutPlan, *, finished: bool) -> None:
        strategy = STRATEGY_LABELS.get(plan.strategy, plan.strategy)
        lifts = f"{plan.lift_count} elevaç{'ão' if plan.lift_count == 1 else 'ões'}"
        if finished:
            parts = [
                f"corte {plan.cut_length:,.0f} mm",
            ]
            if plan.link_count > 0:
                parts.append(
                    f"{plan.link_count} ligaç{'ão' if plan.link_count == 1 else 'ões'}"
                )
            parts.append(f"deslocamento {plan.travel_length:,.0f} mm")
            self.status_dot.configure(text_color=theme.GREEN)
            text = (
                f"Simulação concluída • {strategy} • {plan.label_count} etiquetas • "
                + " + ".join(parts)
                + f" • {lifts}"
            )
        else:
            self.status_dot.configure(text_color=theme.CYAN)
            text = (
                f"Simulação de corte • {strategy} • {plan.label_count} etiquetas • "
                f"{plan.total_length:,.0f} mm • {lifts}"
            )
        self.status_label.configure(text=text, text_color=theme.TEXT_DIM)

    def _stop_simulation(self) -> None:
        if self._cutting_job is not None:
            try:
                self.after_cancel(self._cutting_job)
            except Exception:
                pass
            self._cutting_job = None
        if not self.preview.simulation_active:
            return
        self.preview.stop_simulation()
        self.sim_bar.grid_remove()
        self.view_segment.configure(state="normal")
        previous = self._previous_view_mode
        self.view_segment.set(previous)
        self.preview.set_view_mode(previous)
        self.sim_button.configure(
            text="▶  Simulação",
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            border_color=theme.CYAN,
            text_color=theme.CYAN,
        )
        self.sim_progress_label.configure(text="0%")
        self._sim_plan = None
        self._update_status(self._sheet, self._label, self._layout)

    def _on_sim_speed(self, value: float) -> None:
        self.preview.set_simulation_speed(float(value))
        self.sim_speed_label.configure(text=f"{float(value):.0f} mm/s")

    def _open_save_menu(self) -> None:
        if not self._sim_plan:
            messagebox.showwarning(
                "Sem percurso",
                "Inicie a simulação antes de guardar o percurso otimizado.",
                parent=self,
            )
            return

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label="DXF otimizado (plotter)",
            command=lambda: self._save_cut_plan(".dxf"),
        )
        menu.add_command(
            label="PDF otimizado (referência)",
            command=lambda: self._save_cut_plan(".pdf"),
        )
        x = self.sim_save_button.winfo_rootx()
        y = self.sim_save_button.winfo_rooty() + self.sim_save_button.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _save_cut_plan(self, extension: str) -> None:
        plan = self._sim_plan
        if not plan:
            messagebox.showwarning(
                "Sem percurso",
                "Inicie a simulação antes de guardar o percurso otimizado.",
                parent=self,
            )
            return

        filetype = "DXF" if extension == ".dxf" else "PDF"
        base = Path(self._suggested_name(".dxf")).stem + "_corte"
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=extension,
            initialfile=base + extension,
            initialdir=self._last_export_dir,
            filetypes=[(f"{filetype} otimizado", f"*{extension}")],
        )
        if not path:
            return
        self._last_export_dir = str(Path(path).parent)

        try:
            if extension == ".dxf":
                export_cut_plan_dxf(path, self._sheet, plan)
            else:
                export_cut_plan_pdf(path, self._sheet, plan)
        except OSError as exc:
            messagebox.showerror("Erro ao guardar", str(exc), parent=self)
            return
        except Exception as exc:  # pragma: no cover - proteção da UI
            messagebox.showerror("Erro ao guardar percurso", str(exc), parent=self)
            return

        strategy = STRATEGY_LABELS.get(plan.strategy, plan.strategy)
        messagebox.showinfo(
            f"{filetype} guardado",
            (
                f"Percurso {strategy} guardado com {plan.label_count} etiquetas, "
                f"{plan.lift_count} elevações de lâmina e "
                f"{plan.total_length:,.0f} mm no total:\n{path}"
            ),
            parent=self,
        )

    def _on_simulation_update(self, progress: float, finished: bool) -> None:
        self.sim_progress_label.configure(text=f"{progress * 100.0:.0f}%")
        if finished:
            self.sim_play_button.configure(text="⟲  Repetir")
            plan = self.preview.simulation_plan
            if plan:
                self._show_plan_status(plan, finished=True)
        elif self.preview.simulation_playing:
            self.sim_play_button.configure(text="⏸  Pausar")
        else:
            self.sim_play_button.configure(text="▶  Continuar")

    def _schedule_refresh(self) -> None:
        if self.preview.simulation_active:
            self._stop_simulation()
        if self._refresh_job is not None:
            self.after_cancel(self._refresh_job)
        self._refresh_job = self.after(35, self._refresh)

    # ------------------------------------------------------------------
    #  Recalcular tudo
    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        self._refresh_job = None

        sheet = SheetSpec(
            self._value(self.sheet_w),
            self._value(self.sheet_h),
        )
        shape = ShapeType(self.shape.get())
        width = self._value(self.label_w)
        height = width if shape is ShapeType.CIRCLE else self._value(self.label_h)
        label = LabelSpec(
            width=width,
            height=height,
            corner_radius=max(0.0, self._value(self.label_radius)),
            shape=shape,
            compensation=self._value(self.compensation),
        )

        spacing_h = max(0.0, self._value(self.spacing_h))
        spacing_v = max(0.0, self._value(self.spacing_v))

        if self.auto_mode.get():
            cols, rows = auto_grid(sheet, label, spacing_h, spacing_v)
            self._set_variable(self.columns, str(cols))
            self._set_variable(self.rows, str(rows))
        else:
            cols = max(0, int(round(self._value(self.columns))))
            rows = max(0, int(round(self._value(self.rows))))

        spec = LayoutSpec(
            columns=cols,
            rows=rows,
            align_h=self.align_h.get(),
            align_v=self.align_v.get(),
            auto=self.auto_mode.get(),
        )
        layout = compute_layout(sheet, label, spacing_h, spacing_v, spec)

        self._sheet = sheet
        self._label = label
        self._layout = layout

        self.preview.update_scene(
            sheet, label, layout, spacing_h, spacing_v, auto=spec.auto
        )
        self._refresh_states()
        self._update_status(sheet, label, layout)
        self.header_info.configure(
            text=f"{sheet.width:g} × {sheet.height:g} mm"
            + ("  •  auto" if self.auto_mode.get() else "")
        )

    def _refresh_states(self) -> None:
        auto = self.auto_mode.get()
        self.col_spin.set_enabled(not auto)
        self.row_spin.set_enabled(not auto)

        shape = ShapeType(self.shape.get())
        self.label_h_spin.set_enabled(shape is not ShapeType.CIRCLE)
        self.radius_spin.set_enabled(shape is ShapeType.ROUNDED_RECT)

    def _update_status(
        self, sheet: SheetSpec, label: LabelSpec, layout: LayoutResult
    ) -> None:
        if not sheet.is_valid:
            message, color = "Defina as dimensões da folha.", theme.RED
        elif not label.is_valid:
            message, color = "Defina as dimensões da etiqueta.", theme.RED
        elif not self.auto_mode.get() and (layout.columns <= 0 or layout.rows <= 0):
            message, color = "Indique pelo menos 1 coluna e 1 fileira.", theme.AMBER
        elif layout.count == 0:
            message, color = "A etiqueta não cabe na folha com estes espaçamentos.", theme.AMBER
        elif not layout.fits:
            message, color = layout.warnings[0], theme.AMBER
        elif layout.warnings:
            message, color = layout.warnings[0], theme.AMBER
        else:
            message, color = "Layout válido.", theme.GREEN

        self.status_dot.configure(text_color=color)
        self.status_label.configure(text=message, text_color=theme.TEXT_DIM)

        if sheet.is_valid and label.is_valid:
            occupancy = geometry.shape_area(label) * layout.count / sheet.area * 100.0
            self.occupancy_label.configure(text=f"Ocupação {occupancy:.1f}%")
            self.count_label.configure(
                text=f"{layout.columns} × {layout.rows}  •  {layout.count} etiquetas"
            )
        else:
            self.occupancy_label.configure(text="")
            self.count_label.configure(text="")

    # ------------------------------------------------------------------
    #  Exportação
    # ------------------------------------------------------------------
    def _export_ready(self) -> bool:
        if not self._sheet.is_valid:
            messagebox.showwarning(
                "Dimensões inválidas",
                "Introduza as dimensões da folha antes de exportar.",
                parent=self,
            )
            return False
        if not self._label.is_valid:
            messagebox.showwarning(
                "Dimensões inválidas",
                "Introduza as dimensões da etiqueta antes de exportar.",
                parent=self,
            )
            return False
        if self._layout.count == 0:
            messagebox.showwarning(
                "Nada para exportar",
                "A etiqueta não cabe na folha com os valores atuais.",
                parent=self,
            )
            return False
        if not self._layout.fits:
            messagebox.showwarning(
                "Layout excede a folha",
                self._layout.warnings[0]
                + "\n\nReduza a quantidade de etiquetas ou o espaçamento.",
                parent=self,
            )
            return False
        return True

    def _suggested_name(self, extension: str) -> str:
        label = self._label
        shape = _slug(label.shape.value)
        parts = ["etiqueta", shape, f"{label.width:g}x{label.height:g}"]
        if abs(label.compensation) > 1e-9:
            parts.append(f"comp{label.compensation:g}")
        parts.append(f"{self._layout.columns}x{self._layout.rows}")
        return "_".join(parts) + extension

    def _ask_path(self, extension: str, filetype: str) -> str | None:
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=extension,
            initialfile=self._suggested_name(extension),
            initialdir=self._last_export_dir,
            filetypes=[(filetype, f"*{extension}")],
        )
        if not path:
            return None
        self._last_export_dir = str(Path(path).parent)
        return path

    def _export_pdf(self) -> None:
        if not self._export_ready():
            return
        path = self._ask_path(".pdf", "PDF")
        if not path:
            return
        try:
            export_pdf(path, self._sheet, self._label, self._layout)
        except OSError as exc:
            messagebox.showerror("Erro ao exportar", str(exc), parent=self)
            return
        except Exception as exc:  # pragma: no cover - proteção da UI
            messagebox.showerror("Erro ao exportar PDF", str(exc), parent=self)
            return
        messagebox.showinfo(
            "PDF exportado",
            f"PDF criado com {self._layout.count} dielines:\n{path}",
            parent=self,
        )

    def _export_dxf(self) -> None:
        if not self._export_ready():
            return
        path = self._ask_path(".dxf", "DXF")
        if not path:
            return
        try:
            export_dxf(path, self._sheet, self._label, self._layout)
        except OSError as exc:
            messagebox.showerror("Erro ao exportar", str(exc), parent=self)
            return
        except Exception as exc:  # pragma: no cover - proteção da UI
            messagebox.showerror("Erro ao exportar DXF", str(exc), parent=self)
            return
        messagebox.showinfo(
            "DXF exportado",
            f"DXF criado com {self._layout.count} dielines no layer DIELINE:\n{path}",
            parent=self,
        )

    # ------------------------------------------------------------------
    #  Utilidades
    # ------------------------------------------------------------------
    @staticmethod
    def _value(variable: ctk.StringVar) -> float:
        raw = variable.get().strip().replace(" ", "").replace(",", ".")
        if not raw:
            return 0.0
        try:
            return float(raw)
        except ValueError:
            return 0.0


def _slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-") or "etiqueta"
