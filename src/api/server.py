"""
FastAPI backend exposing the CoinGecko data layer as REST endpoints.

Run with:
    uvicorn src.api.server:app --reload --port 8000
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional
import pandas as pd
import io

from src.data.coingecko_client import CoinGeckoClient
from src.data.date_utils import (
    generate_quarter_dates,
    parse_quarter_string,
    quarter_start,
    quarter_end,
)

app = FastAPI(
    title="Crypto Market Agent API",
    description="Historical cryptocurrency market data for alternative investment analysis",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-init client
_client: CoinGeckoClient | None = None


def get_client() -> CoinGeckoClient:
    global _client
    if _client is None:
        _client = CoinGeckoClient()
    return _client


ALL_COLUMNS = ["date", "symbol", "name", "price", "market_cap", "volume"]


# ── Schemas ───────────────────────────────────────────────────────────

class QuarterDatesResponse(BaseModel):
    dates: list[str]
    count: int


class CoinDataRow(BaseModel):
    date: str | None = None
    symbol: str | None = None
    name: str | None = None
    price: float | None = None
    market_cap: float | None = None
    volume: float | None = None


class TopCoinsResponse(BaseModel):
    data: list[dict]
    total_rows: int
    dates_queried: int


class SingleCoinResponse(BaseModel):
    data: dict


# ── Endpoints ─────────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now(tz=timezone.utc).isoformat()}


@app.get("/api/quarters", response_model=QuarterDatesResponse)
def list_quarter_dates(
    start_year: int = Query(2020, description="First year"),
    end_year: Optional[int] = Query(None, description="Last year (defaults to current)"),
    position: str = Query("end", description="'start', 'end', or 'both'"),
):
    """Return all available quarter boundary dates."""
    end_date = None
    if end_year:
        end_date = datetime(end_year, 12, 31, tzinfo=timezone.utc)
    dates = generate_quarter_dates(
        start_year=start_year,
        end_date=end_date,
        position=position,
    )
    date_strs = [d.strftime("%Y-%m-%d") for d in dates]
    return {"dates": date_strs, "count": len(date_strs)}


@app.get("/api/top-coins", response_model=TopCoinsResponse)
def get_top_coins(
    top_n: int = Query(15, ge=1, le=100, description="Number of top coins per date"),
    start_year: int = Query(2020, description="Start year"),
    end_year: Optional[int] = Query(None, description="End year"),
    position: str = Query("end", description="'start', 'end', or 'both'"),
    quarters: Optional[str] = Query(None, description="Comma-separated quarters like '2024-Q1,2024-Q4'"),
    columns: Optional[str] = Query(None, description="Comma-separated columns like 'date,price,market_cap'"),
):
    """Get top N coins by market cap at quarter boundaries."""
    client = get_client()

    # Build dates
    if quarters:
        quarter_list = [q.strip() for q in quarters.split(",")]
        dates = []
        for qs in quarter_list:
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
        raise HTTPException(status_code=400, detail="No valid dates for the given parameters.")

    df = client.get_top_n_at_dates(dates, top_n=top_n)

    if df.empty:
        return {"data": [], "total_rows": 0, "dates_queried": len(dates)}

    # Filter columns
    col_list = None
    if columns:
        col_list = [c.strip() for c in columns.split(",") if c.strip() in ALL_COLUMNS]

    available = [c for c in ALL_COLUMNS if c in df.columns]
    if col_list:
        available = [c for c in col_list if c in available]

    records = df[available].sort_values("date" if "date" in available else available[0]).to_dict(orient="records")

    return {"data": records, "total_rows": len(records), "dates_queried": len(dates)}


@app.get("/api/top-coins/export")
def export_top_coins_csv(
    top_n: int = Query(15, ge=1, le=100),
    start_year: int = Query(2020),
    end_year: Optional[int] = Query(None),
    position: str = Query("end"),
    quarters: Optional[str] = Query(None),
    columns: Optional[str] = Query(None),
):
    """Export top coins data as a downloadable CSV."""
    result = get_top_coins(
        top_n=top_n,
        start_year=start_year,
        end_year=end_year,
        position=position,
        quarters=quarters,
        columns=columns,
    )
    df = pd.DataFrame(result["data"])
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    stream.seek(0)

    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=top_coins_quarterly.csv"},
    )


@app.get("/api/coin/{coin_id}")
def get_coin_at_date(
    coin_id: str,
    date: str = Query(..., description="Date as YYYY-MM-DD"),
    columns: Optional[str] = Query(None),
):
    """Get a single coin's data at a specific date."""
    client = get_client()
    dt = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    row = client.fetch_coin_at_date(coin_id, dt)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No data found for {coin_id} on {date}")

    if columns:
        col_list = [c.strip() for c in columns.split(",") if c.strip() in ALL_COLUMNS]
        if col_list:
            row = {k: v for k, v in row.items() if k in col_list}

    return {"data": row}


@app.get("/api/summary")
def get_summary():
    """Get summary statistics for the dashboard.
    Reads from the joblib cache for instant results — no API calls."""
    import joblib
    from src.data.coingecko_client import CACHE_PATH

    empty = {
        "total_quarters": 0,
        "unique_coins_tracked": 0,
        "date_range": "",
        "top_coin": None,
        "total_data_points": 0,
    }

    if not CACHE_PATH.exists():
        return empty

    try:
        df = joblib.load(CACHE_PATH)
    except Exception:
        return empty

    if df.empty or "date" not in df.columns:
        return empty

    # Most recent date's #1 coin
    latest_date = df["date"].max()
    latest_df = df[df["date"] == latest_date].sort_values("market_cap", ascending=False)
    top_coin = None
    if not latest_df.empty:
        row = latest_df.iloc[0]
        top_coin = {
            "symbol": str(row.get("symbol", "")),
            "name": str(row.get("name", "")),
            "price": float(row.get("price", 0)),
            "market_cap": float(row.get("market_cap", 0)),
        }

    return {
        "total_quarters": int(df["date"].nunique()),
        "unique_coins_tracked": int(df["symbol"].nunique()) if "symbol" in df.columns else 0,
        "date_range": f"{df['date'].min()} to {df['date'].max()}",
        "top_coin": top_coin,
        "total_data_points": len(df),
    }
