"""Formati solo per i reel, basati sulla serie storica (circa 30 anni).

Regole contro le invenzioni:
- nessun valore viene stimato: un paese senza il dato in un anno, quell'anno
  semplicemente non c'è (esce dalla gara, resta grigio sulla mappa);
- la serie parte dal primo anno con abbastanza paesi, non da un anno vuoto;
- le liste e le gare usano solo i paesi con almeno min_population abitanti,
  tranne la classifica completa ("find your country"), che li mostra tutti.
"""

from collections import defaultdict

REEL_FORMATS = {"bar_race", "line_race", "duel", "scroll_ranking"}


def _by_year(rows):
    out = defaultdict(dict)
    for r in rows:
        out[r["year"]][r["iso3"]] = r
    return out


def _years(by_year, ref_year, span=30, min_countries=50):
    """Anni dalla prima annata con abbastanza paesi (al massimo span anni fa) a ref_year."""
    for y in range(ref_year - span, ref_year + 1):
        if len(by_year.get(y, {})) >= min_countries:
            return list(range(y, ref_year + 1))
    return []


def _big(population, min_population):
    return lambda iso3: population is None or population.get(iso3, 0) >= min_population


def bar_race(rows, ref_year, population=None, min_population=0, top=12, max_volatility=3.5):
    by_year = _by_year(rows)
    years = _years(by_year, ref_year)
    if len(years) < 10:
        return None
    big = _big(population, min_population)
    frames = []
    for y in years:
        data = sorted((r for iso3, r in by_year.get(y, {}).items() if big(iso3)),
                      key=lambda r: r["value"], reverse=True)[:top]
        frames.append({"year": y, "top": [{"iso3": r["iso3"], "name": r["name"],
                                           "value": r["value"]} for r in data]})
    leaders = [f["top"][0]["name"] for f in frames if f["top"]]
    # Quanti paesi cambiano posizione nella top 8, in media, da un anno all'altro.
    # Gli indicatori "nervosi" (tassi di crescita, inflazione) fanno una gara illeggibile.
    moves = []
    for a, b in zip(frames, frames[1:]):
        ra = {r["iso3"]: k for k, r in enumerate(a["top"][:8])}
        rb = {r["iso3"]: k for k, r in enumerate(b["top"][:8])}
        moves.append(sum(1 for iso3 in ra.keys() | rb.keys() if ra.get(iso3) != rb.get(iso3)))
    volatility = sum(moves) / len(moves)
    if volatility > max_volatility:
        return None
    return {"year": ref_year, "start_year": years[0], "frames": frames,
            "volatility": round(volatility, 2),
            "n_countries": len(by_year[ref_year]),
            "n_leaders": len(set(leaders)), "list_min_population": min_population}


def line_race(rows, ref_year, population=None, min_population=0, n=6, min_cover=0.8):
    by_year = _by_year(rows)
    years = _years(by_year, ref_year)
    if len(years) < 10:
        return None
    big = _big(population, min_population)
    ranked = sorted((r for iso3, r in by_year[ref_year].items() if big(iso3)),
                    key=lambda r: r["value"], reverse=True)
    series = []
    for r in ranked:   # i più alti oggi, purché abbiano quasi tutta la serie
        values = [by_year.get(y, {}).get(r["iso3"], {}).get("value") for y in years]
        if sum(v is not None for v in values) >= min_cover * len(years):
            series.append({"iso3": r["iso3"], "name": r["name"], "values": values})
        if len(series) == n:
            break
    if len(series) < 3:
        return None
    return {"year": ref_year, "start_year": years[0], "years": years, "series": series,
            "n_countries": len(by_year[ref_year]), "list_min_population": min_population}


def duel(rows, ref_year, population=None, min_population=0, candidates=10, min_cover=0.9):
    """Due paesi nel tempo. Preferisce una coppia che si è sorpassata (la storia
    più interessante), la più recente; altrimenti i primi due di oggi.
    Un anno senza dato resta vuoto (la linea si interrompe), mai stimato."""
    by_year = _by_year(rows)
    years = _years(by_year, ref_year)
    if len(years) < 10:
        return None
    big = _big(population, min_population)
    serie = lambda iso3: [by_year.get(y, {}).get(iso3, {}).get("value") for y in years]
    top = sorted((r for iso3, r in by_year[ref_year].items() if big(iso3)),
                 key=lambda r: r["value"], reverse=True)[:candidates]
    full = [r for r in top
            if sum(v is not None for v in serie(r["iso3"])) >= min_cover * len(years)]
    if len(full) < 2:
        return None
    best = None
    for i, a in enumerate(full):
        for b in full[i + 1:]:
            pairs = [(y, x - z) for y, x, z in zip(years, serie(a["iso3"]), serie(b["iso3"]))
                     if x is not None and z is not None]
            crossings, prev = [], 0.0
            for year, d in pairs:              # un pareggio esatto non è ancora un sorpasso
                if d != 0:
                    if prev * d < 0:
                        crossings.append(year)
                    prev = d
            if crossings and (best is None or crossings[-1] > best[2]):
                best = (a, b, crossings[-1])
    a, b, overtake = best if best else (full[0], full[1], None)
    return {"year": ref_year, "start_year": years[0], "years": years,
            "n_countries": len(by_year[ref_year]),
            "a": {"iso3": a["iso3"], "name": a["name"], "values": serie(a["iso3"])},
            "b": {"iso3": b["iso3"], "name": b["name"], "values": serie(b["iso3"])},
            "overtake_year": overtake}


def scroll_ranking(rows, ref_year):
    """La classifica completa: tutti i paesi, anche i più piccoli."""
    data = sorted((r for r in rows if r["year"] == ref_year), key=lambda r: r["value"],
                  reverse=True)
    if len(data) < 50:
        return None
    return {"year": ref_year, "n_countries": len(data),
            "rows": [{"iso3": r["iso3"], "name": r["name"], "value": r["value"]} for r in data]}
