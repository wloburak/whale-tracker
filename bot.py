import html
import logging

from telethon import TelegramClient, events
from telethon.tl.types import KeyboardButtonUrl, MessageEntityTextUrl

from config import API_ID, API_HASH, CHANNEL, SOL_THRESHOLD, TARGET_CHANNEL
from db import insert_trade
from parser import extract_mc, extract_sol, extract_ticker, extract_token_address
from price import get_fdv_usd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def get_urls_from_message(message):
    """
    Collect URLs from a Telegram message: link entities (e.g. text links)
    and inline keyboard buttons (e.g. CHART / X•WEB•CHART).
    """
    urls = []
    for entity in message.entities or []:
        if isinstance(entity, MessageEntityTextUrl):
            urls.append(entity.url)
    markup = message.reply_markup
    if markup and getattr(markup, "rows", None):
        for row in markup.rows:
            for btn in getattr(row, "buttons", []):
                if isinstance(btn, KeyboardButtonUrl):
                    urls.append(btn.url)
    return urls


def format_whale_alert_html(
    *,
    ticker: str,
    sol: float,
    mc: float | None,
    entry_value: float | None,
    pool_address: str | None,
    source_preview: str,
) -> str:
    """Telegram HTML (escape all user-facing text)."""
    t = html.escape(ticker)
    sol_s = html.escape(f"{sol:,.2f}")
    if mc and mc > 0:
        mc_s = html.escape(f"${mc:,.0f}")
    else:
        mc_s = "—"
    if entry_value is not None:
        fdv_s = html.escape(f"${entry_value:,.2f}")
    else:
        fdv_s = "<i>unavailable</i>"

    lines = [
        "🐋 <b>Whale alert</b>",
        "",
        f"📌 <b>Token</b>  <code>${t}</code>",
        f"💸 <b>Swap</b>   <code>{sol_s} SOL</code>",
        f"📊 <b>M.C.</b>   {mc_s}",
        f"💎 <b>FDV</b>    {fdv_s}",
    ]

    if pool_address:
        pa = html.escape(pool_address)
        chart = html.escape(
            f"https://www.geckoterminal.com/solana/pools/{pool_address}"
        )
        lines += [
            "",
            f'🔗 <a href="{chart}">GeckoTerminal pool</a>',
            f"<code>{pa}</code>",
        ]

    preview = html.escape(source_preview.strip()[:400])
    if len(source_preview.strip()) > 400:
        preview += "…"
    lines += ["", "────────────", "<b>Source</b>", f"<pre>{preview}</pre>"]

    return "\n".join(lines)


def create_client():
    client = TelegramClient("session", API_ID, API_HASH)

    @client.on(events.NewMessage(chats=CHANNEL))
    async def handler(event):
        try:
            logging.info("Event received from Telegram")

            text = event.message.message

            if not text:
                logging.info("Empty message received")
                return

            logging.info("Raw message: %s", text[:150])

            sol = extract_sol(text)
            ticker = extract_ticker(text)
            mc = extract_mc(text)

            pool_address = None
            for url in get_urls_from_message(event.message):
                pool_address = extract_token_address(url)
                if pool_address:
                    logging.info("Pool from URL: %s -> %s", url[:60], pool_address)
                    break
            if not pool_address:
                pool_address = extract_token_address(text)
            logging.info("Pool address: %s", pool_address)

            if not sol:
                logging.info("No SOL found in message")
                return

            if sol < SOL_THRESHOLD:
                logging.info("Below threshold: %s < %s", sol, SOL_THRESHOLD)
                return

            logging.info("ALERT: %s SOL >= %s", sol, SOL_THRESHOLD)

            display_ticker = ticker or "UNKNOWN"
            entry_value = get_fdv_usd(pool_address) if pool_address else None
            logging.info("Entry value (FDV USD): %s", entry_value)

            alert_html = format_whale_alert_html(
                ticker=display_ticker,
                sol=sol,
                mc=mc,
                entry_value=entry_value,
                pool_address=pool_address,
                source_preview=text,
            )

            try:
                logging.info("Sending Telegram notification...")
                await client.send_message(
                    TARGET_CHANNEL, alert_html, parse_mode="html", link_preview=False
                )
                await client.send_message("me", alert_html, parse_mode="html", link_preview=False)
                logging.info("Message sent")
            except Exception as e:
                logging.error("Failed to send Telegram message: %s", e)

            try:
                logging.info("Saving to database...")
                trade_id = insert_trade(
                    token=display_ticker,
                    sol=sol,
                    mc=mc or 0,
                    entry_value=entry_value,
                    pool_address=pool_address,
                )
                logging.info("Saved to DB (ID: %s)", trade_id)
            except Exception as e:
                logging.error("DB write failed: %s", e)

        except Exception as e:
            logging.error("Handler error: %s", e)

    return client
