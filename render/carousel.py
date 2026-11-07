"""Slide del carosello, una funzione per formato.

Ogni funzione riceve:
  t: i testi del post con i numeri già inseriti (copy risolto)
  v: i valori calcolati da copywriting.values (righe delle classifiche ecc.)
  p: il payload originale
e restituisce una lista di Slide.
"""

from render.base import (ACCENT, CAROUSEL, FG, HANDLE, LINE, MARGIN, MUTED, ROOT,
                         Slide)

WIDTH = CAROUSEL[0] - 2 * MARGIN
LOGO = ROOT / "brand" / "assets" / "mark_dark-bg.png"
LOGO_SMALL = ROOT / "brand" / "assets" / "mark_simple_dark-bg.png"


def source_line(v) -> str:
    return f"Source: {v['source_name']} · {v['year']}"


def cover(tag: str, t: dict, v: dict) -> Slide:
    s = Slide()
    s.text(MARGIN, MARGIN, tag.upper(), size=30, weight="semibold", color=MUTED)
    y = s.text(MARGIN, 360, t["title"], size=100, weight="bold",
               max_width=WIDTH, line_height=1.04)
    s.text(MARGIN, y + 36, t["subtitle"], size=38, color=MUTED, max_width=WIDTH,
           line_height=1.35)
    s.image(LOGO_SMALL, MARGIN, CAROUSEL[1] - MARGIN - 64, 64, 64)
    s.text(MARGIN + 82, CAROUSEL[1] - MARGIN - 48, "World Visualization", size=30, weight="bold")
    s.text(CAROUSEL[0] - MARGIN, CAROUSEL[1] - MARGIN - 50, "Swipe →", size=34,
           weight="semibold", color=ACCENT, ha="right")
    return s


def closing(v: dict) -> Slide:
    s = Slide()
    cx = CAROUSEL[0] / 2
    s.image(LOGO, cx - 190, 250, 380, 380)
    y = 700
    for line in ("One world.", "Real numbers.", "Every day."):
        y = s.text(cx, y, line, size=60, weight="bold", ha="center")
    y = s.text(cx, y + 50, f"Follow {HANDLE}", size=36, weight="semibold",
               color=ACCENT, ha="center")
    y = s.text(cx, y + 50, f"Source: {v['source_name']}, World Development Indicators",
               size=26, color=MUTED, ha="center")
    s.text(cx, y + 8, f"{v['indicator']} ({v['source_code']}) · {v['year']}",
           size=26, color=MUTED, ha="center")
    return s


def ranking_rows(s: Slide, rows, y, vmax, highlight, row_h=88):
    """Righe di classifica: posizione, paese, valore e barra da zero."""
    for r in rows:
        hi = r["rank"] in highlight
        color = ACCENT if hi else FG
        s.text(MARGIN, y, r["rank"], size=36, weight="bold", color=ACCENT if hi else MUTED)
        s.text(MARGIN + 110, y, r["name"], size=38, weight="bold", color=color,
               max_width=WIDTH - 110 - 220)
        s.text(CAROUSEL[0] - MARGIN, y, r["value"], size=38, weight="bold",
               color=color, ha="right")
        bar_w = (WIDTH - 110) * max(0.0, r["raw"]) / vmax if vmax > 0 else 0
        s.rect(MARGIN + 110, y + 54, WIDTH - 110, 8, LINE, 4)
        s.rect(MARGIN + 110, y + 54, bar_w, 8, color, 4)
        y += row_h
    return y


def ranked(t, v, p):
    unit = p["unit"]
    pct = unit.startswith("%")
    top = [dict(r, raw=x["value"]) for r, x in zip(v["_rows_top"], p["top"])]
    bottom = [dict(r, raw=x["value"]) for r, x in zip(v["_rows_bottom"], p["bottom"])]
    vmax = 100.0 if pct else max(r["raw"] for r in top)
    first = {top[0]["rank"]}

    s1 = cover(f"Ranked · {v['indicator']} · {v['year']}", t, v)

    s2 = Slide()
    y = s2.text(MARGIN, MARGIN, f"Top 10 · {unit}", size=30, weight="semibold", color=MUTED)
    y = s2.text(MARGIN, y + 24, t["reveal"], size=50, weight="bold", max_width=WIDTH)
    ranking_rows(s2, top, y + 40, vmax, first)
    s2.footer(source_line(v) + (" · bars start at 0" if not pct else ""))

    s3 = Slide()
    y = s3.text(MARGIN, MARGIN, f"Bottom 5 of {v['n_countries']}", size=30,
                weight="semibold", color=MUTED)
    y = s3.text(MARGIN, y + 24, t["closing"], size=50, weight="bold", max_width=WIDTH)
    ranking_rows(s3, bottom, y + 40, vmax, {bottom[-1]["rank"]})
    s3.footer(source_line(v))

    return [s1, s2, s3, closing(v)]


BUILDERS = {"ranked": ranked}