"""
OpenAI function-calling tool definitions + implementations.

Two tools:
  1. get_top_coins_quarterly  – top N coins at quarter start / end / both
  2. get_coin_price_at_date   – single coin lookup on any date
"""

import json
import os
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

from src.data.coingecko_client import CoinGeckoClient
from src.data.date_utils import (
    generate_quarter_dates,
    parse_quarter_string,
    quarter_start,
    quarter_end,
)

_client: CoinGeckoClient | None = None

EXPORT_DIR = Path(__file__).resolve().parents[2] / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

# Base URL for building download links (set in Railway env)
_BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

ALL_COLUMNS = ["date", "symbol", "name", "price", "market_cap", "volume"]


def _get_client() -> CoinGeckoClient:
    global _client
    if _client is None:
        _client = CoinGeckoClient()
    return _client


def _filter_columns(data: list[dict], columns: list = None) -> list[dict]:
    """Keep only the requested columns from each row."""
    if not columns:
        return data
    valid = [c for c in columns if c in ALL_COLUMNS]
    if not valid:
        return data
    return [{k: row.get(k) for k in valid} for row in data]


def _export_to_csv(data: list[dict], filename_prefix: str) -> str:
    """Save data as CSV and return the filename (not full path)."""
    df = pd.DataFrame(data)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.csv"
    filepath = EXPORT_DIR / filename
    df.to_csv(filepath, index=False)
    return filename


# ═══════════════════════════════════════════════════════════════════════
#  JSON schemas exposed to the LLM
# ═══════════════════════════════════════════════════════════════════════

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_top_coins_quarterly",
            "description": (
                "Get the top N cryptocurrencies by market cap at the start and/or end "
                "of each quarter. Can query ANY year — past or future. "
                "Supports column filtering and CSV export. "
                "Use this whenever the user asks about top coins, quarterly rankings, "
                "market cap over time, or historical crypto prices at quarter boundaries."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "top_n": {
                        "type": "integer",
                        "description": "Number of top coins per date (default 15)",
                        "default": 15,
                    },
                    "start_year": {
                        "type": "integer",
                        "description": "Year to start from (default 2020)",
                        "default": 2020,
                    },
                    "end_year": {
                        "type": "integer",
                        "description": "Year to end at (optional, defaults to current year).",
                    },
                    "position": {
                        "type": "string",
                        "enum": ["start", "end", "both"],
                        "description": "'start' for quarter beginning, 'end' for quarter end, 'both' for both (default 'end')",
                        "default": "end",
                    },
                    "quarters": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional specific quarter strings like ['2024-Q1','2025-Q1']. "
                            "If omitted, all quarters from start_year to end_year are used."
                        ),
                    },
                    "columns": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["date", "symbol", "name", "price", "market_cap", "volume"]
                        },
                        "description": (
                            "Which columns to include in the result. "
                            "Available: date, symbol, name, price, market_cap, volume. "
                            "If omitted, all columns are returned. "
                            "Example: ['date', 'price', 'market_cap'] for only those columns."
                        ),
                    },
                    "export_csv": {
                        "type": "boolean",
                        "description": (
                            "If true, save the result as a CSV file. "
                            "Set to true when the user asks to download, export, or save as CSV."
                        ),
                        "default": False,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_coin_price_at_date",
            "description": (
                "Get a single coin's data on ONE specific date. "
                "Use this only when the user asks about a coin on a single date. "
                "For multiple dates, use get_coin_history instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "coin_id": {
                        "type": "string",
                        "description": "CoinGecko coin id, e.g. 'bitcoin', 'ethereum'",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (any date allowed)",
                    },
                    "columns": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["date", "symbol", "name", "price", "market_cap", "volume"]
                        },
                        "description": "Which columns to include. If omitted, all columns are returned.",
                    },
                    "export_csv": {
                        "type": "boolean",
                        "description": "If true, save as CSV and return the file path.",
                        "default": False,
                    },
                },
                "required": ["coin_id", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_coin_history",
            "description": (
                "Get a SINGLE coin's historical data across multiple dates. "
                "Use this when the user asks for one specific coin's price/market cap/volume "
                "over a time range (e.g. 'BTC price from 2020 to 2022 quarterly', "
                "'Ethereum monthly data for 2024', 'Solana price every quarter from 2021'). "
                "Supports quarterly, monthly, or custom date intervals. "
                "Do NOT use get_top_coins_quarterly for single-coin history."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "coin_id": {
                        "type": "string",
                        "description": "CoinGecko coin id, e.g. 'bitcoin', 'ethereum', 'solana'",
                    },
                    "start_year": {
                        "type": "integer",
                        "description": "Year to start from",
                    },
                    "end_year": {
                        "type": "integer",
                        "description": "Year to end at (defaults to current year)",
                    },
                    "interval": {
                        "type": "string",
                        "enum": ["quarterly", "monthly", "yearly"],
                        "description": "How often to sample data. 'quarterly' = every quarter end, 'monthly' = every month end, 'yearly' = every year end.",
                        "default": "quarterly",
                    },
                    "position": {
                        "type": "string",
                        "enum": ["start", "end", "both"],
                        "description": "For quarterly interval: 'start', 'end', or 'both'. Ignored for monthly/yearly.",
                        "default": "end",
                    },
                    "dates": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of specific dates (YYYY-MM-DD). If provided, start_year/end_year/interval are ignored.",
                    },
                    "columns": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["date", "symbol", "name", "price", "market_cap", "volume"]
                        },
                        "description": "Which columns to include. If omitted, all columns are returned.",
                    },
                    "export_csv": {
                        "type": "boolean",
                        "description": "If true, save result as a downloadable CSV.",
                        "default": False,
                    },
                },
                "required": ["coin_id"],
            },
        },
    },
]


