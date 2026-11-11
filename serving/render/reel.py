"""Reel: video verticale 1080 × 1920 generato dagli stessi dati del carosello.

Ogni fotogramma è disegnato con la stessa Slide del carosello (matplotlib),
poi ffmpeg li monta in un MP4 H.264 con una traccia audio muta: la musica
si sceglie su Instagram al momento della pubblicazione.

I tempi sono in secondi; ogni elemento ha un'entrata (comparsa, barra che
cresce, numero che sale contando) calcolata dal tempo del fotogramma.
"""

import subprocess
from pathlib import Path

from matplotlib.colors import to_rgba

from gold.copywriting.numbers import fmt_value
from serving.render.base import ACCENT, BG, BRAND, FG, HANDLE, LINE, MARGIN, MUTED, REEL, ROOT, Slide

FPS = 30
W, H = REEL
WIDTH = W - 2 * MARGIN
TOP, BOTTOM = 240, H - 380   # fuori da qui ci sono i pulsanti di Instagram
LOGO = ROOT / "brand" / "assets" / "mark_dark-bg.png"


# --- Strumenti di animazione -----------------------------------------------

def progress(t, start, duration):
    """Da 0 a 1 tra start e start + duration, con frenata finale (ease-out)."""
    x = min(1.0, max(0.0, (t - start) / duration))
    return 1 - (1 - x) ** 3


def fade(color, alpha):
    return to_rgba(color, max(0.0, min(1.0, alpha)))


def end_card(s: Slide, v, alpha, note=None):
    """Chiusura: logo, nome, invito a seguire, fonte (e una nota, se serve)."""
    cx = W / 2
    s.image(LOGO, cx - 200, 560, 400, 400)
    y = s.text(cx, 1020, BRAND, size=72, weight="bold", ha="center", color=fade(FG, alpha))
    y = s.text(cx, y + 30, f"Follow {HANDLE}", size=44, weight="semibold", ha="center",
               color=fade(ACCENT, alpha))
    y = s.text(cx, y + 60, f"Source: {v['source_name']} · {v['source_code']} · {v['year']}",
               size=28, ha="center", color=fade(MUTED, alpha))
    if note:
        s.text(cx, y + 12, note, size=26, ha="center", color=fade(MUTED, alpha))


# Nota per le animazioni che passano in modo fluido da un anno all'altro
BETWEEN_YEARS = "Animated between annual values. Countries without data that year are left out."
# Colori stabili per paese (le barre e le linee non cambiano colore durante la gara)
PALETTE = ["#E9EEF3", "#7FA7D9", "#F2A091", "#5B8FD1", "#CBB2BA", "#9CC5A1", "#E8C170",
           "#B39DDB", "#80CBC4", "#F48FB1"]


def color_of(iso3, leader=False):
    return ACCENT if leader else PALETTE[sum(map(ord, iso3)) % len(PALETTE)]


def timeline(now, start, per_year, n_years):
    """Posizione nella serie: (indice dell'anno, frazione verso il successivo)."""
    f = min(max(0.0, (now - start) / per_year), n_years - 1)
    i = int(f)
    return min(i, n_years - 1), f - i


def hook(s: Slide, t, now):
    """I primi 2 secondi di ogni reel: il titolo grande che sale e compare."""
    a = progress(now, 0, 0.6)
    y = s.text(MARGIN, 620 - 40 * a, t["title"], size=104, weight="bold",
               color=fade(FG, a), max_width=WIDTH, line_height=1.04)
    s.text(MARGIN, y + 40, t["subtitle"], size=40,
           color=fade(MUTED, progress(now, 0.7, 0.5)), max_width=WIDTH, line_height=1.3)


def header(s: Slide, v, unit, title, title_color=FG):
    s.text(MARGIN, TOP, f"{v['indicator']} · {unit} · {v['year']}", size=32,
           weight="semibold", color=MUTED, max_width=WIDTH)
    return s.text(MARGIN, TOP + 56, title, size=54, weight="bold", color=title_color,
                  max_width=WIDTH, line_height=1.1)


HOOK_END = 2.2


# --- Ranked: conto alla rovescia -------------------------------------------

