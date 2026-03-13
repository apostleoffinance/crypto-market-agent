"""
CoinGecko API client – fetches historical price, market cap, and volume
for any coin at any date.  Caches results to database/ so repeated
queries are instant.

Uses concurrent requests for speed (respects API rate limits).
"""

import requests
import os
import joblib
import pandas as pd
from datetime import timedelta, timezone, datetime
from dotenv import load_dotenv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

load_dotenv()

DB_DIR = Path(__file__).resolve().parents[2] / "database"
DB_DIR.mkdir(exist_ok=True)

CACHE_PATH = DB_DIR / "top15_quarterly_data.joblib"

# Rate limiter: CoinGecko Pro allows ~500 calls/min ≈ 8 calls/sec
# We use a simple token-bucket approach
_rate_lock = threading.Lock()
_last_call_time = 0.0
_MIN_INTERVAL = 0.13  # ~7.5 calls/sec, safe for Pro plan


def _rate_limited_get(url: str, headers: dict, params: dict = None) -> requests.Response:
    """Thread-safe rate-limited GET request."""
    global _last_call_time
    with _rate_lock:
        now = time.monotonic()
        wait = _MIN_INTERVAL - (now - _last_call_time)
        if wait > 0:
            time.sleep(wait)
        _last_call_time = time.monotonic()

    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r


