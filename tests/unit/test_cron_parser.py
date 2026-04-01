"""Unit tests for the cron expression parser.

Covers:
- Valid and invalid expression parsing
- next_run calculation across edge cases
- validate_cron error messages
- describe_cron human-readable output
"""

from datetime import UTC, datetime

import pytest

from snackbase.core.cron.parser import describe_cron, get_next_run, validate_cron


# ---------------------------------------------------------------------------
# validate_cron — valid expressions
# ---------------------------------------------------------------------------


class TestValidCron:
    def test_every_minute(self):
        ok, err = validate_cron("* * * * *")
        assert ok is True
        assert err == ""

    def test_specific_time(self):
        ok, err = validate_cron("0 9 * * *")
        assert ok is True

    def test_step_syntax(self):
        ok, err = validate_cron("*/5 * * * *")
        assert ok is True

    def test_range_syntax(self):
        ok, err = validate_cron("0 9-17 * * *")
        assert ok is True

    def test_list_syntax(self):
        ok, err = validate_cron("0 0 1,15 * *")
        assert ok is True

    def test_named_dow(self):
        ok, err = validate_cron("0 9 * * MON")
        assert ok is True

    def test_named_month(self):
        ok, err = validate_cron("0 0 1 JAN *")
        assert ok is True

    def test_weekday_range(self):
        ok, err = validate_cron("30 6 * * 1-5")
        assert ok is True

    def test_mixed_list_and_range(self):
        ok, err = validate_cron("0 8,12,18 * * *")
        assert ok is True

    def test_dow_7_treated_as_sunday(self):
        ok, err = validate_cron("0 0 * * 7")
        assert ok is True

    def test_range_with_step(self):
        ok, err = validate_cron("0 0-23/2 * * *")
        assert ok is True

    def test_all_named_dow(self):
        for name in ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]:
            ok, err = validate_cron(f"0 0 * * {name}")
            assert ok is True, f"Expected valid for DOW={name}, got error: {err}"

    def test_all_named_months(self):
        for name in ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                     "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]:
            ok, err = validate_cron(f"0 0 1 {name} *")
            assert ok is True, f"Expected valid for month={name}, got error: {err}"


# ---------------------------------------------------------------------------
# validate_cron — invalid expressions
# ---------------------------------------------------------------------------


class TestInvalidCron:
    def test_too_few_fields(self):
        ok, err = validate_cron("* * * *")
        assert ok is False
        assert "5 fields" in err

    def test_too_many_fields(self):
        ok, err = validate_cron("* * * * * *")
        assert ok is False
        assert "5 fields" in err

    def test_empty_string(self):
        ok, err = validate_cron("")
        assert ok is False

    def test_minute_out_of_range(self):
        ok, err = validate_cron("60 * * * *")
        assert ok is False
        assert "minute" in err.lower()

    def test_hour_out_of_range(self):
        ok, err = validate_cron("0 24 * * *")
        assert ok is False
        assert "hour" in err.lower()

    def test_dom_out_of_range(self):
        ok, err = validate_cron("0 0 32 * *")
        assert ok is False
        assert "day-of-month" in err.lower()

    def test_dom_zero(self):
        ok, err = validate_cron("0 0 0 * *")
        assert ok is False

    def test_month_out_of_range(self):
        ok, err = validate_cron("0 0 1 13 *")
        assert ok is False
        assert "month" in err.lower()

    def test_dow_out_of_range(self):
        ok, err = validate_cron("0 0 * * 8")
        assert ok is False
        assert "day-of-week" in err.lower()

    def test_invalid_step(self):
        ok, err = validate_cron("*/0 * * * *")
        assert ok is False
        assert "step" in err.lower()

    def test_non_numeric_value(self):
        ok, err = validate_cron("abc * * * *")
        assert ok is False

    def test_invalid_range_start_gt_end(self):
        ok, err = validate_cron("0 10-5 * * *")
        assert ok is False
        assert "start" in err.lower() or ">" in err

    def test_range_out_of_bounds(self):
        ok, err = validate_cron("0 0-25 * * *")
        assert ok is False


# ---------------------------------------------------------------------------
# get_next_run — basic functionality
# ---------------------------------------------------------------------------


