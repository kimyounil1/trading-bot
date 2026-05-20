import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# app/에서 실행해도 src import 되게 프로젝트 루트 추가
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.alpaca_client import (
    get_account_summary,
    get_positions_summary,
    get_order_summary,
    get_open_symbols,
    submit_market_buy_notional_order,
    close_position_by_symbol,
    wait_for_order_status,
)
from src.market_clock import get_market_clock
from src.settings import load_settings, CONFIG_PATH
from src.execution_lock import (
    load_execution_lock,
    save_execution_lock,
    get_required_phrase,
    is_cms_execution_enabled,
)
from src.config import LOG_PATH, ORDER_LOG_PATH, ALPACA_PAPER
from src.notifier import notify_info, telegram_is_configured
from src.notification_settings import (
    load_notification_config,
    save_notification_config,
)
from src.logger import log_order, log_order_status
from src.data_loader import load_price_data
from src.strategy import add_indicators, generate_signal
from src.risk_manager import check_buy_allowed, check_exit_allowed
from src.ml_model import predict_ai_score
from src.portfolio_backtester import (
    run_portfolio_backtest,
    save_portfolio_backtest_outputs,
)


st.set_page_config(
    page_title="Trading Bot CMS",
    page_icon="📈",
    layout="wide",
)


def money(value: float) -> str:
    return f"${value:,.2f}"


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def read_csv_if_exists(path: str) -> pd.DataFrame:
    file_path = ROOT_DIR / path

    if not file_path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(file_path)
    except Exception:
        return pd.DataFrame()


def save_strategy_config(data: dict) -> None:
    config_path = ROOT_DIR / CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")



def save_config_history(old_data: dict, new_data: dict) -> Path:
    output_dir = ROOT_DIR / "logs/config_history"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"config_change_{timestamp}.json"

    changed = {}

    all_keys = sorted(set(old_data.keys()) | set(new_data.keys()))

    for key in all_keys:
        old_value = old_data.get(key)
        new_value = new_data.get(key)

        if old_value != new_value:
            changed[key] = {
                "old": old_value,
                "new": new_value,
            }

    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "changed": changed,
        "old_config": old_data,
        "new_config": new_data,
    }

    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return output_path

def sidebar_settings_editor() -> None:
    st.sidebar.header("Strategy Settings")

    settings = load_settings()

    tickers_text = st.sidebar.text_input(
        "Tickers",
        value=", ".join(settings.tickers),
        help="Comma-separated tickers",
    )

    ma_fast = st.sidebar.number_input(
        "MA Fast",
        min_value=2,
        max_value=250,
        value=int(settings.ma_fast),
        step=1,
    )

    ma_slow = st.sidebar.number_input(
        "MA Slow",
        min_value=5,
        max_value=300,
        value=int(settings.ma_slow),
        step=1,
    )

    rsi_buy_limit = st.sidebar.number_input(
        "RSI Buy Limit",
        min_value=1.0,
        max_value=100.0,
        value=float(settings.rsi_buy_limit),
        step=1.0,
    )

    max_position_pct = st.sidebar.number_input(
        "Max Position %",
        min_value=0.01,
        max_value=1.0,
        value=float(settings.max_position_pct),
        step=0.01,
    )

    max_total_positions = st.sidebar.number_input(
        "Max Total Positions",
        min_value=1,
        max_value=20,
        value=int(settings.max_total_positions),
        step=1,
    )

    stop_loss_pct = st.sidebar.number_input(
        "Stop Loss %",
        min_value=0.01,
        max_value=1.0,
        value=float(settings.stop_loss_pct),
        step=0.01,
    )

    take_profit_pct = st.sidebar.number_input(
        "Take Profit %",
        min_value=0.01,
        max_value=5.0,
        value=float(settings.take_profit_pct),
        step=0.01,
    )

    max_test_order_amount = st.sidebar.number_input(
        "Max Test Order Amount",
        min_value=1.0,
        max_value=100000.0,
        value=float(settings.max_test_order_amount),
        step=1.0,
    )

    max_orders_per_run = st.sidebar.number_input(
        "Max Orders Per Run",
        min_value=1,
        max_value=20,
        value=int(settings.max_orders_per_run),
        step=1,
    )

    use_ai_score = st.sidebar.checkbox(
        "Use AI Score Filter",
        value=bool(getattr(settings, "use_ai_score", False)),
        help="아직 주문 조건에는 적용하지 않고, 다음 단계에서 백테스트 후 적용합니다.",
    )

    ai_score_buy_threshold = st.sidebar.number_input(
        "AI Score Buy Threshold",
        min_value=0.0,
        max_value=1.0,
        value=float(getattr(settings, "ai_score_buy_threshold", 0.55)),
        step=0.01,
    )

    st.sidebar.warning(
        "이 화면은 설정 파일만 수정합니다. 주문 실행은 아직 CLI에서만 하세요."
    )

    if st.sidebar.button("Save Settings"):
        tickers = [
            ticker.strip().upper()
            for ticker in tickers_text.split(",")
            if ticker.strip()
        ]

        if ma_fast >= ma_slow:
            st.sidebar.error("MA Fast must be smaller than MA Slow.")
            return

        if not tickers:
            st.sidebar.error("At least one ticker is required.")
            return

        data = {
            "tickers": tickers,
            "ma_fast": int(ma_fast),
            "ma_slow": int(ma_slow),
            "rsi_buy_limit": float(rsi_buy_limit),
            "max_position_pct": float(max_position_pct),
            "max_total_positions": int(max_total_positions),
            "stop_loss_pct": float(stop_loss_pct),
            "take_profit_pct": float(take_profit_pct),
            "max_test_order_amount": float(max_test_order_amount),
            "max_orders_per_run": int(max_orders_per_run),
            "use_ai_score": bool(use_ai_score),
            "ai_score_buy_threshold": float(ai_score_buy_threshold),
        }

        config_path = ROOT_DIR / CONFIG_PATH

        if config_path.exists():
            old_data = json.loads(config_path.read_text(encoding="utf-8"))
        else:
            old_data = {}

        save_strategy_config(data)
        history_path = save_config_history(old_data, data)

        st.sidebar.success(
            f"Settings saved. History: {history_path.relative_to(ROOT_DIR)}"
        )


def render_overview() -> None:
    st.title("Trading Bot CMS")

    clock = get_market_clock()
    account = get_account_summary()
    positions = get_positions_summary()
    settings = load_settings()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Market Open", str(clock.is_open))
    col2.metric("Cash", money(account["cash"]))
    col3.metric("Portfolio Value", money(account["portfolio_value"]))
    col4.metric("Positions", account["positions_count"])

    st.caption(
        f"Market time: {clock.timestamp} | "
        f"Next open: {clock.next_open} | "
        f"Next close: {clock.next_close}"
    )

    st.divider()

    st.subheader("Current Strategy")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("MA Fast", settings.ma_fast)
    c2.metric("MA Slow", settings.ma_slow)
    c3.metric("RSI Buy Limit", settings.rsi_buy_limit)
    c4.metric("Max Positions", settings.max_total_positions)

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Position %", pct(settings.max_position_pct))
    c6.metric("Stop Loss", pct(settings.stop_loss_pct))
    c7.metric("Take Profit", pct(settings.take_profit_pct))
    c8.metric("Test Order Cap", money(settings.max_test_order_amount))

    st.write("Tickers:", ", ".join(settings.tickers))
    st.write(
        "AI Score:",
        {
            "use_ai_score": getattr(settings, "use_ai_score", False),
            "ai_score_buy_threshold": getattr(settings, "ai_score_buy_threshold", None),
        },
    )

    st.divider()

    st.subheader("Open Positions")
    if positions:
        st.dataframe(pd.DataFrame(positions), use_container_width=True)
    else:
        st.info("No open positions.")



