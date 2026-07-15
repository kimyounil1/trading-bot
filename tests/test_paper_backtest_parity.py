from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.execution_audit_io import EXECUTION_AUDIT_COLUMNS
from src.paper_backtest_parity import (
    build_paper_backtest_parity_report,
    maybe_notify_parity_anomalies,
)
from src.portfolio_backtester import (
    _build_equal_weight_benchmark_values,
    run_portfolio_backtest,
    save_portfolio_backtest_outputs,
)
from src.run_portfolio_backtest import latest_covered_market_date


def _write_audit(path: Path, **overrides) -> None:
    row = {column: None for column in EXECUTION_AUDIT_COLUMNS}
    row.update(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event_type": "BUY_PLAN",
            "ticker": "AAPL",
            "action": "BUY",
            "status": "PLANNED",
            "run_id": "run-1",
            "sleeve_id": "core",
            "signal_ticker": "AAPL",
            "execution_ticker": "AAPB",
            "decision_market_date": "2026-07-14",
            "quality_notional_multiplier": 0.5,
            "quality_allow_leveraged": True,
            "route_leveraged": True,
            "portfolio_value": 10_000.0,
            "planned_notional_pct": 0.05,
        }
    )
    row.update(overrides)
    pd.DataFrame([row], columns=list(EXECUTION_AUDIT_COLUMNS)).to_csv(
        path,
        index=False,
    )


def _write_backtest_files(directory: Path, **overrides) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    row = {
        "market_date": "2026-07-14",
        "signal_ticker": "AAPL",
        "execution_ticker": "AAPB",
        "leveraged": True,
        "quality_notional_multiplier": 0.5,
        "quality_allow_leveraged": True,
        "planned_notional": 500.0,
        "planned_notional_pct": 0.05,
        "rank_ai_score": 0.8,
        "rank_ai_percentile": 0.95,
        "sleeve_id": "core",
    }
    row.update(overrides)
    entries = directory / "portfolio_entries.csv"
    equity = directory / "portfolio_equity.csv"
    pd.DataFrame([row]).to_csv(entries, index=False)
    pd.DataFrame([{"date": "2026-07-14", "equity": 10_000.0}]).to_csv(
        equity,
        index=False,
    )
    return entries, equity


def test_exact_paper_backtest_policy_match_is_ok(tmp_path: Path) -> None:
    audit = tmp_path / "audit.csv"
    _write_audit(audit)
    entries, equity = _write_backtest_files(tmp_path / "backtest")

    report, comparison = build_paper_backtest_parity_report(
        audit_path=audit,
        backtest_entries_path=entries,
        backtest_equity_path=equity,
        output_dir=tmp_path / "report",
        config={"operational_error_lookback_hours": 36},
    )

    assert report["status"] == "ok"
    assert report["policy_parity_rate"] == 1.0
    assert report["candidate_recall"] == 1.0
    assert comparison.loc[0, "policy_match"]
    assert (tmp_path / "report" / "latest_summary.json").is_file()


def test_policy_mismatch_and_operational_error_raise_anomaly(tmp_path: Path) -> None:
    audit = tmp_path / "audit.csv"
    _write_audit(
        audit,
        execution_ticker="AAPL",
        quality_notional_multiplier=0.25,
        quality_allow_leveraged=False,
        route_leveraged=False,
    )
    frame = pd.read_csv(audit)
    error = {column: None for column in EXECUTION_AUDIT_COLUMNS}
    error.update(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event_type": "BUY_ERROR",
            "ticker": "AAPL",
            "status": "ERROR",
            "reason": "broker rejected",
        }
    )
    submitted = {column: None for column in EXECUTION_AUDIT_COLUMNS}
    submitted.update(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event_type": "BUY_SUBMITTED",
            "ticker": "AAPL",
            "status": "ACCEPTED",
            "run_id": "run-1",
            "order_id": "order-1",
        }
    )
    filled = {column: None for column in EXECUTION_AUDIT_COLUMNS}
    filled.update(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event_type": "BUY_STATUS",
            "ticker": "AAPL",
            "status": "FILLED",
            "run_id": "run-1",
            "order_id": "order-1",
            "reference_price": 100.0,
            "filled_avg_price": 101.0,
        }
    )
    pd.DataFrame(
        [*frame.to_dict(orient="records"), error, submitted, filled],
        columns=list(EXECUTION_AUDIT_COLUMNS),
    ).to_csv(audit, index=False)
    entries, equity = _write_backtest_files(tmp_path / "backtest")

    report, _ = build_paper_backtest_parity_report(
        audit_path=audit,
        backtest_entries_path=entries,
        backtest_equity_path=equity,
        output_dir=tmp_path / "report",
        config={
            "min_candidate_recall": 0.5,
            "min_policy_parity": 0.95,
            "max_notional_pct_abs_diff": 0.10,
            "operational_error_lookback_hours": 36,
            "max_adverse_slippage_bps": 60.0,
        },
    )

    assert report["status"] == "anomaly"
    assert report["policy_parity_rate"] == 0.0
    assert report["operational_error_count"] == 1
    assert report["buy_fill_rate"] == 1.0
    assert report["max_adverse_buy_slippage_bps"] == 100.0
    assert any("policy parity" in item for item in report["anomalies"])
    assert any("slippage" in item for item in report["anomalies"])


