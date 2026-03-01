"""
OpenAI function-calling tool definitions + implementations.

Two tools:
  1. get_top_coins_quarterly  – top N coins at quarter start / end / both
  2. get_coin_price_at_date   – single coin lookup on any date
"""

import json
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
    """Save data as CSV and return the file path."""
    df = pd.DataFrame(data)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.csv"
    filepath = EXPORT_DIR / filename
    df.to_csv(filepath, index=False)
    return str(filepath)


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
                "Get a single coin's data on a specific date. "
                "Can query any date. Supports column filtering and CSV export."
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
        csv_path = _export_to_csv(records, "top_coins_quarterly")
        response["csv_file"] = csv_path
        response["message"] = f"CSV saved to: {csv_path}"

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
        csv_path = _export_to_csv(records, f"{coin_id}_{date}")
        response["csv_file"] = csv_path
        response["message"] = f"CSV saved to: {csv_path}"

    return json.dumps(response, default=str)


# ═══════════════════════════════════════════════════════════════════════
#  Dispatcher
# ═══════════════════════════════════════════════════════════════════════

TOOL_MAP = {
    "get_top_coins_quarterly": get_top_coins_quarterly,
    "get_coin_price_at_date": get_coin_price_at_date,
}


def call_tool(name: str, arguments: dict) -> str:
    fn = TOOL_MAP.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    return fn(**arguments)
