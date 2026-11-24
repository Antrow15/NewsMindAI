-- Idempotent upgrade for existing NewsMind databases.
BEGIN;

ALTER TABLE content
    ADD COLUMN IF NOT EXISTS assigned_by_user_id BIGINT REFERENCES users(user_id),
    ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS due_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS assignment_note TEXT;

CREATE TABLE IF NOT EXISTS notification (
    notification_id     BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    type                VARCHAR(64) NOT NULL,
    title               VARCHAR(512) NOT NULL,
    body                TEXT NOT NULL DEFAULT '',
    payload             JSONB NOT NULL DEFAULT '{}'::jsonb,
    read_at             TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS notification_user_unread_idx
    ON notification (user_id, created_at DESC)
    WHERE read_at IS NULL;

COMMIT;