# ═══════════════════════════════════════════════════════════════════════
#  Implementations
# ═══════════════════════════════════════════════════════════════════════

def get_top_coins_quarterly(
    top_n: int = 15,
    start_year: int = 2020,
    end_year: int = None,
    position: str = "end",
    quarters: list = None,
    columns: list = None,
    export_csv: bool = False,
) -> str:
    """Fetch quarterly top-N data and return a JSON string."""
    client = _get_client()

    if quarters:
        dates = []
        for qs in quarters:
            y, q = parse_quarter_string(qs)
            if position in ("start", "both"):
                dates.append(quarter_start(y, q))
            if position in ("end", "both"):
                dates.append(quarter_end(y, q))
        dates = sorted(set(dates))
    else:
        end_date = None
        if end_year:
            end_date = datetime(end_year, 12, 31, tzinfo=timezone.utc)
        dates = generate_quarter_dates(
            start_year=start_year,
            end_date=end_date,
            position=position,
        )

    if not dates:
        return json.dumps({"error": "No valid dates generated for the given parameters."})

    def progress(msg):
        print(f"  📊  {msg}")

    df = client.get_top_n_at_dates(dates, top_n=top_n, progress_cb=progress)

    if df.empty:
        return json.dumps({"error": "No data found for the requested dates."})

    # Build full records first
    available = [c for c in ALL_COLUMNS if c in df.columns]
    records = df[available].sort_values("date").to_dict(orient="records")

    # Filter to requested columns
    records = _filter_columns(records, columns)

    response = {"data": records, "total_rows": len(records)}

    if export_csv:
        csv_filename = _export_to_csv(records, "top_coins_quarterly")
        download_url = f"{_BASE_URL}/api/exports/{csv_filename}"
        response["csv_file"] = csv_filename
        response["download_url"] = download_url
        response["message"] = f"CSV ready for download: [Download CSV]({download_url})"

    return json.dumps(response, default=str)


