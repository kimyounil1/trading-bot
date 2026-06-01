import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# app/에서 실행해도 src import 되게 프로젝트 루트 추가
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from src.alpaca_client import (
    get_account_summary,
    get_positions_summary,
    get_order_summary,
    get_open_orders,
    get_recent_closed_orders,
    get_open_symbols,
    wait_for_order_status,
)
from src.broker_adapter import get_broker_adapter
from src.market_clock import get_market_clock, MarketClock
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
from src.data_loader import load_price_data_batch
from src.candidate_cache import load_latest_candidate_cache_full
from src.cms_helpers import (
    cache_age_minutes as _cache_age_minutes,
    classify_buy_candidates,
    count_filled_today as _count_filled_today,
    is_executable_buy_row as _is_executable_buy_row,
    money,
    order_display_columns as _order_display_columns,
    order_is_filled as _order_is_filled,
    orders_to_frame as _orders_to_frame,
    partition_alpaca_orders,
    pct,
    reconcile_cms_execute_with_alpaca,
    sort_buy_candidates,
)


def load_trading_clock(settings=None):
    if settings is None:
        settings = load_settings()
    return get_market_clock(settings)


def render_trading_clock_banner(clock: MarketClock) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("정규장(RTH)", str(clock.is_open))
    col2.metric("주문 가능", str(clock.orders_allowed))
    col3.metric("거래 세션", clock.session.value)
    col4.metric("브로커", clock.broker_provider)
    st.caption(
        f"시장 시간: {clock.timestamp} | "
        f"extended_hours={clock.extended_hours_enabled} | "
        f"다음 개장: {clock.next_open} | "
        f"다음 폐장: {clock.next_close}"
    )


