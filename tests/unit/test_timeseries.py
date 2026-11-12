"""Formati solo reel: regole sulla serie storica e scene dei video."""

import pytest
import yaml

from gold.copywriting import values
from gold.copywriting.generate import TEMPLATES_FILE, make_copy, resolve
from gold.plan import timeseries as ts
from serving.render import reel
from serving.render.base import REEL, Slide

YEARS = range(1995, 2025)
ISOS = [f"C{i:02d}" for i in range(120)]


def rows(value=lambda k, y: 10 + k + (y - 1995), skip=()):
    return [{"iso3": c, "name": f"Country {c}", "year": y, "value": value(k, y)}
            for k, c in enumerate(ISOS) for y in YEARS if (c, y) not in skip]


def test_bar_race_never_estimates_a_missing_year():
    data = rows(skip={("C119", 2010)})            # il primo della classifica manca nel 2010
    p = ts.bar_race(data, 2024)
    frame_2010 = next(f for f in p["frames"] if f["year"] == 2010)
    assert "C119" not in {r["iso3"] for r in frame_2010["top"]}
    assert p["frames"][-1]["top"][0]["iso3"] == "C119"


def test_smooth_lines_pass_through_the_real_values_and_break_on_gaps():
    from serving.render.reel import _smooth

    curves = _smooth([10.0, 12.0, None, 20.0, 21.0, 25.0])
    assert len(curves) == 2                       # anno mancante: due tratti separati
    for ts_, vs in curves:
        for year, value in ((0, 10.0), (1, 12.0), (3, 20.0), (4, 21.0), (5, 25.0)):
            hit = (ts_ == year)
            if hit.any():
                assert abs(vs[hit][0] - value) < 1e-9
    # cubica monotona: tra due anni in salita la curva non scende mai
    ts_, vs = curves[1]
    assert all(b >= a - 1e-9 for a, b in zip(vs, vs[1:]))


RIVALRIES = [["C00", "C01"], ["C02", "C03"], ["C04", "C05"]]


def test_duel_prefers_a_famous_pair_that_overtook():
    def value(k, y):
        if k == 2:
            return 105 + 10 * (y - 1995)         # C02 sorpassa C03 nel 2005
        if k == 3:
            return 200.0
        return 50.0 + k                          # le altre coppie non si incrociano mai
    p = ts.duel(rows(value), 2024, RIVALRIES)
    assert {p["a"]["iso3"], p["b"]["iso3"]} == {"C02", "C03"}
    assert p["overtake_year"] == 2005


def test_a_tie_is_not_an_overtake_until_one_is_ahead():
    def value(k, y):
        if k == 0:
            return 100 + 10 * (y - 1995)         # pari nel 2005, davanti dal 2006
        if k == 1:
            return 200.0
        return 50.0 + k
    assert ts.duel(rows(value), 2024, RIVALRIES)["overtake_year"] == 2006


def test_without_overtakes_the_first_pair_of_the_list_wins():
    p = ts.duel(rows(lambda k, y: 50.0 + k), 2024, RIVALRIES)
    assert (p["a"]["iso3"], p["b"]["iso3"]) == ("C00", "C01") and p["overtake_year"] is None


def test_a_pair_used_recently_is_skipped():
    p = ts.duel(rows(lambda k, y: 50.0 + k), 2024, RIVALRIES, recent={frozenset(("C00", "C01"))})
    assert (p["a"]["iso3"], p["b"]["iso3"]) == ("C02", "C03")


def test_scroll_ranking_keeps_every_country():
    p = ts.scroll_ranking(rows(), 2024)
    assert p["n_countries"] == len(ISOS)


def payloads():
    data = rows()
    out = {
        "bar_race": ts.bar_race(data, 2024),
        "line_race": ts.line_race(data, 2024),
        "duel": ts.duel(data, 2024, RIVALRIES),
        "scroll_ranking": ts.scroll_ranking(data, 2024),
    }
    for p in out.values():
        p.update({"unit": "% of population", "indicator": "Internet users",
                  "source": "worldbank", "source_code": "IT.NET.USER.ZS"})
    return out


@pytest.mark.parametrize("fmt", sorted(ts.REEL_FORMATS))
def test_every_reel_format_writes_its_texts_and_draws_every_scene(fmt):
    p = payloads()[fmt]
    templates = yaml.safe_load(open(TEMPLATES_FILE, encoding="utf-8"))
    v = values.build(fmt, p)
    for post_id in range(3):
        t = resolve(make_copy(templates, fmt, p, post_id, "technology"), v)
    duration, draw = reel.BUILDERS[fmt](t, v, p)
    assert 10 <= duration <= 30
    for second in (0.5, 4, duration * 0.5, duration - 3, duration - 0.5):
        s = Slide(size=REEL)
        draw(s, second)
        assert len(s.rgba()) == REEL[0] * REEL[1] * 4


def test_a_chaotic_ranking_is_not_turned_into_a_bar_race():
    import random

    rnd = random.Random(1)
    noisy = rows(lambda k, y: rnd.uniform(0, 100))  # classifica che cambia tutta ogni anno
    assert ts.bar_race(noisy, 2024) is None
    calm = ts.bar_race(rows(), 2024)                # classifica stabile: si fa
    assert calm is not None and calm["volatility"] == 0