def get_coin_price_at_date(
    coin_id: str,
    date: str,
    columns: list = None,
    export_csv: bool = False,
) -> str:
    """Single-coin lookup."""
    client = _get_client()
    dt = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    print(f"  📊  Fetching {coin_id} on {date}…")
    row = client.fetch_coin_at_date(coin_id, dt)
    if row is None:
        return json.dumps({"error": f"No data found for {coin_id} on {date}."})

    records = _filter_columns([row], columns)
    response = {"data": records}

    if export_csv:
        csv_filename = _export_to_csv(records, f"{coin_id}_{date}")
        download_url = f"{_BASE_URL}/api/exports/{csv_filename}"
        response["csv_file"] = csv_filename
        response["download_url"] = download_url
        response["message"] = f"CSV ready for download: [Download CSV]({download_url})"

    return json.dumps(response, default=str)


def get_coin_history(
    coin_id: str,
    start_year: int = 2020,
    end_year: int = None,
    interval: str = "quarterly",
    position: str = "end",
    dates: list = None,
    columns: list = None,
    export_csv: bool = False,
) -> str:
    """Fetch a single coin's data across multiple dates."""
    client = _get_client()

    if dates:
        # User-specified custom dates
        date_objects = [
            datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            for d in dates
        ]
    elif interval == "monthly":
        date_objects = _generate_monthly_dates(start_year, end_year)
    elif interval == "yearly":
        date_objects = _generate_yearly_dates(start_year, end_year)
    else:
        # quarterly (default)
        end_date = None
        if end_year:
            end_date = datetime(end_year, 12, 31, tzinfo=timezone.utc)
        date_objects = generate_quarter_dates(
            start_year=start_year,
            end_date=end_date,
            position=position,
        )

    if not date_objects:
        return json.dumps({"error": "No valid dates for the given parameters."})

    print(f"  📊  Fetching {coin_id} across {len(date_objects)} dates…")

    rows = []
    for dt in date_objects:
        print(f"  ⏳  {coin_id} on {dt.strftime('%Y-%m-%d')}…")
        row = client.fetch_coin_at_date(coin_id, dt)
        if row:
            rows.append(row)

    if not rows:
        return json.dumps({"error": f"No data found for {coin_id} in the given date range."})

    records = _filter_columns(rows, columns)
    response = {"data": records, "total_rows": len(records), "coin_id": coin_id}

    if export_csv:
        csv_filename = _export_to_csv(records, f"{coin_id}_history")
        download_url = f"{_BASE_URL}/api/exports/{csv_filename}"
        response["csv_file"] = csv_filename
        response["download_url"] = download_url
        response["message"] = f"CSV ready for download: [Download CSV]({download_url})"

    return json.dumps(response, default=str)


def _generate_monthly_dates(start_year: int, end_year: int = None) -> list:
    """Generate month-end dates."""
    now = datetime.now(tz=timezone.utc)
    if end_year is None:
        end_year = now.year
    dates = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            last_day = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)
            dt = datetime(last_day.year, last_day.month, last_day.day, tzinfo=timezone.utc)
            if dt <= now:
                dates.append(dt)
    return sorted(dates)


def _generate_yearly_dates(start_year: int, end_year: int = None) -> list:
    """Generate year-end dates (Dec 31)."""
    now = datetime.now(tz=timezone.utc)
    if end_year is None:
        end_year = now.year
    dates = []
    for year in range(start_year, end_year + 1):
        dt = datetime(year, 12, 31, tzinfo=timezone.utc)
        if dt <= now:
            dates.append(dt)
    return sorted(dates)


# ═══════════════════════════════════════════════════════════════════════
#  Dispatcher
# ═══════════════════════════════════════════════════════════════════════

TOOL_MAP = {
    "get_top_coins_quarterly": get_top_coins_quarterly,
    "get_coin_price_at_date": get_coin_price_at_date,
    "get_coin_history": get_coin_history,
}


def call_tool(name: str, arguments: dict) -> str:
    fn = TOOL_MAP.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    return fn(**arguments)
