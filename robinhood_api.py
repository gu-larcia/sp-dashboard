import os
import getpass
import asyncio
import aiohttp
import json
import time
from pathlib import Path
import atexit
import pandas as pd

BASE_URL = "https://api.robinhood.com/"
TOKEN_FILE = Path.home() / ".rh_token"
SESSION = None
TOKEN_INFO = None

async def _get_session():
    global SESSION
    if SESSION is None or SESSION.closed:
        SESSION = aiohttp.ClientSession()
    return SESSION

def _load_token():
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "r") as f:
            info = json.load(f)
        if info.get("expires_at", 0) > time.time():
            return info
    return None

def _save_token(info):
    with open(TOKEN_FILE, "w") as f:
        json.dump(info, f)
    os.chmod(TOKEN_FILE, 0o600)

async def logout():
    global SESSION
    if SESSION and not SESSION.closed:
        await SESSION.close()

async def login():
    """Authenticate and return access token."""
    global TOKEN_INFO
    info = _load_token()
    if info:
        TOKEN_INFO = info
        return info["access_token"]

    username = os.getenv("RH_USERNAME") or input(
        "Robinhood username: "
    )
    password = os.getenv("RH_PASSWORD") or getpass.getpass(
        "Robinhood password: "
    )
    mfa = os.getenv("RH_MFA")

    data = {
        "username": username,
        "password": password,
        "grant_type": "password",
    }
    if mfa:
        data["mfa_code"] = mfa

    session = await _get_session()
    async with session.post(BASE_URL + "oauth2/token/", data=data) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise RuntimeError(f"Login failed: {resp.status} {text}")
        payload = await resp.json()

    token = payload["access_token"]
    expires = payload.get("expires_in", 86400)
    info = {"access_token": token, "expires_at": time.time() + expires}
    _save_token(info)
    TOKEN_INFO = info
    atexit.register(
        lambda: asyncio.get_event_loop().run_until_complete(logout())
    )
    return token

async def ensure_token():
    global TOKEN_INFO
    if TOKEN_INFO and TOKEN_INFO.get("expires_at", 0) > time.time():
        return TOKEN_INFO["access_token"]
    return await login()

async def fetch_portfolio_history(span="year", interval="day", refresh=False):
    """Fetch portfolio history from Robinhood and return raw JSON."""
    token = await ensure_token()
    cache_dir = Path(".cache")
    cache_dir.mkdir(exist_ok=True)
    cache_path = cache_dir / f"portfolio_{span}_{interval}.json"
    if cache_path.exists() and not refresh and (
        time.time() - cache_path.stat().st_mtime < 24 * 3600
    ):
        return json.loads(cache_path.read_text())

    params = {"span": span, "interval": interval}
    headers = {"Authorization": f"Bearer {token}"}
    session = await _get_session()
    async with session.get(
        BASE_URL + "portfolios/historicals/",
        params=params,
        headers=headers,
    ) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise RuntimeError(
                f"Failed to fetch history: {resp.status} {text}"
            )
        data = await resp.json()
    cache_path.write_text(json.dumps(data))
    return data

async def portfolio_history_df(span="year", interval="day", refresh=False):
    data = await fetch_portfolio_history(span, interval, refresh)
    histor = data.get("equity_historicals") or data.get("historicals") or []
    df = pd.DataFrame(histor)
    if not df.empty:
        df["begins_at"] = pd.to_datetime(df["begins_at"])
        df.set_index("begins_at", inplace=True)
        df["equity"] = df["equity"].astype(float)
    return df


