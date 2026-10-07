import asyncio
from types import SimpleNamespace

import jarvis.__main__ as cli


class _FakeTokenStore:
    def __init__(self):
        self.deleted=False
    def delete(self):
        self.deleted=True


class _FakeOAuth:
    def __init__(self):
        self.token_store=_FakeTokenStore()
    def authenticate_interactive(self,open_browser=True,timeout=240):
        return {
            'scope':'gmail.readonly calendar.readonly',
            'refresh_token':'refresh',
        }


def test_google_auth_does_not_start_second_runtime(monkeypatch,capsys):
    oauth=_FakeOAuth()
    monkeypatch.setattr(cli,'_standalone_google_oauth',lambda data_dir: oauth)

    async def forbidden_runtime(*args,**kwargs):
        raise AssertionError('google-auth must not start ProductRuntime')
    monkeypatch.setattr(cli,'start_product_runtime',forbidden_runtime)

    result=asyncio.run(cli.utility_command(SimpleNamespace(
        command='google-auth',data_dir=None
    )))

    assert result==0
    assert 'Google autorizado.' in capsys.readouterr().out


def test_google_disconnect_does_not_start_second_runtime(monkeypatch):
    oauth=_FakeOAuth()
    monkeypatch.setattr(cli,'_standalone_google_oauth',lambda data_dir: oauth)

    async def forbidden_runtime(*args,**kwargs):
        raise AssertionError('google-disconnect must not start ProductRuntime')
    monkeypatch.setattr(cli,'start_product_runtime',forbidden_runtime)

    result=asyncio.run(cli.utility_command(SimpleNamespace(
        command='google-disconnect',data_dir=None
    )))

    assert result==0
    assert oauth.token_store.deleted is True
