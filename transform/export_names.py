"""Scrive catalog/country_names.yml con TUTTI i paesi del database.

Per ogni paese mette il nome da mostrare (quello già corretto, se c'è,
altrimenti il nome ufficiale World Bank) e, come commento, il nome
ufficiale. Poi il file si modifica a mano: è l'unico posto dei nomi.

Uso (dopo un transform):
    python -m transform.export_names
"""

from common import config
from transform.clean import NAMES_FILE, load_display_names

HEADER = """\
# Nomi da mostrare nei post e sul sito: uno per ogni paese, per codice iso3.
# Il commento a destra è il nome ufficiale World Bank (resta in countries.name).
# Si modifica solo il nome prima del commento. Poi: python -m transform.clean
#
# Nomi politicamente contesi (es. "West Bank and Gaza"): si tiene quello
# della fonte, che è neutro.

"""


def yaml_value(name: str) -> str:
    # Le virgolette servono per nomi con caratteri speciali per YAML
    return f'"{name}"' if any(c in name for c in ":#'\",") else name


def main():
    import psycopg2

    overrides = load_display_names()
    conn = psycopg2.connect(config.PG_DSN)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT iso3, name FROM countries ORDER BY iso3")
            rows = cur.fetchall()
    finally:
        conn.close()
    lines = [f"{iso3}: {yaml_value(overrides.get(iso3, name))}  # {name}"
             for iso3, name in rows]
    NAMES_FILE.write_text(HEADER + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"scritti {len(lines)} paesi in {NAMES_FILE.relative_to(config.ROOT)}, "
          f"{sum(1 for i, _ in rows if i in overrides)} con nome corretto")


if __name__ == "__main__":
    main()