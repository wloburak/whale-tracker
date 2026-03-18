from bot import create_client
from db import init_db
from parser import heartbeat
from datetime import datetime
from zoneinfo import ZoneInfo
from config import TARGET_CHANNEL

async def send_startup_ping(client):
    now = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d %H:%M:%S %Z")
    message = (
        "🐋 <b>Whale Tracker</b> is online\n\n"
        f"🕐 <code>{now}</code>\n"
        "👀 Listening for whale-sized swaps…"
    )
    await client.send_message(TARGET_CHANNEL, message, parse_mode="html")

def main():
    print("🚀 Starting Whale Tracker...")

    # Initialize DB
    init_db()
    print("✅ Database ready")

    # Create Telegram client
    client = create_client()

    # Start client
    client.start()
    print("🤖 Telegram client started")
    print("👀 Listening for whale activity...\n")

    # send startup ping
    client.loop.run_until_complete(send_startup_ping(client))

    # start heartbeat
    client.loop.create_task(heartbeat())

    # Run forever
    client.run_until_disconnected()

if __name__ == "__main__":
    main()