"""실제 거래 내역과 시그널 가격을 비교해 paper 슬리피지를 분석·리포트한다."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.alpaca_client import get_account_summary, get_positions_summary
from src.config import ORDER_LOG_PATH, SIGNAL_LOG_PATH


@dataclass
class SlippageReport:
    generated_at: str
    lookback_days: int
    signals_path: str
    orders_path: str
    matched_trades: int
    overall_avg_slippage_pct: float
    total_slippage_usd: float
    by_ticker: list[dict]
    status: str = "ok"
    message: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _filter_since(df: pd.DataFrame, since: datetime | None, column: str = "timestamp") -> pd.DataFrame:
    if since is None or df.empty or column not in df.columns:
        return df
    frame = df.copy()
    frame["_ts"] = pd.to_datetime(frame[column], utc=True, errors="coerce")
    cutoff = pd.Timestamp(since).tz_convert("UTC") if pd.Timestamp(since).tzinfo else pd.Timestamp(since, tz="UTC")
    return frame[frame["_ts"] >= cutoff].drop(columns=["_ts"])


def _extract_filled_orders(orders_df: pd.DataFrame) -> pd.DataFrame:
    filled_orders = orders_df[orders_df.get("event") == "STATUS_CHECK"].copy()

    if filled_orders.empty:
        mask = orders_df.apply(lambda row: "STATUS_CHECK" in row.values, axis=1)
        filled_orders = orders_df[mask].copy()

        def remap_row(row: pd.Series) -> pd.Series:
            vals = list(row)
            if "STATUS_CHECK" in vals:
                idx = vals.index("STATUS_CHECK")
                if idx == 10:
                    return pd.Series(
                        [
                            vals[0],
                            vals[1],
                            vals[2],
                            vals[3],
                            vals[4],
                            vals[5],
                            vals[6],
                            vals[7],
                            vals[8],
                            vals[9],
                            vals[10],
                        ],
                        index=[
                            "timestamp",
                            "ticker",
                            "notional",
                            "order_id",
                            "status",
                            "side",
                            "order_type",
                            "filled_qty",
                            "filled_avg_price",
                            "reason",
                            "event",
                        ],
                    )
            return row

        if not filled_orders.empty:
            filled_orders = filled_orders.apply(remap_row, axis=1)

    if filled_orders.empty:
        return filled_orders

    filled_orders["filled_avg_price"] = pd.to_numeric(
        filled_orders["filled_avg_price"], errors="coerce"
    )
    return filled_orders.dropna(subset=["filled_avg_price"])


def compute_slippage_report(
    signals_path: str | Path | None = None,
    orders_path: str | Path | None = None,
    *,
    lookback_days: int | None = None,
    since: datetime | None = None,
) -> SlippageReport | None:
    """Match paper fills to signal close prices and compute slippage metrics."""
    signals_path = Path(signals_path or SIGNAL_LOG_PATH)
    orders_path = Path(orders_path or ORDER_LOG_PATH)

    if since is None and lookback_days is not None:
        since = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    try:
        signals_df = pd.read_csv(signals_path)
        orders_df = pd.read_csv(orders_path)
    except FileNotFoundError:
        return None

    signals_df = _filter_since(signals_df, since)
    orders_df = _filter_since(orders_df, since)

    filled_orders = _extract_filled_orders(orders_df)
    if filled_orders.empty:
        return None

    signals_df["ts_short"] = pd.to_datetime(signals_df["timestamp"], utc=True).dt.floor("min")
    filled_orders["ts_short"] = pd.to_datetime(filled_orders["timestamp"], utc=True).dt.floor("min")

    merged = pd.merge(
        filled_orders,
        signals_df,
        on=["ticker", "ts_short"],
        how="inner",
        suffixes=("_order", "_signal"),
    )
    if merged.empty:
        return None

    merged["side_lower"] = merged["side"].astype(str).str.lower()
    sign = np.where(merged["side_lower"].str.contains("sell", na=False), -1, 1)
    merged["slippage_pct"] = (
        sign * (merged["filled_avg_price"] - merged["close"]) / merged["close"] * 100
    )
    merged["filled_qty"] = pd.to_numeric(merged["filled_qty"], errors="coerce")
    merged["slippage_usd"] = (
        sign * (merged["filled_avg_price"] - merged["close"]) * merged["filled_qty"]
    )

    by_ticker_df = merged.groupby("ticker").agg(
        avg_slippage_pct=("slippage_pct", "mean"),
        total_slippage_usd=("slippage_usd", "sum"),
        trades=("ticker", "count"),
    )
    by_ticker = [
        {
            "ticker": str(ticker),
            "avg_slippage_pct": float(row["avg_slippage_pct"]),
            "total_slippage_usd": float(row["total_slippage_usd"]),
            "trades": int(row["trades"]),
        }
        for ticker, row in by_ticker_df.iterrows()
    ]

    return SlippageReport(
        generated_at=_utc_now_iso(),
        lookback_days=int(lookback_days or 0),
        signals_path=str(signals_path),
        orders_path=str(orders_path),
        matched_trades=int(len(merged)),
        overall_avg_slippage_pct=float(merged["slippage_pct"].mean()),
        total_slippage_usd=float(merged["slippage_usd"].sum()),
        by_ticker=by_ticker,
    )


def format_slippage_report(report: SlippageReport) -> str:
    lines = [
        "",
        "=== Slippage Analysis (Paper Fill vs Signal Price) ===",
        f"Window: last {report.lookback_days} day(s)" if report.lookback_days else "Window: all logs",
        f"Status: {report.status}",
        f"Matched trades: {report.matched_trades}",
    ]
    if report.message:
        lines.append(f"Note: {report.message}")
    if report.by_ticker:
        summary = pd.DataFrame(report.by_ticker).set_index("ticker")
        lines.append(summary.to_string())
    lines.append(f"\nOverall Average Slippage: {report.overall_avg_slippage_pct:.4f}%")
    lines.append(f"Total Slippage Cost: ${report.total_slippage_usd:.2f}")
    return "\n".join(lines)


def write_slippage_artifacts(
    report: SlippageReport,
    output_dir: str | Path,
    *,
    run_id: str | None = None,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_dir / f"slippage_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "summary.json").write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if report.by_ticker:
        pd.DataFrame(report.by_ticker).to_csv(run_dir / "by_ticker.csv", index=False)

    latest = output_dir / "latest_summary.json"
    latest.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return run_dir


def analyze_slippage(
    signals_path: str | Path | None = None,
    orders_path: str | Path | None = None,
    *,
    lookback_days: int | None = None,
) -> SlippageReport | None:
    report = compute_slippage_report(
        signals_path=signals_path,
        orders_path=orders_path,
        lookback_days=lookback_days,
    )
    if report is None:
        print("No slippage data available (missing logs, fills, or signal matches).")
        return None
    print(format_slippage_report(report))
    return report


def _maybe_notify_slippage(report: SlippageReport) -> None:
    try:
        from src.notifier import notify_info
    except ImportError:
        return
    notify_info(
        "Weekly paper vs signal slippage",
        (
            f"Matched trades: {report.matched_trades}\n"
            f"Avg slippage: {report.overall_avg_slippage_pct:.4f}%\n"
            f"Total cost: ${report.total_slippage_usd:.2f}"
        ),
    )


def _empty_slippage_report(
    *,
    lookback_days: int,
    signals_path: Path,
    orders_path: Path,
    message: str,
) -> SlippageReport:
    return SlippageReport(
        generated_at=_utc_now_iso(),
        lookback_days=lookback_days,
        signals_path=str(signals_path),
        orders_path=str(orders_path),
        matched_trades=0,
        overall_avg_slippage_pct=0.0,
        total_slippage_usd=0.0,
        by_ticker=[],
        status="no_data",
        message=message,
    )


def run_weekly_slippage_report(
    *,
    lookback_days: int = 7,
    output_dir: str | Path = "logs/slippage_reports",
    signals_path: str | Path | None = None,
    orders_path: str | Path | None = None,
    notify_telegram: bool = False,
    include_account: bool = False,
) -> SlippageReport:
    signals_path = Path(signals_path or SIGNAL_LOG_PATH)
    orders_path = Path(orders_path or ORDER_LOG_PATH)

    report = compute_slippage_report(
        signals_path=signals_path,
        orders_path=orders_path,
        lookback_days=lookback_days,
    )
    if report is None:
        report = _empty_slippage_report(
            lookback_days=lookback_days,
            signals_path=signals_path,
            orders_path=orders_path,
            message="no matched paper fills in lookback window",
        )
        print(f"Weekly slippage report: {report.message}.")

    run_dir = write_slippage_artifacts(report, output_dir)
    print(format_slippage_report(report))
    print(f"\nSaved weekly slippage report to {run_dir}")
    if notify_telegram:
        _maybe_notify_slippage(report)
    if include_account:
        report_account_performance()
    return report


def report_account_performance() -> None:
    """Alpaca paper 계좌의 현재 실적 요약."""
    account = get_account_summary()
    positions = get_positions_summary()

    print("\n=== Account Performance Summary ===")
    print(f"Portfolio Value: ${account['portfolio_value']:.2f}")
    print(f"Cash: ${account['cash']:.2f}")

    if positions:
        print("\n--- Open Positions ---")
        pos_df = pd.DataFrame(positions)
        print(pos_df[["symbol", "qty", "market_value", "unrealized_plpc"]].to_string(index=False))
    else:
        print("\nNo open positions.")


def _load_slippage_config() -> dict:
    path = Path("config/slippage_report_config.json")
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    config = _load_slippage_config()
    parser = argparse.ArgumentParser(description="Paper vs signal slippage reporting")
    parser.add_argument(
        "--weekly",
        action="store_true",
        help="Run weekly lookback, write artifacts under output_dir",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=int(config.get("lookback_days", 7)),
        help="Lookback window in days (default from config or 7)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(config.get("output_dir", "logs/slippage_reports")),
        help="Directory for JSON/CSV weekly artifacts",
    )
    parser.add_argument(
        "--telegram",
        action="store_true",
        default=bool(config.get("notify_telegram", False)),
        help="Send Telegram summary when configured",
    )
    parser.add_argument(
        "--account",
        action="store_true",
        help="Include Alpaca account summary",
    )
    parser.add_argument("--signals", default=None, help="Override signals CSV path")
    parser.add_argument("--orders", default=None, help="Override orders CSV path")
    args = parser.parse_args()

    print(f"Performance Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.weekly:
        run_weekly_slippage_report(
            lookback_days=args.days,
            output_dir=args.output_dir,
            signals_path=args.signals,
            orders_path=args.orders,
            notify_telegram=args.telegram,
            include_account=args.account,
        )
        return

    if args.account:
        report_account_performance()
    analyze_slippage(
        signals_path=args.signals,
        orders_path=args.orders,
        lookback_days=args.days if args.days > 0 else None,
    )


if __name__ == "__main__":
    main()
