import re
import asyncio

def extract_sol(text):
    match = re.search(r'(\d+(\.\d+)?)\s*SOL\s*[→>-]', text)
    if match:
        return float(match.group(1))
    return None  

def extract_ticker(text):
    match = re.search(r'\$([A-Z0-9]+)', text)
    if match:
        return match.group(1)
    return None

def extract_mc(text):
    match = re.search(r'MC:\s*\$([\d\.]+)([KMB]?)', text)
    if match:
        value = float(match.group(1))
        suffix = match.group(2)

        if suffix == 'K':
            value *= 1_000
        elif suffix == 'M':
            value *= 1_000_000
        elif suffix == 'B':
            value *= 1_000_000_000

        return value
    return None

def extract_token_address(url):
    """
    From a GeckoTerminal (or similar) URL, return the pool/token id
    used for the price API. Matches /tokens/<id> or /pools/<id>.
    """
    if not url:
        return None
    # Prefer /pools/ (pool id) then /tokens/ (mint)
    match = re.search(r'/pools/([A-Za-z0-9]+)', url)
    if match:
        return match.group(1)
    match = re.search(r'/tokens/([A-Za-z0-9]+)', url)
    if match:
        return match.group(1)
    return None

async def heartbeat():
    while True:
        print("💓 Bot is running...")
        await asyncio.sleep(30)

   