def ranked(t, v, p):
    """Restituisce la durata e una funzione che disegna il fotogramma al tempo t."""
    from serving.render.carousel import bar_max

    unit = p["unit"]
    rows = [dict(r, raw=x["value"]) for r, x in zip(v["_rows_top"], p["top"])]
    vmax = bar_max(unit, [r["raw"] for r in rows] + [x["value"] for x in p["bottom"]])
    hook_end, step, row_h = HOOK_END, 1.3, 100
    banner_y, list_top = TOP + 150, TOP + 290   # la lista non si sposta mai
    # I paesi entrano dal 10° al 4°; i primi 3 tutti insieme alla rivelazione
    hidden = 3
    starts = {}
    for k, idx in enumerate(range(len(rows) - 1, hidden - 1, -1)):
        starts[idx] = hook_end + k * step
    reveal = hook_end + (len(rows) - hidden) * step + 0.6
    for idx in range(hidden):
        starts[idx] = reveal
    closing_at = reveal + 2.6
    end_at = closing_at + 1.8
    duration = end_at + 2.0

    def draw(s: Slide, now: float):
        if now < hook_end:
            hook(s, t, now)
            return
        if now >= end_at:
            end_card(s, v, progress(now, end_at, 0.5))
            return
        s.text(MARGIN, TOP, f"{v['indicator']} · {unit} · {v['year']}", size=32,
               weight="semibold", color=MUTED, max_width=WIDTH)
        s.text(MARGIN, TOP + 56, "Top 10", size=60, weight="bold")
        # Riga sopra la lista: prima la domanda, poi la risposta, poi l'ultimo posto
        if now < reveal:
            banner, color, since = "Who's #1?", MUTED, hook_end
        elif now < closing_at:
            banner, color, since = t["reveal"], ACCENT, reveal
        else:
            banner, color, since = t["closing"], FG, closing_at
        s.text(MARGIN, banner_y, banner, size=44, weight="bold",
               color=fade(color, progress(now, since, 0.4)), max_width=WIDTH, line_height=1.15)
        first = rows[0]["rank"]
        revealed = now >= reveal
        for idx, r in enumerate(rows):
            y = list_top + idx * row_h
            hi = r["rank"] == first
            color = ACCENT if hi else FG
            appear = progress(now, starts[idx], 0.35)
            grow = progress(now, starts[idx], 1.0)
            if idx < hidden and not revealed:  # posto ancora segreto
                s.text(MARGIN, y, r["rank"], size=40, weight="bold", color=ACCENT)
                s.rect(MARGIN + 120, y + 6, 300, 38, LINE, 8)
                s.text(MARGIN + 140, y, "?", size=40, weight="bold", color=MUTED)
                continue
            s.text(MARGIN, y, r["rank"], size=40, weight="bold",
                   color=fade(ACCENT if hi else MUTED, appear))
            s.text(MARGIN + 120, y, r["name"], size=42, weight="bold", color=fade(color, appear),
                   max_width=WIDTH - 120 - 260)
            counting = r["value"] if grow >= 1 else fmt_value(r["raw"] * grow, unit)
            s.text(W - MARGIN, y, counting, size=42, weight="bold", color=fade(color, appear),
                   ha="right")
            s.rect(MARGIN + 120, y + 62, WIDTH - 120, 10, LINE, 5)
            bar = (WIDTH - 120) * max(0.0, r["raw"]) / vmax * grow
            if bar >= 1:
                s.rect(MARGIN + 120, y + 62, max(bar, 10), 10, color, 5)

    return duration, draw


# --- The Gap: il divario che si apre --------------------------------------

