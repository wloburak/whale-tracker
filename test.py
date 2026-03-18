"""
Run: python test.py

Tests parser/FDV. Test 3 prints whale alert HTML (needs venv + telethon for bot import).
"""
from parser import extract_mc, extract_sol, extract_ticker, extract_token_address
from price import get_fdv_usd


def _fmt_fdv(fdv):
    if fdv is None:
        return "—"
    return f"{fdv:,.2f}"


TEST_MESSAGE = """
MC: $50K
https://www.geckoterminal.com/solana/pools/2gjSjeZvLHWojEsMpqeAT3ASpA3FsXdQxEkrdGaGwPwZ
"""


def debug_test_text():
    print("Test 1: URL in message text\n")

    pool_address = extract_token_address(TEST_MESSAGE)
    print(f"Pool address (parser): {pool_address}")

    if not pool_address:
        print("Parser found no address in message")
        return

    fdv = get_fdv_usd(pool_address)
    print(f"FDV (USD): {_fmt_fdv(fdv)}")

    if fdv is None:
        print("Failed to get FDV")
        return

    print("\nTest 1 passed\n")


def debug_test_bot_style():
    print("Test 2: URL from message entities (CHART-style link)\n")

    try:
        from telethon.tl.types import MessageEntityTextUrl
        from bot import get_urls_from_message
    except ImportError as e:
        print(f"Skip Test 2: {e}\n")
        return

    chart_url = "https://www.geckoterminal.com/solana/pools/Dd4hsmWhwEfkoRh2NxGXmbfYPh474K4yUXuoNmmPYALY"
    mock_message = type(
        "Message",
        (),
        {
            "entities": [MessageEntityTextUrl(offset=0, length=5, url=chart_url)],
            "reply_markup": None,
        },
    )()

    urls = get_urls_from_message(mock_message)
    print(f"URLs from message: {urls}")

    pool_address = None
    for url in urls:
        pool_address = extract_token_address(url)
        if pool_address:
            print(f"Pool address: {pool_address}")
            break

    if not pool_address:
        print("No pool address in extracted URLs")
        return

    fdv = get_fdv_usd(pool_address)
    print(f"FDV (USD): {_fmt_fdv(fdv)}")

    if fdv is None:
        print("Failed to get FDV")
        return

    print("\nTest 2 passed\n")


def test_telegram_message_format():
    print("Test 3: Whale alert HTML\n")

    try:
        from bot import format_whale_alert_html
    except ImportError as e:
        print(f"Skip Test 3: {e}\n")
        return

    source_text = """Afroman New Whale Buy!
Wallet: 247 SOL
1.07 SOL -> 0.08% $FRO
MC: $119924"""

    sol = extract_sol(source_text)
    if sol is None:
        sol = 247.0
    ticker = extract_ticker(source_text) or "FRO"
    mc_val = extract_mc(source_text)
    if mc_val is None:
        mc_val = 119_924.0

    pool = "2gjSjeZvLHWojEsMpqeAT3ASpA3FsXdQxEkrdGaGwPwZ"
    fdv = get_fdv_usd(pool)

    html_out = format_whale_alert_html(
        ticker=ticker,
        sol=sol,
        mc=mc_val,
        entry_value=fdv,
        pool_address=pool,
        source_preview=source_text,
    )

    print("----- HTML (parse_mode=html) -----")
    print(html_out)
    print("----- end -----\n")


if __name__ == "__main__":
    debug_test_text()
    debug_test_bot_style()
    test_telegram_message_format()
    print("Done.")
