#!/usr/bin/env python3
"""
Keep Render free-tier awake by pinging /api/info every 10 minutes.

Usage:
  APP_URL=https://seu-app.onrender.com python healthcheck.py

Reads APP_URL from the environment (set in .env or on the host).
"""
import logging
import os
import time

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

APP_URL = os.environ.get("APP_URL", "").rstrip("/")
INTERVAL = 600  # 10 minutes

if not APP_URL:
    raise RuntimeError(
        "APP_URL não definida. "
        "Defina a variável de ambiente: export APP_URL=https://seu-app.onrender.com"
    )


def ping() -> bool:
    url = f"{APP_URL}/api/info"
    try:
        r = requests.get(url, timeout=30)
        elapsed_ms = int(r.elapsed.total_seconds() * 1000)
        log.info("Ping %s → HTTP %d (%d ms)", url, r.status_code, elapsed_ms)
        return r.status_code == 200
    except Exception as exc:
        log.error("Ping falhou: %s", exc)
        return False


if __name__ == "__main__":
    log.info("SafeRoute healthcheck iniciado. Target: %s (intervalo: %ds)", APP_URL, INTERVAL)
    while True:
        ping()
        time.sleep(INTERVAL)
