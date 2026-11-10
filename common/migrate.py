"""Migrazioni del database: applica i file di migrations/ in ordine.

Ogni file viene applicato una sola volta e registrato in
public.schema_migrations. Funziona con qualsiasi Postgres: quello locale
in Docker, quello di test nella CI e quello gestito in produzione.

Per cambiare lo schema non si modifica un file già applicato: se ne
aggiunge uno nuovo (003_..., 004_...).

Uso:
    python -m common.migrate
"""

import logging

from common import config, db

log = logging.getLogger("migrate")
MIGRATIONS_DIR = config.ROOT / "migrations"


def migrate() -> list[str]:
    conn = db.connect()
    applied = []
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.schema_migrations (
                    filename   TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            # Un solo processo alla volta: evita due migrazioni in parallelo
            cur.execute("SELECT pg_advisory_xact_lock(42)")
            cur.execute("SELECT filename FROM public.schema_migrations")
            done = {r[0] for r in cur.fetchall()}
            for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if path.name in done:
                    continue
                cur.execute(path.read_text(encoding="utf-8"))
                cur.execute("INSERT INTO public.schema_migrations (filename) VALUES (%s)",
                            (path.name,))
                applied.append(path.name)
                log.info("applicata %s", path.name)
    finally:
        conn.close()
    if not applied:
        log.info("database già aggiornato")
    return applied


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    migrate()


if __name__ == "__main__":
    main()
