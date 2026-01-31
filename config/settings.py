"""
Configuration loader.

Reads environment for Sheet connection and shared constants.
Required env:
- SHEET_ID: Google Sheet ID
- GOOGLE_APPLICATION_CREDENTIALS: path to service account JSON
Optional:
- TIMEZONE: default Asia/Taipei
"""

import json
import os
import tempfile
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

def _load_streamlit_secrets() -> None:
    try:
        import streamlit as st
    except Exception:
        return
    try:
        secrets = st.secrets
    except Exception:
        return
    if not os.getenv("SHEET_ID") and "SHEET_ID" in secrets:
        os.environ["SHEET_ID"] = str(secrets["SHEET_ID"])
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and "google" in secrets:
        service_path = os.path.join(tempfile.gettempdir(), "service-account.json")
        if not os.path.exists(service_path) or os.path.getsize(service_path) == 0:
            with open(service_path, "w", encoding="utf-8") as handle:
                json.dump(dict(secrets["google"]), handle)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_path

_load_streamlit_secrets()

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
