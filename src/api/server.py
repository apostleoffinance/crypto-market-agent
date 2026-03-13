"""
FastAPI backend exposing the CoinGecko data layer as REST endpoints.

Run with:
    uvicorn src.api.server:app --reload --port 8000
"""

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
import pandas as pd
import os
import io
import re
import time
from collections import OrderedDict

from src.data.coingecko_client import CoinGeckoClient
from src.data.date_utils import (
    generate_quarter_dates,
    parse_quarter_string,
    quarter_start,
    quarter_end,
)
from src.data.analytics import SECTOR_MAP, get_sector

app = FastAPI(
    title="Crypto Market Agent API",
    description="Historical cryptocurrency market data for alternative investment analysis",
    version="1.0.0",
)

# In production, set ALLOWED_ORIGINS to your Vercel URL(s), comma-separated.
# Defaulting to an empty list rejects cross-origin requests unless explicitly configured.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
_allowed_origins = [o.strip().rstrip("/") for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins if _allowed_origins else [],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Lazy-init client
_client: CoinGeckoClient | None = None


def get_client() -> CoinGeckoClient:
    global _client
    if _client is None:
        _client = CoinGeckoClient()
    return _client


ALL_COLUMNS = ["date", "symbol", "name", "price", "market_cap", "volume"]

VALID_POSITIONS = {"start", "end", "both"}
VALID_INTERVALS = {"quarterly", "monthly", "yearly"}
_COIN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,99}$")


def _validate_position(position: str) -> str:
    if position not in VALID_POSITIONS:
        raise HTTPException(status_code=400, detail=f"position must be one of: {', '.join(VALID_POSITIONS)}")
    return position


def _validate_coin_id(coin_id: str) -> str:
    if not _COIN_ID_RE.match(coin_id):
        raise HTTPException(status_code=400, detail="Invalid coin_id format")
    return coin_id


# ── Rate limiter for chat ─────────────────────────────────────────────

_chat_rate: dict[str, list[float]] = {}
_CHAT_RATE_LIMIT = 10          # max requests per window
_CHAT_RATE_WINDOW = 60.0       # seconds


def _check_chat_rate(ip: str) -> None:
    now = time.monotonic()
    times = _chat_rate.get(ip, [])
    times = [t for t in times if now - t < _CHAT_RATE_WINDOW]
    if len(times) >= _CHAT_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
    times.append(now)
    _chat_rate[ip] = times


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

@app.get("/api/sectors")
def list_sectors():
    """Return the list of available token categories/sectors."""
    sectors = sorted(set(SECTOR_MAP.values()) | {"Other"})
    return {"sectors": sectors}


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
    _validate_position(position)
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
    exclude_sectors: Optional[str] = Query(None, description="Comma-separated sectors to exclude, e.g. 'Meme,Exchange'"),
):
    """Get top N coins by market cap at quarter boundaries."""
    _validate_position(position)
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

    # Fetch more candidates if we need to filter out sectors
    fetch_n = top_n * 3 if exclude_sectors else top_n
    df = client.get_top_n_at_dates(dates, top_n=fetch_n)

    if df.empty:
        return {"data": [], "total_rows": 0, "dates_queried": len(dates)}

    # Exclude sectors if requested
    if exclude_sectors:
        excluded = {s.strip() for s in exclude_sectors.split(",") if s.strip()}
        if "id" in df.columns:
            df["_sector"] = df["id"].map(get_sector)
            df = df[~df["_sector"].isin(excluded)]
            df = df.drop(columns=["_sector"])
        # Re-apply top_n per date after filtering
        if "date" in df.columns:
            df = (
                df.sort_values("market_cap", ascending=False)
                .groupby("date")
                .head(top_n)
                .reset_index(drop=True)
            )

    # Filter columns
    col_list = None
    if columns:
        col_list = [c.strip() for c in columns.split(",") if c.strip() in ALL_COLUMNS]

    available = [c for c in ALL_COLUMNS if c in df.columns]
    if col_list:
        available = [c for c in col_list if c in available]

    sort_cols = []
    sort_asc = []
    if "date" in available:
        sort_cols.append("date")
        sort_asc.append(True)
    if "market_cap" in df.columns:
        sort_cols.append("market_cap")
        sort_asc.append(False)
    if sort_cols:
        records = df[available].sort_values(sort_cols, ascending=sort_asc).to_dict(orient="records")
    else:
        records = df[available].to_dict(orient="records")

    return {"data": records, "total_rows": len(records), "dates_queried": len(dates)}


