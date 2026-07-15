"""Monthly backtest attribution and loss-month review queue."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _monthly_return(series: pd.Series, initial_value: float) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    result = values.pct_change()
    if not result.empty and initial_value > 0:
        result.iloc[0] = values.iloc[0] / initial_value - 1.0
    return result


def build_monthly_backtest_attribution(
    equity_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    *,
    initial_cash: float,
) -> pd.DataFrame:
    if equity_df.empty:
        return pd.DataFrame()
    equity = equity_df.copy()
    equity["date"] = pd.to_datetime(equity["date"], errors="coerce")
    equity = equity.dropna(subset=["date"]).sort_values("date")
    equity["month"] = equity["date"].dt.to_period("M").astype(str)

    monthly = equity.groupby("month", as_index=False).agg(
        start_date=("date", "min"),
        end_date=("date", "max"),
        ending_equity=("equity", "last"),
        ending_cash=("cash", "last"),
        ending_positions_value=("positions_value", "last"),
        min_drawdown=("drawdown", "min"),
        avg_positions=("positions_count", "mean"),
    )
    monthly["monthly_return"] = _monthly_return(
        monthly["ending_equity"],
        initial_cash,
    )
    if "benchmark_equity" in equity.columns:
        benchmark = equity.groupby("month")["benchmark_equity"].last()
        monthly["benchmark_ending_equity"] = monthly["month"].map(benchmark)
        monthly["benchmark_return"] = _monthly_return(
            monthly["benchmark_ending_equity"],
            initial_cash,
        )
        monthly["excess_return"] = (
            monthly["monthly_return"] - monthly["benchmark_return"]
        )

    trades = trades_df.copy()
    if not trades.empty and "exit_date" in trades.columns:
        trades["exit_date"] = pd.to_datetime(trades["exit_date"], errors="coerce")
        trades = trades.dropna(subset=["exit_date"])
        trades["month"] = trades["exit_date"].dt.to_period("M").astype(str)
        trades["pnl_usd"] = (
            pd.to_numeric(trades["exit_value"], errors="coerce")
            - pd.to_numeric(trades["cost_basis"], errors="coerce")
        )

    attribution_rows = []
    for row in monthly.to_dict("records"):
        month = row["month"]
        month_trades = trades[trades["month"] == month] if not trades.empty else trades
        row["closed_trades"] = int(len(month_trades))
        row["realized_pnl_usd"] = float(month_trades["pnl_usd"].sum()) if not month_trades.empty else 0.0
        row["win_rate"] = (
            float((month_trades["return_pct"] > 0).mean())
            if not month_trades.empty
            else 0.0
        )
        row["stop_loss_count"] = int(
            (month_trades.get("exit_reason", pd.Series(dtype=str)) == "STOP_LOSS").sum()
        )
        row["take_profit_count"] = int(
            (month_trades.get("exit_reason", pd.Series(dtype=str)) == "TAKE_PROFIT").sum()
        )
        row["leveraged_trade_count"] = int(
            pd.to_numeric(
                month_trades.get("leveraged", pd.Series(dtype=float)),
                errors="coerce",
            ).fillna(0).astype(bool).sum()
        )
        if not month_trades.empty and "leveraged" in month_trades.columns:
            leveraged_mask = month_trades["leveraged"].fillna(False).astype(bool)
            row["leveraged_realized_pnl_usd"] = float(
                month_trades.loc[leveraged_mask, "pnl_usd"].sum()
            )
            row["underlying_realized_pnl_usd"] = float(
                month_trades.loc[~leveraged_mask, "pnl_usd"].sum()
            )
        else:
            row["leveraged_realized_pnl_usd"] = 0.0
            row["underlying_realized_pnl_usd"] = float(
                month_trades["pnl_usd"].sum()
            ) if not month_trades.empty else 0.0
        if not month_trades.empty and "sleeve_id" in month_trades.columns:
            by_sleeve = month_trades.groupby("sleeve_id")["pnl_usd"].sum().sort_values()
            row["worst_sleeve"] = str(by_sleeve.index[0])
            row["worst_sleeve_pnl_usd"] = float(by_sleeve.iloc[0])
            row["best_sleeve"] = str(by_sleeve.index[-1])
            row["best_sleeve_pnl_usd"] = float(by_sleeve.iloc[-1])
        if not month_trades.empty:
            by_ticker = month_trades.groupby("ticker")["pnl_usd"].sum().sort_values()
            row["worst_ticker"] = str(by_ticker.index[0])
            row["worst_ticker_pnl_usd"] = float(by_ticker.iloc[0])
            row["best_ticker"] = str(by_ticker.index[-1])
            row["best_ticker_pnl_usd"] = float(by_ticker.iloc[-1])
            if "exit_reason" in month_trades.columns:
                by_reason = month_trades.groupby("exit_reason")["pnl_usd"].sum().sort_values()
                row["worst_exit_reason"] = str(by_reason.index[0])
                row["worst_exit_reason_pnl_usd"] = float(by_reason.iloc[0])
        attribution_rows.append(row)
    return pd.DataFrame(attribution_rows)


def _review_reason(row: pd.Series) -> tuple[str, str]:
    benchmark_return = row.get("benchmark_return")
    if pd.notna(benchmark_return) and float(benchmark_return) < 0:
        context = "시장 하락 동반"
    elif pd.notna(benchmark_return):
        context = "시장 상승 중 전략 손실"
    else:
        context = "벤치마크 미확인"
    reason = (
        f"{context}; worst={row.get('worst_ticker', '')} "
        f"${float(row.get('worst_ticker_pnl_usd', 0.0)):.2f}; "
        f"sleeve={row.get('worst_sleeve', '')} "
        f"${float(row.get('worst_sleeve_pnl_usd', 0.0)):.2f}; "
        f"2x=${float(row.get('leveraged_realized_pnl_usd', 0.0)):.2f}; "
        f"exit={row.get('worst_exit_reason', '')} "
        f"${float(row.get('worst_exit_reason_pnl_usd', 0.0)):.2f}"
    )
    if int(row.get("stop_loss_count", 0)) > int(row.get("take_profit_count", 0)):
        action = "진입 점수 구간·레짐·손절 연속 발생 종목을 분해하고 진입/손절 변경안을 OOS로 비교"
    elif int(row.get("leveraged_trade_count", 0)) > 0:
        action = "2배 상품과 본주의 동일 신호 성과·변동성·청산 시점 차이를 비교"
    else:
        action = "종목·섹터·청산 사유 기여도를 분해하고 변경안은 다음 기간 forward 검증 후 채택"
    return reason, action


def write_monthly_backtest_review(
    output_dir: str | Path,
    equity_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    *,
    initial_cash: float,
) -> tuple[Path, Path]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    attribution = build_monthly_backtest_attribution(
        equity_df,
        trades_df,
        initial_cash=initial_cash,
    )
    csv_path = target / "monthly_attribution.csv"
    attribution.to_csv(csv_path, index=False)

    queue_path = target / "monthly_review_queue.md"
    lines = [
        "# Monthly Backtest Review Queue",
        "",
        "손실 월과 벤치마크 미달 월은 원인 분해 후 수정안을 검토한다. "
        "단일 백테스트 결과만으로 설정을 자동 변경하지 않는다.",
        "",
    ]
    flagged = attribution[
        (attribution["monthly_return"] < 0)
        | (
            attribution.get("excess_return", pd.Series(index=attribution.index, dtype=float))
            < 0
        )
    ]
    if flagged.empty:
        lines.append("- 현재 검토 대상 월 없음")
    for _, row in flagged.iterrows():
        reason, action = _review_reason(row)
        status = "손실" if float(row["monthly_return"]) < 0 else "벤치마크 미달"
        lines.extend(
            [
                f"## {row['month']} — {status}",
                "",
                f"- 월 수익률: {float(row['monthly_return']):.2%}",
                f"- 원인 후보: {reason}",
                f"- 검토할 수정안: {action}",
                "- 상태: [ ] 원인 확인  [ ] 수정안 백테스트  [ ] forward 검증  [ ] 채택/기각 기록",
                "",
            ]
        )
    queue_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return csv_path, queue_path
