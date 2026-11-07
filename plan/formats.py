"""Calcolo dei numeri di ogni formato.

Funzioni "pure": ricevono le righe di un indicatore e restituiscono
il payload del post. Nessun valore viene stimato o interpolato:
si usano solo dati presenti nel database.
"""
import statistics

from collections import defaultdict

FORMATS = {"ranked", "mapped", "then_vs_now", "world_in_one_chart", "the_gap"}


def reference_year(rows, current_year, max_age, min_share=0.6, min_countries=50):
    """Ultimo anno con abbastanza paesi e non troppo vecchio.

    rows: lista di dict con iso3, name, year, value.
    Restituisce None se nessun anno va bene: l'indicatore viene saltato.
    """
    by_year = defaultdict(int)
    for r in rows:
        by_year[r["year"]] += 1
    if not by_year:
        return None
    needed = max(min_countries, int(max(by_year.values()) * min_share))
    for year in sorted(by_year, reverse=True):
        if by_year[year] >= needed:
            return year if current_year - year <= max_age else None
    return None


def _year_rows(rows, year):
    return [r for r in rows if r["year"] == year]


def _item(r):
    return {"iso3": r["iso3"], "name": r["name"], "value": r["value"]}


def ranked(rows, year, top=10, bottom=5):
    data = sorted(_year_rows(rows, year), key=lambda r: r["value"], reverse=True)
    vals = [r["value"] for r in data]
    return {
        "year": year,
        "n_countries": len(data),
        "top": [_item(r) for r in data[:top]],
        "bottom": [_item(r) for r in data[-bottom:]],
        # Contesto per l'ultima slide, calcolato su tutti i paesi dell'anno
        "median": statistics.median(vals),
        "below_half": sum(1 for x in vals if x < 50),  # usato solo per le percentuali
    }


def mapped(rows, year, bins=5):
    data = sorted(_year_rows(rows, year), key=lambda r: r["value"])
    n = len(data)
    # Classi a quantili: ogni classe ha circa lo stesso numero di paesi
    edges = [data[min(n - 1, (n * i) // bins)]["value"] for i in range(1, bins)]
    return {
        "year": year,
        "n_countries": n,
        "bins": edges,
        "values": [_item(r) for r in data],
        "highlight": [_item(r) for r in data[::-1][:3]],
    }


def then_vs_now(rows, year, gap_years=20, min_countries=50):
    """Confronta l'anno di riferimento con circa 20 anni prima,
    usando solo i paesi che hanno il dato in entrambi gli anni."""
    now = {r["iso3"]: r for r in _year_rows(rows, year)}
    for base in range(year - gap_years, year - gap_years - 6, -1):
        then = {r["iso3"]: r for r in _year_rows(rows, base)}
        common = now.keys() & then.keys()
        if len(common) >= min_countries:
            break
    else:
        return None
    pairs = [
        {"iso3": c, "name": now[c]["name"], "then": then[c]["value"],
         "now": now[c]["value"], "change": now[c]["value"] - then[c]["value"]}
        for c in common
    ]
    by_change = sorted(pairs, key=lambda p: p["change"], reverse=True)
    return {
        "year": year,
        "base_year": base,
        "n_countries": len(pairs),
        "top_now": sorted(pairs, key=lambda p: p["now"], reverse=True)[:10],
        "risers": by_change[:5],
        "fallers": by_change[-5:][::-1],
    }


def world_in_one_chart(rows, year, top=15):
    """Quota di ogni paese sul totale. Solo per indicatori sommabili
    (popolazione, PIL totale), mai per valori pro capite o percentuali."""
    data = sorted(_year_rows(rows, year), key=lambda r: r["value"], reverse=True)
    total = sum(r["value"] for r in data)
    if total <= 0:
        return None
    shares = [{**_item(r), "share": r["value"] / total} for r in data]
    rest = sum(s["share"] for s in shares[top:])
    return {
        "year": year,
        "n_countries": len(data),
        "total": total,
        "total_note": "sum of countries with data, not an official world total",
        "shares": shares[:top],
        "rest_share": rest,
    }


def the_gap(rows, year, unit="", population=None, min_population=0):
    """Il più alto e il più basso, con regole contro gli estremi fuorvianti:
    - i valori esattamente zero sono esclusi (spesso sono dati mancanti);
    - con population, restano solo i paesi con almeno min_population abitanti,
      perché nei microstati i valori pro capite sono instabili;
    - per le percentuali niente rapporto: si usa la differenza in punti."""
    data = _year_rows(rows, year)
    zeros = sum(1 for r in data if r["value"] == 0)
    data = [r for r in data if r["value"] != 0]
    small = 0
    if population is not None and min_population:
        keep = [r for r in data if population.get(r["iso3"], 0) >= min_population]
        small, data = len(data) - len(keep), keep
    if len(data) < 2:
        return None
    data.sort(key=lambda r: r["value"], reverse=True)
    hi, lo = data[0], data[-1]
    points = unit.startswith("%")
    ratio = None
    if not points and hi["value"] > 0 and lo["value"] > 0:
        ratio = hi["value"] / lo["value"]
    return {
        "year": year,
        "n_countries": len(data),
        "highest": _item(hi),
        "lowest": _item(lo),
        "difference": hi["value"] - lo["value"],
        "ratio": ratio,          # None per le percentuali o con valori negativi
        "points": points,        # True: il divario si esprime in punti percentuali
        "excluded_zero": zeros,
        "excluded_small": small,
        "min_population": min_population,
    }


BUILDERS = {
    "ranked": ranked,
    "mapped": mapped,
    "then_vs_now": then_vs_now,
    "world_in_one_chart": world_in_one_chart,
    "the_gap": the_gap,
}