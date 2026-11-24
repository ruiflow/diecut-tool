"""Diálogo de importação de DXF/PDF."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from ..importers import dxf_layers, load_dxf, load_pdf, pdf_page_count
from . import theme


class ImportDialog(ctk.CTkToplevel):
    WIDTH = 560
    HEIGHT = 520

    def __init__(self, master, path: Path) -> None:
        super().__init__(master)
        self.path = Path(path)
        self.kind = self.path.suffix.lower()
        self.result = None
        self._layer_vars: dict[str, ctk.BooleanVar] = {}
        self._pages = 1

        self.title("Importar DXF/PDF")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.resizable(False, True)
        self.configure(fg_color=theme.BG)
        self.transient(master)
        self.grab_set()
        self.bind("<Escape>", lambda _event: self.destroy())

        self._build()
        self._load_options()
        self._center(master)

    # ------------------------------------------------------------------
    #  Construção
    # ------------------------------------------------------------------
    def _build(self) -> None:
        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.pack(fill="both", expand=True, padx=22, pady=20)

        ctk.CTkLabel(
            wrapper,
            text="IMPORTAR DOCUMENTO",
            font=theme.font(10, "bold"),
            text_color=theme.MUTED,
        ).pack(anchor="w")

        ctk.CTkLabel(
            wrapper,
            text=self.path.name,
            font=theme.font(17, "bold"),
            text_color=theme.TEXT,
            wraplength=500,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        kind = "PDF vetorial" if self.kind == ".pdf" else "DXF"
        ctk.CTkLabel(
            wrapper,
            text=f"{kind} · {self.path}",
            font=theme.font(9),
            text_color=theme.MUTED,
            wraplength=500,
            justify="left",
        ).pack(anchor="w", pady=(2, 14))

        self.options_frame = ctk.CTkFrame(wrapper, fg_color="transparent")
        self.options_frame.pack(fill="both", expand=True)

        self.message = ctk.CTkLabel(
            wrapper,
            text="",
            font=theme.font(10),
            text_color=theme.AMBER,
            wraplength=500,
            justify="left",
        )
        self.message.pack(fill="x", pady=(8, 0))

        buttons = ctk.CTkFrame(wrapper, fg_color="transparent")
        buttons.pack(fill="x", pady=(12, 0))

        self.import_button = ctk.CTkButton(
            buttons,
            text="Importar",
            width=112,
            height=36,
            corner_radius=9,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color="#ffffff",
            font=theme.font(12, "bold"),
            command=self._import,
        )
        self.import_button.pack(side="right")

        ctk.CTkButton(
            buttons,
            text="Cancelar",
            width=96,
            height=36,
            corner_radius=9,
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            text_color=theme.TEXT_DIM,
            font=theme.font(12, "bold"),
            command=self.destroy,
        ).pack(side="right", padx=(0, 8))

    def _load_options(self) -> None:
        try:
            if self.kind == ".pdf":
                self._build_pdf_options()
            elif self.kind == ".dxf":
                self._build_dxf_options()
            else:
                raise ValueError("Formato não suportado. Escolha um ficheiro .dxf ou .pdf.")
        except Exception as exc:
            self.message.configure(text=str(exc), text_color=theme.RED)
            self.import_button.configure(state="disabled")

    def _build_pdf_options(self) -> None:
        self._pages = pdf_page_count(self.path)
        ctk.CTkLabel(
            self.options_frame,
            text="Página",
            font=theme.font(11),
            text_color=theme.TEXT_DIM,
        ).pack(anchor="w", pady=(0, 2))

        if self._pages <= 1:
            ctk.CTkLabel(
                self.options_frame,
                text="O PDF tem uma só página.",
                font=theme.font(11),
                text_color=theme.TEXT,
            ).pack(anchor="w", pady=(0, 10))
        else:
            self.page_var = ctk.StringVar(value="1")
            ctk.CTkComboBox(
                self.options_frame,
                values=[str(index) for index in range(1, self._pages + 1)],
                variable=self.page_var,
                state="readonly",
                height=32,
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
            ).pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            self.options_frame,
            text=(
                "São lidos apenas caminhos vetoriais (linhas e curvas). "
                "Texto, imagens e PDFs digitalizados não são importados."
            ),
            font=theme.font(9),
            text_color=theme.MUTED,
            wraplength=500,
            justify="left",
        ).pack(anchor="w")

    def _build_dxf_options(self) -> None:
        layers = dxf_layers(self.path)
        if not layers:
            raise ValueError("O DXF não tem camadas com entidades.")

        ctk.CTkLabel(
            self.options_frame,
            text="Camadas a importar",
            font=theme.font(11),
            text_color=theme.TEXT_DIM,
        ).pack(anchor="w", pady=(0, 4))

        scroll = ctk.CTkScrollableFrame(
            self.options_frame,
            height=210,
            fg_color=theme.CARD,
            corner_radius=10,
            border_width=1,
            border_color=theme.BORDER,
        )
        scroll.pack(fill="both", expand=True)

        for layer in layers:
            variable = ctk.BooleanVar(value=True)
            self._layer_vars[layer] = variable
            ctk.CTkCheckBox(
                scroll,
                text=layer,
                variable=variable,
                onvalue=True,
                offvalue=False,
                font=theme.font(11),
                text_color=theme.TEXT,
                fg_color=theme.ACCENT,
                hover_color=theme.ACCENT_HOVER,
                border_color=theme.BORDER,
                checkmark_color="#ffffff",
            ).pack(anchor="w", padx=10, pady=5)

        ctk.CTkLabel(
            self.options_frame,
            text=(
                "As entidades são achatadas em polilinhas e convertidas para "
                "milímetros, respeitando o $INSUNITS do ficheiro."
            ),
            font=theme.font(9),
            text_color=theme.MUTED,
            wraplength=500,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

    # ------------------------------------------------------------------
    #  Ações
    # ------------------------------------------------------------------
    def _import(self) -> None:
        self.message.configure(text="A importar…", text_color=theme.TEXT_DIM)
        self.import_button.configure(state="disabled")
        self.update_idletasks()
        try:
            if self.kind == ".pdf":
                page = int(self.page_var.get()) if self._pages > 1 else 1
                document = load_pdf(self.path, page=page)
            else:
                selected = [
                    name for name, variable in self._layer_vars.items() if variable.get()
                ]
                document = load_dxf(self.path, layers=selected or None)
        except Exception as exc:
            self.message.configure(text=str(exc), text_color=theme.RED)
            self.import_button.configure(state="normal")
            return

        self.result = document
        self.destroy()

    def _center(self, master) -> None:
        self.update_idletasks()
        try:
            x = master.winfo_rootx() + (master.winfo_width() - self.WIDTH) // 2
            y = master.winfo_rooty() + (master.winfo_height() - self.HEIGHT) // 2
        except Exception:
            x = y = 120
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
