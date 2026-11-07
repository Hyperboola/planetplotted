"""Formattazione dei numeri per i testi dei post.

Regola: un numero si formatta sempre allo stesso modo, così titolo,
slide e didascalia mostrano esattamente la stessa cifra.
"""


def _big(v: float) -> str:
    a = abs(v)
    if a >= 1e12:
        return f"{v / 1e12:.1f} trillion"
    if a >= 1e9:
        return f"{v / 1e9:.2f} billion"
    if a >= 1e6:
        return f"{v / 1e6:.1f} million"
    return f"{v:,.0f}"


def fmt_value(value: float, unit: str, exact: bool = False) -> str:
    """exact=True mostra la cifra intera (per le slide con i numeri esatti)."""
    if unit.startswith("%"):
        return f"{value:.1f}%"
    if unit == "people":
        return f"{value:,.0f}" if exact else _big(value)
    if "US$" in unit:
        return f"${value:,.0f}" if exact or abs(value) < 1e6 else "$" + _big(value)
    if unit == "years":
        return f"{value:.1f} years"
    return f"{value:,.1f}"


def fmt_ratio(r: float) -> str:
    if r >= 100:
        return f"{r:,.0f}×"
    if r >= 10:
        return f"{r:.0f}×"
    return f"{r:.1f}×"


def fmt_share(s: float) -> str:
    return f"{s * 100:.1f}%"


def competition_ranks(display_values: list[str], start: int = 1) -> list[str]:
    """Posizioni con pari merito calcolate sui valori COME APPAIONO:
    ['100.0%','100.0%','99.8%'] -> ['=1','=1','3']"""
    labels, i = [], 0
    while i < len(display_values):
        j = i
        while j + 1 < len(display_values) and display_values[j + 1] == display_values[i]:
            j += 1
        rank = str(start + i)
        tied = j > i
        labels += [("=" + rank) if tied else rank] * (j - i + 1)
        i = j + 1
    return labels


def join_names(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]