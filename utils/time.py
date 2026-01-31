"""Time helpers."""

import datetime
import pytz

from config import settings


def now() -> datetime.datetime:
    tz = pytz.timezone(settings.TIMEZONE)
    return datetime.datetime.now(tz)


def excel_serial_to_date(serial: float) -> datetime.date:
    """
    Convert Excel serial (days since 1899-12-30) to date.
    """
    base = datetime.datetime(1899, 12, 30)
    return (base + datetime.timedelta(days=serial)).date()
