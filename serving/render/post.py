"""SERVING · RENDER – crea le immagini (e più avanti il video) di un post.

È la "stampante": riceve l'id di un post, o un giorno, e produce i file.
La stessa funzione la lanceranno Airflow ogni mattina e l'admin quando
modifichi un testo.

Uso:
    python -m serving.render.post --post-id 7
    python -m serving.render.post --date 2026-11-07
"""

import argparse
import datetime as dt
import json
import logging
import shutil
from pathlib import Path

from common import config, db
from gold.copywriting import values
from gold.copywriting.generate import resolve
from serving.render import carousel

log = logging.getLogger("serving.render")
OUT_DIR = config.RENDERS_DIR


def render_carousel(post: dict) -> list[str]:
    """Parte senza database: dal post ai file PNG. Restituisce i percorsi."""
    fmt, payload = post["format"], post["payload"]
    if fmt not in carousel.BUILDERS:
        raise NotImplementedError(f"carosello non ancora disponibile per '{fmt}'")
    vals = values.build(fmt, payload)
    texts = resolve(post["copy"], vals)
    folder = OUT_DIR / post["slot_at"].strftime("%Y-%m-%d") / f"post_{post['id']}"
    if folder.exists():  # un nuovo render sostituisce del tutto il precedente
        shutil.rmtree(folder)
    slides = carousel.BUILDERS[fmt](texts, vals, payload)
    paths = []
    for i, slide in enumerate(slides, 1):
        path = slide.save(folder / f"slide_{i:02d}.png")
        # Percorso relativo alla cartella dei render: vale uguale in locale e su S3
        paths.append(str(Path(path).relative_to(OUT_DIR)))
    return paths


def fetch_posts(cur, post_id=None, day=None) -> list[dict]:
    where, arg = ("p.id = %s", post_id) if post_id else (
        "p.slot_at::date = %s AND p.status IN ('copy_ready', 'rendered')", day)
    cur.execute(f"""
        SELECT p.id, p.slot_at, p.format, p.payload, p.copy
        FROM gold.post_queue p WHERE {where} AND p.copy IS NOT NULL ORDER BY p.slot_at
    """, (arg,))
    cols = [c.name for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def remove_stale(cur, day) -> None:
    """Cancella le cartelle di post che non esistono più nel database
    (per esempio dopo un plan --replace), così in data/renders restano
    solo i post veri del giorno."""
    folder = OUT_DIR / day.isoformat()
    if not folder.exists():
        return
    cur.execute("SELECT id FROM gold.post_queue WHERE slot_at::date = %s", (day,))
    keep = {f"post_{post_id}" for (post_id,) in cur.fetchall()}
    for d in folder.iterdir():
        if d.is_dir() and d.name.startswith("post_") and d.name not in keep:
            shutil.rmtree(d)
            log.info("rimossa cartella di un post che non esiste più: %s", d)


def run(post_id=None, day=None) -> int:
    conn = db.connect()
    done = 0
    try:
        with conn, conn.cursor() as cur:
            if day:
                remove_stale(cur, day)
            posts = fetch_posts(cur, post_id, day)
            if not posts:
                log.warning("Nessun post con copy da renderizzare")
            for post in posts:
                try:
                    files = render_carousel(post)
                except NotImplementedError as exc:
                    log.warning("post %s: %s", post["id"], exc)
                    continue
                cur.execute("""
                    UPDATE gold.post_queue SET carousel_files = %s, rendered_at = now(),
                        updated_at = now()
                    WHERE id = %s
                """, (json.dumps(files), post["id"]))
                done += 1
                log.info("post %s (%s): %s slide in %s", post["id"], post["format"],
                         len(files), OUT_DIR / Path(files[0]).parent)
    finally:
        conn.close()
    return done


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--post-id", type=int)
    g.add_argument("--date")
    a = p.parse_args()
    run(a.post_id, dt.date.fromisoformat(a.date) if a.date else None)


if __name__ == "__main__":
    main()