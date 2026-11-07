-- Database separato per i metadati di Airflow, nello stesso server Postgres.
CREATE USER airflow WITH PASSWORD 'airflow';
CREATE DATABASE airflow OWNER airflow;
