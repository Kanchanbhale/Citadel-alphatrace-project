"""
Market data tools — Step 1 (Collect), Data Retrieval Method 2.
Uses yfinance to pull price history for tickers surfaced from 13F filings.
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf
import pandas as pd


# ── Single ticker price history ───────────────────────────────────────────────

def fetch_price_history(ticker: str, period: str = "6mo") -> str:
    """
    Fetch OHLCV price history for a single ticker.

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL".
        period: yfinance period string — "1mo", "3mo", "6mo", "1y", "2y".

    Returns:
        JSON string with keys: ticker, period, data (list of OHLCV dicts),
        latest_close, pct_change_period.
    """
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period)
        if hist.empty:
            return json.dumps({"ticker": ticker, "error": "No data returned"})

        data = [
            {
                "date":   str(idx.date()),
                "open":   round(row["Open"],  2),
                "high":   round(row["High"],  2),
                "low":    round(row["Low"],   2),
                "close":  round(row["Close"], 2),
                "volume": int(row["Volume"]),
            }
            for idx, row in hist.iterrows()
        ]

        start_close = hist["Close"].iloc[0]
        end_close   = hist["Close"].iloc[-1]
        pct_change  = round((end_close - start_close) / start_close * 100, 2)

        return json.dumps({
            "ticker":            ticker,
            "period":            period,
            "data":              data,
            "latest_close":      round(float(end_close), 2),
            "start_close":       round(float(start_close), 2),
            "pct_change_period": pct_change,
        })
    except Exception as e:
        return json.dumps({"ticker": ticker, "error": str(e)})


def get_price_at_date(ticker: str, date_str: str) -> Optional[float]:
    """Return closing price nearest to date_str (YYYY-MM-DD). Returns None on failure."""
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d")
        start  = (target - timedelta(days=5)).strftime("%Y-%m-%d")
        end    = (target + timedelta(days=5)).strftime("%Y-%m-%d")
        hist   = yf.Ticker(ticker).history(start=start, end=end)
        if hist.empty:
            return None
        return round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        return None


# ── Batch price lookup ────────────────────────────────────────────────────────

def get_current_prices(tickers_json: str) -> str:
    """
    Fetch current prices for a batch of tickers.

    Args:
        tickers_json: JSON array of ticker strings, e.g. '["AAPL","MSFT","NVDA"]'.

    Returns:
        JSON string mapping ticker → current_price (float).
    """
    try:
        tickers: list[str] = json.loads(tickers_json)
    except Exception:
        return json.dumps({"error": "tickers_json must be a JSON array of strings"})

    prices: dict[str, Optional[float]] = {}
    for ticker in tickers[:30]:   # cap at 30 to avoid rate limiting
        try:
            info = yf.Ticker(ticker).fast_info
            price = getattr(info, "last_price", None) or getattr(info, "regularMarketPrice", None)
            prices[ticker] = round(float(price), 2) if price else None
        except Exception:
            prices[ticker] = None

    return json.dumps(prices)


# ── Price correlation vs. filing date ────────────────────────────────────────

def compute_price_correlations(holdings_json: str, filing_date: str) -> str:
    """
    For each holding with a ticker, compute return since the filing date.
    This surfaces the "alpha signal" — did the fund's entry precede a price move?

    Args:
        holdings_json: JSON array of holding dicts with at least {ticker, issuer_name}.
        filing_date: Filing date as YYYY-MM-DD.

    Returns:
        JSON array of price correlation dicts compatible with PriceCorrelation schema.
    """
    try:
        holdings: list[dict] = json.loads(holdings_json)
    except Exception:
        return json.dumps({"error": "Invalid holdings_json"})

    results = []
    seen: set[str] = set()

    for h in holdings[:25]:   # top 25 by value
        ticker = h.get("ticker")
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)

        price_at_filing = get_price_at_date(ticker, filing_date)

        # Current price
        try:
            info    = yf.Ticker(ticker).fast_info
            current = getattr(info, "last_price", None) or getattr(info, "regularMarketPrice", None)
            current = round(float(current), 2) if current else None
        except Exception:
            current = None

        ret_pct = None
        if price_at_filing and current:
            ret_pct = round((current - price_at_filing) / price_at_filing * 100, 2)

        if ret_pct is not None:
            signal = "POSITIVE" if ret_pct > 5 else ("NEGATIVE" if ret_pct < -5 else "NEUTRAL")
        else:
            signal = "UNKNOWN"

        results.append({
            "ticker":           ticker,
            "issuer_name":      h.get("issuer_name", ""),
            "price_at_filing":  price_at_filing,
            "price_current":    current,
            "return_pct":       ret_pct,
            "filing_date":      filing_date,
            "alpha_signal":     signal,
        })

    return json.dumps(results)


# ── Sector metadata ───────────────────────────────────────────────────────────

def get_sector_breakdown(tickers_json: str) -> str:
    """
    Return sector for each ticker (used for heatmap visualisation).

    Args:
        tickers_json: JSON array of tickers.

    Returns:
        JSON dict mapping ticker → sector.
    """
    try:
        tickers: list[str] = json.loads(tickers_json)
    except Exception:
        return json.dumps({})

    sectors: dict[str, str] = {}
    for ticker in tickers[:20]:
        try:
            info = yf.Ticker(ticker).info
            sectors[ticker] = info.get("sector", "Unknown")
        except Exception:
            sectors[ticker] = "Unknown"

    return json.dumps(sectors)
