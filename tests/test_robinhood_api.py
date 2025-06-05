import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from unittest.mock import AsyncMock
import json
import asyncio
import pytest
import robinhood_api as api

class DummyResponse:
    def __init__(self, payload):
        self.status = 200
        self._payload = payload
    async def json(self):
        return self._payload
    async def text(self):
        return json.dumps(self._payload)

class DummyCM:
    def __init__(self, resp):
        self.resp = resp
    async def __aenter__(self):
        return self.resp
    async def __aexit__(self, exc_type, exc, tb):
        return False

@pytest.mark.asyncio
async def test_login_success(tmp_path, monkeypatch):
    api.TOKEN_FILE = tmp_path / "token.json"
    monkeypatch.setenv("RH_USERNAME", "u")
    monkeypatch.setenv("RH_PASSWORD", "p")
    mock_session = AsyncMock()
    resp = DummyResponse({"access_token": "tok", "expires_in": 10})
    mock_session.post = lambda *a, **k: DummyCM(resp)
    monkeypatch.setattr(
        api,
        "_get_session",
        AsyncMock(return_value=mock_session),
    )
    token = await api.login()
    assert token == "tok"
    assert api.TOKEN_INFO["access_token"] == "tok"

@pytest.mark.asyncio
async def test_fetch_portfolio_history(tmp_path, monkeypatch):
    api.TOKEN_FILE = tmp_path / "token.json"
    api.TOKEN_INFO = {"access_token": "tok", "expires_at": 9999999999}
    mock_session = AsyncMock()
    data = {
        "historicals": [
            {"begins_at": "2020-01-01T00:00:00Z", "equity": "1"}
        ]
    }
    mock_session.get = lambda *a, **k: DummyCM(DummyResponse(data))
    monkeypatch.setattr(
        api,
        "_get_session",
        AsyncMock(return_value=mock_session),
    )
    result = await api.fetch_portfolio_history(refresh=True)
    assert result == data


@pytest.mark.asyncio
async def test_token_file_permissions(tmp_path, monkeypatch):
    api.TOKEN_FILE = tmp_path / "token.json"
    monkeypatch.setenv("RH_USERNAME", "u")
    monkeypatch.setenv("RH_PASSWORD", "p")
    mock_session = AsyncMock()
    resp = DummyResponse({"access_token": "tok", "expires_in": 10})
    mock_session.post = lambda *a, **k: DummyCM(resp)
    monkeypatch.setattr(
        api,
        "_get_session",
        AsyncMock(return_value=mock_session),
    )
    await api.login()
    mode = api.TOKEN_FILE.stat().st_mode & 0o777
    assert mode == 0o600

def test_session_closed_on_exit(tmp_path, monkeypatch):
    api.TOKEN_FILE = tmp_path / "token.json"
    monkeypatch.setenv("RH_USERNAME", "u")
    monkeypatch.setenv("RH_PASSWORD", "p")
    mock_session = AsyncMock()
    resp = DummyResponse({"access_token": "tok", "expires_in": 10})
    mock_session.post = lambda *a, **k: DummyCM(resp)
    mock_session.close = AsyncMock()
    mock_session.closed = False
    async def fake_get_session():
        api.SESSION = mock_session
        return mock_session
    monkeypatch.setattr(api, "_get_session", AsyncMock(side_effect=fake_get_session))
    registered = []

    def fake_register(func):
        registered.append(func)

    monkeypatch.setattr(api, "atexit", type("M", (), {"register": fake_register}))

    asyncio.run(api.login())
    assert registered
    registered[0]()
    assert mock_session.close.await_count == 1
    assert api.SESSION is None
