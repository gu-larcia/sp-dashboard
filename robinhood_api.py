#!/usr/bin/env python3
"""
Automated Robinhood Client ID updater.
Run this periodically to keep your client ID fresh.
"""
import asyncio
import aiohttp
import re
import json
from pathlib import Path
from datetime import datetime

CLIENT_ID_CACHE = Path.home() / ".rh_client_cache.json"

async def scrape_latest_client_id():
    """Scrape the most current client ID from Robinhood."""
    async with aiohttp.ClientSession() as session:
        # Strategy 1: Login page
        try:
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
                            return match.group(1)
        except Exception as e:
            print(f"Login page scraping failed: {e}")
        
        # Strategy 2: Main page + JS bundles
        try:
            async with session.get("https://robinhood.com") as resp:
                if resp.status == 200:
                    content = await resp.text()
                    script_pattern = r'<script[^>]+src=["\']([^"\']*(?:app|main|bundle)[^"\']*\.js[^"\']*)["\']'
                    scripts = re.findall(script_pattern, content, re.IGNORECASE)
                    
                    for script_path in scripts[:2]:
                        if not script_path.startswith('http'):
                            script_url = f"https://robinhood.com{script_path}"
                        else:
                            script_url = script_path
                        
                        try:
                            async with session.get(script_url) as js_resp:
                                if js_resp.status == 200:
                                    js_content = await js_resp.text()
                                    # Look for the specific client ID pattern
                                    matches = re.findall(r'["\']([a-zA-Z0-9]{32,})["\']', js_content)
                                    for match in matches:
                                        if match.startswith('c82SH0WZ') or len(match) == 32:
                                            return match
                        except Exception:
                            continue
        except Exception as e:
            print(f"JS bundle scraping failed: {e}")
    
    return None

def load_cached_client_id():
    """Load previously cached client ID info."""
    if CLIENT_ID_CACHE.exists():
        try:
            with open(CLIENT_ID_CACHE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_client_id_cache(client_id):
    """Save client ID with timestamp."""
    cache_data = {
        "client_id": client_id,
        "last_updated": datetime.now().isoformat(),
        "last_check": datetime.now().isoformat()
    }
    with open(CLIENT_ID_CACHE, 'w') as f:
        json.dump(cache_data, f, indent=2)
    print(f"💾 Cached client ID: {client_id}")

def update_robinhood_api_file(new_client_id):
    """Update the CLIENT_IDS list in robinhood_api.py."""
    api_file = Path("robinhood_api.py")
    if not api_file.exists():
        print("❌ robinhood_api.py not found")
        return False
    
    try:
        content = api_file.read_text()
        
        # Find and update the CLIENT_IDS list
        pattern = r'CLIENT_IDS\s*=\s*\[(.*?)\]'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            # Create new client IDs list with the new one first
            new_list = f'''CLIENT_IDS = [
    "{new_client_id}",  # Current ({datetime.now().strftime('%b %Y')})
    "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS",  # Previous
    "c82SH0WZTsabGXGGVaTzKqHLHiNTSKqW",  # Backup
]'''
            
            updated_content = content[:match.start()] + new_list + content[match.end():]
            api_file.write_text(updated_content)
            print(f"✅ Updated robinhood_api.py with new client ID")
            return True
    except Exception as e:
        print(f"❌ Failed to update robinhood_api.py: {e}")
    
    return False

async def check_and_update_client_id():
    """Main function to check for new client ID and update if needed."""
    print(f"🔍 Checking for latest Robinhood client ID... ({datetime.now()})")
    
    # Load cached info
    cached = load_cached_client_id()
    
    # Scrape latest
    latest_id = await scrape_latest_client_id()
    
    if not latest_id:
        print("❌ Could not scrape current client ID")
        return False
    
    # Check if it's new
    if cached and cached.get("client_id") == latest_id:
        print(f"✅ Client ID unchanged: {latest_id}")
        # Update last check time
        cached["last_check"] = datetime.now().isoformat()
        with open(CLIENT_ID_CACHE, 'w') as f:
            json.dump(cached, f, indent=2)
        return True
    
    # New client ID found
    print(f"🆕 New client ID detected: {latest_id}")
    if cached:
        print(f"   Previous: {cached.get('client_id', 'None')}")
    
    # Save to cache
    save_client_id_cache(latest_id)
    
    # Update the API file
    update_robinhood_api_file(latest_id)
    
    return True

if __name__ == "__main__":
    asyncio.run(check_and_update_client_id())