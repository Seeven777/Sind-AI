from pathlib import Path
from jarvis.security import SecretStore


def test_secret_store_roundtrip(tmp_path:Path):
    store=SecretStore(tmp_path/"secrets")
    assert store.get("x") is None
    store.set("x","valor-secreto")
    assert store.exists("x")
    assert store.get("x")=="valor-secreto"
    store.delete("x")
    assert not store.exists("x")
