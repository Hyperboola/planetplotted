"""GOLD · PLAN – decide cosa pubblicare in un giorno e lo scrive in gold.post_queue.

Uso:
    python -m gold.plan.schedule --date 2026-11-07
    python -m gold.plan.schedule --date 2026-11-07 --replace   # rifà i post non ancora approvati
"""

import argparse
import datetime as dt
import json
import logging

import yaml

from common import catalog, config, db
from gold.plan import formats

log = logging.getLogger("gold.plan")
SCHEDULE_FILE = config.ROOT / "catalog" / "schedule.yml"
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def load_schedule() -> dict:
    with open(SCHEDULE_FILE, encoding="utf-8") as f:
        s = yaml.safe_load(f)
    for day in DAYS:
        if len(s["week"][day]) != len(s["slots"]):
            raise ValueError(
                f"schedule.yml: '{day}' ha {len(s['week'][day])} post "
                f"ma ci sono {len(s['slots'])} slot. Devono coincidere.")
        for fmt, _topic in s["week"][day]:
            if fmt not in formats.FORMATS:
                raise ValueError(f"schedule.yml: formato sconosciuto '{fmt}'")
    return s


# --- Scelta dell'indicatore (parte pura, testabile) ---------------------------

def choose_indicator(items, fmt, topic, last_used, exclude, day, no_repeat_days,
                     pair_last_used=None, no_repeat_pair_days=0):
    """Sceglie l'indicatore per uno slot.

    items: voci del catalogo. last_used: {id: data dell'ultimo post}.
    pair_last_used: {(id, formato): data dell'ultimo post con quella coppia}.
    exclude: id già usati oggi.

    Memoria a due livelli:
    - un indicatore non torna prima di no_repeat_days giorni;
    - la stessa coppia indicatore + formato non torna prima di no_repeat_pair_days,
      così lo stesso post non si ripete ogni settimana.
    Prima prova sul tema richiesto, poi su qualsiasi tema; se tutte le coppie
    sono in pausa, si rinuncia alla seconda regola piuttosto che saltare lo slot.
    Tra i candidati vince quello usato meno di recente.
    """
    pair_last_used = pair_last_used or {}

    def ok(i, check_pair):
        if i["id"] in exclude:
            return False
        if fmt == "world_in_one_chart" and not i.get("additive", False):
            return False
        if fmt == "the_gap" and i.get("additive", False):
            return False
        last = last_used.get(i["id"])
        if last is not None and (day - last).days < no_repeat_days:
            return False
        pair = pair_last_used.get((i["id"], fmt))
        if check_pair and pair is not None and (day - pair).days < no_repeat_pair_days:
            return False
        return True

    for check_pair in (True, False):
        for pool in ([i for i in items if i["topic"] == topic], items):
            candidates = [i for i in pool if ok(i, check_pair)]
            if candidates:
                return min(candidates, key=lambda i: last_used.get(i["id"], dt.date.min))
    return None


# --- Database -------------------------------------------------------------------


def fetch_rows(cur, indicator_id):
    cur.execute("""
        SELECT o.iso3, COALESCE(c.display_name, c.name), o.year, o.value
        FROM silver.observations o JOIN silver.countries c USING (iso3)
        WHERE o.indicator_id = %s
    """, (indicator_id,))
    return [{"iso3": a, "name": b, "year": y, "value": v} for a, b, y, v in cur.fetchall()]


def fetch_last_used(cur, day):
    cur.execute("""
        SELECT indicator_id, max(slot_at)::date FROM gold.post_queue
        WHERE slot_at::date < %s GROUP BY indicator_id
    """, (day,))
    return dict(cur.fetchall())


def fetch_pair_last_used(cur, day):
    """Ultima data di ogni coppia (indicatore, formato) prima del giorno da pianificare."""
    cur.execute("""
        SELECT indicator_id, format, max(slot_at)::date FROM gold.post_queue
        WHERE slot_at::date < %s GROUP BY indicator_id, format
    """, (day,))
    return {(i, f): d for i, f, d in cur.fetchall()}


