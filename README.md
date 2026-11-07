# World Visualization – pipeline dati

Pipeline ETL a tappe indipendenti. Ogni tappa è uno script che legge
l'output della precedente e scrive il suo, quindi si può lanciare a mano,
da Airflow o da un altro orchestratore senza cambiare il codice.

| Tappa | Script | Legge | Scrive |
|---|---|---|---|
| Extract | `sources/worldbank.py` | API World Bank | raw (`data/raw` o S3) |
| Transform | `transform/clean.py` | raw | Postgres: `countries`, `indicators`, `observations` |
| Plan | `plan/` (da fare) | `observations` | `post_queue` |
| Render | `render/` (da fare) | `post_queue` | carosello e reel |

Il raw non si modifica mai: se cambia la pulizia, si rilancia solo il transform.

## Avvio con Docker

Serve Docker Desktop (o Docker Engine con Compose).

```bash
cp .env.example .env
docker compose up -d --build
```

- **Airflow:** http://localhost:8080, utente `admin`. La password la genera
  Airflow al primo avvio:
  `docker compose exec airflow cat /opt/airflow/standalone_admin_password.txt`
- **Postgres:** `localhost:5432`, database/utente/password `worldviz`.
  Puoi aprirlo con DBeaver o `psql`.

In Airflow attiva il DAG `worldviz_worldbank` e lancialo con il pulsante ▶.

Per fermare tutto: `docker compose down` (aggiungi `-v` per cancellare anche il database).

## Lanciare le tappe a mano

Dentro il container (o in locale, con Postgres avviato e le librerie installate):

```bash
docker compose exec airflow bash
cd /opt/worldviz
python -m sources.worldbank --countries --run-date 2026-11-06
python -m sources.worldbank --run-date 2026-11-06
python -m transform.clean --run-date 2026-11-06
```

## Test

```bash
pip install -r requirements-dev.txt
pytest
```

## Aggiungere un indicatore

1. Trova il codice sul sito della World Bank (per esempio `SP.POP.TOTL`).
2. Aggiungi una voce in `catalog/indicators.yml`.
3. Al prossimo giro la pipeline lo scarica e lo carica da sola.

## Aggiungere una fonte

Crea `sources/<fonte>.py` con la stessa struttura di `worldbank.py`
(scarica e salva nel raw, senza toccare i dati) e la sua funzione di pulizia
in `transform/`. Poi aggiungi i task nel DAG.

## Passaggio al cloud (fase 2)

- **Raw:** imposta `S3_ENDPOINT`, `S3_BUCKET` e le chiavi nel `.env`.
  Il codice usa S3 al posto della cartella locale.
- **Database:** cambia `PG_DSN` con quello del Postgres gestito.
- **Airflow:** stesso DAG, su una macchina virtuale o un servizio gestito.
