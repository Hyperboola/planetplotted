"""Scarica i confini dei paesi per le mappe (Natural Earth, dominio pubblico).

Tiene solo il codice paese e la forma, così il file è più leggero.
Il codice è ISO_A3, lo stesso usato dall'API World Bank. Il campo WB_A3
di Natural Earth contiene invece codici World Bank vecchi (ZAR per il
Congo, ROM per la Romania…), quindi non va usato.

Uso (una sola volta, o dopo aver modificato questo file):
    python -m serving.render.setup_map
"""

import json

import requests

from common.config import ROOT

OUT = ROOT / "brand" / "maps" / "countries_50m.geojson"
URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
       "master/geojson/ne_50m_admin_0_countries.geojson")

# Dove Natural Earth e World Bank usano codici diversi.
# Somaliland: per la World Bank fa parte dei dati della Somalia.
OVERRIDES = {"KOS": "XKX", "SOL": "SOM", "JEY": "CHI", "GGY": "CHI"}


def pick_code(props: dict) -> str:
    code = props.get("ISO_A3")
    if not code or code == "-99":  # Francia, Norvegia e pochi altri
        code = props.get("ADM0_A3")
    return OVERRIDES.get(code, code)


def main():
    r = requests.get(URL, timeout=120)
    r.raise_for_status()
    features = [{"type": "Feature", "properties": {"iso3": pick_code(f["properties"])},
                 "geometry": f["geometry"]} for f in r.json()["features"]]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    print(f"creato {OUT.relative_to(ROOT)}: {len(features)} paesi")


if __name__ == "__main__":
    main()