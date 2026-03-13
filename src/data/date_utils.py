"""
Quarter-date arithmetic.
"""

import pandas as pd
from datetime import timezone, datetime


def quarter_start(year: int, quarter: int) -> datetime:
    """First day of the quarter, UTC."""
    month = (quarter - 1) * 3 + 1
    return datetime(year, month, 1, tzinfo=timezone.utc)


def quarter_end(year: int, quarter: int) -> datetime:
    """Last day of the quarter, UTC."""
    end_month = quarter * 3
    last = pd.Timestamp(year=year, month=end_month, day=1) + pd.offsets.MonthEnd(0)
    return datetime(last.year, last.month, last.day, tzinfo=timezone.utc)


def parse_quarter_string(q_str: str) -> tuple[int, int]:
    """'2024-Q1' → (2024, 1). Raises ValueError on bad format."""
    try:
        year_s, q_s = q_str.split("-Q")
        year, quarter = int(year_s), int(q_s)
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid quarter string: '{q_str}'. Expected format: '2024-Q1'.")
    if quarter < 1 or quarter > 4:
        raise ValueError(f"Quarter must be 1–4, got {quarter}.")
    return year, quarter


def generate_quarter_dates(
    start_year: int = 2020,
    end_date: datetime | None = None,
    position: str = "end",
) -> list[datetime]:
    """
    Build a sorted list of quarter boundary dates.

    Parameters
    ----------
    start_year : first year to include
    end_date   : last date to include (defaults to now; can be a future date)
    position   : "start" | "end" | "both"
    """
    if end_date is None:
        end_date = datetime.now(tz=timezone.utc)

    dates: list[datetime] = []
    for year in range(start_year, end_date.year + 1):
        for q in range(1, 5):
            s = quarter_start(year, q)
            e = quarter_end(year, q)

            # Include quarter start if it's within range
            if position in ("start", "both") and s <= end_date:
                dates.append(s)

            # Include quarter end if it's within range
            if position in ("end", "both") and e <= end_date:
                dates.append(e)

    return sorted(set(dates))
