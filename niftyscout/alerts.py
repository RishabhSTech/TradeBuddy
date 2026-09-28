"""
Where a Signal goes once it's found: always the console, optionally
Telegram (with the chart image attached).

This module never touches a broker API and never places an order — it only
notifies. Telegram credentials come from environment variables so you never
have to hardcode them:

    NIFTYSCOUT_TG_TOKEN   - your bot token from @BotFather
    NIFTYSCOUT_TG_CHAT_ID - the chat id to send alerts to
"""

from __future__ import annotations

import os

import requests

from .patterns import Signal

TG_TOKEN_ENV = "NIFTYSCOUT_TG_TOKEN"
TG_CHAT_ID_ENV = "NIFTYSCOUT_TG_CHAT_ID"


def console_alert(signal: Signal) -> None:
    print(f"[BOSS, WE MIGHT HAVE A TRADE] {signal.timestamp} — {signal.headline()} "
          f"(confidence {signal.confidence})")


def telegram_configured() -> bool:
    return bool(os.environ.get(TG_TOKEN_ENV) and os.environ.get(TG_CHAT_ID_ENV))


def telegram_alert(signal: Signal, chart_path: str | None = None, timeout: int = 10) -> bool:
    """Sends the signal to Telegram. Returns True on success, False if not
    configured or the request failed (never raises, so a flaky network
    connection can't crash the scanner)."""
    token = os.environ.get(TG_TOKEN_ENV)
    chat_id = os.environ.get(TG_CHAT_ID_ENV)
    if not token or not chat_id:
        return False

    caption = (
        f"\U0001F6A8 Boss, we might have a trade!\n"
        f"{signal.index_key} · {signal.interval}\n"
        f"{signal.pattern} — {signal.direction.upper()}\n"
        f"Price: {signal.breakout_price:.2f} | Level: {signal.level:.2f}\n"
        f"Confidence: {signal.confidence}\n"
        f"{signal.note}\n"
        f"Time: {signal.timestamp}"
    )

    try:
        if chart_path and os.path.exists(chart_path):
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            with open(chart_path, "rb") as f:
                resp = requests.post(
                    url,
                    data={"chat_id": chat_id, "caption": caption},
                    files={"photo": f},
                    timeout=timeout,
                )
        else:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            resp = requests.post(
                url, data={"chat_id": chat_id, "text": caption}, timeout=timeout
            )
        return resp.ok
    except requests.RequestException as exc:
        print(f"[alerts] Telegram send failed: {exc}")
        return False


def dispatch(signal: Signal, chart_path: str | None = None) -> None:
    console_alert(signal)
    if telegram_configured():
        telegram_alert(signal, chart_path=chart_path)
