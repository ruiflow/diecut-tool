"""
Gerador de Cortantes para Folhas Autocolantes (Refatorado)
Autor: Rui (refatorado com apoio)
"""

import customtkinter as ctk
from tkinter import Canvas, filedialog, messagebox
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.units import mm as mm_unit


# ------------------------------------------------------------
#  CÁLCULO DO LAYOUT (CLASSE SEPARADA)
# ------------------------------------------------------------
class LayoutCalculator:
    def __init__(self, lf, af, le, ae, esp_h, esp_v, margem, cols, rows, align_h, align_v):
        self.lf = lf
        self.af = af
        self.le = le
        self.ae = ae
        self.esp_h = esp_h
        self.esp_v = esp_v
        self.margem = margem
        self.cols = cols
        self.rows = rows
        self.align_h = align_h
        self.align_v = align_v

    def calcular(self):
        if self.lf <= 0 or self.af <= 0 or self.le <= 0 or self.ae <= 0:
            return []

        largura_bloco = self.cols * self.le + (self.cols - 1) * self.esp_h
        altura_bloco = self.rows * self.ae + (self.rows - 1) * self.esp_v

        # Alinhamento horizontal
        if self.align_h == "Centro":
            ox = (self.lf - largura_bloco) / 2
        elif self.align_h == "Direita":
            ox = self.lf - largura_bloco - self.margem
        else:
            ox = self.margem

        # Alinhamento vertical
        if self.align_v == "Centro":
            oy = (self.af - altura_bloco) / 2
        elif self.align_v == "Baixo":
            oy = self.af - altura_bloco - self.margem
        else:
            oy = self.margem

        coords = []
        for l in range(self.rows):
            for c in range(self.cols):
                x = ox + c * (self.le + self.esp_h)
                y = oy + l * (self.ae + self.esp_v)
                coords.append((x, y))

        return coords


