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
        # 0.04% non deve diventare "0.0%": sembrerebbe uno zero
        return f"{value:.2f}%" if 0 < abs(value) < 0.1 else f"{value:.1f}%"
    if "$" in unit:
        return f"${value:,.0f}" if exact or abs(value) < 1e6 else "$" + _big(value)
    if unit == "years":
        return f"{value:.1f} years"
    if 0 < abs(value) < 1:
        return f"{value:.2g}"  # due cifre significative: 0.045, non 0.0
    if exact:
        return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:,.1f}"
    if abs(value) >= 1e6:
        return _big(value)
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:,.1f}"


def with_unit(text: str, unit: str) -> str:
    """Aggiunge l'unità ai valori che non la mostrano già (% , $, years)."""
    if unit.startswith("%") or "$" in unit or unit == "years":
        return text
    return f"{text} {unit}"


def fmt_ratio(r: float) -> str:
    if r >= 100:
        return f"{r:,.0f}×"
    if r >= 10:
        return f"{r:.0f}×"
    return f"{r:.1f}×"


def fmt_count(x: float) -> str:
    """1000000 -> '1M', 500000 -> '500,000'"""
    return f"{x / 1e6:g}M" if x >= 1e6 else f"{x:,.0f}"


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