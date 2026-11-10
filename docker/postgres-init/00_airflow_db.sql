-- Solo in locale: database per i metadati di Airflow nello stesso Postgres.
-- Eseguito da Docker al primo avvio del container (database vuoto).
-- Lo schema dei dati invece lo crea python -m common.migrate.
CREATE USER airflow WITH PASSWORD 'airflow';
CREATE DATABASE airflow OWNER airflow;