def the_gap(t, v, p):
    from gold.copywriting.numbers import fmt_ratio

    unit = p["unit"]
    hi, lo = p["highest"], p["lowest"]
    scale = hi["value"] if hi["value"] > 0 and lo["value"] >= 0 else None
    big_at, closing_at = 6.0, 9.4
    end_at = closing_at + 2.0
    duration = end_at + 2.0

    def big_number(x):
        """Il numero grande che sale contando, nello stesso formato del carosello."""
        if p.get("ratio"):
            return fmt_ratio(max(1.0, p["ratio"] * x))
        if p.get("points"):
            return f"{abs(p['difference']) * x:.1f} pts"
        return fmt_value(p["difference"] * x, unit)

    def draw(s: Slide, now: float):
        if now < HOOK_END:
            hook(s, t, now)
            return
        if now >= end_at:
            end_card(s, v, progress(now, end_at, 0.5))
            return
        header(s, v, unit, "The gap")
        y = TOP + 220
        for k, (item, color, label) in enumerate(((hi, FG, "HIGHEST"), (lo, ACCENT, "LOWEST"))):
            start = HOOK_END + 0.3 + k * 1.2
            a, grow = progress(now, start, 0.4), progress(now, start, 1.4)
            s.text(MARGIN, y, label, size=30, weight="semibold", color=fade(MUTED, a))
            s.text(MARGIN, y + 46, item["name"], size=56, weight="bold", color=fade(color, a),
                   max_width=WIDTH - 320)
            shown = fmt_value(item["value"] * grow, unit) if grow < 1 else fmt_value(item["value"], unit)
            s.text(W - MARGIN, y + 46, shown, size=56, weight="bold", color=fade(color, a), ha="right")
            s.rect(MARGIN, y + 140, WIDTH, 18, LINE, 9)
            if scale:
                s.rect(MARGIN, y + 140, max(8, WIDTH * item["value"] / scale * grow), 18, color, 9)
            y += 230
        g = progress(now, big_at, 1.6)
        if now >= big_at:
            s.text(MARGIN, y + 60, big_number(g), size=160, weight="bold", color=fade(ACCENT, g * 3))
            s.text(MARGIN, y + 260, "between the highest and the lowest", size=40,
                   color=fade(MUTED, g * 3))
        if now >= closing_at:
            c = progress(now, closing_at, 0.5)
            s.text(MARGIN, y + 360, v["scope_note"] + ".", size=32, color=fade(MUTED, c),
                   max_width=WIDTH, line_height=1.3)

    return duration, draw


# --- Mapped: la mappa che si colora fascia per fascia ----------------------

