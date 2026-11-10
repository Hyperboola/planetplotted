-- SILVER: dati puliti e validati, in formato "lungo".
-- Applicata da: python -m common.migrate (una sola volta, poi registrata
-- in public.schema_migrations). Per cambiare lo schema: nuovo file 003_...

CREATE SCHEMA IF NOT EXISTS silver;

CREATE TABLE IF NOT EXISTS silver.countries (
    iso3          CHAR(3) PRIMARY KEY,
    name          TEXT NOT NULL,             -- nome ufficiale della fonte
    display_name  TEXT,                      -- nome da mostrare (catalog/country_names.yml)
    region        TEXT,
    income        TEXT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS silver.indicators (
    id          TEXT PRIMARY KEY,            -- id del catalogo
    source      TEXT NOT NULL,
    code        TEXT NOT NULL,               -- codice nella fonte
    name        TEXT NOT NULL,
    unit        TEXT NOT NULL,
    topic       TEXT NOT NULL,
    max_age     INT  NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Una riga per indicatore, paese e anno
CREATE TABLE IF NOT EXISTS silver.observations (
    indicator_id TEXT    NOT NULL REFERENCES silver.indicators(id),
    iso3         CHAR(3) NOT NULL REFERENCES silver.countries(iso3),
    year         INT     NOT NULL,
    value        DOUBLE PRECISION NOT NULL,
    source       TEXT    NOT NULL,
    run_date     DATE    NOT NULL,           -- da quale estrazione arriva
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (indicator_id, iso3, year)
);

CREATE INDEX IF NOT EXISTS idx_obs_indicator_year
    ON silver.observations (indicator_id, year);
