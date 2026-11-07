"""Scarica i confini dei paesi per le mappe (Natural Earth, dominio pubblico).

Tiene solo il codice paese e la forma, così il file è più leggero.
Il codice è quello della World Bank (WB_A3) quando c'è, altrimenti ISO_A3:
così combacia con la colonna iso3 del nostro database.

Uso (una sola volta):
    python -m render.setup_map
"""

import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "brand" / "maps" / "countries_50m.geojson"
URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
       "master/geojson/ne_50m_admin_0_countries.geojson")


def pick_code(props: dict) -> str | None:
    for key in ("WB_A3", "ISO_A3", "ADM0_A3"):
        code = props.get(key)
        if code and code != "-99":
            return code
    return None


def main():
    r = requests.get(URL, timeout=120)
    r.raise_for_status()
    features = []
    for f in r.json()["features"]:
        code = pick_code(f["properties"])
        if code:
            features.append({"type": "Feature", "properties": {"iso3": code},
                             "geometry": f["geometry"]})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    print(f"creato {OUT.relative_to(ROOT)}: {len(features)} paesi")


if __name__ == "__main__":
    main()