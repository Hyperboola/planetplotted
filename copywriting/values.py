"""Dal payload ai valori usati nei testi.

Ogni valore è già formattato come stringa: i template possono usare
solo questi segnaposto, quindi i numeri non si possono cambiare a mano.
"""

from copywriting import numbers as n


def _lc(name: str) -> str:
    # "Life expectancy" -> "life expectancy", ma "GDP per capita" resta così
    return name[0].lower() + name[1:] if len(name) > 1 and name[1].islower() else name


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

    if fmt == "ranked":
        top_disp = [f(r["value"]) for r in p["top"]]
        ranks = n.competition_ranks(top_disp)
        leaders = [r["name"] for r, k in zip(p["top"], ranks) if k in ("1", "=1")]
        v.update({
            "top1_name": leaders[0],
            "top1_value": top_disp[0],
            "top1_label": (leaders[0] if len(leaders) == 1 else
                           f"{n.join_names(leaders)} (tied)"),
            "last_name": p["bottom"][-1]["name"],
            "last_value": f(p["bottom"][-1]["value"]),
        })
        v["_rows_top"] = [{"rank": k, "name": r["name"], "value": d}
                          for r, k, d in zip(p["top"], ranks, top_disp)]
        bot_disp = [f(r["value"]) for r in p["bottom"]]
        first = p["n_countries"] - len(p["bottom"]) + 1
        v["_rows_bottom"] = [{"rank": k, "name": r["name"], "value": d} for r, k, d in
                             zip(p["bottom"], n.competition_ranks(bot_disp, first), bot_disp)]

    elif fmt == "the_gap":
        v.update({
            "highest": p["highest"]["name"], "highest_value": f(p["highest"]["value"]),
            "lowest": p["lowest"]["name"], "lowest_value": f(p["lowest"]["value"]),
            "highest_exact": f(p["highest"]["value"], True),
            "lowest_exact": f(p["lowest"]["value"], True),
            "difference": f(p["difference"]),
        })
        if p.get("ratio"):
            v["ratio"] = n.fmt_ratio(p["ratio"])

    elif fmt == "mapped":
        h = p["highlight"]
        v.update({"top1_name": h[0]["name"], "top1_value": f(h[0]["value"]),
                  "top3_names": n.join_names([x["name"] for x in h])})

    elif fmt == "then_vs_now":
        r, d = p["risers"][0], p["fallers"][0]
        v.update({"base_year": str(p["base_year"]),
                  "riser_name": r["name"], "riser_then": f(r["then"]), "riser_now": f(r["now"]),
                  "faller_name": d["name"], "faller_then": f(d["then"]), "faller_now": f(d["now"])})

    elif fmt == "world_in_one_chart":
        s = p["shares"]
        top3 = sum(x["share"] for x in s[:3])
        v.update({"top1_name": s[0]["name"], "top1_share": n.fmt_share(s[0]["share"]),
                  "top3_names": n.join_names([x["name"] for x in s[:3]]),
                  "top3_share": n.fmt_share(top3)})
    return v