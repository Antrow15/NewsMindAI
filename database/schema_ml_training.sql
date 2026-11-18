-- Training rows pushed from CSV (after ingest+clean), then read for model training.
-- Knowledge base used by journalist content relevancy / related history only.

CREATE TABLE IF NOT EXISTS ml_train_file (
    ml_train_file_id    BIGSERIAL PRIMARY KEY,
    source_file         TEXT NOT NULL UNIQUE,
    file_hash           VARCHAR(64) NOT NULL,
    dataset_kind        VARCHAR(32) NOT NULL,
    row_count           INTEGER NOT NULL DEFAULT 0,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ml_train_urgency (
    id              BIGSERIAL PRIMARY KEY,
    headline        TEXT NOT NULL,
    body            TEXT NOT NULL DEFAULT '',
    source          TEXT,
    priority        VARCHAR(32) NOT NULL,
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ml_train_category (
    id              BIGSERIAL PRIMARY KEY,
    headline        TEXT NOT NULL,
    body            TEXT NOT NULL DEFAULT '',
    category        VARCHAR(64) NOT NULL,
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ml_train_adaptation (
    id                      BIGSERIAL PRIMARY KEY,
    article_id              TEXT NOT NULL,
    original_title          TEXT NOT NULL,
    original_content        TEXT NOT NULL,
    target_platform         VARCHAR(40) NOT NULL,
    correct_adapted_article TEXT NOT NULL,
    loaded_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_base (
    kb_id           BIGSERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    body            TEXT NOT NULL DEFAULT '',
    category        VARCHAR(128),
    source_tag      VARCHAR(128),
    published_date  VARCHAR(64),
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS knowledge_base_title_idx ON knowledge_base (title);

-- Upgrade existing DBs: add source_file BEFORE indexes that need it
ALTER TABLE ml_train_urgency ADD COLUMN IF NOT EXISTS source_file TEXT NOT NULL DEFAULT '';
ALTER TABLE ml_train_adaptation ADD COLUMN IF NOT EXISTS source_file TEXT NOT NULL DEFAULT '';

DROP INDEX IF EXISTS ml_train_adaptation_article_platform_uidx;
CREATE UNIQUE INDEX IF NOT EXISTS ml_train_adaptation_file_article_platform_uidx
    ON ml_train_adaptation (source_file, article_id, target_platform);
