"""Controlli di qualità: se un controllo fallisce, la pipeline si ferma
invece di caricare dati sbagliati (regola: mai inventare nulla)."""

import datetime as dt
import math

MIN_COUNTRIES = 50  # sotto questa soglia il download è probabilmente rotto


class DataQualityError(Exception):
    pass


def row_problem(row: dict, valid_iso3: set[str]) -> str | None:
    """Restituisce il motivo per cui scartare una riga, o None se è valida."""
    if row.get("value") is None:
        return "valore mancante"
    try:
        value = float(row["value"])
    except (TypeError, ValueError):
        return "valore non numerico"
    if not math.isfinite(value):
        return "valore non finito"
    iso3 = row.get("iso3") or ""
    if iso3 not in valid_iso3:
        return "aggregato o codice paese non valido"
    try:
        year = int(row["year"])
    except (TypeError, ValueError):
        return "anno non valido"
    if not 1900 <= year <= dt.date.today().year:
        return "anno fuori intervallo"
    return None


def check_dataset(rows: list[dict], indicator_id: str) -> None:
    """Controlli sull'insieme dei dati di un indicatore."""
    countries = {r["iso3"] for r in rows}
    if len(countries) < MIN_COUNTRIES:
        raise DataQualityError(
            f"{indicator_id}: solo {len(countries)} paesi validi "
            f"(minimo {MIN_COUNTRIES}). Controlla l'estrazione."
        )
    keys = [(r["iso3"], r["year"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise DataQualityError(f"{indicator_id}: righe duplicate per paese e anno")
