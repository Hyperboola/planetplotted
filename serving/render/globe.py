"""Globo ortografico: la Terra vista dallo spazio, con i paesi colorati per valore.

Si mostra solo l'emisfero rivolto verso chi guarda; i paesi sul retro non
vengono disegnati, quelli sul bordo sono portati sull'orizzonte.
"""

import json
from functools import lru_cache

import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgba
from matplotlib.patches import Circle

from serving.render.base import FG
from serving.render.worldmap import MAP_FILE

OCEAN = "#132A44"
BORDER = "#0B1524"


@lru_cache(maxsize=1)
def _shapes():
    """Contorni dei paesi in radianti (lon, lat)."""
    out = []
    for f in json.loads(MAP_FILE.read_text())["features"]:
        geom = f["geometry"]
        if geom is None or f["properties"]["iso3"] == "ATA":
            continue
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            out.append((f["properties"]["iso3"], np.radians(np.array(poly[0], dtype=float))))
    return out


def visible(lon0, lat0):
    """I codici dei paesi che si vedono guardando il globo da (lon0, lat0)."""
    lam0, phi0 = np.radians(lon0), np.radians(lat0)
    seen = set()
    for iso3, ring in _shapes():
        lam, phi = ring[:, 0], ring[:, 1]
        cos_c = np.sin(phi0) * np.sin(phi) + np.cos(phi0) * np.cos(phi) * np.cos(lam - lam0)
        if (cos_c > 0).mean() >= 0.5:
            seen.add(iso3)
    return seen


def draw(s, cx, cy, r, lon0, lat0, colors, no_data):
    """Disegna il globo centrato in (cx, cy) con raggio r, guardando (lon0, lat0)."""
    s.ax.add_patch(Circle((cx, cy), r, facecolor=OCEAN, edgecolor=to_rgba(FG, 0.12),
                          linewidth=2, zorder=2))
    lam0, phi0 = np.radians(lon0), np.radians(lat0)
    verts, fills = [], []
    for iso3, ring in _shapes():
        lam, phi = ring[:, 0], ring[:, 1]
        cos_c = np.sin(phi0) * np.sin(phi) + np.cos(phi0) * np.cos(phi) * np.cos(lam - lam0)
        if (cos_c > 0).mean() < 0.5:
            continue                              # paese sul retro del globo
        x = np.cos(phi) * np.sin(lam - lam0)
        y = np.cos(phi0) * np.sin(phi) - np.sin(phi0) * np.cos(phi) * np.cos(lam - lam0)
        back = cos_c <= 0                         # punti oltre il bordo: sull'orizzonte
        norm = np.hypot(x, y)
        x = np.where(back, x / np.maximum(norm, 1e-9), x)
        y = np.where(back, y / np.maximum(norm, 1e-9), y)
        verts.append(np.column_stack([cx + r * x, cy - r * y]))
        fills.append(colors.get(iso3, no_data))
    s.ax.add_collection(PolyCollection(verts, facecolors=fills, edgecolors=BORDER,
                                       linewidths=0.5, zorder=3))