def get_recent_order_ids(limit: int = 10) -> list[str]:
    orders_df = read_csv_if_exists(ORDER_LOG_PATH)

    if orders_df.empty or "order_id" not in orders_df.columns:
        return []

    order_ids = (
        orders_df["order_id"]
        .dropna()
        .astype(str)
        .loc[lambda series: series.str.len() > 0]
        .drop_duplicates()
        .tail(limit)
        .tolist()
    )

    return order_ids


def refresh_recent_order_statuses(limit: int = 10) -> pd.DataFrame:
    order_ids = get_recent_order_ids(limit=limit)
    rows = []

    for order_id in order_ids:
        try:
            order = get_order_summary(order_id)

            row = {
                "order_id": order["id"],
                "ticker": order["symbol"],
                "status": order["status"],
                "side": order["side"],
                "order_type": order["type"],
                "notional": order["notional"],
                "qty": order["qty"],
                "filled_qty": order["filled_qty"],
                "filled_avg_price": order["filled_avg_price"],
                "submitted_at": order["submitted_at"],
                "filled_at": order["filled_at"],
            }
            rows.append(row)

            log_order_status(
                ticker=order["symbol"],
                order_id=order["id"],
                status=order["status"],
                side=order["side"],
                order_type=order["type"],
                filled_qty=order["filled_qty"],
                filled_avg_price=order["filled_avg_price"],
                reason="cms manual refresh",
            )

        except Exception as exc:
            rows.append(
                {
                    "order_id": order_id,
                    "ticker": "",
                    "status": "ERROR",
                    "side": "",
                    "order_type": "",
                    "notional": "",
                    "qty": "",
                    "filled_qty": "",
                    "filled_avg_price": "",
                    "submitted_at": "",
                    "filled_at": "",
                    "error": str(exc),
                }
            )

    return pd.DataFrame(rows)




def load_equity_for_run(run_path: str) -> pd.DataFrame:
    run_dir = ROOT_DIR / run_path
    equity_path = run_dir / "portfolio_equity.csv"

    if not equity_path.exists():
        return pd.DataFrame()

    try:
        df = pd.read_csv(equity_path)
    except Exception:
        return pd.DataFrame()

    if df.empty or "date" not in df.columns or "equity" not in df.columns:
        return pd.DataFrame()

    return df


def render_backtest_compare() -> None:
    st.header("Backtest Compare")

    history_df = load_backtest_run_summaries()

    if history_df.empty:
        st.info("No backtest history found yet.")
        return

    run_options = history_df["run_id"].tolist()

    selected_runs = st.multiselect(
        "Select runs to compare",
        options=run_options,
        default=run_options[: min(3, len(run_options))],
        max_selections=10,
    )

    if not selected_runs:
        st.warning("Select at least one run.")
        return

    selected_df = history_df[history_df["run_id"].isin(selected_runs)].copy()

    metric_cols = [
        "run_id",
        "period",
        "total_return",
        "benchmark_return",
        "excess_return",
        "max_drawdown",
        "trades",
        "win_rate",
        "ma_fast",
        "ma_slow",
        "rsi_buy_limit",
        "max_positions",
        "target_position_pct",
        "tickers",
    ]

    available_cols = [col for col in metric_cols if col in selected_df.columns]

    st.subheader("Comparison Table")
    st.dataframe(selected_df[available_cols], use_container_width=True)

    st.subheader("Return / Risk Metrics")

    chart_metric = st.selectbox(
        "Metric",
        ["total_return", "benchmark_return", "excess_return", "max_drawdown", "win_rate"],
    )

    metric_chart_df = (
        selected_df[["run_id", chart_metric]]
        .set_index("run_id")
        .sort_index()
    )
    st.bar_chart(metric_chart_df)

    st.subheader("Equity Curve Comparison")

    equity_series = []

    for _, row in selected_df.iterrows():
        run_id = row["run_id"]
        run_path = row["run_path"]

        equity_df = load_equity_for_run(run_path)

        if equity_df.empty:
            continue

        tmp = equity_df[["date", "equity"]].copy()
        tmp["date"] = pd.to_datetime(tmp["date"])
        tmp = tmp.sort_values("date")
        tmp = tmp.set_index("date")
        tmp = tmp.rename(columns={"equity": run_id})

        equity_series.append(tmp)

    if not equity_series:
        st.info("No equity curves found for selected runs.")
        return

    combined_equity = pd.concat(equity_series, axis=1).sort_index()
    st.line_chart(combined_equity)

    st.subheader("Normalized Equity Curve")

    normalized = combined_equity / combined_equity.iloc[0]
    st.line_chart(normalized)

    st.caption(
        "Normalized Equity Curve는 각 run의 시작값을 1.0으로 맞춘 비교 차트입니다."
    )

def render_backtest_history() -> None:
    st.header("Backtest History")

    history_df = load_backtest_run_summaries()

    if history_df.empty:
        st.info("No backtest history found yet.")
        return

    display_cols = [
        "run_id",
        "period",
        "total_return",
        "benchmark_return",
        "excess_return",
        "max_drawdown",
        "trades",
        "win_rate",
        "ma_fast",
        "ma_slow",
        "rsi_buy_limit",
        "max_positions",
        "target_position_pct",
        "tickers",
        "run_path",
    ]

    available_cols = [col for col in display_cols if col in history_df.columns]

    st.subheader("Runs")
    st.dataframe(history_df[available_cols], use_container_width=True)

    selected_run = st.selectbox(
        "Select run",
        history_df["run_id"].tolist(),
    )

    selected_row = history_df[history_df["run_id"] == selected_run].iloc[0]
    run_dir = ROOT_DIR / selected_row["run_path"]

    summary_path = run_dir / "portfolio_summary.csv"
    equity_path = run_dir / "portfolio_equity.csv"
    trades_path = run_dir / "portfolio_trades.csv"
    config_path = run_dir / "run_config.json"

    st.subheader("Selected Run Summary")
    summary_df = pd.read_csv(summary_path)
    st.dataframe(summary_df, use_container_width=True)

    if equity_path.exists():
        equity_df = pd.read_csv(equity_path)

        if not equity_df.empty and {"date", "equity", "benchmark_equity"}.issubset(equity_df.columns):
            st.subheader("Equity Curve")
            chart_df = equity_df.set_index("date")[["equity", "benchmark_equity"]]
            st.line_chart(chart_df)

            st.subheader("Recent Equity Rows")
            st.dataframe(equity_df.tail(50), use_container_width=True)

    if trades_path.exists():
        trades_df = pd.read_csv(trades_path)

        st.subheader("Trades")
        if trades_df.empty:
            st.info("No closed trades.")
        else:
            st.dataframe(trades_df, use_container_width=True)

    if config_path.exists():
        st.subheader("Run Config")
        st.json(json.loads(config_path.read_text(encoding="utf-8")))

def render_config_history() -> None:
    st.header("Config History")

    history_dir = ROOT_DIR / "logs/config_history"

    if not history_dir.exists():
        st.info("No config history found.")
        return

    files = sorted(history_dir.glob("config_change_*.json"), reverse=True)

    if not files:
        st.info("No config history files found.")
        return

    selected = st.selectbox(
        "Select history file",
        files,
        format_func=lambda path: path.name,
    )

    payload = json.loads(selected.read_text(encoding="utf-8"))

    st.subheader("Changed Fields")

    changed = payload.get("changed", {})

    if not changed:
        st.info("No changes detected.")
    else:
        rows = []

        for key, value in changed.items():
            rows.append(
                {
                    "field": key,
                    "old": value.get("old"),
                    "new": value.get("new"),
                }
            )

        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    with st.expander("Old Config"):
        st.json(payload.get("old_config", {}))

    with st.expander("New Config"):
        st.json(payload.get("new_config", {}))