def mapped(t, v, p):
    from serving.render import worldmap
    from serving.render.carousel import MAP_SCALE, NO_DATA

    unit = p["unit"]
    edges = p["bins"]
    cls = {r["iso3"]: sum(r["value"] >= e for e in edges) for r in p["values"]}
    fmt = lambda x: fmt_value(x, unit)
    labels = ([f"under {fmt(edges[0])}"] +
              [f"{fmt(a)} – {fmt(b)}" for a, b in zip(edges, edges[1:])] +
              [f"{fmt(edges[-1])} and over"])
    step = 0.9
    classes_at = [HOOK_END + 0.6 + k * step for k in range(len(MAP_SCALE))]
    closing_at = classes_at[-1] + 1.8
    end_at = closing_at + 2.6
    duration = end_at + 2.0

    def draw(s: Slide, now: float):
        if now < HOOK_END:
            hook(s, t, now)
            return
        if now >= end_at:
            end_card(s, v, progress(now, end_at, 0.5))
            return
        y = header(s, v, unit, "Every country, mapped")
        shown = sum(now >= at for at in classes_at)   # quante fasce sono già colorate
        colors = {iso3: MAP_SCALE[k] for iso3, k in cls.items() if k < shown}
        y += 60
        y += worldmap.draw(s.ax, MARGIN - 40, y, WIDTH + 80, colors, NO_DATA, BG) + 50
        col_w = WIDTH / 2
        for k, (c, label) in enumerate(zip(MAP_SCALE, labels)):
            a = progress(now, classes_at[k], 0.4)
            lx, ly = MARGIN + (k % 2) * col_w, y + (k // 2) * 64
            s.rect(lx, ly + 4, 40, 34, fade(c, a), 6)
            s.text(lx + 58, ly, label, size=34, color=fade(FG, a))
        if now >= closing_at:
            c = progress(now, closing_at, 0.5)
            s.text(MARGIN, y + 3 * 64 + 50, t["closing"], size=46, weight="bold",
                   color=fade(ACCENT, c), max_width=WIDTH, line_height=1.15)

    return duration, draw


# --- Then vs Now: i punti che si spostano ----------------------------------

def then_vs_now(t, v, p):
    from serving.render.carousel import bar_max

    unit = p["unit"]
    movers = p["movers"]
    base, year = str(p["base_year"]), str(p["year"])
    vmax = bar_max(unit, [x["then"] for x in movers] + [x["now"] for x in movers]) if movers else 1
    scale = lambda value: MARGIN + WIDTH * max(0.0, value) / vmax
    dots_at, move_at, move_len = HOOK_END + 0.3, HOOK_END + 1.4, 3.6
    closing_at = move_at + move_len + 1.0
    end_at = closing_at + 2.8
    duration = end_at + 2.0

    def draw(s: Slide, now: float):
        if now < HOOK_END:
            hook(s, t, now)
            return
        if now >= end_at:
            end_card(s, v, progress(now, end_at, 0.5))
            return
        y = header(s, v, unit, f"The 10 biggest changes since {base}")
        s.dot(MARGIN + 14, y + 40, 12, MUTED)
        s.text(MARGIN + 38, y + 20, base, size=32, color=MUTED)
        s.dot(MARGIN + 180, y + 40, 12, ACCENT)
        s.text(MARGIN + 204, y + 20, year, size=32, color=ACCENT)
        y += 100
        a = progress(now, dots_at, 0.5)
        m = progress(now, move_at, move_len)
        for row, x in zip(v["_movers"], movers):
            s.text(MARGIN, y, row["name"], size=36, weight="bold", color=fade(FG, a),
                   max_width=WIDTH - 360)
            label = f"{row['then']} → {row['now']}" if m >= 1 else row["then"]
            s.text(W - MARGIN, y, label, size=32, color=fade(MUTED, a), ha="right")
            cy = y + 64
            pos = x["then"] + (x["now"] - x["then"]) * m
            s.line(MARGIN, cy, MARGIN + WIDTH, cy, LINE, 3)
            if m > 0:
                s.line(scale(x["then"]), cy, scale(pos), cy, FG, 6)
            s.dot(scale(x["then"]), cy, 12, fade(MUTED, a))
            if m > 0:
                s.dot(scale(pos), cy, 12, ACCENT)
            y += 96
        if now >= closing_at:
            c = progress(now, closing_at, 0.5)
            s.text(MARGIN, y + 30, v["trend_line"], size=40, weight="bold",
                   color=fade(ACCENT, c), max_width=WIDTH, line_height=1.15)

    return duration, draw


# --- The World in One Chart: il treemap che si compone ---------------------

def world_in_one_chart(t, v, p):
    from serving.render.carousel import draw_treemap

    rest = p["rest_share"]
    items = [(r["name"], x["share"], r["share"], x["iso3"])
             for r, x in zip(v["_shares"], p["shares"])]
    if rest > 0:
        items.append((f"Rest of the world ({p['rest_count']})", rest, f"{rest * 100:.1f}%", None))
    step = 0.35
    boxes_at = HOOK_END + 0.4
    closing_at = boxes_at + len(items) * step + 1.0
    end_at = closing_at + 2.8
    duration = end_at + 2.0

    def draw(s: Slide, now: float):
        if now < HOOK_END:
            hook(s, t, now)
            return
        if now >= end_at:
            end_card(s, v, progress(now, end_at, 0.5))
            return
        y = header(s, v, v["unit"], "Share of the total, by country")
        visible = max(0, int((now - boxes_at) / step) + 1) if now >= boxes_at else 0
        height = 980
        draw_treemap(s, items, MARGIN, y + 40, WIDTH, height, visible=visible)
        if now >= closing_at:
            c = progress(now, closing_at, 0.5)
            s.text(MARGIN, y + 40 + height + 40, t["closing"], size=46, weight="bold",
                   color=fade(ACCENT, c), max_width=WIDTH, line_height=1.15)

    return duration, draw


# =============================================================================
# Reel "cinema": formati pensati per il video, a tutto schermo.
# Niente cornice da slide: sfondo sfumato, titolo che entra grande e poi si
# ritira, telecamera che segue i dati, anno gigante sullo sfondo.
# =============================================================================

TITLE_Y, BOT_SAFE = 250, H - 420   # fuori da qui ci sono i pulsanti di Instagram
CONTENT_TOP = TITLE_Y + 130   # spazio per un titolo su due righe
CINEMA_COLORS = ["#7FA7D9", "#E8C170", "#9CC5A1", "#B39DDB", "#80CBC4", "#CBB2BA", "#5B8FD1"]


def cinema_color(iso3, leader=False):
    """Colore stabile per paese; il corallo è riservato a chi è in testa."""
    return ACCENT if leader else CINEMA_COLORS[sum(map(ord, iso3)) % len(CINEMA_COLORS)]


def backdrop(s: Slide):
    """Sfondo a tinta unita. Le sfumature nei video si vedono a bande
    (compressione a 8 bit), quindi niente gradiente."""


def big_text(s, x, y, text, size, color, alpha=1.0, ha="left", va="top", weight="bold", z=5):
    from serving.render.base import FONTS

    s.ax.text(x, y, text, fontproperties=FONTS[weight], fontsize=size * 0.72,
              color=fade(color, alpha), ha=ha, va=va, zorder=z)


def kinetic_title(s, t, now, closing_at=None, hook_end=HOOK_END):
    """Il titolo entra grande al centro, poi si rimpicciolisce e sale in alto.
    Alla fine (closing_at) lascia il posto alla frase di chiusura, in corallo."""
    from serving.render.base import wrap

    shrink = progress(now, hook_end - 0.5, 0.5)
    size = 108 + (46 - 108) * shrink
    y = 640 + (TITLE_Y - 640) * shrink - 40 * (1 - progress(now, 0, 0.6))
    alpha = progress(now, 0, 0.5)
    if closing_at is not None and now >= closing_at:
        swap = progress(now, closing_at, 0.4)
        alpha *= 1 - swap
        for k, line in enumerate(wrap(t["closing"], 46, WIDTH, "bold")):
            big_text(s, MARGIN, TITLE_Y + k * 48, line, 46, ACCENT, swap, z=9)
    lines = wrap(t["title"], size, WIDTH, "bold")
    for k, line in enumerate(lines):
        big_text(s, MARGIN, y + k * size * 1.05, line, size, FG, alpha, z=9)
    if now < hook_end - 0.5:
        sub_y = y + len(lines) * size * 1.05 + 30
        for k, line in enumerate(wrap(t["subtitle"], 38, WIDTH, "regular")):
            big_text(s, MARGIN, sub_y + k * 46, line, 38, MUTED, progress(now, 0.7, 0.4),
                     weight="regular", z=9)


def fit_size(text, size, max_width, weight="bold"):
    """La dimensione più grande (fino a size) a cui il testo sta in max_width."""
    from serving.render.base import text_width

    while size > 14 and text_width(text, size, weight) > max_width:
        size *= 0.94
    return size


def year_watermark(s, year, x, y, size=300, ha="center", va="center"):
    big_text(s, x, y, str(year), size, FG, 0.08, ha=ha, va=va, z=1)


def cinema_end(s: Slide, v, alpha, note=None):
    backdrop(s)
    end_card(s, v, alpha, note)


def real_year(years, i, frac):
    """L'anno (e quindi il valore) da scrivere: sempre un anno vero, il più vicino."""
    return min(i + 1, len(years) - 1) if frac >= 0.5 else i


# --- Bar chart race a tutto schermo ----------------------------------------

def bar_race(t, v, p):
    from matplotlib.patches import FancyBboxPatch

    unit, frames = p["unit"], p["frames"]
    # Più sorpassi ci sono ogni anno, più tempo serve per seguirli
    per_year, start = min(0.95, 0.5 + 0.12 * p.get("volatility", 0)), HOOK_END
    race_end = start + per_year * (len(frames) - 1)
    closing_at, end_at = race_end + 0.4, race_end + 2.6
    duration = end_at + 2.4
    shown = 8
    bars_bottom = BOT_SAFE - 200                 # sotto le barre, la fascia dell'anno
    row_h = (bars_bottom - CONTENT_TOP) / shown

    def draw(s: Slide, now: float):
        if now >= end_at:
            cinema_end(s, v, progress(now, end_at, 0.5), BETWEEN_YEARS)
            return
        backdrop(s)
        kinetic_title(s, t, now, closing_at)
        if now < HOOK_END - 0.3:
            return
        i, frac = timeline(now, start, per_year, len(frames))
        a, b = frames[i], frames[min(i + 1, len(frames) - 1)]
        near = frames[real_year(frames, i, frac)]
        big_text(s, W - MARGIN, BOT_SAFE, str(near["year"]), 170, MUTED, ha="right", va="bottom", z=7)
        ra = {r["iso3"]: k for k, r in enumerate(a["top"])}
        rb = {r["iso3"]: k for k, r in enumerate(b["top"])}
        va_ = {r["iso3"]: r for r in a["top"]}
        vb_ = {r["iso3"]: r for r in b["top"]}
        vn = {r["iso3"]: r for r in near["top"]}
        top_a = a["top"][0]["value"] if a["top"] else 1
        top_b = b["top"][0]["value"] if b["top"] else top_a
        vmax = (top_a + (top_b - top_a) * frac) or 1
        leader = near["top"][0]["iso3"] if near["top"] else None
        for iso3 in ra.keys() | rb.keys():
            r0, r1 = ra.get(iso3, len(a["top"])), rb.get(iso3, len(b["top"]))
            rank = r0 + (r1 - r0) * frac
            if rank > shown - 0.4:
                continue
            if iso3 in va_ and iso3 in vb_:      # presente in entrambi gli anni: si muove
                value, alpha = va_[iso3]["value"] + (vb_[iso3]["value"] - va_[iso3]["value"]) * frac, 1
            else:                                # manca in uno dei due: compare o scompare
                value = (va_.get(iso3) or vb_[iso3])["value"]
                alpha = (1 - frac) if iso3 in va_ else frac
            row = vn.get(iso3) or va_.get(iso3) or vb_[iso3]
            y = CONTENT_TOP + rank * row_h
            col = cinema_color(iso3, iso3 == leader)
            width = max(24, (W - 2 * MARGIN) * max(0.0, value) / vmax)
            s.ax.add_patch(FancyBboxPatch((MARGIN, y + 10), width, row_h - 26,
                                          boxstyle="round,pad=0,rounding_size=16",
                                          facecolor=fade(col, alpha), linewidth=0, zorder=4))
            label = fmt_value(row["value"], unit)
            mid = y + 10 + (row_h - 26) / 2          # centro verticale della barra
            from serving.render.base import text_width

            name_size = fit_size(row["name"], 40, W - 2 * MARGIN - 48)
            need = max(text_width(row["name"], name_size, "bold"), text_width(label, 28, "semibold"))
            inside = width > need + 48             # il testo sta dentro la barra?
            ink, tx = (BG, MARGIN + 24) if inside else (FG, MARGIN + width + 20)
            if not inside:                          # fuori dalla barra: deve stare nello schermo
                name_size = fit_size(row["name"], 40, W - MARGIN - tx)
            big_text(s, tx, mid - 17, row["name"], name_size, ink, alpha, va="center", z=6)
            big_text(s, tx, mid + 21, label, 28, ink, alpha * 0.85, va="center",
                     weight="semibold", z=6)

    return duration, draw


# --- Linee a tutto schermo: line race e duello ------------------------------

def _smooth(values, steps=12):
    """Curva morbida tra i valori annuali (cubica monotona: non inventa picchi
    né avvallamenti tra due anni). Restituisce tratti continui [(t, y), ...]:
    dove manca un anno la linea si interrompe."""
    import numpy as np

    runs, run = [], []
    for k, val in enumerate(values + [None]):
        if val is None:
            if len(run) > 1:
                runs.append(run)
            run = []
        else:
            run.append((k, val))
    out = []
    for run in runs:
        x = np.array([k for k, _ in run], dtype=float)
        y = np.array([val for _, val in run], dtype=float)
        d = np.diff(y) / np.diff(x)
        m = np.zeros_like(y)                      # pendenze di Fritsch-Carlson
        m[0], m[-1] = d[0], d[-1]
        for k in range(1, len(y) - 1):
            m[k] = 0.0 if d[k - 1] * d[k] <= 0 else 2 / (1 / d[k - 1] + 1 / d[k])
        ts, vs = [], []
        for k in range(len(x) - 1):
            h = x[k + 1] - x[k]
            for u in np.linspace(0, 1, steps, endpoint=False):
                h00, h10 = 2 * u**3 - 3 * u**2 + 1, u**3 - 2 * u**2 + u
                h01, h11 = -2 * u**3 + 3 * u**2, u**3 - u**2
                ts.append(x[k] + u * h)
                vs.append(h00 * y[k] + h10 * h * m[k] + h01 * y[k + 1] + h11 * h * m[k + 1])
        ts.append(x[-1])
        vs.append(y[-1])
        out.append((np.array(ts), np.array(vs)))
    return out


def _lines(t, v, p, years, series, overtake=None, per_year=0.55, window=10):
    """Motore comune: le linee avanzano anno per anno, la telecamera scorre in
    avanti e fa zoom sui valori visibili, l'anno sta nella sua fascia in basso."""
    import numpy as np

    unit = p["unit"]
    start = HOOK_END
    race_end = start + per_year * (len(years) - 1)
    closing_at, end_at = race_end + 0.8, race_end + 3.0
    duration = end_at + 2.4
    ends = {x["iso3"]: x["values"][-1] or 0 for x in series}
    top_iso = max(ends, key=ends.get)
    others = iter(CINEMA_COLORS)
    colors = {x["iso3"]: ACCENT if x["iso3"] == top_iso else next(others) for x in series}
    curves = {x["iso3"]: _smooth(x["values"]) for x in series}
    left, right, top, bottom = MARGIN - 10, W - 330, CONTENT_TOP + 40, BOT_SAFE - 210

    # Inquadratura per ogni anno; tra un anno e l'altro si passa con dolcezza
    def frame_for(k):
        x_hi = max(float(k), window * 0.6)
        x_lo = x_hi - window
        vals = [val for x in series for j, val in enumerate(x["values"])
                if val is not None and x_lo - 1 <= j <= k + 1]
        lo, hi = min(vals), max(vals)
        pad = (hi - lo) * 0.15 or abs(hi) * 0.1 or 1
        return x_lo, x_hi, lo - pad, hi + pad

    cams = [frame_for(k) for k in range(len(years))]

    def draw(s: Slide, now: float):
        if now >= end_at:
            cinema_end(s, v, progress(now, end_at, 0.5), BETWEEN_YEARS)
            return
        backdrop(s)
        kinetic_title(s, t, now, closing_at)
        if now < HOOK_END - 0.3:
            return
        i, frac = timeline(now, start, per_year, len(years))
        pos = i + frac
        ease = frac * frac * (3 - 2 * frac)
        a, b = cams[i], cams[min(i + 1, len(years) - 1)]
        x_lo, x_hi, y_lo, y_hi = (a[n] + (b[n] - a[n]) * ease for n in range(4))
        X = lambda k: left + (right - left) * (k - x_lo) / (x_hi - x_lo)
        Y = lambda val: bottom - (bottom - top) * (val - y_lo) / ((y_hi - y_lo) or 1)
        k_year = real_year(years, i, frac)
        for q in (0.2, 0.5, 0.8):                # griglia leggera con i valori
            val = y_lo + (y_hi - y_lo) * q
            s.ax.plot([left, right], [Y(val), Y(val)], color=fade(FG, 0.07), lw=1.5, zorder=2)
            big_text(s, left, Y(val) - 8, fmt_value(val, unit), 22, MUTED, va="bottom",
                     weight="regular", z=2)
        big_text(s, MARGIN, BOT_SAFE, str(years[k_year]), 170, MUTED, va="bottom", z=7)
        if overtake and pos >= years.index(overtake):     # il punto del sorpasso
            ox = X(years.index(overtake))
            if left <= ox <= right:
                s.ax.plot([ox, ox], [top, bottom], color=fade(ACCENT, 0.5), lw=2,
                          linestyle=(0, (6, 6)), zorder=2)
                big_text(s, ox + 12, top, f"Overtake: {overtake}", 26, ACCENT, z=8)
        tips = []
        for x in series:
            col = colors[x["iso3"]]
            tip = None
            for ts, vs in curves[x["iso3"]]:
                keep = ts <= pos
                if keep.sum() < 2:
                    continue
                px = np.append(ts[keep], pos) if ts[0] <= pos <= ts[-1] else ts[keep]
                py = np.append(vs[keep], np.interp(pos, ts, vs)) if ts[0] <= pos <= ts[-1] else vs[keep]
                xs, ys = [X(k) for k in px], [Y(val) for val in py]
                s.ax.plot(xs, ys, color=col, lw=5, solid_capstyle="round",
                          solid_joinstyle="round", zorder=4)
                tip = (xs[-1], ys[-1])
            if tip:
                s.ax.scatter([tip[0]], [tip[1]], s=150, color=col, zorder=6, linewidths=0)
                shown = x["values"][k_year]
                tips.append([tip[1] - 30, tip[0] + 28, x["name"],
                             fmt_value(shown, unit) if shown is not None else "", col])
        tips.sort()
        for k in range(1, len(tips)):            # etichette che non si sovrappongono
            tips[k][0] = max(tips[k][0], tips[k - 1][0] + 72)
        for ty, tx, name, value, col in tips:
            big_text(s, tx, ty, name, 34, col, z=8)
            big_text(s, tx, ty + 40, value, 28, FG, 0.85, weight="semibold", z=8)

    return duration, draw


def line_race(t, v, p):
    return _lines(t, v, p, p["years"], p["series"])


def duel(t, v, p):
    """Il duello è una line race a due, con il punto del sorpasso."""
    return _lines(t, v, p, p["years"], [p["a"], p["b"]], overtake=p.get("overtake_year"),
                  per_year=0.6, window=12)


# --- Find your country: la ruota della classifica ---------------------------

def scroll_ranking(t, v, p):
    from gold.copywriting.numbers import competition_ranks

    unit, rows = p["unit"], p["rows"]
    disp = [fmt_value(r["value"], unit) for r in rows]
    ranks = competition_ranks(disp)
    per_row, start = 0.075, HOOK_END + 0.4       # secondi per riga
    scroll_end = start + per_row * (len(rows) - 1)
    closing_at, end_at = scroll_end + 0.6, scroll_end + 3.0
    duration = end_at + 2.4
    center, spacing = (CONTENT_TOP + BOT_SAFE) / 2, 96

    def draw(s: Slide, now: float):
        if now >= end_at:
            cinema_end(s, v, progress(now, end_at, 0.5))
            return
        backdrop(s)
        kinetic_title(s, t, now, closing_at)
        if now < HOOK_END - 0.3:
            return
        pos = min(len(rows) - 1, max(0.0, (now - start) / per_row))
        s.rect(MARGIN - 30, center - 60, W - 2 * MARGIN + 60, 120, fade(FG, 0.06), 20)
        for k in range(max(0, int(pos) - 8), min(len(rows), int(pos) + 9)):
            d = k - pos                            # distanza dal centro: effetto ruota
            y = center + d * spacing * (1 - 0.04 * abs(d))
            if y < CONTENT_TOP or y > BOT_SAFE:
                continue
            scale = max(0.45, 1 - 0.09 * abs(d))
            alpha = max(0.0, 1 - 0.13 * abs(d))
            top3 = ranks[k].lstrip("=") in ("1", "2", "3")
            col = ACCENT if top3 else FG
            big_text(s, MARGIN, y, ranks[k], 44 * scale, MUTED if not top3 else ACCENT, alpha,
                     va="center", z=6)
            from serving.render.base import text_width

            value_w = text_width(disp[k], 48 * scale, "bold")
            room = W - 2 * MARGIN - 150 - value_w - 30   # spazio tra posizione e valore
            name_size = fit_size(rows[k]["name"], 52 * scale, room)
            big_text(s, MARGIN + 150, y, rows[k]["name"], name_size, col, alpha, va="center", z=6)
            big_text(s, W - MARGIN, y, disp[k], 48 * scale, FG, alpha, ha="right", va="center", z=6)

    return duration, draw


BUILDERS = {"ranked": ranked, "the_gap": the_gap, "mapped": mapped,
            "then_vs_now": then_vs_now, "world_in_one_chart": world_in_one_chart,
            "bar_race": bar_race, "line_race": line_race, "duel": duel,
            "scroll_ranking": scroll_ranking}




# --- Montaggio ----------------------------------------------------------------

def render_video(builder, t, v, p, out_path: Path) -> Path:
    """Disegna i fotogrammi e li passa direttamente a ffmpeg, senza file
    intermedi: MP4 H.264 con audio muto AAC (alcune piattaforme lo richiedono)."""
    duration, draw = builder(t, v, p)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
        "-preset", "medium", "-c:a", "aac", "-movflags", "+faststart",
        str(out_path),
    ], stdin=subprocess.PIPE)
    try:
        for i in range(int(duration * FPS)):
            s = Slide(size=REEL)
            draw(s, i / FPS)
            ffmpeg.stdin.write(s.rgba())
    finally:
        ffmpeg.stdin.close()
        if ffmpeg.wait() != 0:
            raise RuntimeError(f"ffmpeg non è riuscito a creare {out_path}")
    return out_path
