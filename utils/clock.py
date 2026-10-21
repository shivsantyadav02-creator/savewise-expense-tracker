from datetime import datetime, timezone, timedelta, date
from zoneinfo import ZoneInfo
from config import Config

def now_utc() -> datetime:
    """
    Returns current UTC datetime with timezone awareness.
    Centralized so tests can mock or patch this to simulate time travel.
    """
    return datetime.now(timezone.utc)

def get_app_timezone() -> ZoneInfo:
    """
    Returns the application ZoneInfo timezone from Config (default 'Asia/Kolkata').
    """
    tz_name = getattr(Config, "APP_TIMEZONE", "Asia/Kolkata")
    return ZoneInfo(tz_name)

def now_local() -> datetime:
    """
    Returns the current localized datetime in APP_TIMEZONE (default Asia/Kolkata).
    Derives from now_utc() so patching now_utc() automatically controls now_local().
    """
    utc = now_utc()
    if utc.tzinfo is None:
        utc = utc.replace(tzinfo=timezone.utc)
    return utc.astimezone(get_app_timezone())

def to_local_date(dt: datetime) -> date:
    """
    Converts any datetime (UTC or naive assumed UTC) to a date in APP_TIMEZONE.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_app_timezone()).date()

def today_local() -> date:
    """
    Returns today's date in the timezone from config (APP_TIMEZONE, default 'Asia/Kolkata'),
    using zoneinfo.
    Derives from now_utc() so tests can control today_local() through the clock helper.
    """
    return to_local_date(now_utc())

def to_iso_utc(dt: datetime) -> str:
    """
    Converts datetime to ISO-8601 UTC string (e.g. '2026-10-06T15:30:00Z').
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def parse_iso_utc(dt_str: str) -> datetime:
    """
    Parses an ISO datetime string into a timezone-aware UTC datetime.
    """
    if not dt_str or not isinstance(dt_str, str):
        raise ValueError("Invalid timestamp string")
    clean = dt_str.strip()
    if clean.endswith("Z"):
        clean = clean[:-1] + "+00:00"
    dt = datetime.fromisoformat(clean)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
