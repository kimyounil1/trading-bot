"""Data freshness and quality checks for ops / live readiness."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_loader import load_price_data_batch
from src.settings import load_settings

DEFAULT_OUTPUT = Path("logs/data_health/latest_summary.json")
AI_PERIOD = "2y"

# Volatility indices routinely jump 50-100%+ in a day (e.g. VIX +74% on 2026-04);
# only flag moves large enough to indicate data corruption, not market stress.
VOLATILITY_INDEX_TICKERS = {"^VIX", "VIX", "^VVIX", "VVIX", "^VXN", "VXN"}
DEFAULT_MAX_DAILY_JUMP = 0.35
VOLATILITY_INDEX_MAX_DAILY_JUMP = 1.5


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _max_daily_jump_threshold(ticker: str) -> float:
    if ticker.upper() in VOLATILITY_INDEX_TICKERS:
        return VOLATILITY_INDEX_MAX_DAILY_JUMP
    return DEFAULT_MAX_DAILY_JUMP


def _check_ticker_frame(
    ticker: str,
    df: pd.DataFrame,
    *,
    max_stale_days: int = 5,
    max_daily_jump: float | None = None,
) -> dict[str, Any]:
    if max_daily_jump is None:
        max_daily_jump = _max_daily_jump_threshold(ticker)
    issues: list[str] = []
    if df is None or df.empty:
        return {"ticker": ticker, "ok": False, "issues": ["empty_frame"]}

    work = df.copy()
    if "date" in work.columns:
        work["date"] = pd.to_datetime(work["date"], errors="coerce")
        work = work[work["date"].notna()]
    price_col = "adj_close" if "adj_close" in work.columns else "close"
    if price_col not in work.columns:
        return {"ticker": ticker, "ok": False, "issues": ["missing_price_column"]}

    px = pd.to_numeric(work[price_col], errors="coerce")
    null_pct = float(px.isna().mean()) if len(px) else 1.0
    if null_pct > 0.05:
        issues.append(f"null_price_pct={null_pct:.2%}")

    if len(work) >= 2:
        last_date = pd.Timestamp(work["date"].iloc[-1]).tz_localize(None)
        stale_days = (pd.Timestamp.utcnow().tz_localize(None) - last_date).days
        if stale_days > max_stale_days:
            issues.append(f"stale_days={stale_days}")
        rets = px.pct_change().dropna()
        if not rets.empty:
            jump = float(rets.abs().max())
            if jump > max_daily_jump:
                issues.append(f"max_daily_jump={jump:.2%}")

    return {"ticker": ticker, "ok": len(issues) == 0, "issues": issues, "rows": len(work)}


def build_data_health_report(
    *,
    settings: Any | None = None,
    sample_tickers: int = 12,
) -> dict[str, Any]:
    settings = settings or load_settings()
    tickers = list(settings.tickers)[:sample_tickers]
    for required in ("SPY", "^VIX"):
        if required not in tickers:
            tickers.append(required)

    reasons: list[str] = []
    ticker_results: list[dict[str, Any]] = []

    try:
        batch = load_price_data_batch(tickers, period=AI_PERIOD)
    except Exception as exc:
        return {
            "generated_at": _utc_now_iso(),
            "overall": "NO_GO",
            "reasons": [f"load_price_data_batch failed: {exc}"],
            "ticker_checks": [],
        }

    for ticker in tickers:
        frame = batch.get(ticker)
        if frame is None:
            frame = batch.get(ticker.replace("^", ""))
        result = _check_ticker_frame(ticker, frame)
        ticker_results.append(result)
        if not result["ok"]:
            reasons.append(f"{ticker}: {', '.join(result['issues'])}")

    vix = batch.get("^VIX")
    if vix is None:
        vix = batch.get("VIX")
    if vix is None or (hasattr(vix, "empty") and vix.empty):
        reasons.append("VIX data missing")

    overall = "GO" if not reasons else "NO_GO"
    return {
        "generated_at": _utc_now_iso(),
        "overall": overall,
        "reasons": reasons,
        "tickers_checked": len(ticker_results),
        "ticker_checks": ticker_results,
        "notes": [
            "Sample subset of universe; run before live or after data pipeline changes.",
        ],
    }


def write_data_health_report(output_path: str | Path = DEFAULT_OUTPUT) -> Path:
    report = build_data_health_report()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build data health summary")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    path = write_data_health_report(args.output)
    print(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
