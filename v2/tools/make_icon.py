"""Gera o ícone da aplicação (executar a partir da pasta v2)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

SIZE = 512
BG = (18, 21, 28, 255)
BORDER = (38, 44, 58, 255)
ACCENT = (224, 64, 160, 255)
ACCENT_SOFT = (94, 32, 68, 255)
CYAN = (53, 201, 232, 255)
WHITE = (246, 247, 250, 255)

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# Fundo arredondado
d.rounded_rectangle((16, 16, SIZE - 16, SIZE - 16), radius=112, fill=BG, outline=BORDER, width=8)

# Etiqueta (dieline) em destaque
margin = 118
d.rounded_rectangle(
    (margin, margin + 42, SIZE - margin, SIZE - margin - 24),
    radius=58,
    outline=ACCENT,
    width=18,
)
d.rounded_rectangle(
    (margin + 22, margin + 64, SIZE - margin - 22, SIZE - margin - 46),
    radius=40,
    fill=ACCENT_SOFT,
    outline=None,
)

# Linha de corte tracejada (over-compensate)
y = SIZE // 2 + 34
for x in range(margin + 28, SIZE - margin - 20, 30):
    d.line((x, y, min(x + 17, SIZE - margin - 20), y), fill=ACCENT, width=6)

# Marcas de registo
for cx, cy in ((92, 92), (SIZE - 92, 92), (92, SIZE - 92), (SIZE - 92, SIZE - 92)):
    d.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), outline=CYAN, width=5)
    d.line((cx - 16, cy, cx + 16, cy), fill=CYAN, width=3)
    d.line((cx, cy - 16, cx, cy + 16), fill=CYAN, width=3)

# Pequeno "D" geométrico
d.rounded_rectangle((SIZE // 2 - 34, SIZE // 2 - 54, SIZE // 2 + 34, SIZE // 2 + 10), radius=18, fill=WHITE)
d.rounded_rectangle((SIZE // 2 - 12, SIZE // 2 - 32, SIZE // 2 + 20, SIZE // 2 - 12), radius=10, fill=BG)
d.rectangle((SIZE // 2 - 12, SIZE // 2 - 22, SIZE // 2 + 2, SIZE // 2 - 10), fill=WHITE)

png = ASSETS / "icon.png"
img.save(png)
img.save(
    ASSETS / "icon.ico",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print(f"Icone gerado: {ASSETS / 'icon.ico'}")
