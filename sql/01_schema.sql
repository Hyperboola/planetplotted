-- Schema dei dati puliti (strato "silver") e della coda dei post.
-- Viene eseguito automaticamente al primo avvio del container Postgres.

CREATE TABLE IF NOT EXISTS countries (
    iso3        CHAR(3) PRIMARY KEY,
    name        TEXT NOT NULL,
    region      TEXT,
    income      TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS indicators (
    id          TEXT PRIMARY KEY,          -- id del catalogo
    source      TEXT NOT NULL,
    code        TEXT NOT NULL,             -- codice nella fonte
    name        TEXT NOT NULL,
    unit        TEXT NOT NULL,
    topic       TEXT NOT NULL,
    max_age     INT  NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Una riga per paese, indicatore e anno: formato "lungo", facile da
-- interrogare per i post e per il sito.
CREATE TABLE IF NOT EXISTS observations (
    indicator_id TEXT    NOT NULL REFERENCES indicators(id),
    iso3         CHAR(3) NOT NULL REFERENCES countries(iso3),
    year         INT     NOT NULL,
    value        DOUBLE PRECISION NOT NULL,
    source       TEXT    NOT NULL,
    run_date     DATE    NOT NULL,         -- da quale estrazione arriva
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (indicator_id, iso3, year)
);

CREATE INDEX IF NOT EXISTS idx_obs_indicator_year
    ON observations (indicator_id, year);

-- Coda dei post (la riempirà la tappa "plan").
CREATE TABLE IF NOT EXISTS post_queue (
    id           BIGSERIAL PRIMARY KEY,
    slot_at      TIMESTAMPTZ NOT NULL,     -- quando va pubblicato
    format       TEXT NOT NULL,            -- ranking, then_vs_now, gap, map
    media        TEXT NOT NULL,            -- carousel, reel
    indicator_id TEXT NOT NULL REFERENCES indicators(id),
    payload      JSONB NOT NULL,           -- i numeri esatti del post
    status       TEXT NOT NULL DEFAULT 'planned',  -- planned, rendered, published
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (slot_at)
);
