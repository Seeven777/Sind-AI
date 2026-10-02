from __future__ import annotations

import os
import tomllib
from pathlib import Path

from .models import (
    AgentConfig,AppConfig,FeatureConfig,LoggingConfig,ModelsConfig,
    PrivacyConfig,RuntimeConfig,StorageConfig,SystemConfig
)
from jarvis.core.errors import ConfigError


def default_data_dir()->Path:
    override=os.environ.get('JARVIS_DATA_DIR')
    if override:return Path(override).expanduser().resolve()
    base=os.environ.get('LOCALAPPDATA')
    return ((Path(base)/'JarvisNext') if base else (Path.home()/'.jarvis-next')).resolve()


def _as_bool(value:str)->bool:
    return value.strip().lower() in {'1','true','yes','on'}


def load_config(data_dir:Path|None=None)->AppConfig:
    root=(data_dir or default_data_dir()).resolve()
    cfg_path=root/'config'/'config.toml'
    raw={}
    if cfg_path.exists():
        try:raw=tomllib.loads(cfg_path.read_text(encoding='utf-8'))
        except (OSError,tomllib.TOMLDecodeError) as exc:
            raise ConfigError(f'Invalid config: {cfg_path}: {exc}') from exc

    sysraw=raw.get('system',{})
    storage=raw.get('storage',{})
    logging=raw.get('logging',{})
    runtime=raw.get('runtime',{})
    models=raw.get('models',{})
    agents=raw.get('agents',{})
    privacy=raw.get('privacy',{})
    features=raw.get('features',{})

    feature_defaults={
        'memory':True,'agents':True,'tools':True,'approvals':True,
        'scheduler':True,'connectors':True,'voice':True,'ui':True,
        'distributed':True,'capability_acquisition':True,
    }
    cfg=AppConfig(
        data_dir=root,
        system=SystemConfig(
            str(sysraw.get('name','Jarvis')),
            str(sysraw.get('environment','development')),
        ),
        storage=StorageConfig(str(storage.get('database','data/jarvis.db'))),
        logging=LoggingConfig(
            str(logging.get('level','INFO')).upper(),
            str(logging.get('file','logs/jarvis.jsonl')),
        ),
        runtime=RuntimeConfig(
            bool(runtime.get('resume_interrupted_tasks',True)),
            bool(runtime.get('single_instance',True)),
        ),
        models=ModelsConfig(
            str(models.get('default_provider','ollama')),
            str(models.get('default_model','qwen3.5:4b')),
            str(models.get('ollama_url','http://127.0.0.1:11434')).rstrip('/'),
            int(models.get('timeout_seconds',180)),
            int(models.get('context_tokens',8192)),
            float(models.get('temperature',.25)),
        ),
        agents=AgentConfig(bool(agents.get('research_enabled',True))),
        privacy=PrivacyConfig(str(privacy.get('mode','hybrid'))),
        features=FeatureConfig(**{
            key:bool(features.get(key,default))
            for key,default in feature_defaults.items()
        }),
    )

    if 'JARVIS_LOG_LEVEL' in os.environ:
        cfg.logging.level=os.environ['JARVIS_LOG_LEVEL'].upper()
    if 'JARVIS_MODEL' in os.environ:
        cfg.models.default_model=os.environ['JARVIS_MODEL']
    if 'JARVIS_OLLAMA_URL' in os.environ:
        cfg.models.ollama_url=os.environ['JARVIS_OLLAMA_URL'].rstrip('/')
    if 'JARVIS_PRIVACY_MODE' in os.environ:
        cfg.privacy.mode=os.environ['JARVIS_PRIVACY_MODE']
    if 'JARVIS_LOCAL_ONLY' in os.environ and _as_bool(os.environ['JARVIS_LOCAL_ONLY']):
        cfg.privacy.mode='local_only'
    if 'JARVIS_RESUME_INTERRUPTED_TASKS' in os.environ:
        cfg.runtime.resume_interrupted_tasks=_as_bool(os.environ['JARVIS_RESUME_INTERRUPTED_TASKS'])
    if 'JARVIS_SINGLE_INSTANCE' in os.environ:
        cfg.runtime.single_instance=_as_bool(os.environ['JARVIS_SINGLE_INSTANCE'])
    if cfg.privacy.mode not in {'hybrid','local_only'}:
        raise ConfigError('privacy.mode deve ser hybrid ou local_only.')
    return cfg


def ensure_default_config(config:AppConfig)->Path:
    path=config.data_dir/'config'/'config.toml'
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        path.write_text(
            '[system]\nname = "Jarvis"\nenvironment = "development"\n\n'
            '[privacy]\nmode = "hybrid"\n\n'
            '[storage]\ndatabase = "data/jarvis.db"\n\n'
            '[logging]\nlevel = "INFO"\nfile = "logs/jarvis.jsonl"\n\n'
            '[runtime]\nresume_interrupted_tasks = true\nsingle_instance = true\n\n'
            '[models]\ndefault_provider = "ollama"\ndefault_model = "qwen3.5:4b"\n'
            'ollama_url = "http://127.0.0.1:11434"\ntimeout_seconds = 180\n'
            'context_tokens = 8192\ntemperature = 0.25\n\n'
            '[agents]\nresearch_enabled = true\n\n'
            '[features]\nmemory = true\nagents = true\ntools = true\napprovals = true\n'
            'scheduler = true\nconnectors = true\nvoice = true\nui = true\n'
            'distributed = true\ncapability_acquisition = true\n',
            encoding='utf-8'
        )
    return path
