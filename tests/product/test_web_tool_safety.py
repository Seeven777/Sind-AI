from jarvis.tools import WebFetchTool


def test_web_fetch_blocks_loopback():
    result=WebFetchTool().execute({"url":"http://127.0.0.1:9999/private"})
    assert result.success is False
    assert "privado/local" in result.error
