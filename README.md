# World Visualization – pipeline dati

Pipeline ETL che ogni giorno scarica dati mondiali, li pulisce, decide
cosa pubblicare, scrive i testi e crea i post per Instagram
(carosello e reel). In futuro alimenterà anche il sito e l'area admin.

Ogni tappa è uno script indipendente: legge l'output della precedente e
scrive il suo, quindi si lancia a mano, da Airflow o da un altro
orchestratore senza cambiare il codice.

| Tappa | Script | Legge | Scrive |
|---|---|---|---|
| Extract | `sources/worldbank.py` | API World Bank | raw (`data/raw` o S3) |
| Transform | `transform/clean.py` | raw | `countries`, `indicators`, `observations` |
| Plan | `plan/schedule.py` | `observations` | `post_queue` (formato, indicatore, numeri) |
| Copy | `copywriting/generate.py` | `post_queue` | `post_queue.copy` (testi con segnaposto) |
| Render | `render/post.py` | `post_queue` | `data/renders/` (slide; reel in arrivo) |

Regola del progetto: **mai inventare nulla**. Il raw non si modifica,
i dati non vengono stimati né arrotondati nel database, e i numeri nei
testi arrivano sempre dal payload tramite segnaposto.

## Struttura

```
sources/        extract, uno script per fonte
transform/      pulizia e controlli di qualità
plan/           scelta dei post (formats.py calcola i numeri)
copywriting/    testi: modelli, formattazione dei numeri, generazione
render/         slide e video
catalog/        indicators.yml (cosa scaricare), schedule.yml (programmazione)
brand/          colori, loghi, font, confini dei paesi
sql/            schema del database
dags/           DAG di Airflow
tests/          test
```

## Primo avvio

Serve Docker Desktop.

```bash
cp .env.example .env
docker compose up -d --build
```

Poi, una sola volta, prepara font e mappe per il render:

```bash
docker compose exec airflow python -m render.setup_fonts
docker compose exec airflow python -m render.setup_map
```

- **Airflow:** http://localhost:8080, utente `admin`. Password:
  `docker compose exec airflow cat /opt/airflow/standalone_admin_password.txt`
  (se non funziona, crea l'utente con `airflow users create`).
- **Postgres:** `localhost:5432`, database/utente/password `worldviz`.
  Si può aprire con l'estensione PostgreSQL di VS Code o con DBeaver.

In Airflow attiva il DAG `worldviz_worldbank`: gira ogni giorno alle 4:00 UTC.

## Lanciare le tappe a mano

```bash
docker compose exec airflow python -m sources.worldbank --countries --run-date 2026-11-07
docker compose exec airflow python -m sources.worldbank --run-date 2026-11-07
docker compose exec airflow python -m transform.clean --run-date 2026-11-07
docker compose exec airflow python -m plan.schedule --date 2026-11-07
docker compose exec airflow python -m copywriting.generate --date 2026-11-07
docker compose exec airflow python -m render.post --date 2026-11-07
```

- `plan.schedule --replace` rifà i post del giorno non ancora renderizzati
  e mai modificati a mano.
- `render.post --post-id 7` renderizza un solo post.

## Configurazione senza toccare il codice

- **`catalog/indicators.yml`:** gli indicatori. `additive: true` solo per
  valori sommabili (popolazione, PIL totale).
- **`catalog/schedule.yml`:** slot giornalieri (orari UTC, reel o carosello)
  e formato e tema per ogni giorno della settimana.
- **`copywriting/templates.yml`:** i modelli dei testi. Usa solo i
  `{segnaposto}`, mai cifre scritte a mano.

## Quando ricostruire Docker

- Codice Python, YAML o DAG: **niente**, la cartella è montata nel container.
- `requirements.txt` o `Dockerfile`: `docker compose up -d --build`.
- `docker-compose.yml`: `docker compose up -d`.
- File in `sql/`: girano solo con il database vuoto. Su un database esistente
  lancia l'SQL a mano.

Per fermare tutto: `docker compose down` (con `-v` cancella anche il database).

## Test

```bash
pip install -r requirements-dev.txt
pytest
```

## Aggiungere un indicatore o una fonte

- **Indicatore World Bank:** una voce in `catalog/indicators.yml`
  (controlla il codice sul sito della World Bank).
- **Nuova fonte:** `sources/<fonte>.py` che salva il raw senza modificarlo,
  la sua pulizia in `transform/` e i task nel DAG.

## Prossimi passi

1. Render dei caroselli per tutti i formati e del reel (MP4).
2. API (FastAPI) e sito (Next.js) con grafici e area admin.
3. Pubblicazione e passaggio al cloud: storage, database gestito,
   Airflow su una macchina virtuale, Terraform.