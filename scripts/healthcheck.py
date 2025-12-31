#!/usr/bin/env python3
"""
Healthcheck script that verifies Telegram API connectivity.
Used by Docker HEALTHCHECK to determine container health.
Exit code 0 = healthy, 1 = unhealthy.

Requirements: 4.1, 4.2, 4.3
"""

import os
import sys


TIMEOUT_SECONDS = 10


def check_telegram_httpx(token: str) -> bool:
    """Check Telegram API using httpx library."""
    import httpx

    try:
        response = httpx.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=TIMEOUT_SECONDS,
        )
        return response.status_code == 200 and response.json().get("ok", False)
    except Exception:
        return False


def check_telegram_urllib(token: str) -> bool:
    """Fallback check using urllib (no external dependencies)."""
    import json
    import urllib.request

    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:  # nosec B310 - URL is hardcoded HTTPS to Telegram API
            data = json.loads(response.read().decode())
            return data.get("ok", False)
    except Exception:
        return False


def check_telegram() -> bool:
    """
    Verify Telegram API connectivity.

    Returns True if the Telegram API responds successfully, False otherwise.
    Uses httpx if available, falls back to urllib.
    """
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        return False

    # Try httpx first, fall back to urllib
    try:
        return check_telegram_httpx(token)
    except ImportError:
        return check_telegram_urllib(token)


if __name__ == "__main__":
    sys.exit(0 if check_telegram() else 1)
