from jarvis.connectors import GoogleTokenStore


def test_google_token_store_roundtrip(tmp_path):
    store=GoogleTokenStore(tmp_path/"google-token.bin")
    store.save({"access_token":"abc","expires_in":3600,"obtained_at":9999999999})
    assert store.load()["access_token"]=="abc"
    store.delete()
    assert not store.exists()
