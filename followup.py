"""Schedule FDV snapshots at +5m and +15m after a trade row is inserted."""
import asyncio
import logging

from db import update_trade_15m, update_trade_5m
from price import get_fdv_usd

logger = logging.getLogger(__name__)

DELAY_5M_SEC = 5 * 60
DELAY_10M_SEC = 10 * 60  # after 5m checkpoint -> 15m total from insert


async def schedule_fdv_followups(trade_id: int, pool_address: str) -> None:
    if not pool_address:
        return

    try:
        await asyncio.sleep(DELAY_5M_SEC)
    except asyncio.CancelledError:
        raise

    try:
        fdv = await asyncio.to_thread(get_fdv_usd, pool_address)
        update_trade_5m(trade_id, fdv)
        logger.info("trade %s 5m: %s", trade_id, fdv if fdv is not None else "late")
    except Exception as e:
        logger.warning("trade %s 5m snapshot failed: %s", trade_id, e)
        try:
            update_trade_5m(trade_id, None)
        except Exception:
            logger.exception("trade %s could not mark 5m late", trade_id)

    try:
        await asyncio.sleep(DELAY_10M_SEC)
    except asyncio.CancelledError:
        raise

    try:
        fdv = await asyncio.to_thread(get_fdv_usd, pool_address)
        update_trade_15m(trade_id, fdv)
        logger.info("trade %s 15m: %s", trade_id, fdv if fdv is not None else "late")
    except Exception as e:
        logger.warning("trade %s 15m snapshot failed: %s", trade_id, e)
        try:
            update_trade_15m(trade_id, None)
        except Exception:
            logger.exception("trade %s could not mark 15m late", trade_id)
