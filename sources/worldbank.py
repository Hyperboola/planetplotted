"""EXTRACT – World Bank Open Data.

Scarica i dati così come sono e li salva nel raw, senza modificarli.
Uso:
    python -m sources.worldbank --run-date 2026-11-06
    python -m sources.worldbank --run-date 2026-11-06 --indicator population
"""

import argparse
import logging
import time

import requests

from common import catalog, config, storage

API = "https://api.worldbank.org/v2"
SOURCE = "worldbank"
log = logging.getLogger(SOURCE)


def _get_all_pages(url: str, params: dict) -> list:
    """Scarica tutte le pagine di una risposta dell'API World Bank."""
    rows, page = [], 1
    while True:
        for attempt in range(3):
            try:
                r = requests.get(url, params={**params, "page": page}, timeout=60)
                r.raise_for_status()
                body = r.json()
                break
            except Exception as exc:  # rete o risposta non valida
                if attempt == 2:
                    raise
                log.warning("Tentativo %s fallito: %s", attempt + 1, exc)
                time.sleep(5 * (attempt + 1))
        if not isinstance(body, list) or len(body) < 2:
            # L'API risponde con un messaggio di errore invece dei dati
            raise RuntimeError(f"Risposta inattesa da {url}: {body}")
        meta, data = body[0], body[1] or []
        rows.extend(data)
        if page >= int(meta.get("pages", 1)):
            return rows
        page += 1


def extract_countries(run_date: str) -> str:
    """Anagrafica paesi: serve a distinguere i paesi dagli aggregati."""
    rows = _get_all_pages(f"{API}/country", {"format": "json", "per_page": 400})
    return storage.write_json(storage.raw_key(SOURCE, "countries", run_date), rows)


def extract_indicator(item: dict, run_date: str) -> str:
    rows = _get_all_pages(
        f"{API}/country/all/indicator/{item['code']}",
        {
            "format": "json",
            "per_page": 20000,
            "date": f"{config.YEAR_FROM}:{config.YEAR_TO}",
        },
    )
    key = storage.raw_key(SOURCE, item["id"], run_date)
    return storage.write_json(key, rows)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--run-date", required=True)
    p.add_argument("--indicator", help="id del catalogo; senza, scarica tutti")
    p.add_argument("--countries", action="store_true", help="solo l'anagrafica paesi")
    a = p.parse_args()

    if a.countries:
        log.info("Paesi salvati in %s", extract_countries(a.run_date))
        return
    items = [catalog.get(a.indicator)] if a.indicator else catalog.load(SOURCE)
    for item in items:
        log.info("%s salvato in %s", item["id"], extract_indicator(item, a.run_date))


if __name__ == "__main__":
    main()
