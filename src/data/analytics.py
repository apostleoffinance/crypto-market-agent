"""
Analytics module — correlation matrices, risk metrics, sector performance.

All computations use the cached quarterly data (joblib) plus the CoinGecko
market_chart/range endpoint for daily price series when needed.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Optional

from src.data.coingecko_client import CoinGeckoClient, CACHE_PATH

# ── Sector definitions ────────────────────────────────────────────────
# Map CoinGecko coin IDs → sector. Covers top ~60 coins.
SECTOR_MAP: dict[str, str] = {
    # Layer 1
    "bitcoin": "Layer 1",
    "ethereum": "Layer 1",
    "solana": "Layer 1",
    "cardano": "Layer 1",
    "avalanche-2": "Layer 1",
    "polkadot": "Layer 1",
    "near": "Layer 1",
    "cosmos": "Layer 1",
    "algorand": "Layer 1",
    "aptos": "Layer 1",
    "sui": "Layer 1",
    "toncoin": "Layer 1",
    "internet-computer": "Layer 1",
    "hedera-hashgraph": "Layer 1",
    "kaspa": "Layer 1",
    # Layer 2
    "matic-network": "Layer 2",
    "arbitrum": "Layer 2",
    "optimism": "Layer 2",
    "starknet": "Layer 2",
    "immutable-x": "Layer 2",
    "mantle": "Layer 2",
    # DeFi
    "uniswap": "DeFi",
    "aave": "DeFi",
    "lido-dao": "DeFi",
    "maker": "DeFi",
    "chainlink": "DeFi",
    "the-graph": "DeFi",
    "jupiter-exchange-solana": "DeFi",
    "raydium": "DeFi",
    "pendle": "DeFi",
    "ethena": "DeFi",
    # Exchange tokens
    "binancecoin": "Exchange",
    "crypto-com-chain": "Exchange",
    "okb": "Exchange",
    "leo-token": "Exchange",
    "kucoin-shares": "Exchange",
    # Meme
    "dogecoin": "Meme",
    "shiba-inu": "Meme",
    "pepe": "Meme",
    "bonk": "Meme",
    "floki": "Meme",
    "dogwifcoin": "Meme",
    # AI
    "render-token": "AI",
    "fetch-ai": "AI",
    "bittensor": "AI",
    "akash-network": "AI",
    # RWA / Payments
    "ripple": "Payments",
    "stellar": "Payments",
    "ondo-finance": "RWA",
    # Storage / Infra
    "filecoin": "Infrastructure",
    "arweave": "Infrastructure",
}


def get_sector(coin_id: str) -> str:
    return SECTOR_MAP.get(coin_id, "Other")


# ── Daily price fetcher ───────────────────────────────────────────────

def _fetch_daily_prices(
    client: CoinGeckoClient,
    coin_id: str,
    days: int = 365,
) -> pd.Series:
    """
    Fetch daily prices for a coin over the last N days.
    Returns a pd.Series indexed by date.
    """
    now = datetime.now(tz=timezone.utc)
    from_ts = int((now - timedelta(days=days)).timestamp())
    to_ts = int(now.timestamp())

    try:
        data = client._get(f"/coins/{coin_id}/market_chart/range", {
            "vs_currency": "usd",
            "from": from_ts,
            "to": to_ts,
        })
    except Exception:
        return pd.Series(dtype=float)

    if "prices" not in data or not data["prices"]:
        return pd.Series(dtype=float)

    df = pd.DataFrame(data["prices"], columns=["ts", "price"])
    df["date"] = pd.to_datetime(df["ts"], unit="ms").dt.date
    # Keep one price per day (last value)
    daily = df.groupby("date")["price"].last()
    return daily


# ── Correlation matrix ────────────────────────────────────────────────

def compute_correlation_matrix(
    client: CoinGeckoClient,
    coin_ids: list[str],
    days: int = 365,
) -> dict:
    """
    Compute pairwise price correlation for the given coins
    using daily log returns over the last N days.
    """
    price_data = {}
    for cid in coin_ids:
        series = _fetch_daily_prices(client, cid, days=days)
        if len(series) > 10:
            price_data[cid] = series

    if len(price_data) < 2:
        return {"error": "Not enough data to compute correlations."}

    # Align dates and compute log returns
    prices_df = pd.DataFrame(price_data)
    prices_df = prices_df.dropna(axis=0, how="any")

    if len(prices_df) < 10:
        return {"error": "Not enough overlapping data points."}

    log_returns = np.log(prices_df / prices_df.shift(1)).dropna()
    corr = log_returns.corr()

    coins = list(corr.columns)
    matrix = corr.values.tolist()

    return {
        "coins": coins,
        "matrix": [[round(v, 4) for v in row] for row in matrix],
        "days": days,
        "data_points": len(log_returns),
    }


# ── Risk metrics ──────────────────────────────────────────────────────

def compute_risk_metrics(
    client: CoinGeckoClient,
    coin_ids: list[str],
    days: int = 365,
    risk_free_rate: float = 0.05,
) -> list[dict]:
    """
    Compute risk metrics for each coin:
    - Annualised return, volatility
    - Sharpe ratio, Sortino ratio
    - Max drawdown
    - Value at Risk (95%, 99%)
    """
    results = []

    for cid in coin_ids:
        series = _fetch_daily_prices(client, cid, days=days)
        if len(series) < 30:
            continue

        prices = series.values.astype(float)
        daily_returns = np.diff(np.log(prices))

        if len(daily_returns) < 10:
            continue

        # Annualised return
        total_return = (prices[-1] / prices[0]) - 1
        ann_return = (1 + total_return) ** (365 / len(prices)) - 1

        # Annualised volatility
        ann_vol = float(np.std(daily_returns, ddof=1) * np.sqrt(365))

        # Sharpe ratio
        sharpe = (ann_return - risk_free_rate) / ann_vol if ann_vol > 0 else 0

        # Sortino ratio (using downside deviation)
        downside = daily_returns[daily_returns < 0]
        downside_std = float(np.std(downside, ddof=1) * np.sqrt(365)) if len(downside) > 1 else ann_vol
        sortino = (ann_return - risk_free_rate) / downside_std if downside_std > 0 else 0

        # Max drawdown
        cummax = np.maximum.accumulate(prices)
        drawdowns = (prices - cummax) / cummax
        max_dd = float(np.min(drawdowns))

        # Value at Risk (parametric)
        var_95 = float(np.percentile(daily_returns, 5))
        var_99 = float(np.percentile(daily_returns, 1))

        results.append({
            "coin_id": cid,
            "sector": get_sector(cid),
            "current_price": float(prices[-1]),
            "annualised_return": round(ann_return * 100, 2),
            "annualised_volatility": round(ann_vol * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "sortino_ratio": round(sortino, 3),
            "max_drawdown": round(max_dd * 100, 2),
            "var_95": round(var_95 * 100, 3),
            "var_99": round(var_99 * 100, 3),
            "data_points": len(daily_returns),
        })

    return sorted(results, key=lambda x: x["sharpe_ratio"], reverse=True)


# ── Sector Rotation ───────────────────────────────────────────────────

def compute_sector_performance(
    client: CoinGeckoClient,
    coin_ids: list[str],
    days: int = 365,
) -> dict:
    """
    Compute aggregate sector performance metrics.
    Returns performance by sector and time period (7d, 30d, 90d, YTD).
    """
    now = datetime.now(tz=timezone.utc)
    sector_data: dict[str, list] = {}

    for cid in coin_ids:
        series = _fetch_daily_prices(client, cid, days=days)
        if len(series) < 30:
            continue

        sector = get_sector(cid)
        prices = series.values.astype(float)
        dates = list(series.index)

        current = prices[-1]

        def _pct(n: int) -> Optional[float]:
            if len(prices) > n:
                return ((current / prices[-n]) - 1) * 100
            return None

        # YTD
        jan1 = datetime(now.year, 1, 1).date()
        ytd = None
        for i, d in enumerate(dates):
            if d >= jan1:
                ytd = ((current / prices[i]) - 1) * 100
                break

        coin_perf = {
            "coin_id": cid,
            "current_price": float(current),
            "pct_7d": round(_pct(7), 2) if _pct(7) is not None else None,
            "pct_30d": round(_pct(30), 2) if _pct(30) is not None else None,
            "pct_90d": round(_pct(90), 2) if _pct(90) is not None else None,
            "pct_ytd": round(ytd, 2) if ytd is not None else None,
        }

        if sector not in sector_data:
            sector_data[sector] = []
        sector_data[sector].append(coin_perf)

    # Aggregate by sector
    sectors = []
    for sector_name, coins in sector_data.items():
        def _avg(key):
            vals = [c[key] for c in coins if c[key] is not None]
            return round(sum(vals) / len(vals), 2) if vals else None

        sectors.append({
            "sector": sector_name,
            "coin_count": len(coins),
            "avg_7d": _avg("pct_7d"),
            "avg_30d": _avg("pct_30d"),
            "avg_90d": _avg("pct_90d"),
            "avg_ytd": _avg("pct_ytd"),
            "coins": coins,
        })

    sectors.sort(key=lambda s: s["avg_30d"] or -999, reverse=True)

    return {
        "sectors": sectors,
        "total_coins": sum(s["coin_count"] for s in sectors),
        "as_of": now.strftime("%Y-%m-%d"),
    }
