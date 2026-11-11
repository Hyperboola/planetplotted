"""DAG Airflow: dalla World Bank ai post pronti, strato per strato.

migrazioni -> bronze (extract) -> silver (pulizia) -> gold (plan e copy) -> serving (render)

Gira ogni mattina e prepara i post del GIORNO DOPO: c'è un giorno intero per
controllarli e approvarli, e se un giro fallisce c'è tempo per rilanciarlo.
Tutti gli orari sono in UTC (non cambiano con l'ora legale).

Ogni task lancia uno script indipendente: lo stesso comando funziona
anche a mano dal terminale, senza Airflow.
"""

import datetime as dt

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT = "cd /opt/planetplotted && python -m"
RUN_DATE = "{{ ds }}"                                          # giorno dell'estrazione
POST_DATE = "{{ macros.ds_add(data_interval_end | ds, 1) }}"   # i post di domani

with DAG(
    dag_id="planetplotted_daily",
    description="World Bank -> bronze -> silver -> gold -> serving (post di domani)",
    schedule="0 6 * * *",          # 6:00 UTC = 7:00 in Italia (8:00 con l'ora legale)
    start_date=dt.datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": dt.timedelta(minutes=10)},
    tags=["planetplotted", "etl"],
) as dag:

    # Prima di tutto lo schema del database è aggiornato (se lo è già, non fa nulla)
    db_migrate = BashOperator(
        task_id="db_migrate",
        bash_command=f"{PROJECT} common.migrate",
    )

    bronze_countries = BashOperator(
        task_id="bronze_countries",
        bash_command=f"{PROJECT} bronze.worldbank --countries --run-date {RUN_DATE}",
    )

    bronze_indicators = BashOperator(
        task_id="bronze_indicators",
        bash_command=f"{PROJECT} bronze.worldbank --run-date {RUN_DATE}",
    )

    silver = BashOperator(
        task_id="silver_clean",
        bash_command=f"{PROJECT} silver.clean --run-date {RUN_DATE}",
    )

    gold_plan = BashOperator(
        task_id="gold_plan",
        bash_command=f"{PROJECT} gold.plan.schedule --date {POST_DATE}",
    )

    gold_copy = BashOperator(
        task_id="gold_copy",
        bash_command=f"{PROJECT} gold.copywriting.generate --date {POST_DATE}",
    )

    serving_render = BashOperator(
        task_id="serving_render",
        bash_command=f"{PROJECT} serving.render.post --date {POST_DATE}",
    )

    db_migrate >> [bronze_countries, bronze_indicators] >> silver >> gold_plan >> gold_copy >> serving_render
