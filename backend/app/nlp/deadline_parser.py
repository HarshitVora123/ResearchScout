"""Deadline parsing utilities — converts various date formats to datetime."""

import re
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser


def parse_deadline(text: str | None) -> datetime | None:
    """
    Parse a deadline string into a timezone-aware datetime.

    Handles formats:
    - "January 15, 2025"
    - "15 Jan 2025"
    - "2025-01-15"
    - "01/15/2025"
    - "15/01/2025"
    - "Jan 15, 2025 11:59 PM"
    - "2025-01-15T23:59:59Z"
    - Relative: "rolling", "open until filled"

    Returns None if parsing fails or the string indicates rolling/no deadline.
    """
    if not text:
        return None

    text = text.strip()

    # Check for rolling / no fixed deadline
    no_deadline_patterns = [
        r"(?i)rolling",
        r"(?i)open\s+until\s+filled",
        r"(?i)no\s+(?:fixed\s+)?deadline",
        r"(?i)ongoing",
        r"(?i)continuous",
        r"(?i)asap",
        r"(?i)until\s+(?:position|the\s+position)\s+is\s+filled",
    ]
    for pattern in no_deadline_patterns:
        if re.search(pattern, text):
            return None

    try:
        # Use dateutil for flexible parsing
        dt = dateutil_parser.parse(text, fuzzy=True)

        # If no timezone, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # If the deadline has no time component, set to end of day
        if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
            dt = dt.replace(hour=23, minute=59, second=59)

        return dt

    except (ValueError, TypeError, OverflowError):
        return None


def is_deadline_valid(deadline: datetime | None) -> bool:
    """Check if a deadline is in the future (not expired)."""
    if deadline is None:
        return True  # No deadline means always valid
    now = datetime.now(timezone.utc)
    return deadline > now


def days_until_deadline(deadline: datetime | None) -> int | None:
    """Calculate days until deadline. Returns None if no deadline."""
    if deadline is None:
        return None
    now = datetime.now(timezone.utc)
    delta = deadline - now
    return max(0, delta.days)
