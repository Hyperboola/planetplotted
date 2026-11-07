"""Slide del carosello, una funzione per formato.

Ogni funzione riceve:
  t: i testi del post con i numeri già inseriti (copy risolto)
  v: i valori calcolati da copywriting.values (righe delle classifiche ecc.)
  p: il payload originale
e restituisce una lista di Slide.
"""
from copywriting.numbers import fmt_value as n_fmt
from copywriting.numbers import with_unit as n_with_unit
from render.base import (ACCENT, CAROUSEL, FG, HANDLE, LINE, MARGIN, MUTED, ROOT,
                         Slide)

WIDTH = CAROUSEL[0] - 2 * MARGIN
LOGO = ROOT / "brand" / "assets" / "mark_dark-bg.png"
LOGO_SMALL = ROOT / "brand" / "assets" / "mark_simple_dark-bg.png"


def source_line(v) -> str:
    return f"Source: {v['source_name']} · {v['year']}"


def cover(tag: str, t: dict, v: dict, preview=None) -> Slide:
    """Copertina. preview(slide, y) disegna un'anteprima del contenuto
    sotto il titolo, per incuriosire chi scorre il feed."""
    s = Slide()
    s.text(MARGIN, MARGIN, tag.upper(), size=30, weight="semibold", color=MUTED)
    y = s.text(MARGIN, 250, t["title"], size=100, weight="bold",
               max_width=WIDTH, line_height=1.04)
    y = s.text(MARGIN, y + 30, t["subtitle"], size=38, color=MUTED, max_width=WIDTH,
               line_height=1.35)
    if preview:
        preview(s, y + 70)
    s.image(LOGO_SMALL, MARGIN, CAROUSEL[1] - MARGIN - 64, 64, 64)
    s.text(MARGIN + 82, CAROUSEL[1] - MARGIN - 48, "World Visualization", size=30, weight="bold")
    s.text(CAROUSEL[0] - MARGIN, CAROUSEL[1] - MARGIN - 50, "Swipe →", size=34,
           weight="semibold", color=ACCENT, ha="right")
    return s