def render_logs() -> None:
    st.header("Logs")

    signals_df = read_csv_if_exists(LOG_PATH)
    orders_df = read_csv_if_exists(ORDER_LOG_PATH)

    st.subheader("Recent Signals")
    if signals_df.empty:
        st.info("No signal logs found.")
    else:
        st.dataframe(signals_df.tail(50), use_container_width=True)

    st.subheader("Recent Orders")

    col1, col2 = st.columns([1, 3])
    refresh_clicked = col1.button("Refresh Recent Order Status", type="primary")
    refresh_limit = col2.number_input(
        "Refresh last N unique orders",
        min_value=1,
        max_value=50,
        value=10,
        step=1,
    )

    if refresh_clicked:
        refreshed_df = refresh_recent_order_statuses(limit=int(refresh_limit))

        if refreshed_df.empty:
            st.warning("No order IDs found to refresh.")
        else:
            st.success("Order statuses refreshed.")
            st.dataframe(refreshed_df, use_container_width=True)

    orders_df = read_csv_if_exists(ORDER_LOG_PATH)

    if orders_df.empty:
        st.info("No order logs found.")
    else:
        st.dataframe(orders_df.tail(50), use_container_width=True)

def render_backtest_outputs() -> None:
    st.header("Backtest Outputs")

    portfolio_summary = read_csv_if_exists(
        "logs/portfolio_backtest/portfolio_summary.csv"
    )
    selected_summary = read_csv_if_exists(
        "logs/selected_strategy/portfolio_summary.csv"
    )
    optimization = read_csv_if_exists(
        "logs/optimization/grid_search_results.csv"
    )

    st.subheader("Selected Strategy Summary")
    if selected_summary.empty:
        st.info("No selected strategy summary found.")
    else:
        st.dataframe(selected_summary, use_container_width=True)

    st.subheader("Portfolio Backtest Summary")
    if portfolio_summary.empty:
        st.info("No portfolio backtest summary found.")
    else:
        st.dataframe(portfolio_summary, use_container_width=True)

    st.subheader("Optimization Top 20")
    if optimization.empty:
        st.info("No optimization results found.")
    else:
        st.dataframe(optimization.head(20), use_container_width=True)




