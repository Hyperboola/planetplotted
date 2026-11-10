"""GOLD · COPY – scrive i testi dei post pianificati.

Il copy si salva con i {segnaposto}, non con i numeri: i numeri vengono
inseriti al momento del render. Così dall'admin si può riscrivere ogni
frase, ma i dati restano sempre quelli del payload.

Uso:
    python -m gold.copywriting.generate --date 2026-11-07
"""

import argparse
import datetime as dt
import json
import logging
import string

import yaml

from common import config, db
from gold.copywriting import values

log = logging.getLogger("gold.copy")
TEMPLATES_FILE = config.ROOT / "gold" / "copywriting" / "templates.yml"
HASHTAGS = {
    "economy": "#economy", "people": "#demographics", "technology": "#technology",
    "energy": "#energy", "education": "#education",
}


class CopyError(Exception):
    pass


def placeholders(text: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


def resolve(copy: dict, vals: dict) -> dict:
    """Sostituisce i segnaposto. Errore se un segnaposto non esiste:
    meglio fermarsi che pubblicare un testo rotto."""
    out = {}
    for key, text in copy.items():
        missing = placeholders(text) - vals.keys()
        if missing:
            raise CopyError(f"campo '{key}': segnaposto sconosciuti {sorted(missing)}")
        out[key] = text.format_map(vals)
    return out


def pick_template(templates: dict, fmt: str, vals: dict, post_id: int) -> dict:
    group = fmt
    if fmt == "the_gap":
        if "gap_points" in vals:
            group = "the_gap_points"   # percentuali: differenza in punti
        elif "ratio" not in vals:
            group = "the_gap_diff"     # valori negativi: niente rapporto
    variants = templates[group]
    return dict(variants[post_id % len(variants)])


def make_copy(templates, fmt, payload, post_id, topic) -> dict:
    vals = values.build(fmt, payload)
    copy = pick_template(templates, fmt, vals, post_id)
    tags = f"#data #dataviz #worlddata {HASHTAGS.get(topic, '')}".strip()
    copy["caption"] = copy["caption"].rstrip() + "\n\n" + tags
    resolve(copy, vals)  # verifica subito che tutti i segnaposto esistano
    return copy


def generate_day(day: dt.date) -> int:
    with open(TEMPLATES_FILE, encoding="utf-8") as f:
        templates = yaml.safe_load(f)
    conn = db.connect()
    done = 0
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""
                SELECT p.id, p.format, p.payload, i.topic
                FROM gold.post_queue p JOIN silver.indicators i ON i.id = p.indicator_id
                WHERE p.slot_at::date = %s AND p.status = 'planned' AND NOT p.copy_edited
                ORDER BY p.slot_at
            """, (day,))
            for post_id, fmt, payload, topic in cur.fetchall():
                copy = make_copy(templates, fmt, payload, post_id, topic)
                cur.execute("""
                    UPDATE gold.post_queue SET copy = %s, status = 'copy_ready', updated_at = now()
                    WHERE id = %s
                """, (json.dumps(copy, ensure_ascii=False), post_id))
                done += 1
                preview = resolve(copy, values.build(fmt, payload))
                log.info("post %s (%s): %s", post_id, fmt, preview["title"])
    finally:
        conn.close()
    return done


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True)
    a = p.parse_args()
    generate_day(dt.date.fromisoformat(a.date))


if __name__ == "__main__":
    main()