def closing(v: dict) -> Slide:
    s = Slide()
    cx = CAROUSEL[0] / 2
    s.image(LOGO, cx - 180, 200, 360, 360)
    y = 620
    for line in ("One world.", "Real numbers.", "Every day."):
        y = s.text(cx, y, line, size=60, weight="bold", ha="center")
    y = s.text(cx, y + 44, "Save this post for later", size=34, weight="semibold",
               ha="center")
    y = s.text(cx, y + 14, f"Follow {HANDLE}", size=36, weight="semibold",
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
        if bar_w >= 1:  # un valore zero non disegna nessuna barra
            s.rect(MARGIN + 110, y + 54, max(bar_w, 8), 8, color, 4)
        y += row_h
    return y


def ranked(t, v, p):
    unit = p["unit"]
    pct = unit.startswith("%")
    top = [dict(r, raw=x["value"]) for r, x in zip(v["_rows_top"], p["top"])]
    bottom = [dict(r, raw=x["value"]) for r, x in zip(v["_rows_bottom"], p["bottom"])]
    vmax = 100.0 if pct else max(r["raw"] for r in top)
    first = {top[0]["rank"]}

    def preview(s, y):
        """I primi tre con il nome nascosto: la risposta è nella slide dopo."""
        for r in top[:3]:
            s.text(MARGIN, y, r["rank"], size=36, weight="bold", color=ACCENT)
            s.rect(MARGIN + 110, y + 4, 300, 34, LINE, 8)
            s.text(MARGIN + 130, y, "?", size=36, weight="bold", color=MUTED)
            bar_w = (WIDTH - 110) * max(0.0, r["raw"]) / vmax if vmax > 0 else 0
            s.rect(MARGIN + 110, y + 56, bar_w, 10, ACCENT, 5)
            y += 92

    s1 = cover("Ranked", t, v, preview)

    s2 = Slide()
    y = s2.text(MARGIN, MARGIN, f"Top 10 · {unit}", size=30, weight="semibold", color=MUTED)
    y = s2.text(MARGIN, y + 24, t["reveal"], size=50, weight="bold", max_width=WIDTH)
    ranking_rows(s2, top, y + 40, vmax, first)
    s2.footer(source_line(v) + (" · bars start at 0" if not pct else ""))

    s3 = Slide()
    y = s3.text(MARGIN, MARGIN, f"Bottom 5 of {v['n_countries']}", size=30,
                weight="semibold", color=MUTED)
    y = s3.text(MARGIN, y + 24, t["closing"], size=50, weight="bold", max_width=WIDTH)
    y = ranking_rows(s3, bottom, y + 40, vmax, {bottom[-1]["rank"]})
    if t.get("context"):
        s3.line(MARGIN, y + 40, CAROUSEL[0] - MARGIN, y + 40)
        s3.text(MARGIN, y + 90, t["context"], size=56, weight="bold", color=ACCENT,
                max_width=WIDTH, line_height=1.12)
    s3.footer(source_line(v))

    return [s1, s2, s3, closing(v)]


def the_gap(t, v, p):
    hi, lo = p["highest"], p["lowest"]
    # Barre da zero, in scala sul valore più alto (solo se entrambi positivi)
    scale = hi["value"] if hi["value"] > 0 and lo["value"] >= 0 else None

    def bar(s, y, value, color):
        s.rect(MARGIN, y, WIDTH, 14, LINE, 7)
        if scale:
            s.rect(MARGIN, y, max(6, WIDTH * value / scale), 14, color, 7)

    def preview(s, y):
        """Le due barre a confronto: il divario si vede prima di leggerlo."""
        for item, color in ((hi, FG), (lo, ACCENT)):
            s.text(MARGIN, y, n_with_unit(n_fmt(item["value"], p["unit"]), p["unit"]),
                size=40, weight="bold", color=color)
            bar(s, y + 60, item["value"], color)
            y += 120

    s1 = cover("The Gap", t, v, preview)

    s2 = Slide()
    s2.text(MARGIN, MARGIN, f"The gap · {v['unit']} · {v['year']}", size=30,
            weight="semibold", color=MUTED)
    s2.text(MARGIN, 230, v["gap_big"], size=150, weight="bold", color=ACCENT)
    y = s2.text(MARGIN, 420, "between the highest and the lowest", size=38, color=MUTED)
    for item, color, label in ((hi, FG, "Highest"), (lo, ACCENT, "Lowest")):
        y += 90
        s2.text(MARGIN, y, label.upper(), size=28, weight="semibold", color=MUTED)
        s2.text(MARGIN, y + 44, item["name"], size=52, weight="bold", color=color,
                max_width=WIDTH - 300)
        s2.text(CAROUSEL[0] - MARGIN, y + 44, n_fmt(item["value"], p["unit"]), size=52,
                weight="bold", color=color, ha="right")
        bar(s2, y + 130, item["value"], color)
        y += 150
    s2.footer(source_line(v) + (" · bars start at 0" if scale else ""))

    s3 = Slide()
    y = s3.text(MARGIN, MARGIN, "The numbers", size=56, weight="bold")
    for label, name, value, color in (("Highest", hi["name"], v["highest_exact"], FG),
                                      ("Lowest", lo["name"], v["lowest_exact"], ACCENT)):
        y += 60
        y = s3.text(MARGIN, y, label.upper(), size=30, weight="semibold", color=MUTED)
        y = s3.text(MARGIN, y + 10, name, size=60, weight="bold", color=color, max_width=WIDTH)
        y = s3.text(MARGIN, y + 6, value, size=76, weight="bold", color=color)
        if n_with_unit("", p["unit"]):  # unità sotto il numero, se non è già nel valore
            y = s3.text(MARGIN, y + 4, p["unit"], size=30, color=MUTED)
        s3.line(MARGIN, y + 40, CAROUSEL[0] - MARGIN, y + 40)
        y += 40
    y = s3.text(MARGIN, y + 50, t["closing"], size=40, weight="bold", max_width=WIDTH)
    s3.text(MARGIN, y + 24, f"{v['scope_note']}. {v['n_countries']} compared, {v['year']}.",
            size=30, color=MUTED, max_width=WIDTH, line_height=1.35)
    s3.footer(source_line(v))

    return [s1, s2, s3, closing(v)]


BUILDERS = {"ranked": ranked, "the_gap": the_gap}