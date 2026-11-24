"""Diálogo “Acerca de” da DieCUT Tool."""

from __future__ import annotations

import platform
import webbrowser

import customtkinter as ctk

from .. import __version__
from . import theme

REPO_URL = "https://github.com/ruiflow/diecut-tool"
RELEASES_URL = "https://github.com/ruiflow/diecut-tool/releases"

CREDITS = (
    ("Rui Flow", "Autor e desenvolvimento"),
    ("OpenCode", "Ambiente de desenvolvimento assistido"),
    ("DeepSeek", "Modelo de IA utilizado no desenvolvimento"),
)

TECHNOLOGIES = (
    "Python",
    "CustomTkinter",
    "ReportLab",
    "ezdxf",
    "Pillow",
    "pdfplumber",
)


def _version_text() -> str:
    return (
        f"DieCUT Tool v{__version__}\n"
        f"Python {platform.python_version()} · {platform.system()} {platform.release()}\n"
        f"Repositório: {REPO_URL}"
    )


class AboutDialog(ctk.CTkToplevel):
    WIDTH = 580
    HEIGHT = 660

    def __init__(self, master) -> None:
        super().__init__(master)
        self.title("Acerca da DieCUT Tool")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.resizable(False, False)
        self.configure(fg_color=theme.BG)
        self.transient(master)
        self.grab_set()
        self.bind("<Escape>", lambda _event: self.destroy())

        self._build()
        self._center(master)

    # ------------------------------------------------------------------
    #  Construção
    # ------------------------------------------------------------------
    def _build(self) -> None:
        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.pack(fill="both", expand=True, padx=26, pady=24)

        header = ctk.CTkFrame(wrapper, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))

        logo = ctk.CTkFrame(
            header, width=48, height=48, corner_radius=14, fg_color=theme.ACCENT
        )
        logo.pack(side="left", padx=(0, 14))
        logo.pack_propagate(False)
        ctk.CTkLabel(
            logo, text="D", font=theme.font(24, "bold"), text_color="#ffffff"
        ).place(relx=0.5, rely=0.5, anchor="center")

        titles = ctk.CTkFrame(header, fg_color="transparent")
        titles.pack(side="left")
        title_row = ctk.CTkFrame(titles, fg_color="transparent")
        title_row.pack(anchor="w")
        ctk.CTkLabel(
            title_row,
            text="DieCUT Tool",
            font=theme.font(22, "bold"),
            text_color=theme.TEXT,
        ).pack(side="left")
        ctk.CTkLabel(
            title_row,
            text=f"  v{__version__}",
            font=theme.font(11, "bold"),
            text_color=theme.ACCENT,
            fg_color=theme.ACCENT_SOFT,
            corner_radius=7,
            width=48,
            height=22,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(
            titles,
            text="Gerador de cortantes para etiquetas, com pré-visualização 2D/3D e simulação de corte.",
            font=theme.font(11),
            text_color=theme.MUTED,
            wraplength=430,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        self._section(
            wrapper,
            "Créditos",
            [f"{name} — {role}" for name, role in CREDITS],
        )
        self._section(
            wrapper,
            "Tecnologias",
            [" · ".join(TECHNOLOGIES)],
        )
        self._section(
            wrapper,
            "Projeto",
            [
                "Código-fonte e versões anteriores estão disponíveis no GitHub.",
                "O executável não é assinado digitalmente: o Windows pode mostrar o aviso do SmartScreen.",
            ],
        )

        ctk.CTkLabel(
            wrapper,
            text=(
                "Os contornos encostados são fundidos num grafo de arestas únicas. "
                "O percurso escolhe a melhor ordem para o objetivo ativo e evita "
                "cortar duas vezes a mesma aresta."
            ),
            font=theme.font(10),
            text_color=theme.MUTED,
            wraplength=470,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))

        buttons = ctk.CTkFrame(wrapper, fg_color="transparent")
        buttons.pack(fill="x", side="bottom")

        ctk.CTkButton(
            buttons,
            text="Repositório",
            width=110,
            height=34,
            corner_radius=8,
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            text_color=theme.TEXT_DIM,
            font=theme.font(11, "bold"),
            command=lambda: webbrowser.open(REPO_URL),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            buttons,
            text="Releases",
            width=94,
            height=34,
            corner_radius=8,
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            text_color=theme.TEXT_DIM,
            font=theme.font(11, "bold"),
            command=lambda: webbrowser.open(RELEASES_URL),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            buttons,
            text="Copiar informação",
            width=132,
            height=34,
            corner_radius=8,
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            border_width=1,
            border_color=theme.CYAN,
            text_color=theme.CYAN,
            font=theme.font(11, "bold"),
            command=self._copy_info,
        ).pack(side="left")

        ctk.CTkButton(
            buttons,
            text="Fechar",
            width=88,
            height=34,
            corner_radius=8,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color="#ffffff",
            font=theme.font(11, "bold"),
            command=self.destroy,
        ).pack(side="right")

        self.status = ctk.CTkLabel(
            wrapper,
            text="",
            font=theme.font(10),
            text_color=theme.GREEN,
            anchor="w",
        )
        self.status.pack(fill="x", side="bottom", pady=(8, 0))

    def _section(self, parent, title: str, lines: list[str]) -> None:
        card = ctk.CTkFrame(
            parent,
            fg_color=theme.CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER,
        )
        card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            card,
            text=title.upper(),
            font=theme.font(9, "bold"),
            text_color=theme.MUTED,
        ).pack(anchor="w", padx=16, pady=(12, 4))
        for line in lines:
            ctk.CTkLabel(
                card,
                text=line,
                font=theme.font(11),
                text_color=theme.TEXT_DIM,
                wraplength=460,
                justify="left",
            ).pack(anchor="w", padx=16, pady=(0, 3))
        ctk.CTkFrame(card, fg_color="transparent", height=8).pack()

    def _copy_info(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(_version_text())
        self.status.configure(text="Informação da versão copiada para a área de transferência.")

    def _center(self, master) -> None:
        self.update_idletasks()
        try:
            x = master.winfo_rootx() + (master.winfo_width() - self.WIDTH) // 2
            y = master.winfo_rooty() + (master.winfo_height() - self.HEIGHT) // 2
        except Exception:
            x = y = 120
        self.geometry(f"+{max(0, x)}+{max(0, y)}")


def show_about(master) -> None:
    AboutDialog(master)
