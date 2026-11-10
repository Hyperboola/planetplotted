"""Formattazione dei numeri: ogni cifra nei post passa da qui."""

from gold.copywriting import numbers as n


def test_ties_are_computed_on_displayed_values():
    assert n.competition_ranks(["100.0%", "100.0%", "99.8%"]) == ["=1", "=1", "3"]
    assert n.competition_ranks(["9.0%", "8.6%", "8.6%"], start=180) == ["180", "=181", "=181"]


def test_small_values_are_never_shown_as_zero():
    assert n.fmt_value(0.046, "t CO2e per person") == "0.046"
    assert n.fmt_value(0.04, "% of GDP") == "0.04%"


def test_big_values_and_money():
    assert n.fmt_value(1_463_865_525, "people") == "1.46 billion"
    assert n.fmt_value(1_463_865_525, "people", exact=True) == "1,463,865,525"
    assert n.fmt_value(30.77e12, "current US$") == "$30.77 trillion"


def test_units_are_added_only_where_missing():
    assert n.with_unit("84.0 years", "years") == "84.0 years"
    assert n.with_unit("47.3", "t CO2e per person") == "47.3 t CO2e per person"
    assert n.with_unit("8.6%", "% of population") == "8.6%"
