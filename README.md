# Whale Tracker

Telegram listener for whale-sized SOL swaps; stores alerts and FDV snapshots.

## Setup

1. Python 3.10+
2. `python -m venv venv` then activate and `pip install -r requirements.txt`
3. Copy `config.example.py` to `config.py` and set `API_ID`, `API_HASH`, `CHANNEL`, `TARGET_CHANNEL`, `SOL_THRESHOLD`.
4. Run `python app.py` (first run will prompt for Telegram login).

## Requirements

See `requirements.txt`.
