"""Test della pulizia: si lanciano con  pytest  dalla cartella del progetto."""

import pytest

from transform import checks
from transform.clean import clean_countries, clean_worldbank_rows

RAW_COUNTRIES = [
    {"id": "ITA", "name": "Italy", "region": {"value": "Europe & Central Asia"},
     "incomeLevel": {"value": "High income"}},
    {"id": "WLD", "name": "World", "region": {"value": "Aggregates"},
     "incomeLevel": {"value": "Aggregates"}},
    {"id": "EUU", "name": "European Union", "region": {"value": "Aggregates"}},
]


def test_countries_drop_aggregates():
    out = clean_countries(RAW_COUNTRIES)
    assert [c["iso3"] for c in out] == ["ITA"]


def test_rows_are_cleaned_and_drops_counted():
    raw = [
        {"countryiso3code": "ITA", "date": "2023", "value": 58.9},
        {"countryiso3code": "ITA", "date": "2024", "value": None},
        {"countryiso3code": "WLD", "date": "2023", "value": 8.0e9},
        {"countryiso3code": "", "date": "2023", "value": 1.0},
    ]
    rows, dropped = clean_worldbank_rows(raw, {"ITA"})
    assert rows == [{"iso3": "ITA", "year": 2023, "value": 58.9}]
    assert dropped == {"valore mancante": 1, "aggregato o codice paese non valido": 2}


def test_dataset_with_too_few_countries_fails():
    rows = [{"iso3": "ITA", "year": 2023, "value": 1.0}]
    with pytest.raises(checks.DataQualityError):
        checks.check_dataset(rows, "population")


def test_duplicates_fail():
    rows = [{"iso3": f"C{i:02d}", "year": 2023, "value": 1.0} for i in range(60)]
    rows.append(dict(rows[0]))
    with pytest.raises(checks.DataQualityError):
        checks.check_dataset(rows, "population")
