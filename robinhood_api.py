import os
import getpass
import asyncio
import aiohttp
import json
import time
from pathlib import Path
import atexit
import pandas as pd
import re

BASE_URL = "https://api.robinhood.com/"
TOKEN_FILE = Path.home() / ".rh_token"
SESSION = None
TOKEN_INFO = None
LOGOUT_REGISTERED = False

# Updated client IDs - try these in order
CLIENT_IDS = [
    "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS",  # Current (May 2025)
    "c82SH0WZTsabGXGGVaTzKqHLHiNTSKqW",  # Previous
    "c82SH0WZ3apipdQ9AX-7kgKxuLkMTkOW",  # Original
]

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

async def _scrape_client_id():
    """Scrape current client ID from Robinhood's web app with multiple strategies."""
    try:
        session = await _get_session()
        
        # Strategy 1: Check login page source
        async with session.get("https://robinhood.com/login") as resp:
            if resp.status == 200:
                content = await resp.text()
                patterns = [
                    r'client_id["\']:\s*["\']([^"\']+)["\']',
                    r'"client_id":\s*"([^"]+)"',
                    r'clientId["\']:\s*["\']([^"\']+)["\']',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, content)
                    if match and len(match.group(1)) > 20:
                        client_id = match.group(1)
                        print(f"🔍 Scraped client ID: {client_id}")
                        return client_id
        
        # Strategy 2: Find and parse JS bundles
        async with session.get("https://robinhood.com") as resp:
            if resp.status == 200:
                content = await resp.text()
                # Look for script tags with likely bundle names
                script_pattern = r'<script[^>]+src=["\']([^"\']*(?:app|main|bundle)[^"\']*\.js[^"\']*)["\']'
                scripts = re.findall(script_pattern, content, re.IGNORECASE)
                
                for script_path in scripts[:3]:  # Limit to first 3 to avoid spam
                    if not script_path.startswith('http'):
                        script_url = f"https://robinhood.com{script_path}"
                    else:
                        script_url = script_path
                    
                    try:
                        async with session.get(script_url) as js_resp:
                            if js_resp.status == 200:
                                js_content = await js_resp.text()
                                # Look for client ID patterns in minified JS
                                client_matches = re.findall(r'["\']([a-zA-Z0-9]{32,})["\']', js_content)
                                for match in client_matches:
                                    if match.startswith('c82SH0WZ') or len(match) == 32:
                                        print(f"🎯 Found potential client ID in JS: {match}")
                                        return match
                    except Exception:
                        continue
                        
    except Exception as e:
        print(f"⚠️ Client ID scraping failed: {e}")
    
    return None

async def logout():
    global SESSION
    if SESSION and not SESSION.closed:
        await SESSION.close()
    SESSION = None

async def login():
    """Authenticate and return access token."""
    global TOKEN_INFO, LOGOUT_REGISTERED
    info = _load_token()
    if info:
        TOKEN_INFO = info
        return info["access_token"]

    username = os.getenv("RH_USERNAME") or input("Robinhood username: ")
    password = os.getenv("RH_PASSWORD") or getpass.getpass("Robinhood password: ")

    # Try to scrape current client ID first
    scraped_id = await _scrape_client_id()
    if scraped_id and scraped_id not in CLIENT_IDS:
        CLIENT_IDS.insert(0, scraped_id)

    # Try each client ID until one works
    session = await _get_session()
    last_error = None
    
    for client_id in CLIENT_IDS:
        data = {
            "username": username,
            "password": password,
            "grant_type": "password",
            "scope": "internal",
            "client_id": client_id,
        }

        try:
            async with session.post(BASE_URL + "oauth2/token/", data=data) as resp:
                if resp.status == 200:
                    payload = await resp.json()
                    token = payload["access_token"]
                    expires = payload.get("expires_in", 86400)
                    info = {"access_token": token, "expires_at": time.time() + expires}
                    _save_token(info)
                    TOKEN_INFO = info
                    if not LOGOUT_REGISTERED:
                        atexit.register(lambda: asyncio.run(logout()))
                        LOGOUT_REGISTERED = True
                    print(f"✓ Login successful with client ID: {client_id}")
                    return token
                elif resp.status == 401:
                    error_data = await resp.json()
                    if "invalid_client" in str(error_data):
                        print(f"✗ Client ID {client_id} is invalid, trying next...")
                        continue
                    else:
                        # Other 401 error (wrong credentials, MFA needed, etc.)
                        text = await resp.text()
                        raise RuntimeError(f"Authentication failed: {resp.status} {text}")
                else:
                    text = await resp.text()
                    last_error = f"Login failed: {resp.status} {text}"
        except Exception as e:
            if "invalid_client" not in str(e):
                raise
            last_error = str(e)

    # If we get here, all client IDs failed
    raise RuntimeError(
        f"All client IDs failed. Last error: {last_error}\\n"
        "This usually means Robinhood has updated their client ID. "
        "You may need to find the current client ID manually."
    )

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