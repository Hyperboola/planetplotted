"""DAG Airflow: dalla World Bank ai post pronti, strato per strato.

bronze (extract) -> silver (pulizia) -> gold (plan e copy) -> serving (render)

Ogni task lancia uno script indipendente: lo stesso comando funziona
anche a mano dal terminale, senza Airflow.
"""

import datetime as dt

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT = "cd /opt/worldviz && python -m"
RUN_DATE = "{{ ds }}"                         # giorno dell'estrazione
POST_DATE = "{{ data_interval_end | ds }}"    # giorno dei post da preparare

with DAG(
    dag_id="worldviz_daily",
    description="World Bank -> bronze -> silver -> gold -> serving",
    schedule="0 4 * * *",          # ogni giorno alle 4:00 UTC
    start_date=dt.datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": dt.timedelta(minutes=10)},
    tags=["worldviz", "etl"],
) as dag:

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

    [bronze_countries, bronze_indicators] >> silver >> gold_plan >> gold_copy >> serving_render
