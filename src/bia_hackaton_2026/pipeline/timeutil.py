"""Timestamps for messages shown to family. India Standard Time (UTC+5:30), no extra dependency."""
import time
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def fmt(ts: float | None = None) -> str:
    """'7 Nov, 3:04 PM IST'"""
    dt = datetime.fromtimestamp(ts if ts is not None else time.time(), IST)
    return f"{dt.day} {dt:%b}, {dt.hour % 12 or 12}:{dt:%M} {'AM' if dt.hour < 12 else 'PM'} IST"
