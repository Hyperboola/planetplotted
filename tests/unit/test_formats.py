"""Regole dei formati: anni, microstati, quote, cambiamenti."""

from gold.plan import formats


def rows(values, year=2024):
    return [{"iso3": k, "name": k, "year": year, "value": v} for k, v in values.items()]


def test_half_published_year_is_skipped():
    full = [{"iso3": f"C{i}", "name": f"C{i}", "year": y, "value": 1.0}
            for i in range(100) for y in (2023, 2024)]
    partial = [{"iso3": f"C{i}", "name": f"C{i}", "year": 2025, "value": 1.0} for i in range(70)]
    assert formats.reference_year(full + partial, 2026, 3) == 2024


def test_the_gap_uses_points_and_excludes_zeros_and_microstates():
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
    assert "OLD" not in by_iso
    assert by_iso["C0"]["year"] == 2023
    assert formats.mapped(data[:50], 2026, 5) is None


def test_then_vs_now_counts_unchanged_countries():
    data = []
    for i in range(60):
        then, now = (100.0, 100.0) if i < 10 else (float(i), float(i) + 5)
        data += [{"iso3": f"C{i}", "name": f"C{i}", "year": 2004, "value": then},
                 {"iso3": f"C{i}", "name": f"C{i}", "year": 2024, "value": now}]
    p = formats.then_vs_now(data, 2024, "% of population")
    assert (p["rose"], p["fell"], p["unchanged"]) == (50, 0, 10)
    assert all(m["change"] != 0 for m in p["movers"])


def test_world_in_one_chart_goes_back_when_a_big_country_is_missing():
    data = [{"iso3": f"C{i}", "name": f"C{i}", "year": y, "value": 3000.0 if i == 0 else 10.0}
            for i in range(40) for y in (2023, 2024)]
    data += [{"iso3": f"C{i}", "name": f"C{i}", "year": 2025, "value": 10.0} for i in range(1, 40)]
    p = formats.world_in_one_chart(data, 2025)
    assert p["year"] == 2024 and p["shares"][0]["iso3"] == "C0"
