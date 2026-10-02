CREATE TABLE IF NOT EXISTS system_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    stopped_at TEXT,
    shutdown_clean INTEGER NOT NULL DEFAULT 0,
    version TEXT NOT NULL,
    pid INTEGER,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    run_id TEXT,
    task_id TEXT,
    project_id TEXT,
    agent_id TEXT,
    severity TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES system_runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_events_type_time
ON events(event_type, timestamp);

CREATE INDEX IF NOT EXISTS idx_events_task_time
ON events(task_id, timestamp);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    objective TEXT NOT NULL,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 50,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    checkpoint_seq INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    last_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_status_priority
ON tasks(status, priority DESC, created_at);

CREATE TABLE IF NOT EXISTS task_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    state_json TEXT NOT NULL,
    reason TEXT,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    UNIQUE(task_id, sequence)
);

CREATE TABLE IF NOT EXISTS system_kv (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
