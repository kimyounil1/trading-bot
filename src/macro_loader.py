"""Macro context data loader: yield spread, dollar, gold, VIX percentile."""

from pathlib import Path

import pandas as pd
import yfinance as yf

MACRO_TICKERS = {
    "tnx": "^TNX",      # 10-year Treasury yield
    "irx": "^IRX",      # 13-week Treasury bill rate
    "dxy": "DX-Y.NYB",  # US Dollar Index
    "gold": "GC=F",     # Gold futures
    "skew": "^SKEW",    # CBOE SKEW Index (tail risk)
    "vvix": "^VVIX",    # VIX of VIX (uncertainty in volatility)
}

MACRO_CACHE_DIR = Path("data/macro")


def _download_macro_ticker(symbol: str, period: str) -> pd.DataFrame:
    try:
        df = yf.download(symbol, period=period, auto_adjust=True, progress=False)
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        df.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in df.columns]
        df = df.rename(columns={"date": "date", "close": "close"})
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()
        return df[["date", "close"]].dropna()
    except Exception:
        return pd.DataFrame()


def load_macro_data(period: str = "5y") -> pd.DataFrame:
    """Download and merge macro series into a single daily DataFrame.

    Returns DataFrame with columns:
      date, tnx_close, irx_close, dxy_close, gold_close
    Gaps are forward-filled (macro series don't trade every day).
    """
    frames = {}
    for key, symbol in MACRO_TICKERS.items():
        df = _download_macro_ticker(symbol, period=period)
        if not df.empty:
            frames[key] = df.rename(columns={"close": f"{key}_close"}).set_index("date")

    if not frames:
        return pd.DataFrame()

    macro_df = pd.concat(frames.values(), axis=1).sort_index().ffill().bfill()
    macro_df = macro_df.reset_index().rename(columns={"index": "date"})
    macro_df["date"] = pd.to_datetime(macro_df["date"]).dt.normalize()
    return macro_df