class CoinGeckoClient:
    BASE = "https://pro-api.coingecko.com/api/v3"

    def __init__(self):
        self.api_key = os.getenv("COINGECKO_API_KEY")
        if not self.api_key:
            raise ValueError("COINGECKO_API_KEY not found in .env")
        self.headers = {
            "accept": "application/json",
            "x-cg-pro-api-key": self.api_key,
        }
        self.stablecoin_ids = self._load_stablecoin_ids()
        # Cache the top coins list for the lifetime of the client
        self._top_coins_cache = None
        self._top_coins_cache_time = None

    # ── internal helpers ──────────────────────────────────────────────

    def _get(self, path: str, params: dict = None):
        r = _rate_limited_get(f"{self.BASE}{path}", self.headers, params)
        return r.json()

    def _load_stablecoin_ids(self) -> set:
        cache = DB_DIR / "stablecoin_ids.joblib"
        if cache.exists():
            return joblib.load(cache)
        try:
            data = self._get("/coins/markets", {
                "vs_currency": "usd",
                "category": "stablecoins",
                "order": "market_cap_desc",
                "per_page": 250,
                "page": 1,
                "sparkline": "false",
            })
            ids = {c["id"] for c in data if isinstance(c, dict) and "id" in c}
        except Exception:
            return set()
        joblib.dump(ids, cache)
        return ids

    # ── public ────────────────────────────────────────────────────────

    def get_current_top_coins(self, n_pages: int = 2) -> list:
        """Top coins by market cap right now (stablecoins excluded).
        Cached for 10 minutes to avoid redundant calls."""
        now = time.monotonic()
        if (
            self._top_coins_cache is not None
            and self._top_coins_cache_time is not None
            and (now - self._top_coins_cache_time) < 600  # 10 min cache
        ):
            return self._top_coins_cache

        coins = []
        for page in range(1, n_pages + 1):
            batch = self._get("/coins/markets", {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 100,
                "page": page,
                "sparkline": "false",
            })
            coins.extend(batch)

        result = [
            {"id": c["id"], "symbol": c["symbol"].upper(), "name": c["name"]}
            for c in coins
            if c["id"] not in self.stablecoin_ids
        ]
        self._top_coins_cache = result
        self._top_coins_cache_time = now
        return result

    def fetch_coin_at_date(
        self,
        coin_id: str,
        target_dt: datetime,
        symbol: str = "",
        name: str = "",
    ) -> dict:
        """
        Return {id, symbol, name, price, market_cap, volume, date} for *coin_id*
        at the closest data-point to *target_dt*.
        Returns None on any failure.
        """
        from_ts = int((target_dt - timedelta(days=1)).timestamp())
        to_ts = int((target_dt + timedelta(days=1)).timestamp())
        try:
            data = self._get(f"/coins/{coin_id}/market_chart/range", {
                "vs_currency": "usd",
                "from": from_ts,
                "to": to_ts,
            })
        except (requests.HTTPError, Exception):
            return None

        needed = ("prices", "market_caps", "total_volumes")
        if not all(k in data and data[k] for k in needed):
            return None

        def closest(lst):
            return min(lst, key=lambda x: abs(x[0] / 1000 - target_dt.timestamp()))

        return {
            "id": coin_id,
            "symbol": symbol or coin_id,
            "name": name or coin_id,
            "price": closest(data["prices"])[1],
            "market_cap": closest(data["market_caps"])[1],
            "volume": closest(data["total_volumes"])[1],
            "date": target_dt.strftime("%Y-%m-%d"),
        }

    def _fetch_coins_for_date_parallel(
        self,
        coins: list,
        target_dt: datetime,
        max_workers: int = 6,
    ) -> list:
        """Fetch multiple coins for a single date using thread pool."""
        results = []

        def _fetch_one(coin):
            return self.fetch_coin_at_date(
                coin_id=coin["id"],
                target_dt=target_dt,
                symbol=coin["symbol"],
                name=coin["name"],
            )

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_fetch_one, c): c for c in coins}
            for future in as_completed(futures):
                try:
                    row = future.result()
                    if row:
                        results.append(row)
                except Exception:
                    pass

        return results

    def get_top_n_at_dates(
        self,
        dates: list,
        top_n: int = 15,
        max_workers: int = 6,
        progress_cb=None,
    ) -> pd.DataFrame:
        """
        For every date in *dates*, fetch candidate coins IN PARALLEL
        and keep the top *top_n* by market cap.
        Uses joblib cache for dates already fetched.
        """
        # Load cache
        cached_df = None
        cached_dates = set()
        if CACHE_PATH.exists():
            cached_df = joblib.load(CACHE_PATH)
            if "date" in cached_df.columns:
                cached_dates = set(cached_df["date"].astype(str).unique())

        # Limit candidate pool for speed
        n_pages = 1 if top_n <= 50 else 2
        coins = self.get_current_top_coins(n_pages=n_pages)
        max_candidates = max(top_n * 3, 30)
        coins = coins[:max_candidates]

        all_frames = []

        for dt in dates:
            date_str = dt.strftime("%Y-%m-%d")

            # Serve from cache if we have enough rows
            if date_str in cached_dates and cached_df is not None:
                chunk = cached_df[cached_df["date"].astype(str) == date_str].copy()
                if len(chunk) >= top_n:
                    all_frames.append(chunk.head(top_n))
                    if progress_cb:
                        progress_cb(f"✅ {date_str} (cached)")
                    continue

            if progress_cb:
                progress_cb(f"⏳ Fetching {date_str} ({len(coins)} coins, {max_workers} threads)…")

            # ── PARALLEL fetch ────────────────────────────────────────
            rows = self._fetch_coins_for_date_parallel(
                coins, dt, max_workers=max_workers
            )

            if rows:
                df = (
                    pd.DataFrame(rows)
                    .sort_values("market_cap", ascending=False)
                    .head(top_n)
                )
                all_frames.append(df)
                if progress_cb:
                    progress_cb(f"✅ {date_str} done — top {len(df)} saved")
            else:
                if progress_cb:
                    progress_cb(f"❌ {date_str} — no data available")

        if not all_frames:
            return pd.DataFrame()

        final = pd.concat(all_frames, ignore_index=True)

        # Merge with existing cache
        if cached_df is not None and not cached_df.empty:
            merged = pd.concat([cached_df, final], ignore_index=True)
            merged = merged.drop_duplicates(subset=["id", "date"], keep="last")
            joblib.dump(merged, CACHE_PATH)
        else:
            joblib.dump(final, CACHE_PATH)

        return final
