import requests


def get_fdv_usd(pool_address):
    """
    Fully diluted valuation (USD) for the base token in this pool,
    from GeckoTerminal pool attributes.
    """
    url = f"https://api.geckoterminal.com/api/v2/networks/solana/pools/{pool_address}"

    try:
        response = requests.get(url, timeout=15)
        data = response.json()

        pool = data.get("data") or {}
        attributes = pool.get("attributes") or {}

        fdv = attributes.get("fdv_usd")

        if fdv is None:
            return None
        return round(float(fdv), 2)

    except Exception as e:
        print(f"FDV fetch error: {e}")
        return None
