-- GOLD: dati pronti all'uso. Per ora i post (numeri e testi);
-- più avanti anche le viste per il sito.

CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.post_queue (
    id             BIGSERIAL PRIMARY KEY,
    slot_at        TIMESTAMPTZ NOT NULL UNIQUE,      -- quando va pubblicato
    format         TEXT NOT NULL,                    -- ranked, the_gap, mapped, then_vs_now, world_in_one_chart
    media          TEXT NOT NULL DEFAULT 'carousel', -- reel o carousel
    indicator_id   TEXT NOT NULL REFERENCES silver.indicators(id),
    payload        JSONB NOT NULL,                   -- i numeri esatti del post
    copy           JSONB,                            -- testi con i {segnaposto}
    copy_edited    BOOLEAN NOT NULL DEFAULT false,   -- true se modificato dall'admin
    status         TEXT NOT NULL DEFAULT 'planned'
        CONSTRAINT post_status_chk CHECK (status IN
            ('planned', 'copy_ready', 'rendered', 'approved', 'published', 'failed')),
    carousel_files JSONB,                            -- percorsi delle slide
    reel_file      TEXT,                             -- percorso del video
    rendered_at    TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
