from __future__ import annotations

import os
import re
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

# 상수 설정
PRICE_CACHE_DIR = Path("data/raw")
DEFAULT_PRICE_CACHE_TTL_MINUTES = int(os.getenv("PRICE_CACHE_TTL_MINUTES", "60"))

def _cache_path(ticker: str, period: str) -> Path:
    """지정된 ticker와 period에 대한 파일 경로를 반환합니다."""
    safe_ticker = re.sub(r"[^A-Za-z0-9_.-]+", "_", ticker.upper())
    # 파일 경로는 data/raw/{ticker}/{period}.csv 형태가 됩니다.
    return PRICE_CACHE_DIR / safe_ticker / f"{period}.csv"

def _cache_is_fresh(path: Path, max_age_minutes: int | None) -> bool:
    """캐시 파일이 존재하는지, 그리고 최신인지 확인합니다."""
    if max_age_minutes is None:
        max_age_minutes = DEFAULT_PRICE_CACHE_TTL_MINUTES

    if max_age_minutes <= 0 or not path.exists():
        return False

    age_seconds = time.time() - path.stat().st_mtime
    return age_seconds <= max_age_minutes * 60

def _read_price_cache(path: Path) -> pd.DataFrame:
    """캐시된 CSV 파일을 읽어 DataFrame으로 반환합니다."""
    df = pd.read_csv(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df

def _write_price_cache(path: Path, df: pd.DataFrame) -> None:
    """데이터프레임을 지정된 경로에 CSV로 저장합니다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

def _normalize_price_frame(ticker: str, df: pd.DataFrame) -> pd.DataFrame:
    """데이터프레임을 표준 형식으로 정규화하고 adj_close를 추가합니다."""
    if df.empty:
        raise ValueError(f"No data returned for ticker: {ticker}")

    # MultiIndex 처리 (yfinance batch download 대응)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    df = df.reset_index()
    # 컬럼명 소문자 및 언더바 통일
    df.columns = [str(col).lower().replace(" ", "_") for col in df.columns]

    # 필수 컬럼 확인
    required_columns = {"date", "open", "high", "low", "close", "volume"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns for {ticker}: {missing}")

    # qlib 및 향후 활용을 위해 adj_close 명시적 추가
    # yfinance의 auto_adjust=True를 사용하면 close가 이미 수정 종가임
    df["adj_close"] = df["close"]

    return df

def load_price_data(
    ticker: str,
    period: str = "1y",
    *,
    force_refresh: bool = False,
    cache_max_age_minutes: int | None = None,
) -> pd.DataFrame:
    """단일 티커의 가격 데이터를 로드합니다."""
    path = _cache_path(ticker, period)

    if not force_refresh and _cache_is_fresh(path, cache_max_age_minutes):
        return _read_price_cache(path)

    df = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
    )

    normalized = _normalize_price_frame(ticker, df)
    _write_price_cache(path, normalized)
    return normalized


def load_cached_price_data(ticker: str, period: str = "1y") -> pd.DataFrame:
    """네트워크 요청 없이 캐시된 가격 데이터만 로드합니다."""
    path = _cache_path(ticker, period)
    if not path.exists():
        raise FileNotFoundError(f"Cached price data not found: {path}")

    return _read_price_cache(path)

def _extract_ticker_from_batch(
    downloaded: pd.DataFrame,
    ticker: str,
    requested_count: int,
) -> pd.DataFrame:
    """Batch download 결과에서 특정 티커의 데이터만 추출합니다."""
    if not isinstance(downloaded.columns, pd.MultiIndex):
        return downloaded

    ticker_labels = {str(label) for label in downloaded.columns.get_level_values(0)}
    if ticker in ticker_labels:
        return downloaded[ticker]

    ticker_labels = {str(label) for label in downloaded.columns.get_level_values(1)}
    if ticker in ticker_labels:
        return downloaded.xs(ticker, axis=1, level=1)

    if requested_count == 1:
        return downloaded

    raise ValueError(f"No batch data found for ticker: {ticker}")

def load_price_data_batch(
    tickers: list[str],
    period: str = "1y",
    *,
    force_refresh: bool = False,
    cache_max_age_minutes: int | None = None,
) -> dict[str, pd.DataFrame]:
    """여러 티커의 가격 데이터를 한 번에 로드합니다."""
    unique_tickers = list(dict.fromkeys(tickers))
    result: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    errors: dict[str, str] = {}

    for ticker in unique_tickers:
        path = _cache_path(ticker, period)
        if not force_refresh and _cache_is_fresh(path, cache_max_age_minutes):
            try:
                result[ticker] = _read_price_cache(path)
                continue
            except Exception:
                pass
        missing.append(ticker)

    if not missing:
        return result

    downloaded = yf.download(
        tickers=missing,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=True,
    )

    for ticker in missing:
        try:
            ticker_df = _extract_ticker_from_batch(downloaded, ticker, len(missing))
            normalized = _normalize_price_frame(ticker, ticker_df)
            
            path = _cache_path(ticker, period)
            _write_price_cache(path, normalized)
            result[ticker] = normalized
        except Exception as exc:
            errors[ticker] = str(exc)

    unresolved = [ticker for ticker in missing if ticker not in result]
    if unresolved:
        detail = ", ".join(
            f"{ticker} ({errors.get(ticker, 'no data returned')})"
            for ticker in unresolved
        )
        raise ValueError(f"Failed to load batch price data: {detail}")

    return result


def load_cached_price_data_batch(
    tickers: list[str],
    period: str = "1y",
) -> dict[str, pd.DataFrame]:
    """네트워크 요청 없이 여러 티커의 캐시 데이터만 로드합니다."""
    unique_tickers = list(dict.fromkeys(tickers))
    result: dict[str, pd.DataFrame] = {}

    for ticker in unique_tickers:
        result[ticker] = load_cached_price_data(ticker, period=period)

    return result