def test_anomaly_notification_only_sends_when_needed(monkeypatch) -> None:
    sent = []
    monkeypatch.setattr(
        "src.paper_backtest_parity.notify_error",
        lambda title, body: sent.append((title, body)) or True,
    )

    assert maybe_notify_parity_anomalies(
        {"anomalies": [], "market_date": "2026-07-14"}
    ) is False
    assert maybe_notify_parity_anomalies(
        {
            "anomalies": ["route mismatch"],
            "market_date": "2026-07-14",
            "live_plan_count": 1,
            "backtest_entry_count": 1,
            "matched_count": 1,
        }
    ) is True
    assert len(sent) == 1


def test_backtester_exports_entry_ledger(tmp_path: Path) -> None:
    close = np.linspace(100.0, 150.0, 300)
    prices = pd.DataFrame(
        {
            "date": pd.bdate_range("2025-01-02", periods=300),
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "adj_close": close,
            "volume": 1_000_000,
        }
    )
    result, equity, trades = run_portfolio_backtest(
        ticker_data={"AAPL": prices},
        initial_cash=10_000.0,
        max_positions=1,
        target_position_pct=0.3,
        transaction_cost_pct=0.0,
        ma_fast=5,
        ma_slow=20,
        rsi_buy_limit=101.0,
    )

    entries = equity.attrs["entry_events"]
    assert not entries.empty
    assert entries.iloc[0]["signal_ticker"] == "AAPL"
    save_portfolio_backtest_outputs(tmp_path, result, equity, trades)
    saved = pd.read_csv(tmp_path / "portfolio_entries.csv")
    assert not saved.empty
    assert saved.iloc[0]["execution_ticker"] == "AAPL"


def test_latest_covered_market_date_rejects_partial_refresh() -> None:
    dates = pd.to_datetime(["2026-07-13", "2026-07-14"])
    ticker_data = {
        "A": pd.DataFrame({"date": dates, "close": [10.0, 11.0]}),
        "B": pd.DataFrame({"date": dates, "close": [10.0, 11.0]}),
        "C": pd.DataFrame({"date": dates, "close": [10.0, 11.0]}),
        "D": pd.DataFrame({"date": dates, "close": [10.0, np.nan]}),
    }

    covered = latest_covered_market_date(
        ticker_data,
        base_tickers=["A", "B", "C", "D"],
        requested_end="2026-07-14",
        min_coverage=0.8,
    )

    assert covered == pd.Timestamp("2026-07-13")


def test_buy_hold_benchmark_carries_last_price_across_missing_row() -> None:
    dates = pd.to_datetime(["2026-07-13", "2026-07-14", "2026-07-15"])
    ticker_data = {
        "A": pd.DataFrame({"date": dates, "adj_close": [100.0, 110.0, 120.0]}),
        "B": pd.DataFrame(
            {"date": dates, "adj_close": [50.0, np.nan, 55.0]}
        ),
    }

    values = _build_equal_weight_benchmark_values(
        pd.Series(dates),
        ticker_data,
        10_000.0,
    )

    assert values == [10_000.0, 10_500.0, 11_500.0]
