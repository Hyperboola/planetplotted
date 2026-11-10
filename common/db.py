"""Connessione al database, condivisa da tutti gli strati."""

from common import config


def connect():
    import psycopg2

    if not config.PG_DSN:
        raise RuntimeError("PG_DSN non impostata: aggiungila al file .env "
                           "(in produzione arriva dai segreti di Terraform)")
    return psycopg2.connect(config.PG_DSN)
