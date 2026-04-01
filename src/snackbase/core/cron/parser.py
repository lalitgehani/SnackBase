"""Pure-Python cron expression parser and next-run calculator.

Supports the standard 5-field cron syntax:
    minute hour day-of-month month day-of-week

Each field supports:
    *       any value
    */n     every n units (step)
    n-m     inclusive range
    n,m,k   comma-separated list
    n       specific integer value

Field ranges:
    minute:       0-59
    hour:         0-23
    day-of-month: 1-31
    month:        1-12 (also JAN-DEC names)
    day-of-week:  0-6  (0=Sunday; also SUN-SAT names; 7 treated as 0)

Usage:
    is_valid, error = validate_cron("0 9 * * MON")
    next_dt = get_next_run("0 9 * * MON", datetime.utcnow())
    label = describe_cron("0 9 * * MON")
"""

from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Name mappings
# ---------------------------------------------------------------------------

_MONTH_NAMES: dict[str, int] = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
    "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
    "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

_DOW_NAMES: dict[str, int] = {
    "SUN": 0, "MON": 1, "TUE": 2, "WED": 3,
    "THU": 4, "FRI": 5, "SAT": 6,
}

_MONTH_LABELS = ["", "January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]

_DOW_LABELS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# ---------------------------------------------------------------------------
# Field metadata
# ---------------------------------------------------------------------------

_FIELD_META = [
    ("minute",       0,  59),
    ("hour",         0,  23),
    ("day-of-month", 1,  31),
    ("month",        1,  12),
    ("day-of-week",  0,   6),
]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _resolve_name(token: str, field_index: int) -> str:
    """Replace named aliases (MON, JAN, etc.) with their numeric equivalents."""
    upper = token.upper()
    if field_index == 3 and upper in _MONTH_NAMES:
        return str(_MONTH_NAMES[upper])
    if field_index == 4 and upper in _DOW_NAMES:
        return str(_DOW_NAMES[upper])
    return token


def _parse_field(raw: str, field_index: int) -> set[int]:
    """Parse a single cron field into a set of valid integer values.

    Raises:
        ValueError: If the field cannot be parsed or contains out-of-range values.
    """
    name, lo, hi = _FIELD_META[field_index]

    # Handle comma-separated list by recursively parsing each part
    if "," in raw:
        result: set[int] = set()
        for part in raw.split(","):
            result |= _parse_field(part.strip(), field_index)
        return result

    # Resolve named aliases
    raw = _resolve_name(raw, field_index)

    # Wildcard
    if raw == "*":
        return set(range(lo, hi + 1))

    # Step: */n or m-n/step
    if "/" in raw:
        range_part, step_part = raw.split("/", 1)
        if not step_part.isdigit():
            raise ValueError(f"Invalid step value '{step_part}' in {name} field")
        step = int(step_part)
        if step <= 0:
            raise ValueError(f"Step must be >= 1, got {step} in {name} field")
        if range_part == "*":
            return set(range(lo, hi + 1, step))
        # range/step form
        if "-" in range_part:
            start_s, end_s = range_part.split("-", 1)
            start_s = _resolve_name(start_s, field_index)
            end_s = _resolve_name(end_s, field_index)
            if not (start_s.isdigit() and end_s.isdigit()):
                raise ValueError(f"Invalid range '{range_part}' in {name} field")
            start, end = int(start_s), int(end_s)
        elif range_part.isdigit():
            start = int(range_part)
            end = hi
        else:
            raise ValueError(f"Invalid range part '{range_part}' in {name} field")
        if not (lo <= start <= hi and lo <= end <= hi):
            raise ValueError(
                f"Range {start}-{end} out of bounds [{lo},{hi}] in {name} field"
            )
        if start > end:
            raise ValueError(f"Range start {start} > end {end} in {name} field")
        return set(range(start, end + 1, step))

    # Inclusive range: n-m
    if "-" in raw:
        parts = raw.split("-", 1)
        parts = [_resolve_name(p, field_index) for p in parts]
        if not (parts[0].isdigit() and parts[1].isdigit()):
            raise ValueError(f"Invalid range '{raw}' in {name} field")
        start, end = int(parts[0]), int(parts[1])
        if not (lo <= start <= hi and lo <= end <= hi):
            raise ValueError(
                f"Range {start}-{end} out of bounds [{lo},{hi}] in {name} field"
            )
        if start > end:
            raise ValueError(f"Range start {start} > end {end} in {name} field")
        return set(range(start, end + 1))

    # Specific value
    if not raw.isdigit():
        raise ValueError(f"Invalid value '{raw}' in {name} field")
    val = int(raw)

    # day-of-week: treat 7 as Sunday (0)
    if field_index == 4 and val == 7:
        val = 0

    if not (lo <= val <= hi):
        raise ValueError(f"Value {val} out of bounds [{lo},{hi}] in {name} field")
    return {val}


def _parse(expr: str) -> tuple[set[int], set[int], set[int], set[int], set[int]]:
    """Parse a full cron expression into 5 sets of valid values.

    Returns:
        Tuple of (minutes, hours, doms, months, dows).

    Raises:
        ValueError: On parse error.
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"Cron expression must have exactly 5 fields "
            f"(minute hour dom month dow), got {len(parts)}: '{expr}'"
        )
    return (
        _parse_field(parts[0], 0),
        _parse_field(parts[1], 1),
        _parse_field(parts[2], 2),
        _parse_field(parts[3], 3),
        _parse_field(parts[4], 4),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_cron(expr: str) -> tuple[bool, str]:
    """Validate a cron expression.

    Args:
        expr: A 5-field cron expression string.

    Returns:
        (True, '') if valid, or (False, error_message) if invalid.
    """
    try:
        _parse(expr)
        return True, ""
    except ValueError as exc:
        return False, str(exc)


def get_next_run(expr: str, from_dt: datetime) -> datetime:
    """Calculate the next scheduled datetime after ``from_dt``.

    The result is at least one minute after ``from_dt`` (cron has 1-minute
    minimum resolution).  Seconds and microseconds are stripped from the result.

    Standard day-of-week / day-of-month interaction:
        - If both dom and dow are restricted (not ``*``), either matching
          satisfies the condition (OR logic, matching vixie-cron behaviour).
        - If only one is restricted, only that field is checked.

    Args:
        expr: A valid 5-field cron expression.
        from_dt: Start search from this datetime (naive, UTC assumed).

    Returns:
        Next matching naive datetime.

    Raises:
        ValueError: If ``expr`` is invalid or no match is found within 4 years.
    """
    minutes, hours, doms, months, dows = _parse(expr)

    # Check which fields are "unrestricted" (cover the full range)
    dom_star = len(doms) == 31  # 1-31
    dow_star = len(dows) == 7   # 0-6

    # Advance to next minute, strip seconds/microseconds
    dt = from_dt.replace(second=0, microsecond=0) + timedelta(minutes=1)
    limit = from_dt + timedelta(days=4 * 365)

    while dt <= limit:
        # Check month first — if wrong month, jump to 1st of next valid month
        if dt.month not in months:
            # Find next valid month
            next_month = next((m for m in sorted(months) if m > dt.month), None)
            if next_month is None:
                # Roll over to next year
                dt = dt.replace(year=dt.year + 1, month=min(months), day=1,
                                hour=0, minute=0)
            else:
                dt = dt.replace(month=next_month, day=1, hour=0, minute=0)
            continue

        # Check day (dom / dow interaction)
        dom_match = dt.day in doms
        # dt.weekday() returns 0=Monday; cron uses 0=Sunday
        cron_dow = (dt.weekday() + 1) % 7  # convert to 0=Sunday
        dow_match = cron_dow in dows

        if dom_star and dow_star:
            day_ok = True
        elif dom_star:
            day_ok = dow_match
        elif dow_star:
            day_ok = dom_match
        else:
            # Both restricted → OR logic
            day_ok = dom_match or dow_match

        if not day_ok:
            # Advance to tomorrow
            dt = (dt + timedelta(days=1)).replace(hour=0, minute=0)
            continue

        # Check hour
        if dt.hour not in hours:
            next_hour = next((h for h in sorted(hours) if h > dt.hour), None)
            if next_hour is None:
                dt = (dt + timedelta(days=1)).replace(hour=0, minute=0)
            else:
                dt = dt.replace(hour=next_hour, minute=0)
            continue

        # Check minute
        if dt.minute not in minutes:
            next_minute = next((m for m in sorted(minutes) if m > dt.minute), None)
            if next_minute is None:
                # Advance to next hour
                dt = dt.replace(minute=0) + timedelta(hours=1)
            else:
                dt = dt.replace(minute=next_minute)
            continue

        # All fields match
        return dt

    raise ValueError(
        f"No execution time found within 4 years for cron expression: '{expr}'"
    )


def describe_cron(expr: str) -> str:
    """Return a human-readable description of a cron expression.

    Examples:
        "* * * * *"       → "Every minute"
        "*/5 * * * *"     → "Every 5 minutes"
        "0 * * * *"       → "Every hour"
        "0 9 * * *"       → "Daily at 09:00"
        "0 9 * * MON"     → "Every Monday at 09:00"
        "0 9 1 * *"       → "Monthly on day 1 at 09:00"
        "0 9 1 1 *"       → "Yearly on January 1 at 09:00"
        "30 6 * * 1-5"    → "Weekdays at 06:30"
        "0 0 1,15 * *"    → "On day 1,15 of the month at 00:00"

    Args:
        expr: A valid 5-field cron expression.

    Returns:
        Human-readable description string, or the raw expression if it cannot
        be described simply.
    """
    try:
        minutes, hours, doms, months, dows = _parse(expr)
    except ValueError:
        return expr

    parts = expr.strip().split()
    min_part, hr_part, dom_part, mon_part, dow_part = parts

    dom_star = dom_part == "*"
    dow_star = dow_part == "*"
    mon_star = mon_part == "*"
    hr_star = hr_part == "*"
    min_star = min_part == "*"

    # Build time string for "at HH:MM" clauses
    def _time_str() -> str:
        if len(hours) == 1 and len(minutes) == 1:
            h = next(iter(hours))
            m = next(iter(minutes))
            return f"{h:02d}:{m:02d}"
        return f"{hr_part}:{min_part}"

    # Every minute
    if min_star and hr_star and dom_star and mon_star and dow_star:
        return "Every minute"

    # Every N minutes
    if min_part.startswith("*/") and hr_star and dom_star and mon_star and dow_star:
        step = min_part[2:]
        return f"Every {step} minutes"

    # Every hour (at minute 0 or specific minute)
    if hr_star and dom_star and mon_star and dow_star:
        if min_part == "0":
            return "Every hour"
        if len(minutes) == 1:
            m = next(iter(minutes))
            return f"Every hour at :{m:02d}"

    # Weekdays (Mon-Fri)
    if dow_part in ("1-5", "MON-FRI") and dom_star and mon_star and not hr_star:
        return f"Weekdays at {_time_str()}"

    # Daily (no dom/dow restriction)
    if dom_star and dow_star and mon_star and not hr_star:
        return f"Daily at {_time_str()}"

    # Specific weekday(s)
    if dom_star and mon_star and not dow_star:
        if len(dows) == 1:
            dow_label = _DOW_LABELS[next(iter(dows))]
            return f"Every {dow_label} at {_time_str()}"

    # Monthly (specific dom, no dow)
    if not dom_star and dow_star and mon_star:
        if len(doms) == 1:
            day = next(iter(doms))
            return f"Monthly on day {day} at {_time_str()}"
        days_str = dom_part
        return f"On day {days_str} of the month at {_time_str()}"

    # Yearly (specific dom and month)
    if not dom_star and not mon_star and dow_star:
        if len(doms) == 1 and len(months) == 1:
            day = next(iter(doms))
            month = next(iter(months))
            return f"Yearly on {_MONTH_LABELS[month]} {day} at {_time_str()}"

    # Fallback: return the raw expression
    return expr
