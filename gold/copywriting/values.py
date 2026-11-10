"""Dal payload ai valori usati nei testi.

Ogni valore è già formattato come stringa: i template possono usare
solo questi segnaposto, quindi i numeri non si possono cambiare a mano.
"""

from gold.copywriting import numbers as n


def _lc(name: str) -> str:
    # "Life expectancy" -> "life expectancy", ma "GDP per capita" resta così
    return name[0].lower() + name[1:] if len(name) > 1 and name[1].islower() else name


def _ranked_context(p, f) -> str:
    """Una frase di contesto calcolata sui dati.

    Se l'indicatore ha una frase nel catalogo (below_half_phrase), conta
    quanti paesi sono sotto il 50%; altrimenti indica il valore mediano.
    Vuota se il payload è stato creato prima che il plan calcolasse questi valori.
    """
    places = f"{p['n_countries']} countries and territories"
    phrase, below = p.get("below_half_phrase"), p.get("below_half")
    if phrase and below:
        return f"In {below} of {places}, {phrase}."
    if p.get("median") is not None:
        return f"The middle of {places} (median): {f(p['median'])}."
    return ""


def build(fmt: str, p: dict) -> dict:
    unit = p["unit"]
    v = {
        "indicator": p["indicator"],
        "indicator_lc": _lc(p["indicator"]),
        "unit": unit,
        "year": str(p["year"]),
        "n_countries": str(p["n_countries"]),
        "source_code": p["source_code"],
        "source_name": "World Bank" if p["source"] == "worldbank" else p["source"],
    }
    f = lambda x, exact=False: n.fmt_value(x, unit, exact)
    fu = lambda x: n.with_unit(f(x), unit)  # per i testi: numero con unità

    if fmt == "ranked":
        top_disp = [f(r["value"]) for r in p["top"]]
        ranks = n.competition_ranks(top_disp)
        leaders = [r["name"] for r, k in zip(p["top"], ranks) if k in ("1", "=1")]
        v.update({
            "top1_name": leaders[0],
            "top1_value": n.with_unit(top_disp[0], unit),
            "top1_label": (leaders[0] if len(leaders) == 1 else
                           f"{n.join_names(leaders)} (tied)"),
        })
        bot_disp = [f(r["value"]) for r in p["bottom"]]
        # Pari merito anche in fondo: "Oman, Tuvalu and Yemen (tied)"
        lasts = [r["name"] for r, d in zip(p["bottom"], bot_disp) if d == bot_disp[-1]]
        v.update({
            "last_name": lasts[0] if len(lasts) == 1 else f"{n.join_names(lasts)} (tied)",
            "last_value": n.with_unit(bot_disp[-1], unit),
        })
        v["context_line"] = _ranked_context(p, fu)
        v["_rows_top"] = [{"rank": k, "name": r["name"], "value": d}
                          for r, k, d in zip(p["top"], ranks, top_disp)]
        first = p["n_countries"] - len(p["bottom"]) + 1
        v["_rows_bottom"] = [{"rank": k, "name": r["name"], "value": d} for r, k, d in
                             zip(p["bottom"], n.competition_ranks(bot_disp, first), bot_disp)]

    elif fmt == "the_gap":
        v.update({
            "highest": p["highest"]["name"], "highest_value": fu(p["highest"]["value"]),
            "lowest": p["lowest"]["name"], "lowest_value": fu(p["lowest"]["value"]),
            "highest_exact": f(p["highest"]["value"], True),
            "lowest_exact": f(p["lowest"]["value"], True),
            "difference": f(p["difference"]),
        })
        if p.get("ratio"):
            v["ratio"] = n.fmt_ratio(p["ratio"])
        if p.get("points"):
            pts = abs(p["difference"])
            v["gap_points"] = f"{pts:.1f} percentage points"
            v["gap_points_short"] = f"{pts:.1f}-point"
        # Il numero grande della slide: rapporto, punti o differenza
        v["gap_big"] = (v.get("ratio") or
                        (f"{abs(p['difference']):.1f} pts" if p.get("points") else v["difference"]))
        notes = []
        if p.get("min_population"):
            notes.append(f"Countries and territories with {n.fmt_count(p['min_population'])}+ people")
        if p.get("excluded_zero"):
            notes.append("zero values excluded")
        v["scope_note"] = ", ".join(notes) or f"All {p['n_countries']} countries and territories with data"

    elif fmt == "mapped":
        # La mappa usa l'ultimo dato di ogni paese: l'anno diventa una finestra
        if p.get("year_from") and p["year_from"] != p["year"]:
            v["year"] = f"{p['year_from']}–{p['year']}"
        # Le liste usano solo i paesi sopra la soglia di popolazione
        listed = [r for r in p["values"] if r.get("in_list", True)]
        v["n_list"] = str(len(listed))
        v["list_note"] = (f"countries and territories with {n.fmt_count(p['list_min_population'])}+ people"
                          if p.get("list_min_population") else "countries and territories")
        # Stesso ordine della slide: valore decrescente, poi nome (pari merito stabili)
        ordered = sorted(listed, key=lambda r: (-r["value"], r["name"]))
        disp = [f(r["value"]) for r in ordered]
        ranks = n.competition_ranks(disp)
        rank_num = [int(k.lstrip("=")) for k in ranks]
        firsts = [r["name"] for r, k in zip(ordered, rank_num) if k == 1]
        leaders = [r["name"] for r, k in zip(ordered, rank_num) if k <= 3]
        v.update({
            "top1_name": firsts[0] if len(firsts) == 1 else f"{n.join_names(firsts)} (tied)",
            "top1_value": n.with_unit(disp[0], unit),
            # Se più di 3 paesi sono a pari merito in cima, li nomina tutti
            "top3_names": n.join_names(leaders) + (
                f" (tied at {disp[0]})" if len(leaders) > 3 else ""),
        })

    elif fmt == "then_vs_now":
        pct = unit.startswith("%")

        def change(x):
            """+12.3 pts per le percentuali, +1.2 million people per i valori assoluti."""
            sign = "+" if x > 0 else ("−" if x < 0 else "")
            body = f"{abs(x):.1f} pts" if pct else n.with_unit(f(abs(x)), unit)
            return sign + body

        places = f"{p['n_countries']} countries and territories"
        trend = f"Up in {p['rose']} of {places}, down in {p['fell']}"
        if p["unchanged"]:
            trend += f", unchanged in {p['unchanged']}"
        m = p["movers"][0] if p["movers"] else None
        v.update({
            "base_year": str(p["base_year"]),
            "trend_line": trend + ".",
            "median_then": fu(p["median_then"]),
            "median_now": fu(p["median_now"]),
            "mover_name": m["name"] if m else "",
            "mover_then": fu(m["then"]) if m else "",
            "mover_now": fu(m["now"]) if m else "",
            "mover_change": change(m["change"]) if m else "",
        })
        row = lambda x: {"name": x["name"], "then": f(x["then"]), "now": f(x["now"]),
                         "change": change(x["change"]), "raw_change": x["change"]}
        v["min_population"] = n.fmt_count(p.get("list_min_population") or 0)
        v["_movers"] = [row(x) for x in p["movers"]]
        v["_risers"] = [row(x) for x in p["risers"]]
        v["_fallers"] = [row(x) for x in p["fallers"]]
        v["list_note"] = (f"countries and territories with {n.fmt_count(p['list_min_population'])}+ people"
                          if p.get("list_min_population") else "countries and territories")

    elif fmt == "world_in_one_chart":
        sh = p["shares"]
        top3 = sum(x["share"] for x in sh[:3])
        v.update({
            "top1_name": sh[0]["name"], "top1_share": n.fmt_share(sh[0]["share"]),
            "top3_names": n.join_names([x["name"] for x in sh[:3]]),
            "top3_share": n.fmt_share(top3),
            "top10_share": n.fmt_share(p["top10_share"]),
            "n_to_half": str(p["n_to_half"]),
            "n_to_half_label": ("1 country" if p["n_to_half"] == 1
                                else f"{p['n_to_half']} countries"),
            "total": fu(p["total"]),
        })
        v["_shares"] = [{"name": x["name"], "share": n.fmt_share(x["share"]),
                         "value": fu(x["value"])} for x in sh]
    return v