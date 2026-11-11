"""Widgets reutilizáveis da interface."""

from __future__ import annotations

import customtkinter as ctk

from . import theme


class NumberSpinbox(ctk.CTkFrame):
    """Campo numérico com botões - / + e formatação tolerante a vírgula."""

    def __init__(
        self,
        master,
        variable: ctk.StringVar,
        *,
        step: float = 1.0,
        integer: bool = False,
        minimum: float | None = None,
        maximum: float | None = None,
        decimals: int = 2,
        width: int = 78,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.variable = variable
        self.step = step
        self.integer = integer
        self.minimum = minimum
        self.maximum = maximum
        self.decimals = 0 if integer else decimals

        self.minus_button = ctk.CTkButton(
            self,
            text="−",
            width=30,
            height=30,
            corner_radius=8,
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            border_width=1,
            border_color=theme.BORDER_SOFT,
            text_color=theme.TEXT_DIM,
            font=theme.font(15, "bold"),
            command=lambda: self._nudge(-self.step),
        )
        self.minus_button.pack(side="left")

        self.entry = ctk.CTkEntry(
            self,
            textvariable=self.variable,
            width=width,
            height=30,
            corner_radius=8,
            justify="center",
            fg_color=theme.BG,
            border_color=theme.BORDER,
            border_width=1,
            text_color=theme.TEXT,
            font=theme.font(13),
        )
        self.entry.pack(side="left", padx=4)
        self.entry.bind("<FocusOut>", self._normalize)
        self.entry.bind("<Return>", self._normalize)

        self.plus_button = ctk.CTkButton(
            self,
            text="+",
            width=30,
            height=30,
            corner_radius=8,
            fg_color=theme.CARD_ALT,
            hover_color=theme.BORDER,
            border_width=1,
            border_color=theme.BORDER_SOFT,
            text_color=theme.TEXT_DIM,
            font=theme.font(15, "bold"),
            command=lambda: self._nudge(self.step),
        )
        self.plus_button.pack(side="left")

    def _read(self) -> float | None:
        raw = self.variable.get().strip().replace(" ", "").replace(",", ".")
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    def _clamp(self, value: float) -> float:
        if self.minimum is not None:
            value = max(self.minimum, value)
        if self.maximum is not None:
            value = min(self.maximum, value)
        return value

    def _format(self, value: float) -> str:
        if self.integer:
            return str(int(round(value)))
        text = f"{value:.{self.decimals}f}"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text or "0"

    def _nudge(self, delta: float) -> None:
        current = self._read()
        if current is None:
            current = self.minimum or 0.0
        value = self._clamp(current + delta)
        self.variable.set(self._format(value))

    def _normalize(self, _event=None) -> None:
        current = self._read()
        if current is None:
            return
        formatted = self._format(self._clamp(current))
        if self.variable.get() != formatted:
            self.variable.set(formatted)

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.entry.configure(state=state)
        for button in (self.minus_button, self.plus_button):
            button.configure(state=state)


class Card(ctk.CTkFrame):
    """Secção visual com título e conteúdo."""

    def __init__(self, master, title: str, *, icon: str = "", **kwargs) -> None:
        super().__init__(
            master,
            fg_color=theme.CARD,
            corner_radius=14,
            border_width=1,
            border_color=theme.BORDER,
            **kwargs,
        )
        header = ctk.CTkFrame(self, fg_color="transparent", height=30)
        header.pack(fill="x", padx=14, pady=(12, 2))

        bar = ctk.CTkFrame(
            header,
            width=4,
            height=16,
            corner_radius=2,
            fg_color=theme.ACCENT,
        )
        bar.pack(side="left", padx=(0, 8))

        text = f"{icon}  {title}" if icon else title
        ctk.CTkLabel(
            header,
            text=text.upper(),
            font=theme.font(11, "bold"),
            text_color=theme.TEXT_DIM,
            anchor="w",
        ).pack(side="left")

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="x", padx=14, pady=(4, 12))


class StatusDot(ctk.CTkLabel):
    def __init__(self, master, color: str = theme.GREEN, **kwargs) -> None:
        super().__init__(
            master,
            text="●",
            text_color=color,
            font=theme.font(11),
            width=14,
            **kwargs,
        )
