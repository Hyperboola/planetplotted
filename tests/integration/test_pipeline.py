"""Tutta la pipeline su un database vero: migrazioni, silver, plan, copy, render.

Usa un database dedicato ai test (TEST_PG_DSN), che viene svuotato: non
puntarlo mai al database di sviluppo. Senza TEST_PG_DSN il test viene saltato.
I dati del bronze sono finti ma realistici, generati qui: nessuna chiamata
all'API della World Bank.
"""

import datetime as dt
import json
import os

import pytest

from common import catalog, config, storage

pytestmark = pytest.mark.integration
TEST_DSN = os.getenv("TEST_PG_DSN")
RUN_DATE = "2026-01-15"


def fake_bronze(n_countries=150):
    """Bronze finto: paesi con codici veri (servono alla mappa), anni 1995-2025."""
    geo = json.loads((config.ROOT / "brand" / "maps" / "countries_50m.geojson").read_text())
    isos = sorted({f["properties"]["iso3"] for f in geo["features"]} - {"ATA", "-99"})
    isos = isos[:n_countries]
    countries = [{"id": c, "name": f"Country {c}", "region": {"value": "Region"}} for c in isos]
    countries.append({"id": "WLD", "name": "World", "region": {"value": "Aggregates"}})
    storage.write_json(storage.bronze_key("worldbank", "countries", RUN_DATE), countries)
    for k, item in enumerate(catalog.load("worldbank")):
        rows = []
        for i, c in enumerate(isos):
            base = 2e6 + i * 1e5 if item["id"] == "population" else 1 + (i * 7 + k) % 90
            rows += [{"countryiso3code": c, "date": str(y), "value": base + (y - 1995) * 0.5}
                     for y in range(1995, 2026)]
        storage.write_json(storage.bronze_key("worldbank", item["id"], RUN_DATE), rows)


@pytest.fixture
def pipeline_env(tmp_path, monkeypatch):
    if not TEST_DSN:
        pytest.skip("TEST_PG_DSN non impostata")
    monkeypatch.setattr(config, "PG_DSN", TEST_DSN)
    monkeypatch.setattr(config, "S3_ENDPOINT", None)
    monkeypatch.setattr(config, "LOCAL_BRONZE_DIR", tmp_path / "bronze")
    monkeypatch.setattr(config, "RENDERS_DIR", tmp_path / "renders")
    from common import db
    conn = db.connect()
    with conn, conn.cursor() as cur:  # database di test pulito
        cur.execute("DROP SCHEMA IF EXISTS gold CASCADE; DROP SCHEMA IF EXISTS silver CASCADE;"
                    "DROP TABLE IF EXISTS public.schema_migrations;")
    conn.close()
    return tmp_path


def test_full_pipeline(pipeline_env):
    from common import db
    from common.migrate import migrate
    from gold.copywriting.generate import generate_day
    from gold.plan.schedule import plan_day
    from serving.render.post import run as render
    from silver.clean import run as silver_run

    assert migrate() == ["001_silver.sql", "002_gold.sql"]
    assert migrate() == []  # la seconda volta non fa nulla

    fake_bronze()
    silver_run(RUN_DATE)

    start = dt.date(2026, 1, 19)  # un lunedì: tutti e 5 i formati in una settimana
    for i in range(7):
        day = start + dt.timedelta(days=i)
        plan_day(day)
        generate_day(day)
        render(day=day)

    conn = db.connect()
    with conn, conn.cursor() as cur:
        cur.execute("SELECT format, status, carousel_files FROM gold.post_queue")
        posts = cur.fetchall()
        cur.execute("SELECT count(*) FROM silver.countries WHERE iso3 = 'WLD'")
        aggregates = cur.fetchone()[0]
    conn.close()

    assert aggregates == 0
    assert len(posts) == 14
    assert {f for f, _, _ in posts} == {"ranked", "the_gap", "mapped", "then_vs_now",
                                        "world_in_one_chart"}
    for _fmt, status, files in posts:
        assert status == "rendered"
        assert len(files) == 4
        assert all((pipeline_env / "renders" / f).exists() for f in files)
