"""Connessione al database, condivisa da tutti gli strati."""

from common import config


def connect():
    import psycopg2

    return psycopg2.connect(config.PG_DSN)
