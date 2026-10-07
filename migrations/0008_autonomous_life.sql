CREATE TABLE IF NOT EXISTS autonomy_discoveries (
    discovery_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    importance INTEGER NOT NULL DEFAULT 30,
    attention_level TEXT NOT NULL DEFAULT 'ambient',
    sources_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_autonomy_discoveries_created
ON autonomy_discoveries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_autonomy_discoveries_importance
ON autonomy_discoveries(importance DESC, created_at DESC);

CREATE TABLE IF NOT EXISTS improvement_proposals (
    proposal_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    rationale TEXT NOT NULL DEFAULT '',
    risk TEXT NOT NULL DEFAULT 'low',
    status TEXT NOT NULL DEFAULT 'pending',
    plan_json TEXT NOT NULL DEFAULT '[]',
    fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_improvement_fingerprint
ON improvement_proposals(fingerprint);
CREATE INDEX IF NOT EXISTS idx_improvement_status
ON improvement_proposals(status, created_at DESC);

CREATE TABLE IF NOT EXISTS attention_notifications (
    notification_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    level TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'unread',
    ref_type TEXT,
    ref_id TEXT,
    created_at TEXT NOT NULL,
    acknowledged_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_attention_status_level
ON attention_notifications(status, level, created_at DESC);

CREATE TABLE IF NOT EXISTS autonomy_state (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
