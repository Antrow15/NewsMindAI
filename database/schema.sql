-- NewsMind console — checklist + login/RBAC
-- ERD USER → physical table `users` (no app_user, no user_session)

BEGIN;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO PUBLIC;

CREATE TABLE employee (
    employee_id         BIGSERIAL PRIMARY KEY,
    employee_code       VARCHAR(64) NOT NULL UNIQUE,
    first_name          VARCHAR(128) NOT NULL,
    last_name           VARCHAR(128) NOT NULL,
    email               VARCHAR(255) NOT NULL UNIQUE,
    mobile_number       VARCHAR(32),
    department          VARCHAR(128),
    designation         VARCHAR(128),
    location            VARCHAR(128),
    employment_status   VARCHAR(64) NOT NULL DEFAULT 'active',
    joining_date        DATE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE role (
    role_id             BIGSERIAL PRIMARY KEY,
    role_code           VARCHAR(64) NOT NULL UNIQUE,
    role_name           VARCHAR(128) NOT NULL,
    role_description    TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ERD entity USER (not app_user)
CREATE TABLE users (
    user_id             BIGSERIAL PRIMARY KEY,
    employee_id         BIGINT NOT NULL UNIQUE REFERENCES employee(employee_id) ON DELETE CASCADE,
    role_id             BIGINT NOT NULL REFERENCES role(role_id) ON DELETE RESTRICT,
    username            VARCHAR(64) NOT NULL UNIQUE,
    password_hash       TEXT NOT NULL,
    account_status      VARCHAR(64) NOT NULL DEFAULT 'active',
    last_login          TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE audience_insight_analyst (
    aia_id              BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    focus_region        VARCHAR(128),
    status              VARCHAR(64) NOT NULL DEFAULT 'active',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE editor (
    editor_id           BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    editorial_desk      VARCHAR(128),
    status              VARCHAR(64) NOT NULL DEFAULT 'active',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE journalist (
    journalist_id       BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    primary_specialization   VARCHAR(128),
    secondary_specialization VARCHAR(128),
    availability_status VARCHAR(64) NOT NULL DEFAULT 'available',
    status              VARCHAR(64) NOT NULL DEFAULT 'active',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE content_adaptation_editor (
    cae_id              BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    specialization_channel VARCHAR(128),
    status              VARCHAR(64) NOT NULL DEFAULT 'active',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE publisher (
    publisher_id        BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    publishing_group    VARCHAR(128),
    status              VARCHAR(64) NOT NULL DEFAULT 'active',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE newsroom_manager (
    newsroom_manager_id BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    managed_region      VARCHAR(128),
    status              VARCHAR(64) NOT NULL DEFAULT 'active',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE category (
    category_id         BIGSERIAL PRIMARY KEY,
    category_name       VARCHAR(128) NOT NULL UNIQUE,
    description         TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE story_pitch (
    story_pitch_id      BIGSERIAL PRIMARY KEY,
    audience_insight_id BIGINT,
    title               VARCHAR(512) NOT NULL,
    summary             TEXT,
    priority            VARCHAR(32) DEFAULT 'medium',
    source_type         VARCHAR(64),
    trend_score         NUMERIC(8,4) DEFAULT 0,
    audience_interest_score NUMERIC(8,4) DEFAULT 0,
    coverage_gap_score  NUMERIC(8,4) DEFAULT 0,
    status              VARCHAR(64) NOT NULL DEFAULT 'submitted',
    created_by          BIGINT,
    approved_by         BIGINT,
    submitted_at        TIMESTAMPTZ,
    approved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Raw CSV ingest rows (before / after cleaning decision)
CREATE TABLE raw_ingest (
    raw_ingest_id       BIGSERIAL PRIMARY KEY,
    source_file         TEXT NOT NULL,
    title               TEXT,
    raw_text            TEXT,
    category            VARCHAR(128),
    published_date      VARCHAR(64),
    source_type         VARCHAR(128),
    cleaning_status     VARCHAR(32) NOT NULL DEFAULT 'pending',
    reject_reason       TEXT,
    content_id          BIGINT,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE content (
    content_id          BIGSERIAL PRIMARY KEY,
    author_id           BIGINT REFERENCES journalist(journalist_id),
    title               VARCHAR(512) NOT NULL,
    summary             TEXT,
    raw_body            TEXT,
    content_body        TEXT,
    content_kind        VARCHAR(32) NOT NULL DEFAULT 'article',
    source_type         VARCHAR(128),
    status              VARCHAR(64) NOT NULL DEFAULT 'draft',
    current_version     INTEGER NOT NULL DEFAULT 1,
    submitted_at        TIMESTAMPTZ,
    approved_at         TIMESTAMPTZ,
    published_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE raw_ingest
    ADD CONSTRAINT raw_ingest_content_fk
    FOREIGN KEY (content_id) REFERENCES content(content_id) ON DELETE SET NULL;

CREATE TABLE article (
    article_id          BIGSERIAL PRIMARY KEY,
    content_id          BIGINT NOT NULL UNIQUE REFERENCES content(content_id) ON DELETE CASCADE,
    story_pitch_id      BIGINT REFERENCES story_pitch(story_pitch_id),
    article_type        VARCHAR(64) DEFAULT 'feature',
    estimated_read_time INTEGER
);

CREATE TABLE news (
    news_id             BIGSERIAL PRIMARY KEY,
    content_id          BIGINT NOT NULL UNIQUE REFERENCES content(content_id) ON DELETE CASCADE,
    event_title         VARCHAR(512),
    event_type          VARCHAR(128),
    event_location      VARCHAR(255),
    event_date          TIMESTAMPTZ,
    breaking_news_flag  BOOLEAN NOT NULL DEFAULT FALSE,
    severity            VARCHAR(32)
);

CREATE TABLE evidence (
    evidence_id         BIGSERIAL PRIMARY KEY,
    content_id          BIGINT NOT NULL REFERENCES content(content_id) ON DELETE CASCADE,
    title               VARCHAR(512) NOT NULL,
    evidence_type       VARCHAR(64),
    source_url          TEXT,
    file_path           TEXT,
    ocr_text            TEXT,
    uploaded_by         BIGINT REFERENCES journalist(journalist_id),
    uploaded_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Track which CSV files have been ingested (supports single-file / new-file runs)
CREATE TABLE ingest_file (
    ingest_file_id      BIGSERIAL PRIMARY KEY,
    source_file         TEXT NOT NULL UNIQUE,
    file_hash           VARCHAR(64) NOT NULL,
    row_count           INTEGER NOT NULL DEFAULT 0,
    usable_row_count    INTEGER NOT NULL DEFAULT 0,
    last_status         VARCHAR(32) NOT NULL DEFAULT 'ingested',
    last_ingested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Cleaning quality reports stored in DB (source of truth)
CREATE TABLE cleaning_report (
    cleaning_report_id  BIGSERIAL PRIMARY KEY,
    report_type         VARCHAR(32) NOT NULL,
    source_files        TEXT,
    input_count         INTEGER NOT NULL DEFAULT 0,
    kept_count          INTEGER NOT NULL DEFAULT 0,
    rejected_count      INTEGER NOT NULL DEFAULT 0,
    report_json         JSONB NOT NULL,
    created_by          BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_raw_ingest_status ON raw_ingest(cleaning_status);
CREATE INDEX idx_content_status ON content(status);
CREATE INDEX idx_ingest_file_hash ON ingest_file(file_hash);
CREATE INDEX idx_cleaning_report_created ON cleaning_report(created_at DESC);

COMMIT;
