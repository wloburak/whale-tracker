"""Schedule FDV snapshots at +5m and +15m; notify Telegram with vs-entry color hint."""
import asyncio
import html
import logging

from db import update_trade_15m, update_trade_5m
from price import get_fdv_usd

logger = logging.getLogger(__name__)

DELAY_5M_SEC = 5 * 60
DELAY_10M_SEC = 10 * 60  # after 5m -> 15m total from insert


def format_fdv_checkpoint_html(
    label: str,
    ticker: str,
    entry_fdv: float | None,
    fdv: float | None,
    sol_threshold: float,
) -> str:
    """Telegram HTML. Green/red via emoji (Telegram HTML has no font colors)."""
    t = html.escape(ticker)
    thr = html.escape(f"{sol_threshold} SOL")
    threshold_line = f"\n🎯 Threshold: <code>{thr}</code>"
    header = f"⏱ <b>{html.escape(label)}</b> · <code>${t}</code>"

    if fdv is None:
        return f"{header}\nFDV: <i>late</i> (no data){threshold_line}"

    val_s = html.escape(f"${fdv:,.2f}")
    if entry_fdv is None or entry_fdv <= 0:
        return (
            f"{header}\n"
            f"FDV: <b>{val_s}</b>\n"
            f"<i>No entry baseline</i>{threshold_line}"
        )

    pct = (fdv - float(entry_fdv)) / float(entry_fdv) * 100.0
    entry_s = html.escape(f"${float(entry_fdv):,.2f}")
    pct_s = html.escape(f"{pct:+.2f}%")

    if pct > 0.0001:
        body = f"🟢 <b>UP</b> {val_s} ({pct_s} vs entry {entry_s})"
    elif pct < -0.0001:
        body = f"🔴 <b>DOWN</b> {val_s} ({pct_s} vs entry {entry_s})"
    else:
        body = f"⚪ <b>FLAT</b> {val_s} (vs entry {entry_s})"

    return f"{header}\n{body}{threshold_line}"


async def _send_checkpoint(client, target_channel, msg_html: str) -> None:
    try:
        await client.send_message(
            target_channel, msg_html, parse_mode="html", link_preview=False
        )
        await client.send_message("me", msg_html, parse_mode="html", link_preview=False)
    except Exception as e:
        logger.warning("FDV checkpoint Telegram send failed: %s", e)


async def schedule_fdv_followups(
    trade_id: int,
    pool_address: str,
    entry_value: float | None,
    ticker: str,
    client,
    target_channel,
    sol_threshold: float,
) -> None:
    if not pool_address:
        return

    try:
        await asyncio.sleep(DELAY_5M_SEC)
    except asyncio.CancelledError:
        raise

    fdv_5 = None
    try:
        fdv_5 = await asyncio.to_thread(get_fdv_usd, pool_address, True)
        update_trade_5m(trade_id, fdv_5)
        if fdv_5 is not None:
            logger.info("trade %s 5m: %s", trade_id, fdv_5)
        else:
            logger.warning(
                "trade %s 5m: late (pool=%s, see FDV/price logs above)",
                trade_id,
                pool_address,
            )
    except Exception as e:
        logger.warning("trade %s 5m snapshot failed: %s", trade_id, e)
        try:
            update_trade_5m(trade_id, None)
        except Exception:
            logger.exception("trade %s could not mark 5m late", trade_id)

    msg = format_fdv_checkpoint_html(
        "5m FDV", ticker, entry_value, fdv_5, sol_threshold
    )
    await _send_checkpoint(client, target_channel, msg)

    try:
        await asyncio.sleep(DELAY_10M_SEC)
    except asyncio.CancelledError:
        raise

    fdv_15 = None
    try:
        fdv_15 = await asyncio.to_thread(get_fdv_usd, pool_address, True)
        update_trade_15m(trade_id, fdv_15)
        if fdv_15 is not None:
            logger.info("trade %s 15m: %s", trade_id, fdv_15)
        else:
            logger.warning(
                "trade %s 15m: late (pool=%s, see FDV/price logs above)",
                trade_id,
                pool_address,
            )
    except Exception as e:
        logger.warning("trade %s 15m snapshot failed: %s", trade_id, e)
        try:
            update_trade_15m(trade_id, None)
        except Exception:
            logger.exception("trade %s could not mark 15m late", trade_id)

    msg = format_fdv_checkpoint_html(
        "15m FDV", ticker, entry_value, fdv_15, sol_threshold
    )
    await _send_checkpoint(client, target_channel, msg)