def render_alpaca_order_board(*, closed_limit: int = 50) -> None:
    st.subheader("Alpaca 주문 현황")

    col_refresh, col_limit = st.columns([1, 3])
    col_refresh.button("Alpaca 주문 새로고침", type="primary", key="refresh_alpaca_orders")
    closed_limit = col_limit.number_input(
        "최근 종료 주문 조회 수",
        min_value=10,
        max_value=200,
        value=int(closed_limit),
        step=10,
        key="alpaca_closed_order_limit",
    )

    try:
        open_orders = get_open_orders()
        closed_orders = get_recent_closed_orders(limit=int(closed_limit))
    except Exception as exc:
        st.error(f"Alpaca 주문 조회 실패: {exc}")
        return

    filled_orders, closed_other, partial_open = partition_alpaca_orders(
        open_orders, closed_orders
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("미체결/대기", len(open_orders))
    m2.metric("부분 체결(미완료)", len(partial_open))
    m3.metric("최근 체결 완료", len(filled_orders))
    m4.metric("오늘 체결", _count_filled_today(closed_orders))

    st.caption(
        "미체결은 Alpaca OPEN 주문입니다. extended/overnight 지정가는 시장가 도달 전까지 "
        "대기 상태로 남을 수 있습니다."
    )

    columns = _order_display_columns()
    tab_open, tab_filled, tab_other = st.tabs(
        ["미체결 / 대기", "체결 완료", "취소·만료·거절"]
    )

    with tab_open:
        open_df = _orders_to_frame(open_orders, columns["open"])
        if open_df.empty:
            st.info("현재 미체결 주문이 없습니다.")
        else:
            st.dataframe(open_df, width="stretch")

    with tab_filled:
        filled_df = _orders_to_frame(filled_orders, columns["filled"])
        if filled_df.empty:
            st.info("최근 체결 완료 주문이 없습니다.")
        else:
            st.dataframe(filled_df, width="stretch")

    with tab_other:
        other_df = _orders_to_frame(closed_other, columns["closed_other"])
        if other_df.empty:
            st.info("최근 취소·만료·거절 주문이 없습니다.")
        else:
            st.dataframe(other_df, width="stretch")

    with st.expander("로컬 주문 로그와 비교"):
        log_df = read_csv_if_exists(ORDER_LOG_PATH)
        if log_df.empty:
            st.info("로컬 주문 로그가 없습니다.")
        else:
            recent_log = log_df.tail(30)
            st.write("최근 로컬 로그 30건")
            st.dataframe(recent_log, width="stretch")
            st.caption(
                "로컬 로그는 봇/CMS가 기록한 제출 이력이고, 위 탭은 Alpaca 실시간 상태입니다."
            )


def _portfolio_backtest_api():
    """Defer import so CMS pages without backtest work if optional deps are missing."""
    from src.portfolio_backtester import (
        run_portfolio_backtest,
        save_portfolio_backtest_outputs,
    )

    return run_portfolio_backtest, save_portfolio_backtest_outputs


st.set_page_config(
    page_title="트레이딩 봇 CMS",
    page_icon="📈",
    layout="wide",
)


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
    st.sidebar.header("전략 설정")

    settings = load_settings()

    tickers_text = st.sidebar.text_input(
        "티커 목록",
        value=", ".join(settings.tickers),
        help="쉼표로 구분해서 입력하세요.",
    )

    ma_fast = st.sidebar.number_input(
        "단기 이동평균",
        min_value=2,
        max_value=250,
        value=int(settings.ma_fast),
        step=1,
    )

    ma_slow = st.sidebar.number_input(
        "장기 이동평균",
        min_value=5,
        max_value=300,
        value=int(settings.ma_slow),
        step=1,
    )

    rsi_buy_limit = st.sidebar.number_input(
        "RSI 매수 상한",
        min_value=1.0,
        max_value=100.0,
        value=float(settings.rsi_buy_limit),
        step=1.0,
    )

    max_position_pct = st.sidebar.number_input(
        "포지션 비중 상한",
        min_value=0.01,
        max_value=1.0,
        value=float(settings.max_position_pct),
        step=0.01,
    )

    max_total_positions = st.sidebar.number_input(
        "최대 보유 종목 수",
        min_value=1,
        max_value=20,
        value=int(settings.max_total_positions),
        step=1,
    )

    stop_loss_pct = st.sidebar.number_input(
        "손절 기준",
        min_value=0.01,
        max_value=1.0,
        value=float(settings.stop_loss_pct),
        step=0.01,
    )

    take_profit_pct = st.sidebar.number_input(
        "익절 기준",
        min_value=0.01,
        max_value=5.0,
        value=float(settings.take_profit_pct),
        step=0.01,
    )

    max_test_order_amount = st.sidebar.number_input(
        "테스트 주문 금액 상한",
        min_value=1.0,
        max_value=100000.0,
        value=float(settings.max_test_order_amount),
        step=1.0,
    )

    max_orders_per_run = st.sidebar.number_input(
        "실행당 최대 주문 수",
        min_value=1,
        max_value=20,
        value=int(settings.max_orders_per_run),
        step=1,
    )

    max_daily_order_amount = st.sidebar.number_input(
        "일일 주문 금액 상한",
        min_value=1.0,
        max_value=1000000.0,
        value=float(getattr(settings, "max_daily_order_amount", 1000.0)),
        step=100.0,
    )

    buy_cooldown_days = st.sidebar.number_input(
        "재매수 cooldown 일수",
        min_value=0,
        max_value=30,
        value=int(getattr(settings, "buy_cooldown_days", 1)),
        step=1,
    )

    use_ai_score = st.sidebar.checkbox(
        "AI 점수 필터 사용",
        value=bool(getattr(settings, "use_ai_score", False)),
        help="아직 주문 조건에는 적용하지 않고, 다음 단계에서 백테스트 후 적용합니다.",
    )

    ai_score_buy_threshold = st.sidebar.number_input(
        "AI 매수 점수 기준",
        min_value=0.0,
        max_value=1.0,
        value=float(getattr(settings, "ai_score_buy_threshold", 0.55)),
        step=0.01,
    )

    relative_strength_filter_enabled = st.sidebar.checkbox(
        "상대강도 필터 사용",
        value=bool(getattr(settings, "relative_strength_filter_enabled", False)),
        help="종목 최근 수익률이 벤치마크 최근 수익률 이상일 때만 매수 후보로 남깁니다.",
    )

    relative_strength_benchmark_ticker = st.sidebar.text_input(
        "상대강도 벤치마크",
        value=str(getattr(settings, "relative_strength_benchmark_ticker", "SPY")),
    )

    relative_strength_lookback_days = st.sidebar.number_input(
        "상대강도 기간(일)",
        min_value=1,
        max_value=252,
        value=int(getattr(settings, "relative_strength_lookback_days", 20)),
        step=1,
    )

    relative_strength_min_excess_return = st.sidebar.number_input(
        "최소 초과수익률",
        min_value=-1.0,
        max_value=1.0,
        value=float(getattr(settings, "relative_strength_min_excess_return", 0.0)),
        step=0.01,
    )

    volume_filter_enabled = st.sidebar.checkbox(
        "거래량 필터 사용",
        value=bool(getattr(settings, "volume_filter_enabled", False)),
        help="현재 거래량이 최근 평균 거래량 대비 기준 이상일 때만 매수 후보로 남깁니다.",
    )

    volume_lookback_days = st.sidebar.number_input(
        "거래량 평균 기간(일)",
        min_value=1,
        max_value=252,
        value=int(getattr(settings, "volume_lookback_days", 20)),
        step=1,
    )

    min_volume_ratio = st.sidebar.number_input(
        "최소 거래량 비율",
        min_value=0.0,
        max_value=10.0,
        value=float(getattr(settings, "min_volume_ratio", 1.0)),
        step=0.1,
    )

    volatility_filter_enabled = st.sidebar.checkbox(
        "변동성 필터 사용",
        value=bool(getattr(settings, "volatility_filter_enabled", False)),
        help="최근 일간 수익률 변동성이 기준 이하일 때만 매수 후보로 남깁니다.",
    )

    volatility_lookback_days = st.sidebar.number_input(
        "변동성 기간(일)",
        min_value=1,
        max_value=252,
        value=int(getattr(settings, "volatility_lookback_days", 20)),
        step=1,
    )

    max_volatility = st.sidebar.number_input(
        "최대 변동성",
        min_value=0.0,
        max_value=1.0,
        value=float(getattr(settings, "max_volatility", 0.04)),
        step=0.01,
    )

    rank_trend_weight = st.sidebar.number_input(
        "랭킹 추세 가중치",
        min_value=0.0,
        max_value=10.0,
        value=float(getattr(settings, "rank_trend_weight", 1.0)),
        step=0.1,
    )

    rank_ai_weight = st.sidebar.number_input(
        "랭킹 AI 가중치",
        min_value=0.0,
        max_value=10.0,
        value=float(getattr(settings, "rank_ai_weight", 0.0)),
        step=0.1,
    )

    rank_momentum_weight = st.sidebar.number_input(
        "랭킹 모멘텀 가중치",
        min_value=0.0,
        max_value=10.0,
        value=float(getattr(settings, "rank_momentum_weight", 0.0)),
        step=0.1,
    )

    rank_volatility_weight = st.sidebar.number_input(
        "랭킹 변동성 가중치",
        min_value=0.0,
        max_value=10.0,
        value=float(getattr(settings, "rank_volatility_weight", 0.0)),
        step=0.1,
    )

    st.sidebar.warning(
        "이 화면은 설정 파일만 수정합니다. 주문 실행은 Paper 실행 화면에서 별도 확인 후 진행하세요."
    )

    if st.sidebar.button("설정 저장"):
        tickers = [
            ticker.strip().upper()
            for ticker in tickers_text.split(",")
            if ticker.strip()
        ]

        if ma_fast >= ma_slow:
            st.sidebar.error("단기 이동평균은 장기 이동평균보다 작아야 합니다.")
            return

        if not tickers:
            st.sidebar.error("최소 1개 이상의 티커가 필요합니다.")
            return

        config_path = ROOT_DIR / CONFIG_PATH

        if config_path.exists():
            old_data = json.loads(config_path.read_text(encoding="utf-8"))
        else:
            old_data = {}

        data = dict(old_data)
        data.update({
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
            "max_daily_order_amount": float(max_daily_order_amount),
            "buy_cooldown_days": int(buy_cooldown_days),
            "use_ai_score": bool(use_ai_score),
            "ai_score_buy_threshold": float(ai_score_buy_threshold),
            "relative_strength_filter_enabled": bool(relative_strength_filter_enabled),
            "relative_strength_benchmark_ticker": relative_strength_benchmark_ticker.strip().upper(),
            "relative_strength_lookback_days": int(relative_strength_lookback_days),
            "relative_strength_min_excess_return": float(relative_strength_min_excess_return),
            "volume_filter_enabled": bool(volume_filter_enabled),
            "volume_lookback_days": int(volume_lookback_days),
            "min_volume_ratio": float(min_volume_ratio),
            "volatility_filter_enabled": bool(volatility_filter_enabled),
            "volatility_lookback_days": int(volatility_lookback_days),
            "max_volatility": float(max_volatility),
            "rank_trend_weight": float(rank_trend_weight),
            "rank_ai_weight": float(rank_ai_weight),
            "rank_momentum_weight": float(rank_momentum_weight),
            "rank_volatility_weight": float(rank_volatility_weight),
        })

        save_strategy_config(data)
        history_path = save_config_history(old_data, data)

        st.sidebar.success(
            f"설정을 저장했습니다. 변경 이력: {history_path.relative_to(ROOT_DIR)}"
        )


def render_overview() -> None:
    st.title("트레이딩 봇 CMS")

    settings = load_settings()
    clock = load_trading_clock(settings)
    account = get_account_summary()
    positions = get_positions_summary()

    render_trading_clock_banner(clock)

    col1, col2, col3 = st.columns(3)
    col1.metric("현금", money(account["cash"]))
    col2.metric("포트폴리오 가치", money(account["portfolio_value"]))
    col3.metric("보유 포지션", account["positions_count"])

    st.divider()

    st.subheader("현재 전략")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("단기 MA", settings.ma_fast)
    c2.metric("장기 MA", settings.ma_slow)
    c3.metric("RSI 매수 상한", settings.rsi_buy_limit)
    c4.metric("최대 보유 종목", settings.max_total_positions)

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("포지션 비중", pct(settings.max_position_pct))
    c6.metric("손절", pct(settings.stop_loss_pct))
    c7.metric("익절", pct(settings.take_profit_pct))
    c8.metric("주문 금액 상한", money(settings.max_test_order_amount))

    st.write("티커:", ", ".join(settings.tickers))
    st.write(
        "AI 점수:",
        {
            "use_ai_score": getattr(settings, "use_ai_score", False),
            "ai_score_buy_threshold": getattr(settings, "ai_score_buy_threshold", None),
        },
    )

    st.divider()

    render_alpaca_order_board()

    st.divider()

    st.subheader("보유 포지션")
    if positions:
        st.dataframe(pd.DataFrame(positions), width="stretch")
    else:
        st.info("현재 보유 포지션이 없습니다.")



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
    st.header("백테스트 비교")

    history_df = load_backtest_run_summaries()

    if history_df.empty:
        st.info("아직 백테스트 이력이 없습니다.")
        return

    run_options = history_df["run_id"].tolist()

    selected_runs = st.multiselect(
        "비교할 실행 이력",
        options=run_options,
        default=run_options[: min(3, len(run_options))],
        max_selections=10,
    )

    if not selected_runs:
        st.warning("최소 1개 이상의 실행 이력을 선택하세요.")
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

    st.subheader("비교 테이블")
    st.dataframe(selected_df[available_cols], width="stretch")

    st.subheader("수익률 / 리스크 지표")

    chart_metric = st.selectbox(
        "지표",
        ["total_return", "benchmark_return", "excess_return", "max_drawdown", "win_rate"],
    )

    metric_chart_df = (
        selected_df[["run_id", chart_metric]]
        .set_index("run_id")
        .sort_index()
    )
    st.bar_chart(metric_chart_df)

    st.subheader("자산 곡선 비교")

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
        st.info("선택한 실행 이력에서 자산 곡선을 찾지 못했습니다.")
        return

    combined_equity = pd.concat(equity_series, axis=1).sort_index()
    st.line_chart(combined_equity)

    st.subheader("정규화 자산 곡선")

    normalized = combined_equity / combined_equity.iloc[0]
    st.line_chart(normalized)

    st.caption(
        "정규화 자산 곡선은 각 실행 이력의 시작값을 1.0으로 맞춘 비교 차트입니다."
    )

def render_backtest_history() -> None:
    st.header("백테스트 이력")

    history_df = load_backtest_run_summaries()

    if history_df.empty:
        st.info("아직 백테스트 이력이 없습니다.")
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

    st.subheader("실행 목록")
    st.dataframe(history_df[available_cols], width="stretch")

    selected_run = st.selectbox(
        "실행 이력 선택",
        history_df["run_id"].tolist(),
    )

    selected_row = history_df[history_df["run_id"] == selected_run].iloc[0]
    run_dir = ROOT_DIR / selected_row["run_path"]

    summary_path = run_dir / "portfolio_summary.csv"
    equity_path = run_dir / "portfolio_equity.csv"
    trades_path = run_dir / "portfolio_trades.csv"
    config_path = run_dir / "run_config.json"

    st.subheader("선택한 실행 요약")
    summary_df = pd.read_csv(summary_path)
    st.dataframe(summary_df, width="stretch")

    if equity_path.exists():
        equity_df = pd.read_csv(equity_path)

        if not equity_df.empty and {"date", "equity", "benchmark_equity"}.issubset(equity_df.columns):
            st.subheader("자산 곡선")
            chart_df = equity_df.set_index("date")[["equity", "benchmark_equity"]]
            st.line_chart(chart_df)

            st.subheader("최근 자산 데이터")
            st.dataframe(equity_df.tail(50), width="stretch")

    if trades_path.exists():
        trades_df = pd.read_csv(trades_path)

        st.subheader("거래 내역")
        if trades_df.empty:
            st.info("종료된 거래가 없습니다.")
        else:
            st.dataframe(trades_df, width="stretch")

    if config_path.exists():
        st.subheader("실행 설정")
        st.json(json.loads(config_path.read_text(encoding="utf-8")))

def render_config_history() -> None:
    st.header("설정 변경 이력")

    history_dir = ROOT_DIR / "logs/config_history"

    if not history_dir.exists():
        st.info("설정 변경 이력이 없습니다.")
        return

    files = sorted(history_dir.glob("config_change_*.json"), reverse=True)

    if not files:
        st.info("설정 변경 이력 파일이 없습니다.")
        return

    selected = st.selectbox(
        "이력 파일 선택",
        files,
        format_func=lambda path: path.name,
    )

    payload = json.loads(selected.read_text(encoding="utf-8"))

    st.subheader("변경된 항목")

    changed = payload.get("changed", {})

    if not changed:
        st.info("변경된 항목이 없습니다.")
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

        st.dataframe(pd.DataFrame(rows), width="stretch")

    with st.expander("이전 설정"):
        st.json(payload.get("old_config", {}))

    with st.expander("새 설정"):
        st.json(payload.get("new_config", {}))

def render_logs() -> None:
    st.header("로그")

    signals_df = read_csv_if_exists(LOG_PATH)
    orders_df = read_csv_if_exists(ORDER_LOG_PATH)

    st.subheader("최근 신호")
    if signals_df.empty:
        st.info("신호 로그가 없습니다.")
    else:
        st.dataframe(signals_df.tail(50), width="stretch")

    st.subheader("최근 주문")

    render_alpaca_order_board(closed_limit=40)

    st.divider()

    col1, col2 = st.columns([1, 3])
    refresh_clicked = col1.button("최근 주문 상태 갱신", type="primary")
    refresh_limit = col2.number_input(
        "최근 N개 고유 주문 갱신",
        min_value=1,
        max_value=50,
        value=10,
        step=1,
    )

    if refresh_clicked:
        refreshed_df = refresh_recent_order_statuses(limit=int(refresh_limit))

        if refreshed_df.empty:
            st.warning("갱신할 주문 ID가 없습니다.")
        else:
            st.success("주문 상태를 갱신했습니다.")
            st.dataframe(refreshed_df, width="stretch")

    orders_df = read_csv_if_exists(ORDER_LOG_PATH)

    if orders_df.empty:
        st.info("주문 로그가 없습니다.")
    else:
        st.dataframe(orders_df.tail(50), width="stretch")

def render_backtest_outputs() -> None:
    st.header("백테스트 결과")

    portfolio_summary = read_csv_if_exists(
        "logs/portfolio_backtest/portfolio_summary.csv"
    )
    selected_summary = read_csv_if_exists(
        "logs/selected_strategy/portfolio_summary.csv"
    )
    optimization = read_csv_if_exists(
        "logs/optimization/grid_search_results.csv"
    )

    st.subheader("선택 전략 요약")
    if selected_summary.empty:
        st.info("선택 전략 요약이 없습니다.")
    else:
        st.dataframe(selected_summary, width="stretch")

    st.subheader("포트폴리오 백테스트 요약")
    if portfolio_summary.empty:
        st.info("포트폴리오 백테스트 요약이 없습니다.")
    else:
        st.dataframe(portfolio_summary, width="stretch")

    st.subheader("최적화 상위 20개")
    if optimization.empty:
        st.info("최적화 결과가 없습니다.")
    else:
        st.dataframe(optimization.head(20), width="stretch")




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
                "max_daily_order_amount": settings.max_daily_order_amount,
                "buy_cooldown_days": settings.buy_cooldown_days,
                "volume_filter_enabled": settings.volume_filter_enabled,
                "volume_lookback_days": settings.volume_lookback_days,
                "min_volume_ratio": settings.min_volume_ratio,
                "volatility_filter_enabled": settings.volatility_filter_enabled,
                "volatility_lookback_days": settings.volatility_lookback_days,
                "max_volatility": settings.max_volatility,
                "rank_trend_weight": settings.rank_trend_weight,
                "rank_ai_weight": settings.rank_ai_weight,
                "rank_momentum_weight": settings.rank_momentum_weight,
                "rank_volatility_weight": settings.rank_volatility_weight,
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
        "max_daily_order_amount": settings.max_daily_order_amount,
        "buy_cooldown_days": settings.buy_cooldown_days,
        "volume_filter_enabled": settings.volume_filter_enabled,
        "volume_lookback_days": settings.volume_lookback_days,
        "min_volume_ratio": settings.min_volume_ratio,
        "volatility_filter_enabled": settings.volatility_filter_enabled,
        "volatility_lookback_days": settings.volatility_lookback_days,
        "max_volatility": settings.max_volatility,
        "rank_trend_weight": settings.rank_trend_weight,
        "rank_ai_weight": settings.rank_ai_weight,
        "rank_momentum_weight": settings.rank_momentum_weight,
        "rank_volatility_weight": settings.rank_volatility_weight,
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

    progress = st.progress(0)
    status = st.empty()

    status.write(f"{len(settings.tickers)}개 티커 데이터를 불러오는 중입니다...")
    ticker_data = load_price_data_batch(settings.tickers, period=period)
    progress.progress(0.6)

    status.write("포트폴리오 백테스트를 실행하는 중입니다...")

    run_portfolio_backtest, save_portfolio_backtest_outputs = _portfolio_backtest_api()
    result, equity_df, trades_df = run_portfolio_backtest(
        ticker_data=ticker_data,
        initial_cash=10000.0,
        max_positions=settings.max_total_positions,
        target_position_pct=settings.max_position_pct,
        transaction_cost_pct=0.001,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
        rsi_buy_limit=settings.rsi_buy_limit,
        volume_filter_enabled=settings.volume_filter_enabled,
        volume_lookback_days=settings.volume_lookback_days,
        min_volume_ratio=settings.min_volume_ratio,
        volatility_filter_enabled=settings.volatility_filter_enabled,
        volatility_lookback_days=settings.volatility_lookback_days,
        max_volatility=settings.max_volatility,
        rank_trend_weight=settings.rank_trend_weight,
        rank_ai_weight=settings.rank_ai_weight,
        rank_momentum_weight=settings.rank_momentum_weight,
        rank_volatility_weight=settings.rank_volatility_weight,
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
    status.write(f"백테스트 완료. 이력 저장: {history_dir.relative_to(ROOT_DIR)}")

    return result, equity_df, trades_df


def render_run_backtest() -> None:
    st.header("백테스트 실행")

    settings = load_settings()

    st.write("현재 저장된 전략 설정으로 포트폴리오 백테스트를 실행합니다.")
    st.code(
        f"""tickers={settings.tickers}
ma_fast={settings.ma_fast}
ma_slow={settings.ma_slow}
rsi_buy_limit={settings.rsi_buy_limit}
max_positions={settings.max_total_positions}
target_position_pct={settings.max_position_pct}
volume_filter_enabled={settings.volume_filter_enabled}
min_volume_ratio={settings.min_volume_ratio}
volatility_filter_enabled={settings.volatility_filter_enabled}
max_volatility={settings.max_volatility}
rank_trend_weight={settings.rank_trend_weight}
rank_ai_weight={settings.rank_ai_weight}
rank_momentum_weight={settings.rank_momentum_weight}
rank_volatility_weight={settings.rank_volatility_weight}
""",
        language="text",
    )

    period = st.selectbox(
        "백테스트 기간",
        ["1y", "2y", "5y"],
        index=1,
    )

    st.warning(
        "이 버튼은 주문을 실행하지 않습니다. 과거 데이터 백테스트만 실행합니다."
    )

    if st.button("포트폴리오 백테스트 실행", type="primary"):
        try:
            result, equity_df, trades_df = run_cms_backtest(period=period)

            st.success("백테스트가 완료되었습니다.")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("전략 수익률", pct(result.total_return))
            col2.metric("벤치마크 수익률", pct(result.benchmark_return))
            col3.metric("최대 낙폭", pct(result.max_drawdown))
            col4.metric("최종 자산", money(result.final_equity))

            col5, col6 = st.columns(2)
            col5.metric("거래 수", result.trades)
            col6.metric("승률", pct(result.win_rate))

            chart_df = equity_df.set_index("date")[["equity", "benchmark_equity"]]
            st.subheader("자산 곡선")
            st.line_chart(chart_df)

            st.subheader("거래 내역")
            if trades_df.empty:
                st.info("종료된 거래가 없습니다.")
            else:
                st.dataframe(trades_df, width="stretch")

            st.subheader("자산 테이블")
            st.dataframe(equity_df.tail(50), width="stretch")

        except Exception as exc:
            st.error(f"백테스트 실패: {exc}")



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


def render_buy_candidate_tabs(buy_df: pd.DataFrame, clock: MarketClock | None = None) -> None:
    if buy_df.empty:
        st.info("매수 후보가 없습니다.")
        return

    if clock is None:
        clock = load_trading_clock()

    executable_df, blocked_df, error_df = classify_buy_candidates(buy_df, clock)

    tabs = st.tabs(
        [
            f"실행 가능 ({len(executable_df)})",
            f"차단/대기 ({len(blocked_df)})",
            f"오류 ({len(error_df)})",
            f"전체 ({len(buy_df)})",
        ]
    )

    def display(df: pd.DataFrame) -> None:
        if df.empty:
            st.info("표시할 항목이 없습니다.")
            return
        st.dataframe(sort_buy_candidates(df), width="stretch")

    with tabs[0]:
        display(executable_df)
    with tabs[1]:
        display(blocked_df)
    with tabs[2]:
        display(error_df)
    with tabs[3]:
        display(buy_df)


def render_cache_quality(quality_df: pd.DataFrame, errors_df: pd.DataFrame) -> None:
    st.subheader("데이터 품질")

    if quality_df.empty:
        st.info("데이터 품질 리포트가 없습니다. 후보 캐시를 다시 생성하세요.")
        return

    status_counts = quality_df["data_status"].value_counts(dropna=False).to_dict()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("정상", int(status_counts.get("OK", 0)))
    c2.metric("주의", int(status_counts.get("WARN", 0)))
    c3.metric("오류", int(status_counts.get("ERROR", 0)))
    c4.metric("전체", len(quality_df))

    tabs = st.tabs(
        [
            f"주의/오류 ({len(errors_df)})",
            f"전체 품질 ({len(quality_df)})",
        ]
    )

    with tabs[0]:
        if errors_df.empty:
            st.success("데이터 품질 경고나 오류가 없습니다.")
        else:
            st.dataframe(errors_df, width="stretch")

    with tabs[1]:
        display_df = quality_df.copy()
        if "data_status" in display_df.columns:
            status_order = {"ERROR": 0, "WARN": 1, "OK": 2}
            display_df["_status_order"] = (
                display_df["data_status"].map(status_order).fillna(9)
            )
            display_df = display_df.sort_values(["_status_order", "ticker"])
            display_df = display_df.drop(columns=["_status_order"])

        st.dataframe(display_df, width="stretch")


def render_dry_run() -> None:
    st.header("Dry-run 점검")

    st.warning(
        "이 페이지는 주문을 실행하지 않습니다. 최신 후보 캐시 기준의 예상 매수/청산 판단만 보여줍니다."
    )

    try:
        meta, exit_df, buy_df, quality_df, errors_df = load_latest_candidate_cache_full()
    except Exception as exc:
        st.error(f"후보 캐시를 찾을 수 없습니다: {exc}")
        st.info("`python -m src.generate_candidate_cache`를 실행하거나 아래 버튼으로 캐시를 갱신하세요.")
        if st.button("후보 캐시 지금 갱신"):
            with st.spinner("후보 캐시를 갱신하는 중입니다..."):
                proc = subprocess.run(
                    [str(ROOT_DIR / ".venv/bin/python"), "-m", "src.generate_candidate_cache"],
                    cwd=str(ROOT_DIR),
                    capture_output=True,
                    text=True,
                    timeout=1800,
                )

            if proc.returncode == 0:
                st.success("후보 캐시를 갱신했습니다. 페이지를 새로고침하세요.")
                st.code(proc.stdout[-4000:], language="text")
            else:
                st.error("후보 캐시 갱신에 실패했습니다.")
                st.code((proc.stderr or proc.stdout)[-8000:], language="text")
        return

    generated_at = str(meta.get("generated_at"))
    cache_age_minutes = _cache_age_minutes(generated_at)

    st.subheader("실행 안전 점검")
    live_clock = load_trading_clock()
    render_trading_clock_banner(live_clock)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("캐시 기준 주문 가능", str(meta.get("orders_allowed", meta.get("market_is_open"))))
    c2.metric("현금", money(float(meta.get("cash", 0.0))))
    c3.metric("포지션", meta.get("positions_count"))
    c4.metric("실행당 최대 주문", meta.get("max_orders_per_run"))

    c5, c6, c7 = st.columns(3)
    c5.metric("오늘 매수 금액", money(float(meta.get("today_buy_notional") or 0.0)))
    c6.metric("일일 주문 상한", money(float(meta.get("max_daily_order_amount") or 0.0)))
    c7.metric("재매수 cooldown", f"{meta.get('buy_cooldown_days') or 0}일")

    st.caption(
        f"캐시 생성: {generated_at} | "
        f"경과: {cache_age_minutes:.1f}분 | "
        f"감시 종목: {meta.get('watchlist_size')} | "
        f"시장 시간: {meta.get('market_timestamp')}"
    )

    if st.button("후보 캐시 지금 갱신"):
        with st.spinner("후보 캐시를 갱신하는 중입니다..."):
            proc = subprocess.run(
                [str(ROOT_DIR / ".venv/bin/python"), "-m", "src.generate_candidate_cache"],
                cwd=str(ROOT_DIR),
                capture_output=True,
                text=True,
                timeout=1800,
            )

        if proc.returncode == 0:
            st.success("후보 캐시를 갱신했습니다. 페이지를 새로고침하세요.")
            st.code(proc.stdout[-4000:], language="text")
        else:
            st.error("후보 캐시 갱신에 실패했습니다.")
            st.code((proc.stderr or proc.stdout)[-8000:], language="text")

    st.divider()

    st.subheader("보유 포지션 청산 점검")

    if not exit_df.empty:
        st.dataframe(exit_df, width="stretch")
    else:
        st.info("현재 보유 포지션이 없습니다.")

    st.divider()

    st.subheader("매수 후보 점검")

    render_buy_candidate_tabs(buy_df, live_clock)

    st.caption(
        "SESSION_CLOSED는 execute 시 주문이 차단된다는 뜻입니다. "
        "WOULD_SUBMIT_IF_EXECUTED는 Alpaca 허용 세션(정규장·프리·애프터·오버나잇)에서 "
        "execute 시 주문 후보라는 뜻입니다. 장외·오버나잇은 지정가로 제출됩니다."
    )

    st.divider()

    if st.button("Dry-run 스냅샷 저장"):
        output_path = save_dry_run_snapshot(exit_df, buy_df)
        st.success(f"Dry-run 스냅샷을 저장했습니다: {output_path.relative_to(ROOT_DIR)}")

    st.divider()
    render_cache_quality(quality_df, errors_df)



def build_cms_dry_run_rows():
    meta, exit_df, buy_df, _, _ = load_latest_candidate_cache_full()
    settings = load_settings()
    account = get_account_summary()
    clock = load_trading_clock(settings)
    return account, clock, settings, exit_df, buy_df



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
        "orders_allowed": clock.orders_allowed,
        "trading_session": clock.session.value,
        "broker_provider": clock.broker_provider,
        "extended_hours_enabled": clock.extended_hours_enabled,
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
            "max_daily_order_amount": settings.max_daily_order_amount,
            "buy_cooldown_days": settings.buy_cooldown_days,
        },
    }

    (output_dir / "run_context.json").write_text(
        json.dumps(context, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return output_dir

def execute_cms_paper_actions(
    exit_df: pd.DataFrame,
    buy_df: pd.DataFrame,
    settings,
    clock: MarketClock,
) -> pd.DataFrame:
    if not clock.orders_allowed:
        raise RuntimeError(
            f"현재 거래 세션({clock.session.value})에서는 주문이 허용되지 않습니다."
        )

    broker = get_broker_adapter(settings.broker_provider)
    extended_slippage = float(
        getattr(settings, "extended_hours_limit_slippage_pct", 0.005)
    )
    positions_by_symbol = {
        str(item["symbol"]).upper(): item for item in get_positions_summary()
    }
    rows = []

    if not exit_df.empty:
        for _, row in exit_df.iterrows():
            if not bool(row.get("should_exit", False)):
                continue

            ticker = str(row["ticker"]).upper()
            reason = str(row.get("exit_reason", ""))
            position = positions_by_symbol.get(ticker)
            if position is None:
                rows.append(
                    {
                        "action": "CLOSE",
                        "ticker": ticker,
                        "status": "SKIPPED",
                        "reason": reason,
                        "error": "position not found",
                    }
                )
                continue

            try:
                submission = broker.submit_sell_qty(
                    ticker,
                    float(position["qty"]),
                    limit_price=float(position["current_price"]),
                    market_clock=clock,
                    slippage_pct=extended_slippage,
                    client_order_id=f"cms_exit_{datetime.now().strftime('%Y%m%dT%H%M%S')}_{ticker}",
                )

                log_order(
                    ticker=ticker,
                    notional=0.0,
                    order_id=submission.order_id,
                    status=submission.status,
                    side=submission.side,
                    order_type=submission.order_type,
                    reason=reason,
                )

                checked_order = wait_for_order_status(submission.order_id)

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
                        "session": clock.session.value,
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

    orders_submitted = 0

    if not buy_df.empty:
        for _, row in buy_df.iterrows():
            if orders_submitted >= settings.max_orders_per_run:
                break

            if not _is_executable_buy_row(row, clock):
                continue

            ticker = str(row["ticker"]).upper()
            order_amount = float(row["order_amount"])
            reason = str(row.get("reason", ""))
            limit_price = float(row.get("close") or 0)

            if order_amount <= 0 or limit_price <= 0:
                continue

            try:
                submission = broker.submit_buy_notional(
                    ticker=ticker,
                    notional=order_amount,
                    limit_price=limit_price,
                    market_clock=clock,
                    slippage_pct=extended_slippage,
                    client_order_id=f"cms_buy_{datetime.now().strftime('%Y%m%dT%H%M%S')}_{ticker}",
                )
                orders_submitted += 1

                log_order(
                    ticker=ticker,
                    notional=order_amount,
                    order_id=submission.order_id,
                    status=submission.status,
                    side=submission.side,
                    order_type=submission.order_type,
                    reason=reason,
                )

                checked_order = wait_for_order_status(submission.order_id)

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

                row_payload = {
                    "action": "BUY",
                    "ticker": ticker,
                    "notional": order_amount,
                    "order_id": checked_order["id"],
                    "status": checked_order["status"],
                    "session": clock.session.value,
                    "filled_qty": checked_order["filled_qty"],
                    "filled_avg_price": checked_order["filled_avg_price"],
                    "reason": reason,
                }
                if not _order_is_filled(checked_order["status"]):
                    row_payload["note"] = "limit order pending (extended/overnight)"
                rows.append(row_payload)

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
    st.header("Paper 주문 실행")

    st.warning(
        "이 페이지는 캐시된 후보 결과를 사용합니다. "
        "100개 티커 계산은 10분마다 백그라운드 timer가 수행합니다."
    )

    lock_enabled = is_cms_execution_enabled()
    required_phrase = get_required_phrase()
    settings = load_settings()
    clock = load_trading_clock(settings)
    account = get_account_summary()

    st.subheader("안전 점검")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("실행 잠금", "ENABLED" if lock_enabled else "LOCKED")
    c2.metric("주문 가능", str(clock.orders_allowed))
    c3.metric("Alpaca Paper", str(ALPACA_PAPER))
    c4.metric("주문 금액 상한", money(settings.max_test_order_amount))

    render_trading_clock_banner(clock)

    st.divider()

    render_alpaca_order_board(closed_limit=80)

    st.divider()

    st.subheader("캐시된 후보")

    try:
        meta, exit_df, buy_df, quality_df, errors_df = load_latest_candidate_cache_full()
    except Exception as exc:
        st.error(f"후보 캐시를 찾을 수 없습니다: {exc}")
        st.info("`python -m src.generate_candidate_cache`를 실행하거나 후보 캐시 timer를 활성화하세요.")
        return

    generated_at = str(meta.get("generated_at"))
    cache_age_minutes = _cache_age_minutes(generated_at)

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("캐시 생성 시각", generated_at)
    c6.metric("캐시 경과", f"{cache_age_minutes:.1f}분")
    c7.metric("감시 종목 수", meta.get("watchlist_size"))
    c8.metric("캐시 기준 주문 가능", str(meta.get("orders_allowed", meta.get("market_is_open"))))

    c9, c10, c11 = st.columns(3)
    c9.metric("오늘 매수 금액", money(float(meta.get("today_buy_notional") or 0.0)))
    c10.metric("일일 주문 상한", money(float(meta.get("max_daily_order_amount") or 0.0)))
    c11.metric("재매수 cooldown", f"{meta.get('buy_cooldown_days') or 0}일")

    c12, c13, c14, c15 = st.columns(4)
    c12.metric("가격 데이터 정상", meta.get("price_data_success_count", 0))
    c13.metric("가격 데이터 주의", meta.get("price_data_warning_count", 0))
    c14.metric("가격 데이터 오류", meta.get("price_data_error_count", 0))
    c15.metric("캐시 생성 시간", f"{meta.get('cache_duration_seconds', 0)}초")

    cache_fresh = cache_age_minutes <= 15

    if cache_fresh:
        st.success("후보 캐시가 최신입니다.")
    else:
        st.error("후보 캐시가 오래되었습니다. 캐시를 갱신하기 전까지 실행이 차단됩니다.")

    if st.button("후보 캐시 지금 갱신"):
        with st.spinner("후보 캐시를 갱신하는 중입니다..."):
            proc = subprocess.run(
                [str(ROOT_DIR / ".venv/bin/python"), "-m", "src.generate_candidate_cache"],
                cwd=str(ROOT_DIR),
                capture_output=True,
                text=True,
                timeout=1800,
            )

        if proc.returncode == 0:
            st.success("후보 캐시를 갱신했습니다. 페이지를 새로고침하세요.")
            st.code(proc.stdout[-4000:], language="text")
        else:
            st.error("후보 캐시 갱신에 실패했습니다.")
            st.code((proc.stderr or proc.stdout)[-8000:], language="text")

    st.divider()

    st.subheader("청산 후보")
    if exit_df.empty:
        st.info("점검할 보유 포지션이 없습니다.")
    else:
        st.dataframe(exit_df, width="stretch")

    st.subheader("매수 후보")

    render_buy_candidate_tabs(buy_df, clock)

    st.divider()
    render_cache_quality(quality_df, errors_df)

    st.divider()

    st.subheader("최종 확인")

    allowed = lock_enabled and clock.orders_allowed and ALPACA_PAPER and cache_fresh

    if not lock_enabled:
        st.error("CMS 실행 잠금이 해제되어 있지 않습니다.")

    if not clock.orders_allowed:
        st.error(
            f"현재 거래 세션({clock.session.value})에서는 주문이 허용되지 않습니다. "
            "Alpaca extended/overnight 설정을 확인하세요."
        )

    if not ALPACA_PAPER:
        st.error("ALPACA_PAPER가 False입니다. CMS 실행이 차단됩니다.")

    if not cache_fresh:
        st.error("후보 캐시가 오래되었습니다. 실행 전에 캐시를 갱신하세요.")

    st.write("실행 가능 상태:", "YES" if allowed else "NO")

    confirmation = st.text_input(
        f"실행 버튼을 활성화하려면 `{required_phrase}`를 입력하세요",
        type="password",
    )

    final_allowed = allowed and confirmation == required_phrase

    if not final_allowed:
        st.info("조건이 모두 충족되고 확인 문구가 일치해야 실행 버튼이 활성화됩니다.")

    execute_clicked = st.button(
        "Paper 주문 실행",
        type="primary",
        disabled=not final_allowed,
    )

    if execute_clicked:
        result_df = execute_cms_paper_actions(exit_df, buy_df, settings, clock)

        history_dir = save_execution_run_history(
            result_df=result_df,
            exit_df=exit_df,
            buy_df=buy_df,
            account=account,
            clock=clock,
            settings=settings,
        )

        if result_df.empty:
            st.warning(f"실행된 paper 액션이 없습니다. 이력: {history_dir.relative_to(ROOT_DIR)}")
        else:
            st.success(
                f"Paper 액션을 제출하고 상태를 확인했습니다. "
                f"이력: {history_dir.relative_to(ROOT_DIR)}"
            )
            st.dataframe(result_df, width="stretch")

            try:
                reconcile_alerts = reconcile_cms_execute_with_alpaca(
                    result_df,
                    get_open_orders(),
                    get_recent_closed_orders(limit=100),
                )
                for alert in reconcile_alerts:
                    st.warning(alert["message"])
            except ConnectionError as exc:
                st.info(f"Alpaca 대조 알림 생략 (연결 불가): {exc}")

def render_execution_runs() -> None:
    st.header("실행 이력")

    runs_dir = ROOT_DIR / "logs/execution_runs"

    if not runs_dir.exists():
        st.info("아직 실행 이력이 없습니다.")
        return

    run_dirs = sorted(
        [path for path in runs_dir.iterdir() if path.is_dir()],
        reverse=True,
    )

    if not run_dirs:
        st.info("아직 실행 이력이 없습니다.")
        return

    selected_dir = st.selectbox(
        "실행 이력 선택",
        run_dirs,
        format_func=lambda path: path.name,
    )

    context_path = selected_dir / "run_context.json"
    account_path = selected_dir / "account_before.json"
    result_path = selected_dir / "execution_result.csv"
    exit_path = selected_dir / "exit_candidates.csv"
    buy_path = selected_dir / "buy_candidates.csv"

    st.subheader("실행 컨텍스트")
    if context_path.exists():
        st.json(json.loads(context_path.read_text(encoding="utf-8")))
    else:
        st.info("run_context.json 파일이 없습니다.")

    st.subheader("실행 전 계좌")
    if account_path.exists():
        st.json(json.loads(account_path.read_text(encoding="utf-8")))
    else:
        st.info("account_before.json 파일이 없습니다.")

    st.subheader("실행 결과")
    if result_path.exists():
        result_df = pd.read_csv(result_path)
        if result_df.empty:
            st.info("실행된 액션이 없습니다.")
        else:
            st.dataframe(result_df, width="stretch")
    else:
        st.info("execution_result.csv 파일이 없습니다.")

    st.subheader("청산 후보")
    if exit_path.exists():
        exit_df = pd.read_csv(exit_path)
        st.dataframe(exit_df, width="stretch")
    else:
        st.info("exit_candidates.csv 파일이 없습니다.")

    st.subheader("매수 후보")
    if buy_path.exists():
        buy_df = pd.read_csv(buy_path)
        st.dataframe(buy_df, width="stretch")
    else:
        st.info("buy_candidates.csv 파일이 없습니다.")

def render_execution_lock() -> None:
    st.header("실행 잠금")

    lock = load_execution_lock()
    required_phrase = get_required_phrase()

    enabled = bool(lock.get("cms_execution_enabled", False))

    if enabled:
        st.success("현재 CMS paper 실행이 활성화되어 있습니다.")
    else:
        st.warning("현재 CMS paper 실행이 잠겨 있습니다.")

    st.write("이 잠금은 나중에 CMS에서 paper 주문/청산 버튼을 만들 때 사용할 안전장치입니다.")
    st.write("현재 단계에서는 잠금 상태만 관리하고, 실제 주문 버튼은 아직 추가하지 않습니다.")

    c1, c2 = st.columns(2)
    c1.metric("CMS 실행 활성화", str(enabled))
    c2.metric("마지막 수정", str(lock.get("last_updated")))

    st.divider()

    st.subheader("CMS 실행 잠금 해제")

    st.info(
        f"잠금을 해제하려면 아래 문구를 정확히 입력하세요: `{required_phrase}`"
    )

    phrase = st.text_input("확인 문구", type="password")

    if st.button("CMS Paper 실행 활성화"):
        if phrase == required_phrase:
            save_execution_lock(True)
            st.success("CMS paper 실행을 활성화했습니다. 페이지를 새로고침해서 확인하세요.")
        else:
            st.error("확인 문구가 일치하지 않습니다.")

    st.divider()

    st.subheader("CMS 실행 잠금")

    if st.button("CMS Paper 실행 비활성화"):
        save_execution_lock(False)
        st.success("CMS paper 실행을 비활성화했습니다. 페이지를 새로고침해서 확인하세요.")


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
    st.header("스케줄러")

    st.warning(
        "자동 execute는 실제 Alpaca paper 주문/청산을 실행합니다. "
        "처음에는 dry-run으로 며칠 확인한 뒤 execute로 바꾸는 것을 추천합니다."
    )

    config = load_scheduler_config()

    st.subheader("스케줄러 설정")

    enabled = st.checkbox("설정에서 활성화", value=bool(config.get("enabled", False)))

    mode = st.selectbox(
        "실행 모드",
        ["dry-run", "execute"],
        index=0 if config.get("mode", "dry-run") == "dry-run" else 1,
    )

    timezone = st.text_input(
        "타임존",
        value=str(config.get("timezone", "America/New_York")),
    )

    current_times = config.get("on_calendar_times") or [
        config.get("systemd_on_calendar", "Mon..Fri 10:00:00")
    ]

    default_time_1 = current_times[0] if len(current_times) > 0 else "Mon..Fri 10:00:00"
    default_time_2 = current_times[1] if len(current_times) > 1 else "Mon..Fri 15:30:00"

    on_calendar_1 = st.text_input(
        "실행 시간 1",
        value=default_time_1,
        help="예: Mon..Fri 10:00:00, 뉴욕 시장 시간 기준 가정",
    )

    on_calendar_2 = st.text_input(
        "실행 시간 2",
        value=default_time_2,
        help="예: Mon..Fri 15:30:00",
    )

    schedule_note = st.text_area(
        "스케줄 메모",
        value=str(config.get("schedule_note", "")),
    )

    st.info(
        "주의: systemd timer는 서버/PC의 로컬 타임존 기준으로 실행됩니다. "
        "미국 동부 시간 기준으로 정확히 돌리고 싶으면 서버 타임존을 확인하거나 "
        "실행 시 봇의 trading_session guard에 의존하세요. "
        "extended_hours_enabled=true이면 프리·애프터·오버나잇에도 지정가 주문이 가능합니다."
    )

    if st.button("스케줄러 설정 저장"):
        times = [
            item.strip()
            for item in [on_calendar_1, on_calendar_2]
            if item.strip()
        ]

        new_config = {
            "enabled": bool(enabled),
            "mode": mode,
            "timezone": timezone,
            "schedule_note": schedule_note,
            "on_calendar_times": times,
            "service_name": "trading-bot.service",
            "timer_name": "trading-bot.timer",
        }
        save_scheduler_config(new_config)
        st.success("스케줄러 설정을 저장했습니다.")

    st.divider()

    st.subheader("systemd Timer 적용")

    st.write(
        "아래 버튼은 config/scheduler_config.json 기준으로 user-level systemd timer 파일을 생성/갱신합니다."
    )

    col_apply, col_enable, col_disable = st.columns(3)

    if col_apply.button("Timer 파일 적용", type="primary"):
        proc = subprocess.run(
            [str(ROOT_DIR / "scripts/install_user_timer.sh")],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode == 0:
            st.success("Timer 파일을 적용했습니다.")
            st.code(proc.stdout, language="text")
        else:
            st.error("Timer 파일 적용에 실패했습니다.")
            st.code(proc.stderr, language="text")

    if col_enable.button("Timer 활성화"):
        proc = subprocess.run(
            ["systemctl", "--user", "enable", "--now", "trading-bot.timer"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode == 0:
            st.success("Timer를 활성화했습니다.")
            st.code(proc.stdout or "enabled", language="text")
        else:
            st.error("Timer 활성화에 실패했습니다.")
            st.code(proc.stderr, language="text")

    if col_disable.button("Timer 비활성화"):
        proc = subprocess.run(
            ["systemctl", "--user", "disable", "--now", "trading-bot.timer"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode == 0:
            st.success("Timer를 비활성화했습니다.")
            st.code(proc.stdout or "disabled", language="text")
        else:
            st.error("Timer 비활성화에 실패했습니다.")
            st.code(proc.stderr, language="text")

    st.divider()

    st.subheader("Timer 상태")

    if st.button("Timer 상태 새로고침"):
        proc = subprocess.run(
            ["systemctl", "--user", "list-timers", "trading-bot.timer"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=60,
        )
        st.code((proc.stdout or proc.stderr)[-8000:], language="text")

        proc_status = subprocess.run(
            ["systemctl", "--user", "status", "trading-bot.timer"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=60,
        )
        st.code((proc_status.stdout or proc_status.stderr)[-8000:], language="text")

    st.divider()

    st.subheader("수동 봇 실행")

    col1, col2 = st.columns(2)

    if col1.button("Dry-run 지금 실행"):
        proc = subprocess.run(
            [str(ROOT_DIR / "scripts/run_bot_once.sh"), "dry-run"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            st.success("Dry-run이 완료되었습니다. 아래 최근 로그를 확인하세요.")
        else:
            st.error("Dry-run에 실패했습니다.")
            st.code(proc.stderr)

    if col2.button("Execute 지금 실행"):
        st.error(
            "스케줄러 화면에서 execute 실행은 의도적으로 비활성화되어 있습니다. "
            "Paper 주문 실행 화면에서 잠금과 확인 문구를 거쳐 실행하세요."
        )

    st.divider()

    st.subheader("최근 봇 실행 로그")

    logs = get_recent_bot_run_logs(limit=10)

    if not logs:
        st.info("봇 실행 로그가 없습니다.")
        return

    selected_log = st.selectbox(
        "로그 선택",
        logs,
        format_func=lambda path: path.name,
    )

    st.code(selected_log.read_text(encoding="utf-8")[-8000:], language="text")

def render_telegram() -> None:
    st.header("Telegram 알림")

    configured = telegram_is_configured()
    config = load_notification_config()

    if configured:
        st.success("Telegram 설정이 완료되어 있습니다.")
    else:
        st.warning(
            "Telegram 설정이 완료되지 않았습니다. .env의 TELEGRAM_BOT_TOKEN, "
            "TELEGRAM_CHAT_ID, TELEGRAM_ENABLED와 아래 알림 설정을 확인하세요."
        )

    st.write("Telegram 알림은 실행 요약, 주문 체결 확인, 청산, 주요 에러에 사용됩니다.")

    st.subheader("알림 설정")

    telegram_enabled_value = st.checkbox(
        "Telegram 활성화",
        value=bool(config.get("telegram_enabled", True)),
    )

    notify_run_summary_value = st.checkbox(
        "실행 요약 알림",
        value=bool(config.get("notify_run_summary", True)),
    )

    notify_orders_value = st.checkbox(
        "주문 알림",
        value=bool(config.get("notify_orders", True)),
    )

    notify_errors_value = st.checkbox(
        "에러 알림",
        value=bool(config.get("notify_errors", True)),
    )

    if st.button("알림 설정 저장"):
        save_notification_config(
            {
                "telegram_enabled": telegram_enabled_value,
                "notify_run_summary": notify_run_summary_value,
                "notify_orders": notify_orders_value,
                "notify_errors": notify_errors_value,
            }
        )
        st.success("알림 설정을 저장했습니다.")

    st.divider()

    st.subheader("테스트 메시지")

    test_message = st.text_area(
        "테스트 메시지",
        value="CMS에서 보내는 트레이딩 봇 Telegram 테스트입니다.",
    )

    if st.button("Telegram 테스트 메시지 보내기"):
        try:
            ok = notify_info(
                title="CMS Telegram 테스트",
                body=test_message,
            )

            if ok:
                st.success("Telegram 메시지를 보냈습니다.")
            else:
                st.error("Telegram 메시지를 보내지 못했습니다. 설정을 확인하세요.")

        except Exception as exc:
            st.error(f"Telegram 전송 실패: {exc}")



def load_json_summary(relative_path: str) -> dict | None:
    path = ROOT_DIR / relative_path
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def render_ops_dashboard() -> None:
    """Ops reports, universe profiles, and paper gates (Phase 26–28)."""
    from src.universe_loader import (
        load_master_tickers,
        load_smoke_tickers,
        resolve_scan_tickers,
    )
    from src.instrument_meta import get_instrument, load_instrument_registry
    from src.margin_leverage_paper_gate import (
        evaluate_margin_leverage_buy_block,
        evaluate_margin_leverage_paper_gate,
        load_stress_summary,
    )

    st.title("Ops / 게이트 대시보드")
    st.caption("로컬 로그·설정 기준 — paper 계좌와 동일하지 않을 수 있음")

    settings = load_settings()
    active_profile = os.environ.get("UNIVERSE_PROFILE", "paper").strip().lower()

    st.subheader("유니버스 프로필")
    c1, c2, c3 = st.columns(3)
    paper_count = len(resolve_scan_tickers(list(settings.tickers), profile="paper"))
    try:
        smoke_count = len(load_smoke_tickers())
    except (FileNotFoundError, ValueError):
        smoke_count = 0
    try:
        research_count = len(load_master_tickers())
    except FileNotFoundError:
        research_count = 0
    c1.metric("paper (config)", paper_count)
    c2.metric("smoke (CI)", smoke_count)
    c3.metric("research (master)", research_count)
    st.info(
        f"현재 프로세스 `UNIVERSE_PROFILE={active_profile}`. "
        "Streamlit은 기본 paper; 터미널에서 `UNIVERSE_PROFILE=research` 로 봇 실행."
    )
    with st.expander("smoke 티커 목록"):
        try:
            st.write(", ".join(load_smoke_tickers()))
        except (FileNotFoundError, ValueError) as exc:
            st.warning(str(exc))

    st.divider()
    st.subheader("마진 레버리지 paper")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("leverage_factor", float(getattr(settings, "leverage_factor", 1.0)))
    m2.metric("paper_enabled", bool(getattr(settings, "margin_leverage_paper_enabled", False)))
    m3.metric("stress_gate", bool(getattr(settings, "margin_leverage_stress_gate_required", True)))
    block, block_reason = evaluate_margin_leverage_buy_block(
        float(getattr(settings, "leverage_factor", 1.0)),
        margin_leverage_paper_enabled=bool(
            getattr(settings, "margin_leverage_paper_enabled", False)
        ),
        margin_leverage_stress_gate_required=bool(
            getattr(settings, "margin_leverage_stress_gate_required", True)
        ),
    )
    m4.metric("신규 매수 차단", "예" if block else "아니오")

    if block_reason:
        st.warning(block_reason)

    margin_gate = load_json_summary("logs/margin_leverage_paper/go_no_go_checklist.json")
    if margin_gate:
        st.json(margin_gate)
    else:
        st.caption("게이트 산출물 없음 — 아래 버튼으로 생성")

    col_a, col_b = st.columns(2)
    if col_a.button("Stress 리포트 갱신", key="ops_stress"):
        with st.spinner("leverage stress..."):
            code, out, err = run_project_command(
                [
                    str(ROOT_DIR / ".venv/bin/python"),
                    "-m",
                    "src.leverage_stress_report",
                    "--leverage",
                    "2.0",
                ],
                timeout=120,
            )
        if code == 0:
            st.success("완료")
        else:
            st.error("실패")
        if out:
            st.code(out[-4000:])
        if err:
            st.code(err[-2000:])

    if col_b.button("마진 paper 게이트 실행", key="ops_margin_gate"):
        with st.spinner("margin leverage gate..."):
            code, out, err = run_project_command(
                [
                    str(ROOT_DIR / ".venv/bin/python"),
                    "-m",
                    "src.margin_leverage_paper_gate",
                    "--refresh-stress",
                ],
                timeout=120,
            )
        if code == 0:
            st.success("완료 — 새로고침하세요")
        else:
            st.error("실패")
        if out:
            st.code(out[-4000:])

    stress_path = ROOT_DIR / "logs/leverage_stress/latest_summary.json"
    if stress_path.is_file():
        try:
            stress = load_stress_summary(stress_path)
            preview = evaluate_margin_leverage_paper_gate(
                stress,
                configured_leverage_factor=float(
                    getattr(settings, "leverage_factor", 1.25)
                ),
            )
            st.caption("실시간 게이트 평가 (저장 파일과 동일 로직)")
            st.json(preview)
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("레버리지 ETF 메타")
    st.write(
        {
            "allow_leveraged_etfs": getattr(settings, "allow_leveraged_etfs", False),
            "max_leveraged_etf_positions": getattr(
                settings, "max_leveraged_etf_positions", 1
            ),
            "max_effective_leverage_exposure_pct": getattr(
                settings, "max_effective_leverage_exposure_pct", 1.25
            ),
        }
    )
    registry = load_instrument_registry()
    leveraged = [t for t, m in registry.items() if m.is_leveraged_etf]
    st.caption(f"registry leveraged ETF: {len(leveraged)}종")
    sample = st.text_input("티커 조회", value="TQQQ")
    if sample:
        meta = get_instrument(sample.strip().upper())
        st.json(
            {
                "kind": meta.instrument_kind,
                "multiple": meta.multiple,
                "underlying": meta.underlying,
                "direction": meta.direction,
            }
        )

    st.divider()
    st.subheader("Ops latest_summary 뷰어")

    if st.button("Crowding live 리포트 생성", key="ops_crowding_live"):
        with st.spinner("crowding live impact..."):
            code, out, err = run_project_command(
                [
                    str(ROOT_DIR / ".venv/bin/python"),
                    "-m",
                    "src.crowding_live_impact_report",
                    "--lookback-days",
                    "7",
                ],
                timeout=60,
            )
        if code == 0:
            st.success("logs/crowding_live/latest_summary.json 갱신됨")
        else:
            st.error("실패")
        if out:
            st.code(out[-3000:])
        if err:
            st.code(err[-1500:])

    ops_report_catalog = [
        ("모니터링", [
            ("일별 audit", "logs/audit_daily/latest_summary.json"),
            ("슬리피지", "logs/slippage_reports/latest_summary.json"),
            ("LLM cache", "logs/llm_cache/latest_summary.json"),
            ("실행 정합", "logs/execution_alignment/latest_summary.json"),
        ]),
        ("백테스트·가드", [
            ("벤치마크 gap", "logs/benchmark_gap/latest_summary.json"),
            ("guard impact (백테스트)", "logs/guard_impact/latest_summary.json"),
            ("crowding live (audit 대조)", "logs/crowding_live/latest_summary.json"),
            ("crowding paper GO/NO-GO", "logs/crowding_paper/go_no_go_checklist.json"),
            ("guard/leverage stress", "logs/leverage_stress/latest_summary.json"),
        ]),
        ("모델·승격", [
            ("fold variance", "logs/fold_variance/latest_summary.json"),
            ("promotion summary", "logs/promotion_summary/latest_summary.json"),
            ("model quality", "logs/model_quality/latest_summary.json"),
        ]),
    ]
    for section, entries in ops_report_catalog:
        st.markdown(f"**{section}**")
        for label, rel in entries:
            data = load_json_summary(rel)
            with st.expander(f"{label} — `{rel}`"):
                if data is None:
                    st.caption("산출물 없음 — runbook Quick commands 또는 위 버튼으로 생성")
                else:
                    if label.startswith("벤치마크 gap"):
                        gap = data.get("gap_pct")
                        beats = data.get("beats_benchmark")
                        if gap is not None:
                            st.metric("vs benchmark (pp)", f"{gap:+.2f}", delta="OK" if beats else "under")
                    st.json(data)
                    if "alignment" in data and isinstance(data["alignment"], dict):
                        for note in data["alignment"].get("notes") or []:
                            st.info(note)
                    for rec in data.get("recommendations") or []:
                        st.warning(rec)


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

    ticker_data = load_price_data_batch(settings.tickers, period="2y")

    run_portfolio_backtest, _ = _portfolio_backtest_api()
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
        volume_filter_enabled=settings.volume_filter_enabled,
        volume_lookback_days=settings.volume_lookback_days,
        min_volume_ratio=settings.min_volume_ratio,
        volatility_filter_enabled=settings.volatility_filter_enabled,
        volatility_lookback_days=settings.volatility_lookback_days,
        max_volatility=settings.max_volatility,
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
        volume_filter_enabled=settings.volume_filter_enabled,
        volume_lookback_days=settings.volume_lookback_days,
        min_volume_ratio=settings.min_volume_ratio,
        volatility_filter_enabled=settings.volatility_filter_enabled,
        volatility_lookback_days=settings.volatility_lookback_days,
        max_volatility=settings.max_volatility,
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
    st.header("AI 모델")

    settings = load_settings()

    model_path = ROOT_DIR / "models/ai_score_model.joblib"
    metrics_path = ROOT_DIR / "logs/ml/ai_model_metrics.csv"
    threshold_path = ROOT_DIR / "logs/ai_threshold/threshold_results.csv"

    st.subheader("현재 AI 설정")

    c1, c2, c3 = st.columns(3)
    c1.metric("AI 점수 사용", str(getattr(settings, "use_ai_score", False)))
    c2.metric("AI 기준값", getattr(settings, "ai_score_buy_threshold", None))
    c3.metric("모델 파일 존재", str(model_path.exists()))

    if model_path.exists():
        st.caption(f"모델 경로: {model_path.relative_to(ROOT_DIR)}")
    else:
        st.warning("AI 모델 파일이 없습니다. 먼저 `python -m src.train_ai_model`을 실행하세요.")

    st.divider()

    st.subheader("모델 학습 지표")

    if not metrics_path.exists():
        st.info("AI 모델 학습 지표가 없습니다. `python -m src.train_ai_model`을 실행하세요.")
    else:
        metrics_df = pd.read_csv(metrics_path)
        st.dataframe(metrics_df, width="stretch")

        metric_cols = [
            col for col in ["accuracy", "precision", "recall", "roc_auc"]
            if col in metrics_df.columns
        ]

        if metric_cols and "fold" in metrics_df.columns:
            chart_df = metrics_df.set_index("fold")[metric_cols]
            st.line_chart(chart_df)

    st.divider()

    st.subheader("AI 기준값 최적화")

    if not threshold_path.exists():
        st.info("기준값 최적화 결과가 없습니다. `python -m src.optimize_ai_threshold`를 실행하세요.")
    else:
        threshold_df = pd.read_csv(threshold_path)
        st.dataframe(threshold_df, width="stretch")

        ai_only = threshold_df[threshold_df["mode"] == "ai_filtered"].copy()

        if not ai_only.empty:
            ai_only["label"] = ai_only["ai_threshold"].astype(str)

            st.subheader("기준값별 수익률 / 최대 낙폭")

            chart_df = ai_only.set_index("label")[
                ["total_return", "max_drawdown", "win_rate"]
            ]
            st.bar_chart(chart_df)

            st.subheader("리스크 조정 점수")

            if "risk_adjusted_score" in ai_only.columns:
                score_df = ai_only.set_index("label")[["risk_adjusted_score"]]
                st.bar_chart(score_df)

            best_row = ai_only.sort_values(
                ["risk_adjusted_score", "total_return"],
                ascending=[False, False],
            ).iloc[0]

            st.success(
                "리스크 조정 점수 기준 최적 threshold: "
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

            st.subheader("전략에 기준값 적용")

            threshold_options = sorted(
                ai_only["ai_threshold"].dropna().astype(float).unique().tolist()
            )

            default_index = 0
            if 0.45 in threshold_options:
                default_index = threshold_options.index(0.45)

            selected_threshold = st.selectbox(
                "AI 기준값 선택",
                threshold_options,
                index=default_index,
            )

            enable_ai_filter = st.checkbox(
                "전략에서 AI 점수 필터 사용",
                value=True,
            )

            st.warning(
                "이 버튼은 실제 주문을 실행하지 않습니다. "
                "config/strategy_config.json의 AI 설정만 변경합니다."
            )

            if st.button("선택한 AI 기준값 적용", type="primary"):
                history_path = apply_ai_threshold_to_strategy(
                    threshold=float(selected_threshold),
                    enable_ai=bool(enable_ai_filter),
                )

                st.success(
                    f"AI 기준값={selected_threshold}을 적용했습니다. "
                    f"이력: {history_path.relative_to(ROOT_DIR)}"
                )

            if st.button("선택한 기준값 검증"):
                with st.spinner("Baseline과 AI 필터 전략을 비교 검증하는 중입니다..."):
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

                        st.subheader("검증 결과")
                        st.dataframe(comparison_df, width="stretch")

                        chart_df = pd.DataFrame(
                            {
                                "date": baseline_equity["date"],
                                "baseline": baseline_equity["equity"],
                                "ai_filtered": ai_equity["equity"],
                                "benchmark": baseline_equity["benchmark_equity"],
                            }
                        ).set_index("date")

                        st.subheader("검증 자산 곡선")
                        st.line_chart(chart_df)

                    except Exception as exc:
                        st.error(f"검증 실패: {exc}")

    st.divider()

    st.subheader("CMS에서 AI 작업 실행")

    st.warning(
        "이 작업들은 주문을 실행하지 않습니다. 다만 데이터 다운로드와 백테스트 때문에 시간이 걸릴 수 있습니다."
    )

    col1, col2, col3 = st.columns(3)

    if col1.button("AI 모델 학습", type="primary"):
        with st.spinner("AI 모델을 학습하는 중입니다..."):
            try:
                code, stdout, stderr = run_project_command(
                    [str(ROOT_DIR / ".venv/bin/python"), "-m", "src.train_ai_model"],
                    timeout=900,
                )

                if code == 0:
                    st.success("AI 모델 학습이 완료되었습니다.")
                else:
                    st.error("AI 모델 학습에 실패했습니다.")

                if stdout:
                    st.subheader("stdout")
                    st.code(stdout[-12000:], language="text")

                if stderr:
                    st.subheader("stderr")
                    st.code(stderr[-12000:], language="text")

            except Exception as exc:
                st.error(f"AI 모델 학습 실패: {exc}")

    if col2.button("AI 기준값 최적화"):
        with st.spinner("AI 기준값을 최적화하는 중입니다..."):
            try:
                code, stdout, stderr = run_project_command(
                    [str(ROOT_DIR / ".venv/bin/python"), "-m", "src.optimize_ai_threshold"],
                    timeout=3600,
                )

                if code == 0:
                    st.success("AI 기준값 최적화가 완료되었습니다.")
                else:
                    st.error("AI 기준값 최적화에 실패했습니다.")

                if stdout:
                    st.subheader("stdout")
                    st.code(stdout[-12000:], language="text")

                if stderr:
                    st.subheader("stderr")
                    st.code(stderr[-12000:], language="text")

            except Exception as exc:
                st.error(f"AI 기준값 최적화 실패: {exc}")

    if col3.button("AI 점수 확인"):
        with st.spinner("AI 점수를 확인하는 중입니다..."):
            try:
                code, stdout, stderr = run_project_command(
                    [str(ROOT_DIR / ".venv/bin/python"), "-m", "src.check_ai_score"],
                    timeout=300,
                )

                if code == 0:
                    st.success("AI 점수 확인이 완료되었습니다.")
                else:
                    st.error("AI 점수 확인에 실패했습니다.")

                if stdout:
                    st.subheader("stdout")
                    st.code(stdout[-12000:], language="text")

                if stderr:
                    st.subheader("stderr")
                    st.code(stderr[-12000:], language="text")

            except Exception as exc:
                st.error(f"AI 점수 확인 실패: {exc}")

    st.info("작업 완료 후 페이지를 새로고침하면 최신 metrics/threshold 결과가 반영됩니다.")

    st.divider()

    st.subheader("명령어")

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
        "페이지",
        [
            "개요",
            "로그",
            "백테스트 결과",
            "백테스트 실행",
            "백테스트 이력",
            "백테스트 비교",
            "Dry-run 점검",
            "설정 변경 이력",
            "실행 잠금",
            "Paper 주문 실행",
            "실행 이력",
            "스케줄러",
            "Telegram",
            "AI 모델",
            "Ops / 게이트",
        ],
    )

    if page == "개요":
        render_overview()
    elif page == "로그":
        render_logs()
    elif page == "백테스트 결과":
        render_backtest_outputs()
    elif page == "백테스트 실행":
        render_run_backtest()
    elif page == "백테스트 이력":
        render_backtest_history()
    elif page == "백테스트 비교":
        render_backtest_compare()
    elif page == "Dry-run 점검":
        render_dry_run()
    elif page == "설정 변경 이력":
        render_config_history()
    elif page == "실행 잠금":
        render_execution_lock()
    elif page == "Paper 주문 실행":
        render_paper_execution()
    elif page == "실행 이력":
        render_execution_runs()
    elif page == "스케줄러":
        render_scheduler()
    elif page == "Telegram":
        render_telegram()
    elif page == "AI 모델":
        render_ai_model()
    elif page == "Ops / 게이트":
        render_ops_dashboard()


if __name__ == "__main__":
    main()
