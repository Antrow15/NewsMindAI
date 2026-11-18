-- CAE adaptation + publisher tables (safe to re-run)
BEGIN;

CREATE TABLE IF NOT EXISTS adaptation_requests (
    id                  BIGSERIAL PRIMARY KEY,
    original_title      VARCHAR(500) NOT NULL,
    original_content    TEXT NOT NULL,
    created_by          BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    status              VARCHAR(40) NOT NULL DEFAULT 'PROCESSING',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS adaptation_drafts (
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

CREATE INDEX IF NOT EXISTS idx_adaptation_drafts_request ON adaptation_drafts(request_id);
CREATE INDEX IF NOT EXISTS idx_adaptation_drafts_platform ON adaptation_drafts(platform);

CREATE TABLE IF NOT EXISTS adaptation_reviews (
    id                  BIGSERIAL PRIMARY KEY,
    draft_id            BIGINT NOT NULL REFERENCES adaptation_drafts(id) ON DELETE CASCADE,
    action              VARCHAR(40) NOT NULL,
    remarks             TEXT,
    reviewed_by         BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    reviewed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_adaptation_reviews_draft ON adaptation_reviews(draft_id);

CREATE TABLE IF NOT EXISTS final_adaptations (
    id                  BIGSERIAL PRIMARY KEY,
    draft_id            BIGINT NOT NULL UNIQUE REFERENCES adaptation_drafts(id) ON DELETE CASCADE,
    final_title         VARCHAR(500) NOT NULL,
    final_content       TEXT NOT NULL,
    finalized_by        BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    remarks             TEXT,
    finalized_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS publication (
    publication_id      BIGSERIAL PRIMARY KEY,
    content_id          BIGINT NOT NULL UNIQUE REFERENCES content(content_id) ON DELETE CASCADE,
    template_code       VARCHAR(64),
    status              VARCHAR(32) NOT NULL DEFAULT 'ready',
    scheduled_at        TIMESTAMPTZ,
    published_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_publication_status ON publication(status);

COMMIT;