def fetch_population(cur) -> dict:
    """Ultima popolazione disponibile per ogni paese."""
    cur.execute("""
        SELECT DISTINCT ON (iso3) iso3, value FROM silver.observations
        WHERE indicator_id = 'population' ORDER BY iso3, year DESC
    """)
    return dict(cur.fetchall())


def build_payload(item, fmt, rows, day, population=None, min_population=0):
    if fmt == "mapped":
        # Mappa: ultimo dato per paese, non un solo anno per tutti
        payload = formats.mapped(rows, day.year, item["max_age"], population, min_population)
    else:
        year = formats.reference_year(rows, day.year, item["max_age"])
        if year is None:
            return None
        if fmt == "the_gap":
            payload = formats.the_gap(rows, year, item["unit"], population, min_population)
        elif fmt == "then_vs_now":
            payload = formats.then_vs_now(rows, year, item["unit"], population, min_population)
        else:
            payload = formats.BUILDERS[fmt](rows, year)
    if payload is None:
        return None
    payload.update({
        "indicator": item["name"], "unit": item["unit"],
        "source": item["source"], "source_code": item["code"],
        "below_half_phrase": item.get("below_half_phrase"),
    })
    return payload


def plan_day(day: dt.date, replace: bool = False) -> int:
    sched = load_schedule()
    items = catalog.load()
    todo = sched["week"][DAYS[day.weekday()]]
    conn = db.connect()
    planned = 0
    try:
        with conn, conn.cursor() as cur:
            if replace:
                # Rifà solo i post non ancora approvati né pubblicati, e mai modificati a mano
                cur.execute("""
                    DELETE FROM gold.post_queue
                    WHERE slot_at::date = %s
                      AND status IN ('planned', 'copy_ready', 'rendered')
                      AND NOT copy_edited
                """, (day,))
            cur.execute("SELECT count(*) FROM gold.post_queue WHERE slot_at::date = %s", (day,))
            if cur.fetchone()[0]:
                log.info("%s già pianificato: niente da fare (usa --replace)", day)
                return 0
            last_used = fetch_last_used(cur, day)
            pair_last_used = fetch_pair_last_used(cur, day)
            population = fetch_population(cur)
            min_pop = sched.get("gap_min_population", 0)
            used_today = set()
            for slot, (fmt, topic) in zip(sched["slots"], todo):
                slot_at = dt.datetime.combine(
                    day, dt.time.fromisoformat(slot["time"]), tzinfo=dt.timezone.utc)
                payload = item = None
                tried = set(used_today)
                # Se un indicatore non ha dati adatti, prova il successivo
                while True:
                    item = choose_indicator(items, fmt, topic, last_used, tried,
                                            day, sched["no_repeat_days"], pair_last_used,
                                            sched.get("no_repeat_pair_days", 0))
                    if item is None:
                        break
                    payload = build_payload(item, fmt, fetch_rows(cur, item["id"]), day,
                                            population, min_pop)
                    if payload:
                        break
                    tried.add(item["id"])
                if not payload:
                    log.warning("%s %s: nessun indicatore adatto, slot saltato", slot_at, fmt)
                    continue
                payload["media"] = slot["media"]
                cur.execute("""
                    INSERT INTO gold.post_queue (slot_at, format, indicator_id, payload, media)
                    VALUES (%s, %s, %s, %s, %s)
                """, (slot_at, fmt, item["id"], json.dumps(payload), slot["media"]))
                used_today.add(item["id"])
                planned += 1
                log.info("%s %s %s: %s (anno %s)", slot_at, slot["media"], fmt,
                         item["id"], payload["year"])
    finally:
        conn.close()
    return planned


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True, help="giorno da pianificare, AAAA-MM-GG")
    p.add_argument("--replace", action="store_true")
    a = p.parse_args()
    plan_day(dt.date.fromisoformat(a.date), a.replace)


if __name__ == "__main__":
    main()