@app.get("/api/top-coins/export")
def export_top_coins_csv(
    top_n: int = Query(15, ge=1, le=100),
    start_year: int = Query(2020),
    end_year: Optional[int] = Query(None),
    position: str = Query("end"),
    quarters: Optional[str] = Query(None),
    columns: Optional[str] = Query(None),
    exclude_sectors: Optional[str] = Query(None),
):
    """Export top coins data as a downloadable CSV."""
    result = get_top_coins(
        top_n=top_n,
        start_year=start_year,
        end_year=end_year,
        position=position,
        quarters=quarters,
        columns=columns,
        exclude_sectors=exclude_sectors,
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
    _validate_coin_id(coin_id)
    client = get_client()
    try:
        dt = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    row = client.fetch_coin_at_date(coin_id, dt)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No data found for {coin_id} on {date}")

    if columns:
        col_list = [c.strip() for c in columns.split(",") if c.strip() in ALL_COLUMNS]
        if col_list:
            row = {k: v for k, v in row.items() if k in col_list}

    return {"data": row}


@app.get("/api/coin/{coin_id}/history")
def get_coin_history(
    coin_id: str,
    start_year: int = Query(2020, description="Start year"),
    end_year: Optional[int] = Query(None, description="End year"),
    interval: str = Query("quarterly", description="'quarterly', 'monthly', or 'yearly'"),
    position: str = Query("end", description="'start', 'end', or 'both' (quarterly only)"),
    columns: Optional[str] = Query(None, description="Comma-separated columns"),
):
    """Get a single coin's historical data across multiple dates."""
    _validate_coin_id(coin_id)
    _validate_position(position)
    if interval not in VALID_INTERVALS:
        raise HTTPException(status_code=400, detail=f"interval must be one of: {', '.join(VALID_INTERVALS)}")
    from src.agent.tools import _generate_monthly_dates, _generate_yearly_dates

    client = get_client()

    if interval == "monthly":
        dates = _generate_monthly_dates(start_year, end_year)
    elif interval == "yearly":
        dates = _generate_yearly_dates(start_year, end_year)
    else:
        end_date = None
        if end_year:
            end_date = datetime(end_year, 12, 31, tzinfo=timezone.utc)
        dates = generate_quarter_dates(
            start_year=start_year, end_date=end_date, position=position,
        )

    if not dates:
        raise HTTPException(status_code=400, detail="No valid dates for the given parameters.")

    rows = []
    for dt in dates:
        row = client.fetch_coin_at_date(coin_id, dt)
        if row:
            rows.append(row)

    if not rows:
        raise HTTPException(status_code=404, detail=f"No data found for {coin_id}")

    col_list = None
    if columns:
        col_list = [c.strip() for c in columns.split(",") if c.strip() in ALL_COLUMNS]

    records = rows
    if col_list:
        records = [{k: v for k, v in r.items() if k in col_list} for r in rows]

    return {"data": records, "total_rows": len(records), "coin_id": coin_id}


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


# ── Analytics ─────────────────────────────────────────────────────────

def _default_coin_ids(n: int = 20) -> list[str]:
    """Get the top N coin IDs from the current market data."""
    client = get_client()
    coins = client.get_current_top_coins(n_pages=1)
    return [c["id"] for c in coins[:n]]


@app.get("/api/analytics/correlation")
def get_correlation(
    days: int = Query(365, ge=30, le=1095, description="Number of days for price history"),
    top_n: int = Query(15, ge=2, le=30, description="Number of top coins to include"),
):
    """Compute a correlation matrix of daily log returns for top coins."""
    from src.data.analytics import compute_correlation_matrix
    coin_ids = _default_coin_ids(top_n)
    result = compute_correlation_matrix(get_client(), coin_ids, days=days)
    return result


@app.get("/api/analytics/risk-metrics")
def get_risk_metrics(
    days: int = Query(365, ge=30, le=1095, description="Lookback period in days"),
    top_n: int = Query(20, ge=1, le=50, description="Number of top coins"),
    risk_free_rate: float = Query(0.05, description="Annualised risk-free rate"),
):
    """Compute Sharpe, Sortino, max drawdown, VaR for top coins."""
    from src.data.analytics import compute_risk_metrics
    coin_ids = _default_coin_ids(top_n)
    metrics = compute_risk_metrics(get_client(), coin_ids, days=days, risk_free_rate=risk_free_rate)
    return {"data": metrics, "days": days, "risk_free_rate": risk_free_rate}


@app.get("/api/analytics/sectors")
def get_sector_performance(
    days: int = Query(365, ge=30, le=1095),
    top_n: int = Query(30, ge=5, le=60),
):
    """Compute sector-level aggregate performance metrics."""
    from src.data.analytics import compute_sector_performance
    coin_ids = _default_coin_ids(top_n)
    return compute_sector_performance(get_client(), coin_ids, days=days)


# ── Chat ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, max_length=100)


class ChatResponse(BaseModel):
    response: str
    session_id: str


# Store agent sessions in memory (keyed by session_id)
# Capped to prevent memory exhaustion
_MAX_SESSIONS = 200
_chat_sessions: OrderedDict = OrderedDict()


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    """Send a natural-language question to the AI agent and get an answer."""
    from src.agent.agent import CryptoAgent
    import uuid

    # Rate-limit by client IP
    client_ip = request.client.host if request.client else "unknown"
    _check_chat_rate(client_ip)

    sid = req.session_id or str(uuid.uuid4())

    # Reuse or create agent for this session
    if sid not in _chat_sessions:
        # Evict oldest session if at capacity
        while len(_chat_sessions) >= _MAX_SESSIONS:
            _chat_sessions.popitem(last=False)
        try:
            _chat_sessions[sid] = CryptoAgent()
        except ValueError:
            raise HTTPException(status_code=500, detail="Chat service unavailable")

    agent = _chat_sessions[sid]

    try:
        answer = agent.chat(req.message)
    except Exception:
        raise HTTPException(status_code=500, detail="An error occurred processing your request")

    return {"response": answer, "session_id": sid}


@app.post("/api/chat/reset")
def reset_chat(session_id: Optional[str] = Query(None)):
    """Reset a chat session."""
    if session_id and session_id in _chat_sessions:
        _chat_sessions[session_id].reset()
        return {"status": "reset", "session_id": session_id}
    return {"status": "no session found"}


# ── CSV file downloads ────────────────────────────────────────────────

@app.get("/api/exports/{filename}")
def download_export(filename: str):
    """Serve a CSV file from the exports directory."""
    from pathlib import Path

    # Strict filename validation: alphanumeric, hyphens, underscores, single .csv extension
    if not re.match(r'^[\w\-]+\.csv$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    exports_dir = Path(__file__).resolve().parents[2] / "exports"
    filepath = (exports_dir / filename).resolve()

    # Double-check the resolved path is inside exports_dir (defense in depth)
    if not str(filepath).startswith(str(exports_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    def _read_file():
        with open(filepath, "r") as f:
            yield f.read()

    return StreamingResponse(
        _read_file(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
