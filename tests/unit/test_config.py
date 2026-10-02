from pathlib import Path
from jarvis.config import ensure_default_config, load_config


def test_defaults_and_config_file(tmp_path: Path):
    cfg = load_config(tmp_path)
    ensure_default_config(cfg)
    cfg2 = load_config(tmp_path)
    assert cfg2.system.name == "Jarvis"
    assert cfg2.database_path == tmp_path / "data" / "jarvis.db"
    assert cfg2.runtime.single_instance is True