# ------------------------------------------------------------
#  SPINBOX FLOAT
# ------------------------------------------------------------
class FloatSpinbox(ctk.CTkFrame):
    def __init__(self, *args, var=None, step=1.0, callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.var, self.step, self.callback = var, step, callback
        self.configure(fg_color="transparent")

        ctk.CTkButton(self, text="-", width=30, height=28, fg_color="#404040",
                      command=self.subtract).pack(side="left", padx=(0, 2))

        self.entry = ctk.CTkEntry(self, textvariable=self.var, width=70, height=28, justify="center")
        self.entry.pack(side="left", padx=2)
        self.entry.bind("<KeyRelease>", lambda e: self.callback())

        ctk.CTkButton(self, text="+", width=30, height=28, fg_color="#404040",
                      command=self.add).pack(side="left", padx=(2, 0))

    def add(self):
        try:
            val = float(self.var.get().replace(",", "."))
            self.var.set(str(round(val + self.step, 2)))
            if self.callback: self.callback()
        except:
            self.var.set("0")

    def subtract(self):
        try:
            val = float(self.var.get().replace(",", "."))
            self.var.set(str(round(max(0, val - self.step), 2)))
            if self.callback: self.callback()
        except:
            self.var.set("0")


# ------------------------------------------------------------
#  APLICAÇÃO PRINCIPAL
# ------------------------------------------------------------
class FlowCutApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DieCut Tool - Gerador de Cortantes")
        self.geometry("1200x850")

        # Variáveis
        self.largura_folha = ctk.StringVar(value="210")
        self.altura_folha = ctk.StringVar(value="297")
        self.largura_etiqueta = ctk.StringVar(value="50")
        self.altura_etiqueta = ctk.StringVar(value="30")
        self.espacamento_h = ctk.StringVar(value="2")
        self.espacamento_v = ctk.StringVar(value="2")
        self.margem_seguranca = ctk.StringVar(value="5")
        self.raio_canto = ctk.StringVar(value="2")
        self.colunas_manual = ctk.StringVar(value="2")
        self.fileiras_manual = ctk.StringVar(value="4")

        self.alinhamento_h = ctk.StringVar(value="Centro")
        self.alinhamento_v = ctk.StringVar(value="Centro")

        self._setup_ui()
        self.after(200, self.atualizar_preview)

    # --------------------------------------------------------
    #  UI
    # --------------------------------------------------------
    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkScrollableFrame(self, width=320, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        ctk.CTkLabel(self.sidebar, text="CONFIGURAÇÕES", font=("Roboto", 18, "bold")).pack(pady=15)

        self._create_input("Largura Folha (mm):", self.largura_folha, 10)
        self._create_input("Altura Folha (mm):", self.altura_folha, 10)

        ctk.CTkLabel(self.sidebar, text="--- ETIQUETA ---", font=("Roboto", 12, "italic")).pack(pady=(15, 5))
        self._create_input("Largura (mm):", self.largura_etiqueta, 1)
        self._create_input("Altura (mm):", self.altura_etiqueta, 1)
        self._create_input("Espaço Horizontal (mm):", self.espacamento_h, 0.5)
        self._create_input("Espaço Vertical (mm):", self.espacamento_v, 0.5)
        self._create_input("Raio Canto (mm):", self.raio_canto, 0.5)

        ctk.CTkLabel(self.sidebar, text="--- QUANTIDADE ---", font=("Roboto", 12, "italic")).pack(pady=(15, 5))
        self._create_input("Colunas:", self.colunas_manual, 1)
        self._create_input("Fileiras:", self.fileiras_manual, 1)

        ctk.CTkLabel(self.sidebar, text="--- ALINHAMENTO ---", font=("Roboto", 12, "italic")).pack(pady=(15, 5))
        ctk.CTkLabel(self.sidebar, text="Horizontal:").pack()
        ctk.CTkComboBox(self.sidebar, values=["Esquerda", "Centro", "Direita"],
                        variable=self.alinhamento_h, command=lambda _: self.atualizar_preview()).pack(pady=5)

        ctk.CTkLabel(self.sidebar, text="Vertical:").pack()
        ctk.CTkComboBox(self.sidebar, values=["Topo", "Centro", "Baixo"],
                        variable=self.alinhamento_v, command=lambda _: self.atualizar_preview()).pack(pady=5)

        ctk.CTkButton(self.sidebar, text="Exportar PDF", fg_color="#2ecc71",
                      command=self.exportar_pdf).pack(pady=(20, 5), padx=20, fill="x")

        # PREVIEW
        self.preview_frame = ctk.CTkFrame(self, fg_color="#1a1a1a")
        self.preview_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.canvas = Canvas(self.preview_frame, bg="#252525", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=20, pady=20)
        self.canvas.bind("<Configure>", lambda e: self.atualizar_preview())

    def _create_input(self, label, var, step):
        ctk.CTkLabel(self.sidebar, text=label, anchor="w").pack(fill="x", padx=20, pady=(5, 0))
        FloatSpinbox(self.sidebar, var=var, step=step, callback=self.atualizar_preview).pack(padx=20, pady=2)

    # --------------------------------------------------------
    #  UTILIDADES
    # --------------------------------------------------------
    def get_val(self, var):
        try:
            return float(var.get().replace(",", "."))
        except:
            return 0.0

    # --------------------------------------------------------
    #  PREVIEW
    # --------------------------------------------------------
    def atualizar_preview(self, event=None):
        self.canvas.delete("all")

        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        lf, af = self.get_val(self.largura_folha), self.get_val(self.altura_folha)

        if lf <= 0 or af <= 0 or cw < 50:
            return

        esc = min((cw - 60) / lf, (ch - 60) / af)
        x0, y0 = (cw - lf * esc) / 2, (ch - af * esc) / 2

        # Folha
        self.canvas.create_rectangle(x0, y0, x0 + lf * esc, y0 + af * esc,
                                     fill="white", outline="#00b4d8", width=2)

        # Etiquetas
        le = self.get_val(self.largura_etiqueta)
        ae = self.get_val(self.altura_etiqueta)
        r = min(self.get_val(self.raio_canto), le / 2, ae / 2)

        calc = LayoutCalculator(
            lf, af, le, ae,
            self.get_val(self.espacamento_h),
            self.get_val(self.espacamento_v),
            self.get_val(self.margem_seguranca),
            int(self.get_val(self.colunas_manual)),
            int(self.get_val(self.fileiras_manual)),
            self.alinhamento_h.get(),
            self.alinhamento_v.get()
        )

        for x, y in calc.calcular():
            self._draw_round_rect(
                x0 + x * esc, y0 + y * esc,
                x0 + (x + le) * esc, y0 + (y + ae) * esc,
                r * esc, "#e040a0"
            )

    def _draw_round_rect(self, x1, y1, x2, y2, r, outline):
        if r <= 0:
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=outline)
            return

        d = 2 * r
        self.canvas.create_arc(x1, y1, x1 + d, y1 + d, start=90, extent=90, outline=outline, style="arc")
        self.canvas.create_arc(x2 - d, y1, x2, y1 + d, start=0, extent=90, outline=outline, style="arc")
        self.canvas.create_arc(x1, y2 - d, x1 + d, y2, start=180, extent=90, outline=outline, style="arc")
        self.canvas.create_arc(x2 - d, y2 - d, x2, y2, start=270, extent=90, outline=outline, style="arc")

        self.canvas.create_line(x1 + r, y1, x2 - r, y1, fill=outline)
        self.canvas.create_line(x1 + r, y2, x2 - r, y2, fill=outline)
        self.canvas.create_line(x1, y1 + r, x1, y2 - r, fill=outline)
        self.canvas.create_line(x2, y1 + r, x2, y2 - r, fill=outline)

    # --------------------------------------------------------
    #  EXPORTAÇÃO PDF
    # --------------------------------------------------------
    def exportar_pdf(self):
        le = self.get_val(self.largura_etiqueta)
        ae = self.get_val(self.altura_etiqueta)
        r = self.get_val(self.raio_canto)

        nome_sugerido = f"Etiqueta_{int(le)}x{int(ae)}_r{int(r)}.pdf"

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=nome_sugerido,
            filetypes=[("PDF", "*.pdf")]
        )

        if not path:
            return

        lf, af = self.get_val(self.largura_folha), self.get_val(self.altura_folha)
        r = min(r, le / 2, ae / 2)

        c = pdf_canvas.Canvas(path, pagesize=(lf * mm_unit, af * mm_unit))

        calc = LayoutCalculator(
            lf, af, le, ae,
            self.get_val(self.espacamento_h),
            self.get_val(self.espacamento_v),
            self.get_val(self.margem_seguranca),
            int(self.get_val(self.colunas_manual)),
            int(self.get_val(self.fileiras_manual)),
            self.alinhamento_h.get(),
            self.alinhamento_v.get()
        )

        for x, y in calc.calcular():
            c.setStrokeColorRGB(0.87, 0.25, 0.62)
            c.roundRect(x * mm_unit, (af - y - ae) * mm_unit,
                        le * mm_unit, ae * mm_unit, radius=r * mm_unit)

        c.save()
        messagebox.showinfo("Sucesso", "PDF Gerado com sucesso!")


# ------------------------------------------------------------
#  MAIN
# ------------------------------------------------------------
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    FlowCutApp().mainloop()
