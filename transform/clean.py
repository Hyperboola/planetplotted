"""TRANSFORM – legge il raw, pulisce i dati e li carica nel database.

Uso:
    python -m transform.clean --run-date 2026-11-06
    python -m transform.clean --run-date 2026-11-06 --indicator population
"""

import argparse
import collections
import logging

import yaml

from common import catalog, config, storage
from transform import checks

log = logging.getLogger("transform")
NAMES_FILE = config.ROOT / "catalog" / "country_names.yml"


def load_display_names() -> dict:
    """Nomi comuni da mostrare (South Korea invece di Korea, Rep.)."""
    with open(NAMES_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# --- Parte "pura": nessun database, facile da testare ----------------------

def clean_countries(raw: list[dict], display: dict | None = None) -> list[dict]:
    """Tiene solo i paesi veri: la World Bank segna gli aggregati
    (World, High income, Euro area…) con la regione 'Aggregates'.
    display: nomi da mostrare per iso3; gli altri paesi usano il nome ufficiale."""
    out = []
    for c in raw:
        region = (c.get("region") or {}).get("value", "")
        iso3 = c.get("id", "")
        if region == "Aggregates" or len(iso3) != 3:
            continue
        name = c.get("name", "").strip()
        out.append({
            "iso3": iso3,
            "name": name,
            "display_name": (display or {}).get(iso3, name),
            "region": region.strip() or None,
            "income": ((c.get("incomeLevel") or {}).get("value") or "").strip() or None,
        })
    return out


def clean_worldbank_rows(raw: list[dict], valid_iso3: set[str]) -> tuple[list[dict], dict]:
    """Converte le righe dell'API nel formato lungo e conta gli scarti."""
    rows, dropped = [], collections.Counter()
    for r in raw:
        row = {
            "iso3": r.get("countryiso3code"),
            "year": r.get("date"),
            "value": r.get("value"),
        }
        problem = checks.row_problem(row, valid_iso3)
        if problem:
            dropped[problem] += 1
            continue
        rows.append({"iso3": row["iso3"], "year": int(row["year"]),
                     "value": float(row["value"])})
    return rows, dict(dropped)


# --- Caricamento nel database -------------------------------------------------

def _connect():
    import psycopg2

    return psycopg2.connect(config.PG_DSN)


def load_countries(conn, countries: list[dict]) -> None:
    from psycopg2.extras import execute_values

    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO countries (iso3, name, region, income, display_name) VALUES %s
            ON CONFLICT (iso3) DO UPDATE SET name = EXCLUDED.name,
                region = EXCLUDED.region, income = EXCLUDED.income,
                display_name = EXCLUDED.display_name, updated_at = now()
        """, [(c["iso3"], c["name"], c["region"], c["income"], c["display_name"])
              for c in countries])


def load_indicator(conn, item: dict, rows: list[dict], run_date: str) -> None:
    from psycopg2.extras import execute_values

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO indicators (id, source, code, name, unit, topic, max_age)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET source = EXCLUDED.source,
                code = EXCLUDED.code, name = EXCLUDED.name, unit = EXCLUDED.unit,
                topic = EXCLUDED.topic, max_age = EXCLUDED.max_age, updated_at = now()
        """, (item["id"], item["source"], item["code"], item["name"],
              item["unit"], item["topic"], item["max_age"]))
        execute_values(cur, """
            INSERT INTO observations (indicator_id, iso3, year, value, source, run_date)
            VALUES %s
            ON CONFLICT (indicator_id, iso3, year) DO UPDATE SET
                value = EXCLUDED.value, source = EXCLUDED.source,
                run_date = EXCLUDED.run_date, loaded_at = now()
        """, [(item["id"], r["iso3"], r["year"], r["value"], item["source"], run_date)
              for r in rows])


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--run-date", required=True)
    p.add_argument("--indicator")
    a = p.parse_args()

    countries = clean_countries(
        storage.read_json(storage.raw_key("worldbank", "countries", a.run_date)),
        load_display_names())
    valid = {c["iso3"] for c in countries}
    items = [catalog.get(a.indicator)] if a.indicator else catalog.load("worldbank")

    conn = _connect()
    try:
        with conn:  # una transazione: o si carica tutto o niente
            load_countries(conn, countries)
            for item in items:
                raw = storage.read_json(storage.raw_key("worldbank", item["id"], a.run_date))
                rows, dropped = clean_worldbank_rows(raw, valid)
                checks.check_dataset(rows, item["id"])
                load_indicator(conn, item, rows, a.run_date)
                log.info("%s: %s righe caricate, scartate %s", item["id"], len(rows), dropped)
    finally:
        conn.close()


if __name__ == "__main__":
    main()