class TestGetNextRun:
    def test_every_minute_advances_one_minute(self):
        now = datetime(2026, 1, 1, 12, 0, 0)
        nxt = get_next_run("* * * * *", now)
        assert nxt == datetime(2026, 1, 1, 12, 1, 0)

    def test_result_strips_seconds(self):
        now = datetime(2026, 1, 1, 12, 0, 30)  # 30 seconds past
        nxt = get_next_run("* * * * *", now)
        assert nxt.second == 0
        assert nxt.microsecond == 0

    def test_result_is_at_least_one_minute_after_from_dt(self):
        now = datetime(2026, 1, 1, 12, 0, 0)
        nxt = get_next_run("0 12 * * *", now)
        assert nxt > now

    def test_specific_hour_and_minute(self):
        now = datetime(2026, 1, 1, 8, 0, 0)
        nxt = get_next_run("30 9 * * *", now)
        assert nxt == datetime(2026, 1, 1, 9, 30, 0)

    def test_next_day_if_time_passed(self):
        now = datetime(2026, 1, 1, 10, 0, 0)
        nxt = get_next_run("0 9 * * *", now)  # 9:00 already passed
        assert nxt == datetime(2026, 1, 2, 9, 0, 0)

    def test_every_5_minutes(self):
        now = datetime(2026, 1, 1, 12, 0, 0)
        nxt = get_next_run("*/5 * * * *", now)
        assert nxt == datetime(2026, 1, 1, 12, 5, 0)

    def test_every_5_minutes_mid_interval(self):
        now = datetime(2026, 1, 1, 12, 3, 0)
        nxt = get_next_run("*/5 * * * *", now)
        assert nxt == datetime(2026, 1, 1, 12, 5, 0)

    def test_hourly(self):
        now = datetime(2026, 1, 1, 12, 30, 0)
        nxt = get_next_run("0 * * * *", now)
        assert nxt == datetime(2026, 1, 1, 13, 0, 0)

    def test_monthly_first_day(self):
        now = datetime(2026, 1, 15, 0, 0, 0)
        nxt = get_next_run("0 0 1 * *", now)
        assert nxt == datetime(2026, 2, 1, 0, 0, 0)

    def test_specific_day_of_week_monday(self):
        # 2026-01-01 is a Thursday; next Monday is 2026-01-05
        now = datetime(2026, 1, 1, 0, 0, 0)
        nxt = get_next_run("0 9 * * MON", now)
        assert nxt == datetime(2026, 1, 5, 9, 0, 0)

    def test_year_rollover(self):
        now = datetime(2025, 12, 31, 23, 59, 0)
        nxt = get_next_run("0 0 1 1 *", now)
        assert nxt == datetime(2026, 1, 1, 0, 0, 0)

    def test_month_boundary(self):
        now = datetime(2026, 1, 31, 23, 59, 0)
        nxt = get_next_run("0 0 1 * *", now)
        assert nxt == datetime(2026, 2, 1, 0, 0, 0)

    def test_leap_year_feb_29(self):
        # 2028 is a leap year
        now = datetime(2028, 2, 28, 0, 0, 0)
        nxt = get_next_run("0 0 29 2 *", now)
        assert nxt == datetime(2028, 2, 29, 0, 0, 0)

    def test_non_leap_year_feb_29_skips_to_next_leap(self):
        # 2026 is not a leap year; next Feb 29 is 2028
        now = datetime(2026, 2, 1, 0, 0, 0)
        nxt = get_next_run("0 0 29 2 *", now)
        assert nxt.year == 2028
        assert nxt.month == 2
        assert nxt.day == 29

    def test_dom_and_dow_or_logic(self):
        # "Every 1st of month OR every Monday"
        # 2026-01-01 is Thursday, 2026-01-02 is Friday, 2026-01-05 is Monday
        now = datetime(2026, 1, 1, 12, 0, 0)
        nxt = get_next_run("0 0 1 * MON", now)
        # Next occurrence: 2026-01-05 (Monday) OR 2026-02-01 (1st of month)
        # Monday comes first
        assert nxt == datetime(2026, 1, 5, 0, 0, 0)

    def test_list_of_days(self):
        now = datetime(2026, 1, 1, 12, 0, 0)
        nxt = get_next_run("0 0 1,15 * *", now)
        assert nxt == datetime(2026, 1, 15, 0, 0, 0)

    def test_list_wraps_to_next_month(self):
        now = datetime(2026, 1, 15, 12, 0, 0)
        nxt = get_next_run("0 0 1,15 * *", now)
        assert nxt == datetime(2026, 2, 1, 0, 0, 0)

    def test_weekday_range(self):
        # 2026-01-01 is Thursday (cron 4); next day is Friday (5), within 1-5
        now = datetime(2026, 1, 1, 6, 31, 0)
        nxt = get_next_run("30 6 * * 1-5", now)
        assert nxt == datetime(2026, 1, 2, 6, 30, 0)

    def test_raises_on_impossible_expression(self):
        # Feb 31 never exists
        now = datetime(2026, 1, 1, 0, 0, 0)
        with pytest.raises(ValueError, match="No execution time"):
            get_next_run("0 0 31 2 *", now)

    def test_invalid_expression_raises(self):
        with pytest.raises(ValueError):
            get_next_run("not a cron", datetime.now(UTC).replace(tzinfo=None))

    def test_dow_7_treated_as_sunday(self):
        # 2026-01-04 is a Sunday
        now = datetime(2026, 1, 1, 0, 0, 0)
        nxt = get_next_run("0 0 * * 7", now)
        assert nxt.weekday() == 6  # Python: 6 = Sunday

    def test_minute_list(self):
        now = datetime(2026, 1, 1, 12, 0, 0)
        nxt = get_next_run("10,30,50 * * * *", now)
        assert nxt == datetime(2026, 1, 1, 12, 10, 0)

    def test_step_from_value(self):
        now = datetime(2026, 1, 1, 0, 0, 0)
        nxt = get_next_run("0 2/4 * * *", now)
        assert nxt == datetime(2026, 1, 1, 2, 0, 0)


# ---------------------------------------------------------------------------
# describe_cron
# ---------------------------------------------------------------------------


class TestDescribeCron:
    def test_every_minute(self):
        assert describe_cron("* * * * *") == "Every minute"

    def test_every_5_minutes(self):
        assert describe_cron("*/5 * * * *") == "Every 5 minutes"

    def test_every_hour(self):
        assert describe_cron("0 * * * *") == "Every hour"

    def test_daily(self):
        assert describe_cron("0 9 * * *") == "Daily at 09:00"

    def test_weekly_monday(self):
        result = describe_cron("0 9 * * MON")
        assert "Monday" in result
        assert "09:00" in result

    def test_monthly(self):
        result = describe_cron("0 0 1 * *")
        assert "Monthly" in result or "day 1" in result
        assert "00:00" in result

    def test_weekdays(self):
        result = describe_cron("30 6 * * 1-5")
        assert "Weekday" in result
        assert "06:30" in result

    def test_invalid_returns_raw(self):
        raw = "not valid"
        assert describe_cron(raw) == raw

    def test_yearly(self):
        result = describe_cron("0 0 1 1 *")
        assert "January" in result or "Yearly" in result
