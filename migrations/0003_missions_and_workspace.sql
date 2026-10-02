CREATE TABLE IF NOT EXISTS missions (
    mission_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    workspace_id TEXT,
    title TEXT NOT NULL,
    objective TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY(workspace_id) REFERENCES workspaces(workspace_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status, updated_at);
CREATE INDEX IF NOT EXISTS idx_missions_workspace ON missions(workspace_id, updated_at);

CREATE TABLE IF NOT EXISTS mission_steps (
    step_id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    input_artifact_id TEXT,
    output_artifact_id TEXT,
    started_at TEXT,
    ended_at TEXT,
    error TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE,
    UNIQUE(mission_id, sequence)
);
CREATE INDEX IF NOT EXISTS idx_mission_steps_mission
ON mission_steps(mission_id, sequence);

ALTER TABLE agent_runs ADD COLUMN activity TEXT;
ALTER TABLE agent_runs ADD COLUMN progress REAL NOT NULL DEFAULT 0.0;

CREATE TABLE IF NOT EXISTS workspace_notes (
    note_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE
);
