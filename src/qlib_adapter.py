from __future__ import annotations

from pathlib import Path

import pandas as pd


QLIB_READY_COLUMNS = [
    "instrument",
    "datetime",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "factor",
]


def to_qlib_ready_frame(ticker: str, df: pd.DataFrame) -> pd.DataFrame:
    """현재 원시 가격 데이터를 qlib 도입 전 단계의 정규화 포맷으로 변환합니다."""
    required = {"date", "open", "high", "low", "close", "volume", "adj_close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns for qlib export: {sorted(missing)}")

    qlib_df = df.copy()
    qlib_df["instrument"] = ticker.upper()
    qlib_df["datetime"] = pd.to_datetime(qlib_df["date"]).dt.strftime("%Y-%m-%d")

    close_series = pd.to_numeric(qlib_df["close"], errors="coerce")
    adj_close_series = pd.to_numeric(qlib_df["adj_close"], errors="coerce")
    qlib_df["factor"] = (adj_close_series / close_series).replace([pd.NA, float("inf"), float("-inf")], 1.0)
    qlib_df["factor"] = qlib_df["factor"].fillna(1.0)

    for column in ("open", "high", "low", "close", "volume"):
        qlib_df[column] = pd.to_numeric(qlib_df[column], errors="coerce")

    qlib_df = qlib_df[QLIB_READY_COLUMNS].dropna().reset_index(drop=True)
    if qlib_df.empty:
        raise ValueError(f"No rows available after qlib normalization for {ticker}")

    return qlib_df


def export_qlib_ready_data(
    ticker_data: dict[str, pd.DataFrame],
    output_dir: str | Path,
) -> list[Path]:
    """티커별 CSV로 qlib-ready 데이터를 저장합니다."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    written_paths: list[Path] = []
    for ticker, df in ticker_data.items():
        qlib_df = to_qlib_ready_frame(ticker, df)
        path = target_dir / f"{ticker.upper()}.csv"
        qlib_df.to_csv(path, index=False)
        written_paths.append(path)

    return written_paths
