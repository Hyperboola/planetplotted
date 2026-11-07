"""Controlla il catalogo contro l'API World Bank, prima di usarlo.

Per ogni indicatore verifica che il codice esista e quanto sono recenti
e completi i dati. Non scrive nulla: stampa solo un resoconto.

Uso:
    python -m sources.check_catalog
"""

import datetime as dt
from collections import Counter

import requests

from common import catalog

API = "https://api.worldbank.org/v2"


def check(item: dict) -> tuple[str, str]:
    r = requests.get(f"{API}/indicator/{item['code']}", params={"format": "json"}, timeout=60)
    body = r.json()
    if not isinstance(body, list) or len(body) < 2 or not body[1]:
        return "ERRORE", "codice non trovato"
    # Valore più recente non vuoto per ogni paese (include anche gli aggregati)
    r = requests.get(f"{API}/country/all/indicator/{item['code']}",
                     params={"format": "json", "mrnev": 1, "per_page": 500}, timeout=60)
    rows = r.json()[1] or []
    years = Counter(int(x["date"]) for x in rows if x.get("value") is not None)
    if not years:
        return "ERRORE", "nessun dato"
    # Anno utilizzabile: il più recente in cui almeno il 60% dei paesi ha già
    # un dato, come fa il plan. Un anno con 2 paesi non basta per un post.
    total, covered, usable = sum(years.values()), 0, None
    for year in sorted(years, reverse=True):
        covered += years[year]
        if covered >= total * 0.6:
            usable = year
            break
    age = dt.date.today().year - usable
    detail = (f"anno utilizzabile {usable} (età {age}, max {item['max_age']}) · "
              f"ultimo {max(years)} con {years[max(years)]} paesi · totale {total}")
    return ("OK" if age <= item["max_age"] else "VECCHIO"), detail


def main():
    problems = 0
    for item in catalog.load("worldbank"):
        try:
            status, detail = check(item)
        except Exception as exc:  # rete o risposta non valida
            status, detail = "ERRORE", str(exc)
        problems += status != "OK"
        print(f"{status:8} {item['id']:24} {item['code']:24} {detail}")
    print(f"\n{problems} indicatori da controllare")


if __name__ == "__main__":
    main()