import logging
import threading
import time

import requests

logger = logging.getLogger(__name__)

# GeckoTerminal free tier rate limit: throttle FDV requests
_FDV_LOCK = threading.Lock()
_FDV_LAST_TS = 0.0
_FDV_MIN_INTERVAL = 2.5  # seconds between requests


def _wait_for_rate_limit():
    global _FDV_LAST_TS
    with _FDV_LOCK:
        now = time.monotonic()
        elapsed = now - _FDV_LAST_TS
        if elapsed < _FDV_MIN_INTERVAL:
            time.sleep(_FDV_MIN_INTERVAL - elapsed)
        _FDV_LAST_TS = time.monotonic()


def _fetch_fdv_from_pool(pool_address, debug=False):
    """Direct pool lookup. Returns (fdv, status). Throttles and retries on 429."""
    url = f"https://api.geckoterminal.com/api/v2/networks/solana/pools/{pool_address}"
    if debug:
        logger.info("FDV request: pool=%s", pool_address)
    try:
        _wait_for_rate_limit()
        response = requests.get(url, timeout=15)
        if response.status_code == 429:
            logger.warning("FDV 429 rate limit, retrying after 6s: pool=%s", pool_address)
            time.sleep(6)
            _wait_for_rate_limit()
            response = requests.get(url, timeout=15)
        if debug or response.status_code != 200:
            logger.info(
                "FDV response: status=%s pool=%s body=%s",
                response.status_code,
                pool_address,
                (response.text or "")[:300],
            )
        if response.status_code != 200:
            logger.warning("FDV non-200: %s for pool %s", response.status_code, pool_address)
            return None, response.status_code
        data = response.json()
        pool = data.get("data") or {}
        attributes = pool.get("attributes") or {}
        fdv = attributes.get("fdv_usd")
        if fdv is None:
            logger.warning(
                "FDV missing: pool=%s attr_keys=%s",
                pool_address,
                list(attributes.keys())[:15],
            )
            return None, 200
        return round(float(fdv), 2), 200
    except requests.RequestException as e:
        logger.warning("FDV request failed pool=%s: %s", pool_address, e)
        return None, 0
    except (ValueError, KeyError, TypeError) as e:
        logger.warning("FDV parse error pool=%s: %s", pool_address, e)
        return None, 0


def _resolve_token_mint_to_pool(token_mint):
    """Given a token mint, return first pool's address or None."""
    _wait_for_rate_limit()
    url = f"https://api.geckoterminal.com/api/v2/networks/solana/tokens/{token_mint}/pools"
    try:
        r = requests.get(url, params={"page": 1}, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        pools = data.get("data") or []
        if not pools:
            return None
        raw_id = pools[0].get("id") or ""
        if "_" in raw_id:
            return raw_id.split("_", 1)[1]
        return raw_id or None
    except Exception as e:
        logger.warning("Token-to-pool resolve failed mint=%s: %s", token_mint, e)
        return None


def get_fdv_usd(pool_or_mint, debug=False):
    """
    FDV (USD) from GeckoTerminal. Accepts pool address or token mint.
    If pool lookup 404s (e.g. token mint from /tokens/ URL), resolves via
    tokens/{mint}/pools and fetches from first pool.
    """
    fdv, status = _fetch_fdv_from_pool(pool_or_mint, debug=debug)
    if fdv is not None:
        return fdv
    if status == 404:
        logger.info("Pool 404, resolving as token mint: %s", pool_or_mint)
        actual_pool = _resolve_token_mint_to_pool(pool_or_mint)
        if actual_pool:
            fdv, _ = _fetch_fdv_from_pool(actual_pool, debug=debug)
            return fdv
        logger.warning("No pool found for token mint %s", pool_or_mint)
    return None
