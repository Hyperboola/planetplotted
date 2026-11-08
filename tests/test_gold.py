"""Test dello strato gold: regole dei formati e testi."""

import yaml

from gold.copywriting import numbers, values
from gold.copywriting.generate import TEMPLATES_FILE, make_copy, resolve
from gold.plan import formats


def rows(values_by_iso, year=2024):
    return [{"iso3": k, "name": k, "year": year, "value": v} for k, v in values_by_iso.items()]


def test_ties_are_computed_on_displayed_values():
    assert numbers.competition_ranks(["100.0%", "100.0%", "99.8%"]) == ["=1", "=1", "3"]


def test_small_values_are_not_shown_as_zero():
    assert numbers.fmt_value(0.046, "t CO2e per person") == "0.046"
    assert numbers.fmt_value(0.04, "% of GDP") == "0.04%"


def test_the_gap_uses_points_for_percentages_and_excludes_zeros_and_microstates():
    data = rows({"AAA": 34.2, "BBB": 0.13, "ZER": 0.0, "TIN": 50.0})
    pop = {"AAA": 2e6, "BBB": 3e6, "ZER": 5e6, "TIN": 10_000}
    p = formats.the_gap(data, 2024, "% of labor force", pop, 1_000_000)
    assert (p["highest"]["iso3"], p["lowest"]["iso3"]) == ("AAA", "BBB")
    assert p["ratio"] is None and p["points"] is True
    assert (p["excluded_zero"], p["excluded_small"]) == (1, 1)


def test_mapped_uses_latest_value_per_country_within_max_age():
    data = ([{"iso3": f"C{i}", "name": f"C{i}", "year": 2023, "value": float(i)} for i in range(130)]
            + [{"iso3": "OLD", "name": "OLD", "year": 2010, "value": 1.0},
               {"iso3": "C0", "name": "C0", "year": 2021, "value": 99.0}])
    p = formats.mapped(data, 2026, 5)
    by_iso = {v["iso3"]: v for v in p["values"]}
    assert "OLD" not in by_iso                    # più vecchio di max_age
    assert by_iso["C0"]["year"] == 2023           # vince il dato più recente
    assert formats.mapped(data[:50], 2026, 5) is None  # copertura insufficiente


def test_every_template_resolves():
    templates = yaml.safe_load(open(TEMPLATES_FILE, encoding="utf-8"))
    base = {"unit": "% of population", "year": 2024, "source": "worldbank",
            "indicator": "Internet users", "source_code": "IT.NET.USER.ZS", "n_countries": 150}
    payloads = {
        "ranked": {**base, "top": [{"iso3": "A", "name": "A", "value": 99.0}] * 10,
                   "bottom": [{"iso3": "B", "name": "B", "value": 9.0}] * 5,
                   "median": 70.0, "below_half": 30},
        "the_gap": {**base, "highest": {"iso3": "A", "name": "A", "value": 90.0},
                    "lowest": {"iso3": "B", "name": "B", "value": 10.0},
                    "difference": 80.0, "ratio": None, "points": True,
                    "excluded_zero": 0, "min_population": 1_000_000},
        "mapped": {**base, "bins": [1, 2, 3, 4], "list_min_population": 1_000_000,
                   "values": [{"iso3": "A", "name": "A", "value": 5.0, "in_list": True}]},
        "then_vs_now": {**base, "base_year": 2004,
                        "risers": [{"name": "A", "then": 1.0, "now": 90.0}],
                        "fallers": [{"name": "B", "then": 5.0, "now": 4.0}]},
        "world_in_one_chart": {**base, "shares": [{"name": n, "share": 0.2} for n in "ABC"]},
    }
    for fmt, p in payloads.items():
        for post_id in range(4):
            resolve(make_copy(templates, fmt, p, post_id, "technology"), values.build(fmt, p))