def save_backtest_run_history(
    result,
    equity_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    settings,
    period: str,
) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ROOT_DIR / "logs/backtest_runs" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_df = pd.DataFrame(
        [
            {
                "timestamp": timestamp,
                "period": period,
                "initial_cash": result.initial_cash,
                "final_equity": result.final_equity,
                "total_return": result.total_return,
                "benchmark_return": result.benchmark_return,
                "excess_return": result.total_return - result.benchmark_return,
                "max_drawdown": result.max_drawdown,
                "trades": result.trades,
                "win_rate": result.win_rate,
                "ma_fast": settings.ma_fast,
                "ma_slow": settings.ma_slow,
                "rsi_buy_limit": settings.rsi_buy_limit,
                "max_positions": settings.max_total_positions,
                "target_position_pct": settings.max_position_pct,
                "tickers": ",".join(settings.tickers),
            }
        ]
    )

    summary_df.to_csv(output_dir / "portfolio_summary.csv", index=False)
    equity_df.to_csv(output_dir / "portfolio_equity.csv", index=False)
    trades_df.to_csv(output_dir / "portfolio_trades.csv", index=False)

    run_config = {
        "timestamp": timestamp,
        "period": period,
        "tickers": settings.tickers,
        "ma_fast": settings.ma_fast,
        "ma_slow": settings.ma_slow,
        "rsi_buy_limit": settings.rsi_buy_limit,
        "max_position_pct": settings.max_position_pct,
        "max_total_positions": settings.max_total_positions,
        "stop_loss_pct": settings.stop_loss_pct,
        "take_profit_pct": settings.take_profit_pct,
        "max_test_order_amount": settings.max_test_order_amount,
        "max_orders_per_run": settings.max_orders_per_run,
    }

    (output_dir / "run_config.json").write_text(
        json.dumps(run_config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return output_dir


def load_backtest_run_summaries() -> pd.DataFrame:
    runs_dir = ROOT_DIR / "logs/backtest_runs"

    if not runs_dir.exists():
        return pd.DataFrame()

    rows = []

    for summary_path in sorted(runs_dir.glob("*/portfolio_summary.csv")):
        try:
            df = pd.read_csv(summary_path)

            if df.empty:
                continue

            row = df.iloc[0].to_dict()
            row["run_id"] = summary_path.parent.name
            row["run_path"] = str(summary_path.parent.relative_to(ROOT_DIR))
            rows.append(row)

        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)
    return result.sort_values("timestamp", ascending=False)

def run_cms_backtest(period: str = "2y") -> tuple[object, pd.DataFrame, pd.DataFrame]:
    settings = load_settings()

    ticker_data = {}

    progress = st.progress(0)
    status = st.empty()

    for index, ticker in enumerate(settings.tickers, start=1):
        status.write(f"Loading {ticker}...")
        ticker_data[ticker] = load_price_data(ticker, period=period)
        progress.progress(index / len(settings.tickers))

    status.write("Running portfolio backtest...")

    result, equity_df, trades_df = run_portfolio_backtest(
        ticker_data=ticker_data,
        initial_cash=10000.0,
        max_positions=settings.max_total_positions,
        target_position_pct=settings.max_position_pct,
        transaction_cost_pct=0.001,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
        rsi_buy_limit=settings.rsi_buy_limit,
    )

    output_dir = ROOT_DIR / "logs/cms_backtest"
    save_portfolio_backtest_outputs(
        output_dir=output_dir,
        result=result,
        equity_df=equity_df,
        trades_df=trades_df,
    )

    history_dir = save_backtest_run_history(
        result=result,
        equity_df=equity_df,
        trades_df=trades_df,
        settings=settings,
        period=period,
    )

    progress.progress(1.0)
    status.write(f"Backtest complete. Saved history: {history_dir.relative_to(ROOT_DIR)}")

    return result, equity_df, trades_df


def render_run_backtest() -> None:
    st.header("Run Backtest")

    settings = load_settings()

    st.write("현재 저장된 전략 설정으로 포트폴리오 백테스트를 실행합니다.")
    st.code(
        f"""tickers={settings.tickers}
ma_fast={settings.ma_fast}
ma_slow={settings.ma_slow}
rsi_buy_limit={settings.rsi_buy_limit}
max_positions={settings.max_total_positions}
target_position_pct={settings.max_position_pct}
""",
        language="text",
    )

    period = st.selectbox(
        "Backtest Period",
        ["1y", "2y", "5y"],
        index=1,
    )

    st.warning(
        "이 버튼은 주문을 실행하지 않습니다. 과거 데이터 백테스트만 실행합니다."
    )

    if st.button("Run Portfolio Backtest", type="primary"):
        try:
            result, equity_df, trades_df = run_cms_backtest(period=period)

            st.success("Backtest finished.")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Strategy Return", pct(result.total_return))
            col2.metric("Benchmark Return", pct(result.benchmark_return))
            col3.metric("Max Drawdown", pct(result.max_drawdown))
            col4.metric("Final Equity", money(result.final_equity))

            col5, col6 = st.columns(2)
            col5.metric("Trades", result.trades)
            col6.metric("Win Rate", pct(result.win_rate))

            chart_df = equity_df.set_index("date")[["equity", "benchmark_equity"]]
            st.subheader("Equity Curve")
            st.line_chart(chart_df)

            st.subheader("Trades")
            if trades_df.empty:
                st.info("No closed trades.")
            else:
                st.dataframe(trades_df, use_container_width=True)

            st.subheader("Equity Table")
            st.dataframe(equity_df.tail(50), use_container_width=True)

        except Exception as exc:
            st.error(f"Backtest failed: {exc}")



def save_dry_run_snapshot(exit_df: pd.DataFrame, buy_df: pd.DataFrame) -> Path:
    output_dir = ROOT_DIR / "logs/dry_runs"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"dry_run_{timestamp}.csv"

    rows = []

    if not exit_df.empty:
        tmp = exit_df.copy()
        tmp.insert(0, "section", "exit_check")
        rows.append(tmp)

    if not buy_df.empty:
        tmp = buy_df.copy()
        tmp.insert(0, "section", "buy_check")
        rows.append(tmp)

    if rows:
        combined = pd.concat(rows, ignore_index=True, sort=False)
    else:
        combined = pd.DataFrame([{"section": "empty"}])

    combined.to_csv(output_path, index=False)
    return output_path

def get_signal_for_cms(ticker: str, settings) -> tuple[str, pd.Series, float | None]:
    raw_df = load_price_data(ticker)

    df = add_indicators(
        raw_df,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
    )
    signal = generate_signal(df, rsi_buy_limit=settings.rsi_buy_limit)
    latest = df.iloc[-1]

    ai_score = None

    try:
        ai_score = predict_ai_score(raw_df)
    except Exception:
        ai_score = None

    return signal, latest, ai_score


def render_dry_run() -> None:
    st.header("Dry-run")

    st.warning(
        "이 페이지는 주문을 실행하지 않습니다. 현재 설정 기준의 예상 매수/청산 판단만 보여줍니다."
    )

    settings = load_settings()
    clock = get_market_clock()
    account = get_account_summary()
    positions = get_positions_summary()
    open_symbols = {position["symbol"] for position in positions}

    st.subheader("Execution Safety")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Market Open", str(clock.is_open))
    c2.metric("Cash", money(account["cash"]))
    c3.metric("Positions", account["positions_count"])
    c4.metric("Max Orders / Run", settings.max_orders_per_run)

    st.caption(
        f"Market time: {clock.timestamp} | "
        f"Next open: {clock.next_open} | "
        f"Next close: {clock.next_close}"
    )

    st.divider()

    st.subheader("Open Position Exit Check")

    exit_rows = []

    for position in positions:
        ticker = position["symbol"]

        try:
            signal, latest, ai_score = get_signal_for_cms(ticker, settings)
            unrealized_plpc = float(position["unrealized_plpc"])

            exit_decision = check_exit_allowed(
                signal=signal,
                unrealized_plpc=unrealized_plpc,
            )

            exit_rows.append(
                {
                    "ticker": ticker,
                    "qty": position["qty"],
                    "market_value": position["market_value"],
                    "unrealized_pl": position["unrealized_pl"],
                    "unrealized_plpc": unrealized_plpc,
                    "signal": signal,
                    "ai_score": ai_score,
                    "should_exit": exit_decision.should_exit,
                    "exit_reason": exit_decision.reason,
                    "close": float(latest["close"]),
                    "rsi": float(latest["rsi"]),
                    "ma_fast": float(latest["ma_fast"]),
                    "ma_slow": float(latest["ma_slow"]),
                }
            )

        except Exception as exc:
            exit_rows.append(
                {
                    "ticker": ticker,
                    "error": str(exc),
                }
            )

    if exit_rows:
        exit_df = pd.DataFrame(exit_rows)
        st.dataframe(exit_df, use_container_width=True)
    else:
        st.info("No open positions.")

    st.divider()

    st.subheader("Buy Candidate Check")

    buy_rows = []
    cash = account["cash"]
    positions_count = account["positions_count"]
    dry_run_orders_count = 0

    for ticker in settings.tickers:
        try:
            signal, latest, ai_score = get_signal_for_cms(ticker, settings)

            if ticker in open_symbols:
                risk_allowed = False
                reason = "already holding position"
                target_amount = 0.0
            else:
                risk = check_buy_allowed(
                    signal=signal,
                    cash=cash,
                    current_positions_count=positions_count,
                )
                risk_allowed = risk.allowed
                reason = risk.reason
                target_amount = risk.target_amount

            order_amount = min(target_amount, settings.max_test_order_amount)

            would_submit = False
            execution_label = "NOT_ALLOWED"

            if risk_allowed:
                if dry_run_orders_count >= settings.max_orders_per_run:
                    execution_label = "SKIP_MAX_ORDERS"
                elif not clock.is_open:
                    execution_label = "MARKET_CLOSED"
                    would_submit = False
                    dry_run_orders_count += 1
                else:
                    execution_label = "WOULD_SUBMIT_IF_EXECUTED"
                    would_submit = True
                    dry_run_orders_count += 1

            buy_rows.append(
                {
                    "ticker": ticker,
                    "signal": signal,
                    "ai_score": ai_score,
                    "ai_threshold": getattr(settings, "ai_score_buy_threshold", None),
                    "use_ai_score": getattr(settings, "use_ai_score", False),
                    "risk_allowed": risk_allowed,
                    "reason": reason,
                    "target_amount": target_amount,
                    "order_amount": order_amount,
                    "execution_label": execution_label,
                    "would_submit_if_execute": would_submit,
                    "close": float(latest["close"]),
                    "rsi": float(latest["rsi"]),
                    "ma_fast": float(latest["ma_fast"]),
                    "ma_slow": float(latest["ma_slow"]),
                }
            )

        except Exception as exc:
            buy_rows.append(
                {
                    "ticker": ticker,
                    "error": str(exc),
                }
            )

    buy_df = pd.DataFrame(buy_rows)
    st.dataframe(buy_df, use_container_width=True)

    st.caption(
        "MARKET_CLOSED는 --execute를 눌러도 현재 장이 닫혀 실제 주문이 차단된다는 뜻입니다. "
        "WOULD_SUBMIT_IF_EXECUTED는 장이 열려 있고 CLI에서 --execute 실행 시 주문 후보라는 뜻입니다."
    )

    st.divider()

    if st.button("Save Dry-run Snapshot"):
        exit_df_to_save = pd.DataFrame(exit_rows)
        buy_df_to_save = pd.DataFrame(buy_rows)
        output_path = save_dry_run_snapshot(exit_df_to_save, buy_df_to_save)
        st.success(f"Saved dry-run snapshot: {output_path.relative_to(ROOT_DIR)}")



def build_cms_dry_run_rows():
    settings = load_settings()
    clock = get_market_clock()
    account = get_account_summary()
    positions = get_positions_summary()
    open_symbols = {position["symbol"] for position in positions}

    exit_rows = []
    buy_rows = []

    for position in positions:
        ticker = position["symbol"]

        try:
            signal, latest, ai_score = get_signal_for_cms(ticker, settings)
            unrealized_plpc = float(position["unrealized_plpc"])

            exit_decision = check_exit_allowed(
                signal=signal,
                unrealized_plpc=unrealized_plpc,
            )

            exit_rows.append(
                {
                    "ticker": ticker,
                    "qty": position["qty"],
                    "market_value": position["market_value"],
                    "unrealized_pl": position["unrealized_pl"],
                    "unrealized_plpc": unrealized_plpc,
                    "signal": signal,
                    "ai_score": ai_score,
                    "should_exit": exit_decision.should_exit,
                    "exit_reason": exit_decision.reason,
                    "close": float(latest["close"]),
                    "rsi": float(latest["rsi"]),
                    "ma_fast": float(latest["ma_fast"]),
                    "ma_slow": float(latest["ma_slow"]),
                }
            )

        except Exception as exc:
            exit_rows.append(
                {
                    "ticker": ticker,
                    "error": str(exc),
                }
            )

    cash = account["cash"]
    positions_count = account["positions_count"]
    dry_run_orders_count = 0

    for ticker in settings.tickers:
        try:
            signal, latest, ai_score = get_signal_for_cms(ticker, settings)

            if ticker in open_symbols:
                risk_allowed = False
                reason = "already holding position"
                target_amount = 0.0
            else:
                risk = check_buy_allowed(
                    signal=signal,
                    cash=cash,
                    current_positions_count=positions_count,
                )
                risk_allowed = risk.allowed
                reason = risk.reason
                target_amount = risk.target_amount

            order_amount = min(target_amount, settings.max_test_order_amount)

            would_submit = False
            execution_label = "NOT_ALLOWED"

            if risk_allowed:
                if dry_run_orders_count >= settings.max_orders_per_run:
                    execution_label = "SKIP_MAX_ORDERS"
                elif not clock.is_open:
                    execution_label = "MARKET_CLOSED"
                    dry_run_orders_count += 1
                else:
                    execution_label = "WOULD_SUBMIT_IF_EXECUTED"
                    would_submit = True
                    dry_run_orders_count += 1

            buy_rows.append(
                {
                    "ticker": ticker,
                    "signal": signal,
                    "ai_score": ai_score,
                    "ai_threshold": getattr(settings, "ai_score_buy_threshold", None),
                    "use_ai_score": getattr(settings, "use_ai_score", False),
                    "risk_allowed": risk_allowed,
                    "reason": reason,
                    "target_amount": target_amount,
                    "order_amount": order_amount,
                    "execution_label": execution_label,
                    "would_submit_if_execute": would_submit,
                    "close": float(latest["close"]),
                    "rsi": float(latest["rsi"]),
                    "ma_fast": float(latest["ma_fast"]),
                    "ma_slow": float(latest["ma_slow"]),
                }
            )

        except Exception as exc:
            buy_rows.append(
                {
                    "ticker": ticker,
                    "error": str(exc),
                }
            )

    return account, clock, settings, pd.DataFrame(exit_rows), pd.DataFrame(buy_rows)



def save_execution_run_history(
    result_df: pd.DataFrame,
    exit_df: pd.DataFrame,
    buy_df: pd.DataFrame,
    account: dict,
    clock,
    settings,
) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ROOT_DIR / "logs/execution_runs" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    result_df.to_csv(output_dir / "execution_result.csv", index=False)
    exit_df.to_csv(output_dir / "exit_candidates.csv", index=False)
    buy_df.to_csv(output_dir / "buy_candidates.csv", index=False)

    account_path = output_dir / "account_before.json"
    account_path.write_text(
        json.dumps(account, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    context = {
        "timestamp": timestamp,
        "market_is_open": clock.is_open,
        "market_timestamp": clock.timestamp,
        "next_open": clock.next_open,
        "next_close": clock.next_close,
        "settings": {
            "tickers": settings.tickers,
            "ma_fast": settings.ma_fast,
            "ma_slow": settings.ma_slow,
            "rsi_buy_limit": settings.rsi_buy_limit,
            "max_position_pct": settings.max_position_pct,
            "max_total_positions": settings.max_total_positions,
            "stop_loss_pct": settings.stop_loss_pct,
            "take_profit_pct": settings.take_profit_pct,
            "max_test_order_amount": settings.max_test_order_amount,
            "max_orders_per_run": settings.max_orders_per_run,
        },
    }

    (output_dir / "run_context.json").write_text(
        json.dumps(context, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return output_dir

def execute_cms_paper_actions(exit_df: pd.DataFrame, buy_df: pd.DataFrame, settings) -> pd.DataFrame:
    rows = []

    # 1) 청산 후보 먼저 실행
    if not exit_df.empty:
        for _, row in exit_df.iterrows():
            if not bool(row.get("should_exit", False)):
                continue

            ticker = str(row["ticker"])
            reason = str(row.get("exit_reason", ""))

            try:
                order = close_position_by_symbol(ticker)

                log_order(
                    ticker=ticker,
                    notional=0.0,
                    order_id=str(order.id),
                    status=str(order.status),
                    side=str(order.side),
                    order_type=str(order.type),
                    reason=reason,
                )

                checked_order = wait_for_order_status(str(order.id))

                log_order_status(
                    ticker=ticker,
                    order_id=checked_order["id"],
                    status=checked_order["status"],
                    side=checked_order["side"],
                    order_type=checked_order["type"],
                    filled_qty=checked_order["filled_qty"],
                    filled_avg_price=checked_order["filled_avg_price"],
                    reason=f"cms close: {reason}",
                )

                rows.append(
                    {
                        "action": "CLOSE",
                        "ticker": ticker,
                        "order_id": checked_order["id"],
                        "status": checked_order["status"],
                        "filled_qty": checked_order["filled_qty"],
                        "filled_avg_price": checked_order["filled_avg_price"],
                        "reason": reason,
                    }
                )

            except Exception as exc:
                rows.append(
                    {
                        "action": "CLOSE",
                        "ticker": ticker,
                        "status": "ERROR",
                        "reason": reason,
                        "error": str(exc),
                    }
                )

    # 2) 신규 매수 후보 실행
    orders_submitted = 0

    if not buy_df.empty:
        for _, row in buy_df.iterrows():
            if orders_submitted >= settings.max_orders_per_run:
                break

            if str(row.get("execution_label")) != "WOULD_SUBMIT_IF_EXECUTED":
                continue

            ticker = str(row["ticker"])
            order_amount = float(row["order_amount"])
            reason = str(row.get("reason", ""))

            if order_amount <= 0:
                continue

            try:
                order = submit_market_buy_notional_order(
                    ticker=ticker,
                    notional=order_amount,
                )
                orders_submitted += 1

                log_order(
                    ticker=ticker,
                    notional=order_amount,
                    order_id=str(order.id),
                    status=str(order.status),
                    side=str(order.side),
                    order_type=str(order.type),
                    reason=reason,
                )

                checked_order = wait_for_order_status(str(order.id))

                log_order_status(
                    ticker=ticker,
                    order_id=checked_order["id"],
                    status=checked_order["status"],
                    side=checked_order["side"],
                    order_type=checked_order["type"],
                    filled_qty=checked_order["filled_qty"],
                    filled_avg_price=checked_order["filled_avg_price"],
                    reason=f"cms buy: {reason}",
                )

                rows.append(
                    {
                        "action": "BUY",
                        "ticker": ticker,
                        "notional": order_amount,
                        "order_id": checked_order["id"],
                        "status": checked_order["status"],
                        "filled_qty": checked_order["filled_qty"],
                        "filled_avg_price": checked_order["filled_avg_price"],
                        "reason": reason,
                    }
                )

            except Exception as exc:
                rows.append(
                    {
                        "action": "BUY",
                        "ticker": ticker,
                        "notional": order_amount,
                        "status": "ERROR",
                        "reason": reason,
                        "error": str(exc),
                    }
                )

    return pd.DataFrame(rows)


def render_paper_execution() -> None:
    st.header("Paper Execution")

    st.warning(
        "이 페이지는 Alpaca paper 주문/청산을 실행할 수 있습니다. "
        "실계좌가 아니라 paper mode에서만 사용하세요."
    )

    account, clock, settings, exit_df, buy_df = build_cms_dry_run_rows()

    lock_enabled = is_cms_execution_enabled()
    required_phrase = get_required_phrase()

    st.subheader("Safety Checks")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Execution Lock", "ENABLED" if lock_enabled else "LOCKED")
    c2.metric("Market Open", str(clock.is_open))
    c3.metric("Alpaca Paper", str(ALPACA_PAPER))
    c4.metric("Max Order Amount", money(settings.max_test_order_amount))

    st.caption(
        f"Market time: {clock.timestamp} | "
        f"Next open: {clock.next_open} | "
        f"Next close: {clock.next_close}"
    )

    allowed = lock_enabled and clock.is_open and ALPACA_PAPER

    if not lock_enabled:
        st.error("CMS execution lock is disabled. Enable it from Execution Lock page first.")

    if not clock.is_open:
        st.error("Market is closed. CMS paper execution is blocked.")

    if not ALPACA_PAPER:
        st.error("ALPACA_PAPER is False. CMS execution is blocked.")

    st.divider()

    st.subheader("Exit Candidates")
    if exit_df.empty:
        st.info("No open positions to check.")
    else:
        st.dataframe(exit_df, use_container_width=True)

    st.subheader("Buy Candidates")
    if buy_df.empty:
        st.info("No buy candidates.")
    else:
        st.dataframe(buy_df, use_container_width=True)

    st.divider()

    st.subheader("Final Confirmation")

    st.write("실행 가능 상태:", "YES" if allowed else "NO")

    confirmation = st.text_input(
        f"Type `{required_phrase}` to enable the execution button",
        type="password",
    )

    final_allowed = allowed and confirmation == required_phrase

    if not final_allowed:
        st.info("조건이 모두 충족되고 확인 문구가 일치해야 실행 버튼이 활성화됩니다.")

    execute_clicked = st.button(
        "Execute Paper Actions",
        type="primary",
        disabled=not final_allowed,
    )

    if execute_clicked:
        result_df = execute_cms_paper_actions(exit_df, buy_df, settings)

        history_dir = save_execution_run_history(
            result_df=result_df,
            exit_df=exit_df,
            buy_df=buy_df,
            account=account,
            clock=clock,
            settings=settings,
        )

        if result_df.empty:
            st.warning("No paper actions were executed.")
        else:
            st.success(
                f"Paper actions submitted and checked. "
                f"History: {history_dir.relative_to(ROOT_DIR)}"
            )
            st.dataframe(result_df, use_container_width=True)



def render_execution_runs() -> None:
    st.header("Execution Runs")

    runs_dir = ROOT_DIR / "logs/execution_runs"

    if not runs_dir.exists():
        st.info("No execution runs found yet.")
        return

    run_dirs = sorted(
        [path for path in runs_dir.iterdir() if path.is_dir()],
        reverse=True,
    )

    if not run_dirs:
        st.info("No execution runs found yet.")
        return

    selected_dir = st.selectbox(
        "Select execution run",
        run_dirs,
        format_func=lambda path: path.name,
    )

    context_path = selected_dir / "run_context.json"
    account_path = selected_dir / "account_before.json"
    result_path = selected_dir / "execution_result.csv"
    exit_path = selected_dir / "exit_candidates.csv"
    buy_path = selected_dir / "buy_candidates.csv"

    st.subheader("Run Context")
    if context_path.exists():
        st.json(json.loads(context_path.read_text(encoding="utf-8")))
    else:
        st.info("No run_context.json found.")

    st.subheader("Account Before")
    if account_path.exists():
        st.json(json.loads(account_path.read_text(encoding="utf-8")))
    else:
        st.info("No account_before.json found.")

    st.subheader("Execution Result")
    if result_path.exists():
        result_df = pd.read_csv(result_path)
        if result_df.empty:
            st.info("No actions executed.")
        else:
            st.dataframe(result_df, use_container_width=True)
    else:
        st.info("No execution_result.csv found.")

    st.subheader("Exit Candidates")
    if exit_path.exists():
        exit_df = pd.read_csv(exit_path)
        st.dataframe(exit_df, use_container_width=True)
    else:
        st.info("No exit_candidates.csv found.")

    st.subheader("Buy Candidates")
    if buy_path.exists():
        buy_df = pd.read_csv(buy_path)
        st.dataframe(buy_df, use_container_width=True)
    else:
        st.info("No buy_candidates.csv found.")

def render_execution_lock() -> None:
    st.header("Execution Lock")

    lock = load_execution_lock()
    required_phrase = get_required_phrase()

    enabled = bool(lock.get("cms_execution_enabled", False))

    if enabled:
        st.success("CMS paper execution is currently ENABLED.")
    else:
        st.warning("CMS paper execution is currently LOCKED.")

    st.write("이 잠금은 나중에 CMS에서 paper 주문/청산 버튼을 만들 때 사용할 안전장치입니다.")
    st.write("현재 단계에서는 잠금 상태만 관리하고, 실제 주문 버튼은 아직 추가하지 않습니다.")

    c1, c2 = st.columns(2)
    c1.metric("cms_execution_enabled", str(enabled))
    c2.metric("last_updated", str(lock.get("last_updated")))

    st.divider()

    st.subheader("Unlock CMS Execution")

    st.info(
        f"잠금을 해제하려면 아래 문구를 정확히 입력하세요: `{required_phrase}`"
    )

    phrase = st.text_input("Confirmation phrase", type="password")

    if st.button("Enable CMS Paper Execution"):
        if phrase == required_phrase:
            save_execution_lock(True)
            st.success("CMS paper execution enabled. Refresh page to confirm.")
        else:
            st.error("Confirmation phrase does not match.")

    st.divider()

    st.subheader("Lock CMS Execution")

    if st.button("Disable CMS Paper Execution"):
        save_execution_lock(False)
        st.success("CMS paper execution disabled. Refresh page to confirm.")


SCHEDULER_CONFIG_PATH = ROOT_DIR / "config/scheduler_config.json"


def load_scheduler_config() -> dict:
    default = {
        "enabled": False,
        "mode": "dry-run",
        "timezone": "America/New_York",
        "schedule_note": "Weekdays after US market open. Recommended: 10:00 ET.",
        "systemd_on_calendar": "Mon..Fri 10:00",
        "service_name": "trading-bot.service",
        "timer_name": "trading-bot.timer",
    }

    if not SCHEDULER_CONFIG_PATH.exists():
        SCHEDULER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULER_CONFIG_PATH.write_text(
            json.dumps(default, indent=2),
            encoding="utf-8",
        )
        return default

    data = json.loads(SCHEDULER_CONFIG_PATH.read_text(encoding="utf-8"))
    default.update(data)
    return default


def save_scheduler_config(data: dict) -> None:
    SCHEDULER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULER_CONFIG_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_recent_bot_run_logs(limit: int = 10) -> list[Path]:
    log_dir = ROOT_DIR / "logs/bot_runs"

    if not log_dir.exists():
        return []

    return sorted(log_dir.glob("bot_run_*.log"), reverse=True)[:limit]


def render_scheduler() -> None:
    st.header("Scheduler")

    st.warning(
        "현재 자동 실행은 기본 dry-run 전용으로 구성합니다. "
        "execute 자동 실행은 충분한 paper 검증 후 별도로 바꾸는 것을 추천합니다."
    )

    config = load_scheduler_config()

    st.subheader("Scheduler Config")

    enabled = st.checkbox("Enabled in config", value=bool(config.get("enabled", False)))
    mode = st.selectbox(
        "Mode",
        ["dry-run", "execute"],
        index=0 if config.get("mode", "dry-run") == "dry-run" else 1,
    )
    on_calendar = st.text_input(
        "systemd OnCalendar",
        value=str(config.get("systemd_on_calendar", "Mon..Fri 10:00")),
    )
    timezone = st.text_input(
        "Timezone",
        value=str(config.get("timezone", "America/New_York")),
    )
    schedule_note = st.text_area(
        "Schedule Note",
        value=str(config.get("schedule_note", "")),
    )

    if st.button("Save Scheduler Config"):
        new_config = {
            "enabled": bool(enabled),
            "mode": mode,
            "timezone": timezone,
            "schedule_note": schedule_note,
            "systemd_on_calendar": on_calendar,
            "service_name": "trading-bot.service",
            "timer_name": "trading-bot.timer",
        }
        save_scheduler_config(new_config)
        st.success("Scheduler config saved.")

    st.divider()

    st.subheader("Manual Bot Run")

    col1, col2 = st.columns(2)

    if col1.button("Run Dry-run Now"):
        proc = subprocess.run(
            [str(ROOT_DIR / "scripts/run_bot_once.sh"), "dry-run"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            st.success("Dry-run completed. Check recent logs below.")
        else:
            st.error("Dry-run failed.")
            st.code(proc.stderr)

    if col2.button("Run Execute Now"):
        st.error(
            "Execute from Scheduler page is intentionally disabled. "
            "Use Paper Execution page with lock + confirmation."
        )

    st.divider()

    st.subheader("systemd Timer Commands")

    st.code(
        """./scripts/install_user_timer.sh
systemctl --user enable --now trading-bot.timer
systemctl --user list-timers trading-bot.timer
systemctl --user status trading-bot.timer
systemctl --user disable --now trading-bot.timer""",
        language="bash",
    )

    st.divider()

    st.subheader("Recent Bot Run Logs")

    logs = get_recent_bot_run_logs(limit=10)

    if not logs:
        st.info("No bot run logs found.")
        return

    selected_log = st.selectbox(
        "Select log",
        logs,
        format_func=lambda path: path.name,
    )

    st.code(selected_log.read_text(encoding="utf-8")[-8000:], language="text")


def render_telegram() -> None:
    st.header("Telegram Alerts")

    configured = telegram_is_configured()
    config = load_notification_config()

    if configured:
        st.success("Telegram is configured.")
    else:
        st.warning(
            "Telegram is not fully configured. Check TELEGRAM_BOT_TOKEN, "
            "TELEGRAM_CHAT_ID, TELEGRAM_ENABLED in .env and notification settings below."
        )

    st.write("Telegram 알림은 실행 요약, 주문 체결 확인, 청산, 주요 에러에 사용됩니다.")

    st.subheader("Notification Settings")

    telegram_enabled_value = st.checkbox(
        "Telegram Enabled",
        value=bool(config.get("telegram_enabled", True)),
    )

    notify_run_summary_value = st.checkbox(
        "Run Summary Alerts",
        value=bool(config.get("notify_run_summary", True)),
    )

    notify_orders_value = st.checkbox(
        "Order Alerts",
        value=bool(config.get("notify_orders", True)),
    )

    notify_errors_value = st.checkbox(
        "Error Alerts",
        value=bool(config.get("notify_errors", True)),
    )

    if st.button("Save Notification Settings"):
        save_notification_config(
            {
                "telegram_enabled": telegram_enabled_value,
                "notify_run_summary": notify_run_summary_value,
                "notify_orders": notify_orders_value,
                "notify_errors": notify_errors_value,
            }
        )
        st.success("Notification settings saved.")

    st.divider()

    st.subheader("Test Message")

    test_message = st.text_area(
        "Test message",
        value="Trading bot Telegram test from CMS.",
    )

    if st.button("Send Telegram Test Message"):
        try:
            ok = notify_info(
                title="CMS Telegram Test",
                body=test_message,
            )

            if ok:
                st.success("Telegram message sent.")
            else:
                st.error("Telegram message was not sent. Check configuration.")

        except Exception as exc:
            st.error(f"Telegram send failed: {exc}")



def run_project_command(command: list[str], timeout: int = 600) -> tuple[int, str, str]:
    proc = subprocess.run(
        command,
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr



def validate_selected_ai_threshold(threshold: float) -> tuple[object, object, pd.DataFrame, pd.DataFrame]:
    settings = load_settings()

    ticker_data = {}

    for ticker in settings.tickers:
        ticker_data[ticker] = load_price_data(ticker, period="2y")

    baseline_result, baseline_equity, _ = run_portfolio_backtest(
        ticker_data=ticker_data,
        initial_cash=10000.0,
        max_positions=settings.max_total_positions,
        target_position_pct=settings.max_position_pct,
        transaction_cost_pct=0.001,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
        rsi_buy_limit=settings.rsi_buy_limit,
        use_ai_score=False,
        ai_score_buy_threshold=threshold,
    )

    ai_result, ai_equity, _ = run_portfolio_backtest(
        ticker_data=ticker_data,
        initial_cash=10000.0,
        max_positions=settings.max_total_positions,
        target_position_pct=settings.max_position_pct,
        transaction_cost_pct=0.001,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
        rsi_buy_limit=settings.rsi_buy_limit,
        use_ai_score=True,
        ai_score_buy_threshold=threshold,
    )

    return baseline_result, ai_result, baseline_equity, ai_equity

def apply_ai_threshold_to_strategy(threshold: float, enable_ai: bool = True) -> Path:
    config_path = ROOT_DIR / CONFIG_PATH

    if config_path.exists():
        old_data = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        old_data = {}

    new_data = dict(old_data)
    new_data["use_ai_score"] = bool(enable_ai)
    new_data["ai_score_buy_threshold"] = float(threshold)

    save_strategy_config(new_data)
    history_path = save_config_history(old_data, new_data)

    return history_path

def render_ai_model() -> None:
    st.header("AI Model")

    settings = load_settings()

    model_path = ROOT_DIR / "models/ai_score_model.joblib"
    metrics_path = ROOT_DIR / "logs/ml/ai_model_metrics.csv"
    threshold_path = ROOT_DIR / "logs/ai_threshold/threshold_results.csv"

    st.subheader("Current AI Settings")

    c1, c2, c3 = st.columns(3)
    c1.metric("Use AI Score", str(getattr(settings, "use_ai_score", False)))
    c2.metric("AI Threshold", getattr(settings, "ai_score_buy_threshold", None))
    c3.metric("Model Exists", str(model_path.exists()))

    if model_path.exists():
        st.caption(f"Model path: {model_path.relative_to(ROOT_DIR)}")
    else:
        st.warning("AI model file not found. Run `python -m src.train_ai_model` first.")

    st.divider()

    st.subheader("Model Training Metrics")

    if not metrics_path.exists():
        st.info("No AI model metrics found. Run `python -m src.train_ai_model`.")
    else:
        metrics_df = pd.read_csv(metrics_path)
        st.dataframe(metrics_df, use_container_width=True)

        metric_cols = [
            col for col in ["accuracy", "precision", "recall", "roc_auc"]
            if col in metrics_df.columns
        ]

        if metric_cols and "fold" in metrics_df.columns:
            chart_df = metrics_df.set_index("fold")[metric_cols]
            st.line_chart(chart_df)

    st.divider()

    st.subheader("AI Threshold Optimization")

    if not threshold_path.exists():
        st.info("No threshold optimization results found. Run `python -m src.optimize_ai_threshold`.")
    else:
        threshold_df = pd.read_csv(threshold_path)
        st.dataframe(threshold_df, use_container_width=True)

        ai_only = threshold_df[threshold_df["mode"] == "ai_filtered"].copy()

        if not ai_only.empty:
            ai_only["label"] = ai_only["ai_threshold"].astype(str)

            st.subheader("Return / MDD by Threshold")

            chart_df = ai_only.set_index("label")[
                ["total_return", "max_drawdown", "win_rate"]
            ]
            st.bar_chart(chart_df)

            st.subheader("Risk Adjusted Score")

            if "risk_adjusted_score" in ai_only.columns:
                score_df = ai_only.set_index("label")[["risk_adjusted_score"]]
                st.bar_chart(score_df)

            best_row = ai_only.sort_values(
                ["risk_adjusted_score", "total_return"],
                ascending=[False, False],
            ).iloc[0]

            st.success(
                "Best threshold by risk_adjusted_score: "
                f"{best_row['ai_threshold']} | "
                f"return={best_row['total_return'] * 100:.2f}% | "
                f"mdd={best_row['max_drawdown'] * 100:.2f}% | "
                f"win_rate={best_row['win_rate'] * 100:.2f}%"
            )

            st.caption(
                "현재 결과 기준으로는 0.40~0.45 구간이 좋고, "
                "실제 paper bot에는 0.45를 적용한 상태입니다."
            )

            st.divider()

            st.subheader("Apply Threshold to Strategy")

            threshold_options = sorted(
                ai_only["ai_threshold"].dropna().astype(float).unique().tolist()
            )

            default_index = 0
            if 0.45 in threshold_options:
                default_index = threshold_options.index(0.45)

            selected_threshold = st.selectbox(
                "Select AI threshold",
                threshold_options,
                index=default_index,
            )

            enable_ai_filter = st.checkbox(
                "Enable AI score filter in strategy",
                value=True,
            )

            st.warning(
                "이 버튼은 실제 주문을 실행하지 않습니다. "
                "config/strategy_config.json의 AI 설정만 변경합니다."
            )

            if st.button("Apply Selected AI Threshold", type="primary"):
                history_path = apply_ai_threshold_to_strategy(
                    threshold=float(selected_threshold),
                    enable_ai=bool(enable_ai_filter),
                )

                st.success(
                    f"Applied AI threshold={selected_threshold}. "
                    f"History: {history_path.relative_to(ROOT_DIR)}"
                )

            if st.button("Validate Selected Threshold"):
                with st.spinner("Running baseline vs AI-filtered validation..."):
                    try:
                        baseline_result, ai_result, baseline_equity, ai_equity = (
                            validate_selected_ai_threshold(float(selected_threshold))
                        )

                        comparison_df = pd.DataFrame(
                            [
                                {
                                    "mode": "baseline",
                                    "threshold": None,
                                    "total_return": baseline_result.total_return,
                                    "benchmark_return": baseline_result.benchmark_return,
                                    "max_drawdown": baseline_result.max_drawdown,
                                    "trades": baseline_result.trades,
                                    "win_rate": baseline_result.win_rate,
                                    "final_equity": baseline_result.final_equity,
                                },
                                {
                                    "mode": "ai_filtered",
                                    "threshold": float(selected_threshold),
                                    "total_return": ai_result.total_return,
                                    "benchmark_return": ai_result.benchmark_return,
                                    "max_drawdown": ai_result.max_drawdown,
                                    "trades": ai_result.trades,
                                    "win_rate": ai_result.win_rate,
                                    "final_equity": ai_result.final_equity,
                                },
                            ]
                        )

                        st.subheader("Validation Result")
                        st.dataframe(comparison_df, use_container_width=True)

                        chart_df = pd.DataFrame(
                            {
                                "date": baseline_equity["date"],
                                "baseline": baseline_equity["equity"],
                                "ai_filtered": ai_equity["equity"],
                                "benchmark": baseline_equity["benchmark_equity"],
                            }
                        ).set_index("date")

                        st.subheader("Validation Equity Curve")
                        st.line_chart(chart_df)

                    except Exception as exc:
                        st.error(f"Validation failed: {exc}")

    st.divider()

    st.subheader("Run AI Jobs from CMS")

    st.warning(
        "이 작업들은 주문을 실행하지 않습니다. 다만 데이터 다운로드와 백테스트 때문에 시간이 걸릴 수 있습니다."
    )

    col1, col2, col3 = st.columns(3)

    if col1.button("Train AI Model", type="primary"):
        with st.spinner("Training AI model..."):
            try:
                code, stdout, stderr = run_project_command(
                    [str(ROOT_DIR / ".venv/bin/python"), "-m", "src.train_ai_model"],
                    timeout=900,
                )

                if code == 0:
                    st.success("AI model training completed.")
                else:
                    st.error("AI model training failed.")

                if stdout:
                    st.subheader("stdout")
                    st.code(stdout[-12000:], language="text")

                if stderr:
                    st.subheader("stderr")
                    st.code(stderr[-12000:], language="text")

            except Exception as exc:
                st.error(f"AI model training failed: {exc}")

    if col2.button("Optimize AI Threshold"):
        with st.spinner("Optimizing AI threshold..."):
            try:
                code, stdout, stderr = run_project_command(
                    [str(ROOT_DIR / ".venv/bin/python"), "-m", "src.optimize_ai_threshold"],
                    timeout=3600,
                )

                if code == 0:
                    st.success("AI threshold optimization completed.")
                else:
                    st.error("AI threshold optimization failed.")

                if stdout:
                    st.subheader("stdout")
                    st.code(stdout[-12000:], language="text")

                if stderr:
                    st.subheader("stderr")
                    st.code(stderr[-12000:], language="text")

            except Exception as exc:
                st.error(f"AI threshold optimization failed: {exc}")

    if col3.button("Check AI Scores"):
        with st.spinner("Checking AI scores..."):
            try:
                code, stdout, stderr = run_project_command(
                    [str(ROOT_DIR / ".venv/bin/python"), "-m", "src.check_ai_score"],
                    timeout=300,
                )

                if code == 0:
                    st.success("AI score check completed.")
                else:
                    st.error("AI score check failed.")

                if stdout:
                    st.subheader("stdout")
                    st.code(stdout[-12000:], language="text")

                if stderr:
                    st.subheader("stderr")
                    st.code(stderr[-12000:], language="text")

            except Exception as exc:
                st.error(f"AI score check failed: {exc}")

    st.info("작업 완료 후 페이지를 새로고침하면 최신 metrics/threshold 결과가 반영됩니다.")

    st.divider()

    st.subheader("Commands")

    st.code(
        """python -m src.train_ai_model
python -m src.check_ai_score
python -m src.run_ai_backtest
python -m src.optimize_ai_threshold""",
        language="bash",
    )

def main() -> None:
    sidebar_settings_editor()

    page = st.sidebar.radio(
        "Page",
        ["Overview", "Logs", "Backtests", "Run Backtest", "Backtest History", "Backtest Compare", "Dry-run", "Config History", "Execution Lock", "Paper Execution", "Execution Runs", "Scheduler", "Telegram", "AI Model"],
    )

    if page == "Overview":
        render_overview()
    elif page == "Logs":
        render_logs()
    elif page == "Backtests":
        render_backtest_outputs()
    elif page == "Run Backtest":
        render_run_backtest()
    elif page == "Backtest History":
        render_backtest_history()
    elif page == "Backtest Compare":
        render_backtest_compare()
    elif page == "Dry-run":
        render_dry_run()
    elif page == "Config History":
        render_config_history()
    elif page == "Execution Lock":
        render_execution_lock()
    elif page == "Paper Execution":
        render_paper_execution()
    elif page == "Execution Runs":
        render_execution_runs()
    elif page == "Scheduler":
        render_scheduler()
    elif page == "Telegram":
        render_telegram()
    elif page == "AI Model":
        render_ai_model()


if __name__ == "__main__":
    main()
