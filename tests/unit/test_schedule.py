"""Memoria del plan: niente ripetizioni dello stesso post."""

import datetime as dt

from gold.plan.schedule import choose_indicator

ITEMS = [{"id": "cereal", "topic": "food", "additive": True},
         {"id": "agri_land", "topic": "food"},
         {"id": "population", "topic": "people", "additive": True}]
DAY = dt.date(2026, 11, 21)


def test_same_indicator_and_format_is_not_repeated_within_the_pause():
    pick = choose_indicator(ITEMS, "world_in_one_chart", "food",
                            {"cereal": dt.date(2026, 11, 14)}, set(), DAY, 7,
                            {("cereal", "world_in_one_chart"): dt.date(2026, 11, 14)}, 90)
    assert pick["id"] == "population"


def test_slot_is_not_skipped_when_every_pair_is_paused():
    last = {i["id"]: dt.date(2026, 11, 1) for i in ITEMS}
    pairs = {(i["id"], "world_in_one_chart"): dt.date(2026, 11, 1) for i in ITEMS}
    assert choose_indicator(ITEMS, "world_in_one_chart", "food", last, set(), DAY, 7,
                            pairs, 90) is not None


def test_the_gap_never_uses_additive_indicators():
    pick = choose_indicator(ITEMS, "the_gap", "food", {}, set(), DAY, 7)
    assert pick["id"] == "agri_land"
