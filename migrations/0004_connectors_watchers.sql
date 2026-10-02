CREATE TABLE IF NOT EXISTS connector_sources (
    connector_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'configured',
    read_only INTEGER NOT NULL DEFAULT 1,
    config_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_sync_at TEXT,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS connector_items (
    item_id TEXT PRIMARY KEY,
    connector_id TEXT NOT NULL,
    external_id TEXT NOT NULL,
    item_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    occurred_at TEXT,
    received_at TEXT NOT NULL,
    source_uri TEXT,
    priority INTEGER NOT NULL DEFAULT 50,
    is_read INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(connector_id, external_id),
    FOREIGN KEY(connector_id) REFERENCES connector_sources(connector_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_connector_items_time
ON connector_items(connector_id, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_connector_items_priority
ON connector_items(is_read, priority DESC, received_at DESC);

CREATE TABLE IF NOT EXISTS connector_sync_runs (
    sync_id TEXT PRIMARY KEY,
    connector_id TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    discovered INTEGER NOT NULL DEFAULT 0,
    stored INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    FOREIGN KEY(connector_id) REFERENCES connector_sources(connector_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS watchers (
    watcher_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'enabled',
    config_json TEXT NOT NULL DEFAULT '{}',
    state_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_checked_at TEXT,
    last_triggered_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_watchers_status ON watchers(status, updated_at);
