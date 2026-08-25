from datetime import datetime
from typing import Optional


def format_date_human(date_str: Optional[str]) -> Optional[str]:
    """Converts '2026-08-22' or '2026-08-14T20:40:00Z' into 'August 22, 2026'."""
    if not date_str:
        return None
    try:
        clean = date_str.split("T")[0]
        dt = datetime.strptime(clean, "%Y-%m-%d")
        return dt.strftime("%B %d, %Y").replace(" 0", " ")
    except Exception:
        return date_str
