"""Prepara il font Manrope per il render.

Manrope è distribuito come font "variabile" (tutti i pesi in un file),
che matplotlib non gestisce bene. Questo script lo scarica una volta
e ne ricava tre file statici: Regular, SemiBold ed ExtraBold.

Uso (una sola volta):
    python -m render.setup_fonts
"""

import io
from pathlib import Path

import requests
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "brand" / "fonts"
BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/"
VARIABLE_URL = BASE + "Manrope%5Bwght%5D.ttf"
LICENSE_URL = BASE + "OFL.txt"
WEIGHTS = {"Regular": 400, "SemiBold": 600, "ExtraBold": 800}


def main():
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    data = requests.get(VARIABLE_URL, timeout=60)
    data.raise_for_status()
    for style, weight in WEIGHTS.items():
        font = TTFont(io.BytesIO(data.content))
        static = instantiateVariableFont(font, {"wght": weight}, updateFontNames=True)
        out = FONT_DIR / f"Manrope-{style}.ttf"
        static.save(out)
        print("creato", out.relative_to(ROOT))
    lic = requests.get(LICENSE_URL, timeout=60)
    if lic.ok:  # la licenza OFL va tenuta insieme al font
        (FONT_DIR / "OFL.txt").write_text(lic.text, encoding="utf-8")
        print("creato", (FONT_DIR / "OFL.txt").relative_to(ROOT))


if __name__ == "__main__":
    main()