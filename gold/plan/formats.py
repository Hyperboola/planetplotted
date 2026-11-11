"""Calcolo dei numeri di ogni formato.

Funzioni "pure": ricevono le righe di un indicatore e restituiscono
il payload del post. Nessun valore viene stimato o interpolato:
si usano solo dati presenti nel database.
"""
import statistics
from collections import defaultdict

# Formati del carosello (e del loro reel)
CAROUSEL_FORMATS = {"ranked", "mapped", "globe", "then_vs_now", "world_in_one_chart", "the_gap"}


def reference_year(rows, current_year, max_age, min_share=0.6, min_countries=50,
                   min_vs_prev=0.85):
    """Ultimo anno "completo", non troppo vecchio.

    Un anno va bene se ha abbastanza paesi in assoluto (min_share della copertura
    massima, almeno min_countries) e se ha quasi tutti i paesi dell'anno prima
    (min_vs_prev): l'ultimo anno pubblicato è spesso a metà, e mancano proprio
    paesi grandi come gli Stati Uniti.
    Restituisce None se nessun anno va bene: l'indicatore viene saltato.
    """
    by_year = defaultdict(int)
    for r in rows:
        by_year[r["year"]] += 1
    if not by_year:
        return None
    needed = max(min_countries, int(max(by_year.values()) * min_share))
    for year in sorted(by_year, reverse=True):
        prev = by_year.get(year - 1, 0)
        if by_year[year] >= needed and by_year[year] >= prev * min_vs_prev:
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


def mapped(rows, current_year, max_age, population=None, min_population=0,
           bins=5, min_countries=120):
    """Mappa con l'ultimo dato disponibile per ogni paese, entro max_age anni.

    Non tutti i paesi pubblicano ogni anno: con un solo anno la mappa perde
    proprio i paesi grandi. Qui ogni paese ha il suo dato più recente, e la
    slide dichiara la finestra di anni usata.
    Le liste "highest e lowest" usano solo i paesi con almeno min_population
    abitanti: sulla mappa i microstati restano, nelle liste no.
    """
    oldest = current_year - max_age
    latest = {}
    for r in rows:
        if r["year"] >= oldest and (r["iso3"] not in latest or r["year"] > latest[r["iso3"]]["year"]):
            latest[r["iso3"]] = r
    data = sorted(latest.values(), key=lambda r: r["value"])
    n = len(data)
    if n < min_countries:
        return None
    # Classi a quantili: ogni classe ha circa lo stesso numero di paesi
    edges = [data[min(n - 1, (n * i) // bins)]["value"] for i in range(1, bins)]
    in_list = lambda r: population is None or population.get(r["iso3"], 0) >= min_population
    values = [{**_item(r), "year": r["year"], "in_list": in_list(r)} for r in data]
    return {
        "year": max(r["year"] for r in data),
        "year_from": min(r["year"] for r in data),
        "n_countries": n,
        "bins": edges,
        "values": values,
        "list_min_population": min_population,
        "n_list": sum(v["in_list"] for v in values),
    }


def then_vs_now(rows, year, unit="", population=None, min_population=0,
                gap_years=20, min_countries=50):
    """Confronta l'anno di riferimento con circa 20 anni prima,
    usando solo i paesi che hanno il dato in entrambi gli anni.

    - Il quadro generale (mediane, quanti sono saliti o scesi) usa tutti i paesi.
    - Le liste usano solo i paesi con almeno min_population abitanti.
    - "Invariato" vuol dire che la differenza non si vede una volta arrotondata:
      un paese fermo al 100% non è né salito né sceso.
    """
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
    tol = 0.05 if unit.startswith("%") else 1e-9
    moved = lambda x: abs(x["change"]) >= tol
    listed = [x for x in pairs if population is None
              or population.get(x["iso3"], 0) >= min_population]
    up = sorted((x for x in listed if moved(x) and x["change"] > 0),
                key=lambda x: x["change"], reverse=True)
    down = sorted((x for x in listed if moved(x) and x["change"] < 0),
                  key=lambda x: x["change"])
    return {
        "year": year,
        "base_year": base,
        "n_countries": len(pairs),
        "rose": sum(1 for x in pairs if moved(x) and x["change"] > 0),
        "fell": sum(1 for x in pairs if moved(x) and x["change"] < 0),
        "unchanged": sum(1 for x in pairs if not moved(x)),
        "median_then": statistics.median(x["then"] for x in pairs),
        "median_now": statistics.median(x["now"] for x in pairs),
        # I 10 cambiamenti più grandi, in su o in giù
        "movers": sorted((x for x in listed if moved(x)),
                         key=lambda x: abs(x["change"]), reverse=True)[:10],
        "risers": up[:5],
        "fallers": down[:5],
        "list_min_population": min_population,
    }


def world_in_one_chart(rows, year, top=15, max_missing=0.02, max_back=3):
    """Quota di ogni paese sul totale. Solo per indicatori sommabili
    (popolazione, PIL totale), mai per valori pro capite o percentuali.
    Il totale è la somma dei paesi con il dato, non un totale mondiale ufficiale.

    Le quote hanno senso solo se mancano pochi paesi: se quelli assenti
    pesavano più di max_missing del totale l'anno prima, si usa l'anno precedente.
    """
    for y in range(year, year - max_back - 1, -1):
        now = {r["iso3"]: r for r in _year_rows(rows, y)}
        before = {r["iso3"]: r["value"] for r in _year_rows(rows, y - 1)}
        if not now:
            continue
        missing = sum(v for iso3, v in before.items() if iso3 not in now)
        if not before or missing <= max_missing * sum(before.values()):
            break
    else:
        return None
    data = sorted(now.values(), key=lambda r: r["value"], reverse=True)
    total = sum(r["value"] for r in data)
    if total <= 0 or len(data) <= top:
        return None
    shares = [{**_item(r), "share": r["value"] / total} for r in data]
    # Quanti paesi servono per arrivare a metà del totale
    running, n_half = 0.0, 0
    for s in shares:
        running += s["share"]
        n_half += 1
        if running >= 0.5:
            break
    return {
        "year": y,
        "n_countries": len(data),
        "total": total,
        "shares": shares[:top],
        "rest_share": sum(s["share"] for s in shares[top:]),
        "rest_count": len(shares) - top,
        "top10_share": sum(s["share"] for s in shares[:10]),
        "n_to_half": n_half,
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


# Formati che si calcolano solo con righe e anno. Mapped, The Gap e
# Then vs Now hanno bisogno anche della popolazione: li chiama il plan.
BUILDERS = {
    "ranked": ranked,
    "world_in_one_chart": world_in_one_chart,
}
