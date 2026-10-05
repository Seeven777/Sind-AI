from dataclasses import dataclass,field
from pathlib import Path


@dataclass(slots=True)
class SystemConfig:
    name:str='Jarvis'
    environment:str='development'


@dataclass(slots=True)
class LoggingConfig:
    level:str='INFO'
    file:str='logs/jarvis.jsonl'


@dataclass(slots=True)
class StorageConfig:
    database:str='data/jarvis.db'


@dataclass(slots=True)
class RuntimeConfig:
    resume_interrupted_tasks:bool=True
    single_instance:bool=True


@dataclass(slots=True)
class ModelsConfig:
    default_provider:str='ollama'
    default_model:str='qwen3.5:4b'
    ollama_url:str='http://127.0.0.1:11434'
    timeout_seconds:int=180
    context_tokens:int=8192
    temperature:float=.25


@dataclass(slots=True)
class AIIntegrationsConfig:
    hermes_enabled:bool=True
    hermes_command:str='hermes'
    hermes_profile:str=''
    hermes_toolsets:str='safe'
    hermes_timeout_seconds:int=300
    nvidia_enabled:bool=True
    nvidia_base_url:str='https://integrate.api.nvidia.com/v1'
    nvidia_model:str='nvidia/nemotron-3-ultra-550b-a55b'
    nvidia_thinking:bool=True
    nvidia_max_tokens:int=16384
    nvidia_thinking_token_budget:int=4096
    wa_akg_url:str=''
    wa_akg_session:str=''
    wa_akg_timeout_seconds:int=30
    creative_api_url:str='https://api.muapi.ai'
    creative_timeout_seconds:int=60
    creative_poll_seconds:int=3
    creative_max_polls:int=100


@dataclass(slots=True)
class AgentConfig:
    research_enabled:bool=True


@dataclass(slots=True)
class PrivacyConfig:
    mode:str='hybrid'  # hybrid | local_only


@dataclass(slots=True)
class FeatureConfig:
    memory:bool=True
    agents:bool=True
    tools:bool=True
    approvals:bool=True
    scheduler:bool=True
    connectors:bool=True
    voice:bool=True
    ui:bool=True
    distributed:bool=True
    capability_acquisition:bool=True


@dataclass(slots=True)
class AppConfig:
    data_dir:Path
    system:SystemConfig=field(default_factory=SystemConfig)
    logging:LoggingConfig=field(default_factory=LoggingConfig)
    storage:StorageConfig=field(default_factory=StorageConfig)
    runtime:RuntimeConfig=field(default_factory=RuntimeConfig)
    models:ModelsConfig=field(default_factory=ModelsConfig)
    ai:AIIntegrationsConfig=field(default_factory=AIIntegrationsConfig)
    agents:AgentConfig=field(default_factory=AgentConfig)
    privacy:PrivacyConfig=field(default_factory=PrivacyConfig)
    features:FeatureConfig=field(default_factory=FeatureConfig)

    @property
    def database_path(self)->Path:
        p=Path(self.storage.database)
        return p if p.is_absolute() else self.data_dir/p

    @property
    def log_path(self)->Path:
        p=Path(self.logging.file)
        return p if p.is_absolute() else self.data_dir/p

    @property
    def artifacts_dir(self)->Path:
        return self.data_dir/'artifacts'

    @property
    def local_only(self)->bool:
        return self.privacy.mode.lower()=='local_only'
