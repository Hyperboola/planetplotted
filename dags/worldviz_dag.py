"""DAG Airflow: estrae i dati World Bank e li carica puliti nel database.

Ogni tappa lancia uno script indipendente: lo stesso comando funziona
anche a mano dal terminale, senza Airflow.
Le tappe plan e render si aggiungeranno qui quando saranno pronte.
"""

import datetime as dt

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT = "cd /opt/worldviz && python -m"

with DAG(
    dag_id="worldviz_worldbank",
    description="World Bank: extract -> transform",
    schedule="0 4 * * *",          # ogni giorno alle 4:00 UTC
    start_date=dt.datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": dt.timedelta(minutes=10)},
    tags=["worldviz", "etl"],
) as dag:

    extract_countries = BashOperator(
        task_id="extract_countries",
        bash_command=f"{PROJECT} sources.worldbank --countries --run-date {{{{ ds }}}}",
    )

    extract_indicators = BashOperator(
        task_id="extract_indicators",
        bash_command=f"{PROJECT} sources.worldbank --run-date {{{{ ds }}}}",
    )

    transform = BashOperator(
        task_id="transform_load",
        bash_command=f"{PROJECT} transform.clean --run-date {{{{ ds }}}}",
    )

    plan = BashOperator(
        task_id="plan_day",
        bash_command=f"{PROJECT} plan.schedule --date {{{{ data_interval_end | ds }}}}",
    )

    write_copy = BashOperator(
        task_id="write_copy",
        bash_command=f"{PROJECT} copywriting.generate --date {{{{ data_interval_end | ds }}}}",
    )

    [extract_countries, extract_indicators] >> transform >> plan >> write_copy
