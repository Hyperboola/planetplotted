"""Mappa del mondo per il render: proiezione Equal Earth e disegno dei paesi.

Equal Earth mantiene le aree reali dei paesi (l'Africa non sembra più
piccola della Groenlandia). È una formula pubblicata nel 2018 da
Šavrič, Patterson e Jenny: la scriviamo qui, senza librerie in più.
"""

import json
import math
from functools import lru_cache

import numpy as np
from matplotlib.collections import PolyCollection

from render.base import ROOT

MAP_FILE = ROOT / "brand" / "maps" / "countries_50m.geojson"
A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
M = math.sqrt(3) / 2
MIN_LAT = -58  # sotto non c'è nessun paese (si esclude l'Antartide)


def equal_earth(lon, lat):
    """Gradi -> coordinate Equal Earth (x circa ±2.71, y circa ±1.32)."""
    lam, phi = np.radians(lon), np.radians(lat)
    theta = np.arcsin(M * np.sin(phi))
    t2, t6 = theta ** 2, theta ** 6
    x = 2 * math.sqrt(3) * lam * np.cos(theta) / (3 * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)))
    y = theta * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))
    return x, y


X_MAX = float(equal_earth(180, 0)[0])
Y_MAX = float(equal_earth(0, 90)[1])
Y_MIN = float(equal_earth(0, MIN_LAT)[1])
ASPECT = (2 * X_MAX) / (Y_MAX - Y_MIN)  # larghezza / altezza della mappa


def _area(xy):
    x, y = xy[:, 0], xy[:, 1]
    return abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2


@lru_cache(maxsize=1)
def shapes():
    """Lista di (iso3, poligono proiettato), dal più grande al più piccolo:
    così i paesi dentro altri paesi (Lesotho nel Sudafrica) restano visibili."""
    data = json.loads(MAP_FILE.read_text())
    out = []
    for f in data["features"]:
        iso3, geom = f["properties"]["iso3"], f["geometry"]
        if iso3 == "ATA" or geom is None:
            continue
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            ring = np.array(poly[0], dtype=float)  # solo il contorno esterno
            x, y = equal_earth(ring[:, 0], np.clip(ring[:, 1], MIN_LAT, 90))
            out.append((iso3, np.column_stack([x, y])))
    out.sort(key=lambda s: _area(s[1]), reverse=True)
    return out


def draw(ax, x, y, width, colors: dict, no_data: str, border: str):
    """Disegna la mappa nel riquadro che parte da (x, y) in pixel, largo width.
    colors: {iso3: colore}. Restituisce l'altezza occupata."""
    height = width / ASPECT
    sx = width / (2 * X_MAX)
    sy = height / (Y_MAX - Y_MIN)
    verts, fills = [], []
    for iso3, xy in shapes():
        px = x + (xy[:, 0] + X_MAX) * sx
        py = y + (Y_MAX - xy[:, 1]) * sy  # in pixel la y cresce verso il basso
        verts.append(np.column_stack([px, py]))
        fills.append(colors.get(iso3, no_data))
    ax.add_collection(PolyCollection(verts, facecolors=fills, edgecolors=border,
                                     linewidths=0.35, zorder=2))
    return height