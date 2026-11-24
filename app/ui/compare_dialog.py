"""Diálogo de comparação de estratégias de percurso."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ..cutting import (
    CUT_SPEED_MM_S,
    LIFT_TIME_S,
    OBJECTIVE_LABELS,
    TRAVEL_SPEED_MM_S,
    STRATEGY_LABELS,
    CutPlan,
    objective_score,
)
from . import theme

COLUMNS = (
    ("Estratégia", 116),
    ("Corte", 92),
    ("Deslocam.", 92),
    ("Ligações", 76),
    ("Elevações", 76),
    ("Tempo", 74),
    ("Pontos", 72),
)


class CompareDialog(ctk.CTkToplevel):
    WIDTH = 760
    HEIGHT = 460

    def __init__(
        self,
        master,
        plans: list[tuple[str, CutPlan]],
        objective: str,
        on_apply: Callable[[str], None],
    ) -> None:
        super().__init__(master)
        self.plans = plans
        self.objective = objective
        self.on_apply = on_apply

        self.title("Comparar percursos")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.resizable(False, True)
        self.configure(fg_color=theme.BG)
        self.transient(master)
        self.grab_set()
        self.bind("<Escape>", lambda _event: self.destroy())

        self._build()
        self._center(master)

    def _build(self) -> None:
        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.pack(fill="both", expand=True, padx=22, pady=20)

        ctk.CTkLabel(
            wrapper,
            text="COMPARAR PERCURSOS",
            font=theme.font(10, "bold"),
            text_color=theme.MUTED,
        ).pack(anchor="w")
        ctk.CTkLabel(
            wrapper,
            text=f"Objetivo: {OBJECTIVE_LABELS.get(self.objective, self.objective)}",
            font=theme.font(16, "bold"),
            text_color=theme.TEXT,
        ).pack(anchor="w", pady=(4, 2))
        ctk.CTkLabel(
            wrapper,
            text=(
                "Tempo estimado com corte a "
                f"{CUT_SPEED_MM_S:.0f} mm/s, deslocamento a "
                f"{TRAVEL_SPEED_MM_S:.0f} mm/s e {LIFT_TIME_S:.1f} s por elevação."
            ),
            font=theme.font(9),
            text_color=theme.MUTED,
            wraplength=700,
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

        table = ctk.CTkFrame(
            wrapper,
            fg_color=theme.CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER,
        )
        table.pack(fill="both", expand=True)
        for index, (_label, width) in enumerate(COLUMNS):
            table.grid_columnconfigure(index, minsize=width)

        header = ctk.CTkFrame(table, fg_color=theme.CARD_ALT, corner_radius=8)
        header.grid(row=0, column=0, columnspan=len(COLUMNS), sticky="ew", padx=8, pady=(8, 4))
        for index, (label, width) in enumerate(COLUMNS):
            ctk.CTkLabel(
                header,
                text=label,
                width=width,
                font=theme.font(9, "bold"),
                text_color=theme.MUTED,
                anchor="w",
            ).grid(row=0, column=index, sticky="w", padx=(8 if index == 0 else 2, 2), pady=6)

        for row, (strategy, plan) in enumerate(self.plans, start=1):
            best = row == 1
            row_frame = ctk.CTkFrame(
                table,
                fg_color=theme.ACCENT_SOFT if best else "transparent",
                corner_radius=8,
                border_width=1 if best else 0,
                border_color=theme.ACCENT if best else theme.CARD,
            )
            row_frame.grid(
                row=row,
                column=0,
                columnspan=len(COLUMNS),
                sticky="ew",
                padx=8,
                pady=2,
            )
            for index, (_label, width) in enumerate(COLUMNS):
                row_frame.grid_columnconfigure(index, minsize=width)

            values = (
                STRATEGY_LABELS.get(strategy, strategy),
                f"{plan.cut_length:,.0f} mm",
                f"{plan.travel_length:,.0f} mm",
                str(plan.link_count),
                str(plan.lift_count),
                f"{plan.estimated_time:.1f} s",
                f"{objective_score(plan, self.objective):,.0f}",
            )
            for index, (value, (_label, width)) in enumerate(zip(values, COLUMNS)):
                ctk.CTkLabel(
                    row_frame,
                    text=value,
                    width=width,
                    font=theme.font(11, "bold" if index == 0 else "normal"),
                    text_color=theme.TEXT if index == 0 else theme.TEXT_DIM,
                    anchor="w",
                ).grid(row=0, column=index, sticky="w", padx=(8 if index == 0 else 2, 2), pady=9)

            ctk.CTkButton(
                row_frame,
                text="Usar",
                width=54,
                height=26,
                corner_radius=7,
                fg_color=theme.ACCENT if best else theme.CARD_ALT,
                hover_color=theme.ACCENT_HOVER if best else theme.BORDER,
                text_color="#ffffff" if best else theme.TEXT_DIM,
                font=theme.font(10, "bold"),
                command=lambda key=strategy: self._apply(key),
            ).grid(row=0, column=len(COLUMNS), padx=(4, 8), pady=6)

        buttons = ctk.CTkFrame(wrapper, fg_color="transparent")
        buttons.pack(fill="x", pady=(12, 0))

        ctk.CTkButton(
            buttons,
            text="Aplicar melhor",
            width=132,
            height=36,
            corner_radius=9,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color="#ffffff",
            font=theme.font(12, "bold"),
            command=lambda: self._apply(self.plans[0][0]),
        ).pack(side="left")

        ctk.CTkButton(
            buttons,
            text="Fechar",
            width=96,
            height=36,
            corner_radius=9,
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            text_color=theme.TEXT_DIM,
            font=theme.font(12, "bold"),
            command=self.destroy,
        ).pack(side="right")

    def _apply(self, strategy: str) -> None:
        self.on_apply(strategy)
        self.destroy()

    def _center(self, master) -> None:
        self.update_idletasks()
        try:
            x = master.winfo_rootx() + (master.winfo_width() - self.WIDTH) // 2
            y = master.winfo_rooty() + (master.winfo_height() - self.HEIGHT) // 2
        except Exception:
            x = y = 120
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
