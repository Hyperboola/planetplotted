"""SERVING · RENDER – crea le slide del carosello e, per i post "reel", il video.

È la "stampante": riceve l'id di un post, o un giorno, e produce i file.
La stessa funzione la lanceranno Airflow ogni mattina e l'admin quando
modifichi un testo.

Uso:
    python -m serving.render.post --post-id 7
    python -m serving.render.post --date 2026-11-07
    python -m serving.render.post --date 2026-11-07 --skip-reel   # solo slide, più veloce
"""

import argparse
import datetime as dt
import json
import logging
import shutil
from pathlib import Path

from common import config, db, storage
from gold.copywriting import values
from gold.copywriting.generate import resolve
from serving.render import carousel, reel

log = logging.getLogger("serving.render")


def post_folder(post: dict) -> Path:
    return config.RENDERS_DIR / post["slot_at"].strftime("%Y-%m-%d") / f"post_{post['id']}"


def _publish(path: Path) -> str:
    """Carica il file nel bucket (se configurato) e restituisce il percorso relativo,
    uguale in locale e su S3: è quello salvato in gold.post_queue."""
    key = str(path.relative_to(config.RENDERS_DIR))
    storage.publish_render(path, key)
    return key


def render_carousel(post: dict) -> list[str]:
    """Parte senza database: dal post ai file PNG. Restituisce i percorsi."""
    fmt, payload = post["format"], post["payload"]
    if fmt not in carousel.BUILDERS:
        raise NotImplementedError(f"carosello non ancora disponibile per '{fmt}'")
    vals = values.build(fmt, payload)
    texts = resolve(post["copy"], vals)
    folder = post_folder(post)
    if folder.exists():  # un nuovo render sostituisce del tutto il precedente
        shutil.rmtree(folder)
    slides = carousel.BUILDERS[fmt](texts, vals, payload)
    return [_publish(slide.save(folder / f"slide_{i:02d}.png")) for i, slide in enumerate(slides, 1)]


def render_reel(post: dict) -> str | None:
    """Il video del post, dagli stessi numeri e testi del carosello.
    None se per questo formato il reel non esiste ancora."""
    fmt, payload = post["format"], post["payload"]
    if fmt not in reel.BUILDERS:
        return None
    vals = values.build(fmt, payload)
    texts = resolve(post["copy"], vals)
    path = reel.render_video(reel.BUILDERS[fmt], texts, vals, payload,
                             post_folder(post) / "reel.mp4")
    return _publish(path)


def fetch_posts(cur, post_id=None, day=None) -> list[dict]:
    where, arg = ("p.id = %s", post_id) if post_id else (
        "p.slot_at::date = %s AND p.status IN ('copy_ready', 'rendered')", day)
    cur.execute(f"""
        SELECT p.id, p.slot_at, p.format, p.media, p.payload, p.copy
        FROM gold.post_queue p WHERE {where} AND p.copy IS NOT NULL ORDER BY p.slot_at
    """, (arg,))
    cols = [c.name for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def remove_stale(cur, day) -> None:
    """Cancella le cartelle di post che non esistono più nel database
    (per esempio dopo un plan --replace), così in data/renders restano
    solo i post veri del giorno."""
    folder = config.RENDERS_DIR / day.isoformat()
    if not folder.exists():
        return
    cur.execute("SELECT id FROM gold.post_queue WHERE slot_at::date = %s", (day,))
    keep = {f"post_{post_id}" for (post_id,) in cur.fetchall()}
    for d in folder.iterdir():
        if d.is_dir() and d.name.startswith("post_") and d.name not in keep:
            shutil.rmtree(d)
            log.info("rimossa cartella di un post che non esiste più: %s", d)


def run(post_id=None, day=None, skip_reel=False) -> int:
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
                video = None
                if post["media"] == "reel" and not skip_reel:
                    video = render_reel(post)
                    if video is None:
                        log.warning("post %s: reel non ancora disponibile per '%s', "
                                    "resta solo il carosello", post["id"], post["format"])
                cur.execute("""
                    UPDATE gold.post_queue SET carousel_files = %s, reel_file = %s,
                        rendered_at = now(), status = 'rendered', updated_at = now()
                    WHERE id = %s
                """, (json.dumps(files), video, post["id"]))
                done += 1
                log.info("post %s (%s, %s): %s slide%s", post["id"], post["format"],
                         post["media"], len(files), f" + {video}" if video else "")
    finally:
        conn.close()
    return done


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--post-id", type=int)
    g.add_argument("--date")
    p.add_argument("--skip-reel", action="store_true", help="solo le slide, senza video")
    a = p.parse_args()
    run(a.post_id, dt.date.fromisoformat(a.date) if a.date else None, a.skip_reel)


if __name__ == "__main__":
    main()
