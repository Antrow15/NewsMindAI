-- NewsMindAI V2 — single database bootstrap (fresh install; wipes public schema).
-- Applied by: python app.py --init-db
-- Includes: RBAC/desks, content/evidence, CAE/publisher, ml_train_*.
-- Relevancy uses desk-published content only (TF-IDF + cosine); no history CSV corpus.

BEGIN;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO PUBLIC;

-- ---------------------------------------------------------------------------
-- Core RBAC + newsroom entities
-- ---------------------------------------------------------------------------

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
    assigned_by_user_id BIGINT REFERENCES users(user_id),
    assigned_at         TIMESTAMPTZ,
    due_at              TIMESTAMPTZ,
    assignment_note     TEXT,
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

-- ---------------------------------------------------------------------------
-- Seed roles + categories
-- ---------------------------------------------------------------------------

INSERT INTO role (role_code, role_name, is_active) VALUES
    ('administrator', 'Administrator', TRUE),
    ('audience_insight_analyst', 'Audience Insight Analyst', TRUE),
    ('editor', 'Editor', TRUE),
    ('journalist', 'Journalist', TRUE),
    ('content_adaptation_editor', 'Content Adaptation Editor', TRUE),
    ('publisher', 'Publisher', TRUE),
    ('newsroom_manager', 'Newsroom Manager', TRUE)
ON CONFLICT (role_code) DO NOTHING;

INSERT INTO category (category_name, description, is_active) VALUES
    ('Politics', 'Political coverage (ML topic)', TRUE),
    ('Sports', 'Sports coverage (ML topic)', TRUE),
    ('Business', 'Business and markets (ML topic)', TRUE),
    ('Entertainment', 'Entertainment and culture (ML topic)', TRUE),
    ('World', 'World / international news (ML topic)', TRUE),
    ('City', 'City and civic news (manual desk label)', TRUE),
    ('Weather', 'Weather and climate (manual desk label)', TRUE)
ON CONFLICT (category_name) DO NOTHING;

-- ---------------------------------------------------------------------------
-- CAE adaptation + publisher
-- ---------------------------------------------------------------------------

CREATE TABLE adaptation_requests (
    id                  BIGSERIAL PRIMARY KEY,
    original_title      VARCHAR(500) NOT NULL,
    original_content    TEXT NOT NULL,
    created_by          BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    status              VARCHAR(40) NOT NULL DEFAULT 'PROCESSING',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE adaptation_drafts (
    id                  BIGSERIAL PRIMARY KEY,
    request_id          BIGINT NOT NULL REFERENCES adaptation_requests(id) ON DELETE CASCADE,
    platform            VARCHAR(40) NOT NULL,
    version_number      INTEGER NOT NULL DEFAULT 1,
    adapted_title       VARCHAR(500) NOT NULL,
    adapted_content     TEXT NOT NULL,
    model_version       VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    status              VARCHAR(40) NOT NULL DEFAULT 'PENDING_REVIEW',
    parent_draft_id     BIGINT REFERENCES adaptation_drafts(id) ON DELETE SET NULL,
    generation_parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_flags    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_adaptation_drafts_request ON adaptation_drafts(request_id);
CREATE INDEX idx_adaptation_drafts_platform ON adaptation_drafts(platform);

CREATE TABLE adaptation_reviews (
    id                  BIGSERIAL PRIMARY KEY,
    draft_id            BIGINT NOT NULL REFERENCES adaptation_drafts(id) ON DELETE CASCADE,
    action              VARCHAR(40) NOT NULL,
    remarks             TEXT,
    reviewed_by         BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    reviewed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_adaptation_reviews_draft ON adaptation_reviews(draft_id);

CREATE TABLE final_adaptations (
    id                  BIGSERIAL PRIMARY KEY,
    draft_id            BIGINT NOT NULL UNIQUE REFERENCES adaptation_drafts(id) ON DELETE CASCADE,
    final_title         VARCHAR(500) NOT NULL,
    final_content       TEXT NOT NULL,
    finalized_by        BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    remarks             TEXT,
    finalized_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE publication (
    publication_id      BIGSERIAL PRIMARY KEY,
    content_id          BIGINT NOT NULL UNIQUE REFERENCES content(content_id) ON DELETE CASCADE,
    template_code       VARCHAR(64),
    status              VARCHAR(32) NOT NULL DEFAULT 'ready',
    scheduled_at        TIMESTAMPTZ,
    published_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_publication_status ON publication(status);

-- ---------------------------------------------------------------------------
-- ML training tables (urgency / CAE datasets → train → artifacts)
-- ---------------------------------------------------------------------------

CREATE TABLE ml_train_file (
    ml_train_file_id    BIGSERIAL PRIMARY KEY,
    source_file         TEXT NOT NULL UNIQUE,
    file_hash           VARCHAR(64) NOT NULL,
    dataset_kind        VARCHAR(32) NOT NULL,
    row_count           INTEGER NOT NULL DEFAULT 0,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ml_train_urgency (
    id              BIGSERIAL PRIMARY KEY,
    headline        TEXT NOT NULL,
    body            TEXT NOT NULL DEFAULT '',
    source          TEXT,
    priority        VARCHAR(32) NOT NULL,
    source_file     TEXT NOT NULL DEFAULT '',
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ml_train_category (
    id              BIGSERIAL PRIMARY KEY,
    headline        TEXT NOT NULL,
    body            TEXT NOT NULL DEFAULT '',
    category        VARCHAR(64) NOT NULL,
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ml_train_adaptation (
    id                      BIGSERIAL PRIMARY KEY,
    article_id              TEXT NOT NULL,
    original_title          TEXT NOT NULL,
    original_content        TEXT NOT NULL,
    target_platform         VARCHAR(40) NOT NULL,
    correct_adapted_article TEXT NOT NULL,
    source_file             TEXT NOT NULL DEFAULT '',
    loaded_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX ml_train_adaptation_file_article_platform_uidx
    ON ml_train_adaptation (source_file, article_id, target_platform);

CREATE TABLE notification (
    notification_id     BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    type                VARCHAR(64) NOT NULL,
    title               VARCHAR(512) NOT NULL,
    body                TEXT NOT NULL DEFAULT '',
    payload             JSONB NOT NULL DEFAULT '{}'::jsonb,
    read_at             TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX notification_user_unread_idx
    ON notification (user_id, created_at DESC)
    WHERE read_at IS NULL;

COMMIT;
