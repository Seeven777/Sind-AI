from __future__ import annotations

import os
import tomllib
from pathlib import Path

from .models import AppConfig, LoggingConfig, RuntimeConfig, StorageConfig, SystemConfig
from jarvis.core.errors import ConfigError


def default_data_dir() -> Path:
    override = os.environ.get("JARVIS_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return (Path(base) / "JarvisNext").resolve()
    return (Path.home() / ".jarvis-next").resolve()


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config(data_dir: Path | None = None) -> AppConfig:
    root = (data_dir or default_data_dir()).resolve()
    cfg_path = root / "config" / "config.toml"
    raw: dict = {}
    if cfg_path.exists():
        try:
            raw = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ConfigError(f"Invalid config: {cfg_path}: {exc}") from exc

    system_raw = raw.get("system", {})
    storage_raw = raw.get("storage", {})
    logging_raw = raw.get("logging", {})
    runtime_raw = raw.get("runtime", {})

    cfg = AppConfig(
        data_dir=root,
        system=SystemConfig(
            name=str(system_raw.get("name", "Jarvis")),
            environment=str(system_raw.get("environment", "development")),
        ),
        storage=StorageConfig(
            database=str(storage_raw.get("database", "data/jarvis.db")),
        ),
        logging=LoggingConfig(
            level=str(logging_raw.get("level", "INFO")).upper(),
            file=str(logging_raw.get("file", "logs/jarvis.jsonl")),
        ),
        runtime=RuntimeConfig(
            resume_interrupted_tasks=bool(runtime_raw.get("resume_interrupted_tasks", True)),
            single_instance=bool(runtime_raw.get("single_instance", True)),
        ),
    )

    # Environment overrides are intentionally explicit, not magical.
    if "JARVIS_LOG_LEVEL" in os.environ:
        cfg.logging.level = os.environ["JARVIS_LOG_LEVEL"].upper()
    if "JARVIS_RESUME_INTERRUPTED_TASKS" in os.environ:
        cfg.runtime.resume_interrupted_tasks = _as_bool(os.environ["JARVIS_RESUME_INTERRUPTED_TASKS"])
    if "JARVIS_SINGLE_INSTANCE" in os.environ:
        cfg.runtime.single_instance = _as_bool(os.environ["JARVIS_SINGLE_INSTANCE"])

    return cfg


def ensure_default_config(config: AppConfig) -> Path:
    config_path = config.data_dir / "config" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        config_path.write_text(
            '[system]\nname = "Jarvis"\nenvironment = "development"\n\n'
            '[storage]\ndatabase = "data/jarvis.db"\n\n'
            '[logging]\nlevel = "INFO"\nfile = "logs/jarvis.jsonl"\n\n'
            '[runtime]\nresume_interrupted_tasks = true\nsingle_instance = true\n',
            encoding="utf-8",
        )
    return config_path
