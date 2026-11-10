"""Base comune del render: colori, font e una "slide" su cui disegnare.

Tutte le misure sono in pixel, con l'origine in alto a sinistra,
come in un programma di grafica: è più semplice ragionare così.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # nessuna finestra: disegna solo su file
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

from brand import theme
from common.config import ROOT

FONT_DIR = ROOT / "brand" / "fonts"
FONTS = {w: FontProperties(fname=str(FONT_DIR / f"Manrope-{s}.ttf"))
         for w, s in [("regular", "Regular"), ("semibold", "SemiBold"), ("bold", "ExtraBold")]}

BG, FG, ACCENT = theme.MIDNIGHT, theme.MIST, theme.CORAL
MUTED, LINE = theme.MUTED_DARK, theme.RING
HANDLE = theme.HANDLE
BRAND = theme.BRAND_NAME
CAROUSEL = (1080, 1350)
REEL = (1080, 1920)
MARGIN = 88


def text_width(s: str, size: float, weight: str = "regular") -> float:
    """Larghezza in pixel di un testo, misurata sul font vero."""
    if not s:
        return 0.0
    return TextPath((0, 0), s, size=size, prop=FONTS[weight]).get_extents().width


def wrap(s: str, size: float, max_width: float, weight: str = "regular") -> list[str]:
    """Va a capo sulle parole in modo che ogni riga stia in max_width."""
    lines, line = [], ""
    for word in s.split():
        test = f"{line} {word}".strip()
        if line and text_width(test, size, weight) > max_width:
            lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    return lines


class Slide:
    def __init__(self, size=CAROUSEL, bg=BG):
        self.w, self.h = size
        self.fig = plt.figure(figsize=(self.w / 100, self.h / 100), dpi=100)
        self.fig.patch.set_facecolor(bg)
        # Un unico "foglio" che copre tutta la slide, in coordinate pixel
        self.ax = self.fig.add_axes((0, 0, 1, 1))
        self.ax.set_xlim(0, self.w)
        self.ax.set_ylim(self.h, 0)  # y cresce verso il basso
        self.ax.axis("off")

    def text(self, x, y, s, size=40, weight="regular", color=FG, ha="left",
             max_width=None, line_height=1.15) -> float:
        """Scrive un testo (con a capo automatico) partendo dall'alto.
        Restituisce la y subito sotto il testo, per impilare gli elementi."""
        lines = wrap(s, size, max_width, weight) if max_width else [s]
        step = size * line_height
        for i, line in enumerate(lines):
            self.ax.text(x, y + i * step, line, fontproperties=FONTS[weight],
                         fontsize=size * 0.72, color=color, ha=ha, va="top")
        return y + len(lines) * step

    def rich(self, x, y, parts, size=40, weight="bold"):
        """Una riga con pezzi di colori diversi: [(testo, colore), ...]."""
        for s, color in parts:
            self.ax.text(x, y, s, fontproperties=FONTS[weight], fontsize=size * 0.72,
                         color=color, ha="left", va="top")
            x += text_width(s, size, weight) + size * 0.3  # spazio tra i pezzi

    def rect(self, x, y, w, h, color, radius=0):
        from matplotlib.patches import FancyBboxPatch
        box = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}",
                             linewidth=0, facecolor=color)
        self.ax.add_patch(box)

    def dot(self, x, y, r, color):
        from matplotlib.patches import Circle
        self.ax.add_patch(Circle((x, y), r, facecolor=color, linewidth=0, zorder=4))

    def line(self, x1, y1, x2, y2, color=LINE, width=2):
        self.ax.plot([x1, x2], [y1, y2], color=color, linewidth=width * 0.72)

    def image(self, path, x, y, w, h):
        img = plt.imread(str(path))
        self.ax.imshow(img, extent=(x, x + w, y + h, y), zorder=3)

    def footer(self, source: str):
        """Fonte a sinistra e nome della pagina a destra, in fondo."""
        y = self.h - MARGIN - 30
        self.text(MARGIN, y, source, size=26, color=MUTED)
        self.text(self.w - MARGIN, y, BRAND, size=26,
                  weight="bold", ha="right")

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fig.savefig(path, dpi=100, facecolor=self.fig.get_facecolor())
        plt.close(self.fig)
        return path