"""Testi e disegno: ogni modello funziona, ogni etichetta sta nel suo riquadro."""

import yaml

from gold.copywriting import values
from gold.copywriting.generate import TEMPLATES_FILE, make_copy, resolve
from serving.render.carousel import _fit_label, bar_max
from serving.render.treemap import squarify

BASE = {"unit": "% of population", "year": 2024, "source": "worldbank",
        "indicator": "Internet users", "source_code": "IT.NET.USER.ZS", "n_countries": 150}
PAYLOADS = {
    "ranked": {**BASE, "top": [{"iso3": "A", "name": "A", "value": 99.0}] * 10,
               "bottom": [{"iso3": "B", "name": "B", "value": 9.0}] * 5,
               "median": 70.0, "below_half": 30},
    "the_gap": {**BASE, "highest": {"iso3": "A", "name": "A", "value": 90.0},
                "lowest": {"iso3": "B", "name": "B", "value": 10.0},
                "difference": 80.0, "ratio": None, "points": True,
                "excluded_zero": 0, "min_population": 1_000_000},
    "mapped": {**BASE, "bins": [1, 2, 3, 4], "list_min_population": 1_000_000,
               "values": [{"iso3": "A", "name": "A", "value": 5.0, "in_list": True}]},
    "globe": {**BASE, "bins": [1, 2, 3, 4], "list_min_population": 1_000_000,
              "values": [{"iso3": "USA", "name": "United States", "value": 5.0, "in_list": True,
                          "region": "North America"}]},
    "then_vs_now": {**BASE, "base_year": 2004, "rose": 140, "fell": 5, "unchanged": 5,
                    "median_then": 20.0, "median_now": 80.0, "list_min_population": 1_000_000,
                    "movers": [{"name": "A", "then": 1.0, "now": 90.0, "change": 89.0}],
                    "risers": [{"name": "A", "then": 1.0, "now": 90.0, "change": 89.0}],
                    "fallers": [{"name": "B", "then": 5.0, "now": 4.0, "change": -1.0}]},
    "world_in_one_chart": {**BASE, "unit": "people", "total": 8e9, "top10_share": 0.6,
                           "n_to_half": 8, "rest_share": 0.3, "rest_count": 100,
                           "shares": [{"iso3": n, "name": n, "value": 1e8, "share": 0.2}
                                      for n in "ABC"]},
}


def test_every_template_resolves():
    templates = yaml.safe_load(open(TEMPLATES_FILE, encoding="utf-8"))
    for fmt, p in PAYLOADS.items():
        for post_id in range(4):
            resolve(make_copy(templates, fmt, p, post_id, "technology"), values.build(fmt, p))


def test_treemap_areas_are_proportional():
    rects = squarify([50, 30, 20], 0, 0, 100, 100)
    areas = [w * h for _, _, w, h in rects]
    assert [round(a) for a in areas] == [5000, 3000, 2000]


def test_labels_fit_or_are_skipped():
    size, lines = _fit_label("Netherlands", 120, 80, 40)
    assert size < 40 and lines == ["Netherlands"]
    assert _fit_label("Netherlands", 20, 10, 40) is None


def test_bars_use_100_only_for_shares():
    assert bar_max("% of population", [99, 8]) == 100.0
    assert bar_max("% per year", [4.7, -4.7]) == 4.7


def test_globe_carousel_shows_three_sides_of_the_world():
    from serving.render import carousel

    templates = yaml.safe_load(open(TEMPLATES_FILE, encoding="utf-8"))
    p = PAYLOADS["globe"]
    v = values.build("globe", p)
    slides = carousel.globe(resolve(make_copy(templates, "globe", p, 0, "education"), v), v, p)
    assert len(slides) == 4                       # tre emisferi e la chiusura
