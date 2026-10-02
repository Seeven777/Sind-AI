from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class SystemConfig:
    name: str = "Jarvis"
    environment: str = "development"


@dataclass(slots=True)
class LoggingConfig:
    level: str = "INFO"
    file: str = "logs/jarvis.jsonl"


@dataclass(slots=True)
class StorageConfig:
    database: str = "data/jarvis.db"


@dataclass(slots=True)
class RuntimeConfig:
    resume_interrupted_tasks: bool = True
    single_instance: bool = True


@dataclass(slots=True)
class AppConfig:
    data_dir: Path
    system: SystemConfig = field(default_factory=SystemConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)

    @property
    def database_path(self) -> Path:
        p = Path(self.storage.database)
        return p if p.is_absolute() else self.data_dir / p

    @property
    def log_path(self) -> Path:
        p = Path(self.logging.file)
        return p if p.is_absolute() else self.data_dir / p
