"""
Configuration loader.

Reads environment for Sheet connection and shared constants.
Required env:
- SHEET_ID: Google Sheet ID
- GOOGLE_APPLICATION_CREDENTIALS: path to service account JSON
Optional:
- TIMEZONE: default Asia/Taipei
"""

import os
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

# Allow .env to live next to app.py (project root).
dotenv_path = Path(__file__).resolve().parents[1] / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path, override=True)
    for key, value in dotenv_values(dotenv_path).items():
        if key.startswith("\ufeff"):
            key = key.lstrip("\ufeff")
        if value is not None and not os.getenv(key):
            os.environ[key] = value
else:
    load_dotenv(override=True)

SHEET_ID = os.getenv("SHEET_ID", "")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Taipei")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")


def require_settings() -> None:
    missing = []
    if not SHEET_ID:
        missing.append("SHEET_ID")
    if not SERVICE_ACCOUNT_JSON:
        missing.append("GOOGLE_APPLICATION_CREDENTIALS")
    if missing:
        raise RuntimeError(f"Missing required settings: {', '.join(missing)}")
