"""
Trading Bot Dashboard — src/dashboard.py
실행: streamlit run src/dashboard.py
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.settings import load_settings
from src.market_clock import get_market_clock

# ── 경로 상수 ──────────────────────────────────────────────────────────────
BASELINE_DIR = Path("logs/baselines/current_strategy")
SNAPSHOT_PATH = BASELINE_DIR / "baseline_snapshot.json"
EQUITY_PATH = BASELINE_DIR / "portfolio_equity.csv"
TRADES_PATH = BASELINE_DIR / "portfolio_trades.csv"
ORDER_LOG_PATH = Path("logs/orders.csv")
SIGNAL_LOG_PATH = Path("logs/signals.csv")
AI_METRICS_PATH = Path("logs/ml/ai_model_metrics.csv")


# ── 데이터 로더 (캐시) ──────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_account():
    try:
        from src.alpaca_client import get_account_summary, get_positions_summary
        account = get_account_summary()
        positions = get_positions_summary()
        return account, positions, None
    except Exception as exc:
        return None, [], str(exc)


@st.cache_data(ttl=300)
def load_snapshot():
    if not SNAPSHOT_PATH.exists():
        return None
    with open(SNAPSHOT_PATH) as f:
        return json.load(f)


@st.cache_data(ttl=300)
def load_equity():
    if not EQUITY_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(EQUITY_PATH, parse_dates=["date"])
    return df


@st.cache_data(ttl=300)
def load_trades():
    if not TRADES_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(TRADES_PATH, parse_dates=["entry_date", "exit_date"])


@st.cache_data(ttl=60)
def load_orders():
    if not ORDER_LOG_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(ORDER_LOG_PATH, parse_dates=["timestamp"])


@st.cache_data(ttl=60)
def load_signals():
    if not SIGNAL_LOG_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(SIGNAL_LOG_PATH, parse_dates=["timestamp"])
    return df


@st.cache_data(ttl=300)
def load_ai_metrics():
    if not AI_METRICS_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(AI_METRICS_PATH)


@st.cache_data(ttl=120)
def load_market_clock():
    try:
        return get_market_clock()
    except Exception:
        return None


# ── 유틸 ───────────────────────────────────────────────────────────────────
def pct(value: float, decimals: int = 2) -> str:
    return f"{value * 100:.{decimals}f}%"


def color_return(value: float) -> str:
    color = "green" if value >= 0 else "red"
    return f":{color}[{pct(value)}]"


# ── 레이아웃 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Trading Bot Dashboard",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Trading Bot Dashboard")

settings = load_settings()
clock = load_market_clock()

# 마켓 상태 배너
if clock:
    if clock.is_open:
        st.success(f"시장 열림 — {clock.timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    else:
        st.warning(
            f"시장 닫힘 — 다음 오픈: {clock.next_open.strftime('%Y-%m-%d %H:%M %Z')}"
        )

if st.button("새로고침"):
    st.cache_data.clear()
    st.rerun()

st.divider()

# ── 1. 계좌 현황 ────────────────────────────────────────────────────────────
st.header("계좌 현황 (Alpaca Paper)")

account, positions, err = load_account()

if err:
    st.error(f"Alpaca 연결 실패: {err}")
else:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("포트폴리오 가치", f"${account['portfolio_value']:,.2f}")
    col2.metric("현금", f"${account['cash']:,.2f}")
    col3.metric("매수 여력", f"${account['buying_power']:,.2f}")
    col4.metric("보유 종목 수", account["positions_count"])

    # 포지션 테이블
    if positions:
        st.subheader("보유 포지션")
        pos_rows = []
        for p in positions:
            plpc = float(p["unrealized_plpc"])
            pos_rows.append(
                {
                    "티커": p["symbol"],
                    "수량": float(p["qty"]),
                    "시장가치": f"${float(p['market_value']):,.2f}",
                    "매입원가": f"${float(p['cost_basis']):,.2f}",
                    "미실현손익": f"${float(p['unrealized_pl']):,.2f}",
                    "수익률": f"{plpc * 100:+.2f}%",
                }
            )
        pos_df = pd.DataFrame(pos_rows)
        st.dataframe(pos_df, use_container_width=True, hide_index=True)
    else:
        st.info("보유 포지션 없음")

st.divider()

# ── 2. 백테스트 성과 (2y 기준) ───────────────────────────────────────────────
st.header("백테스트 성과 (2년 기준선)")

snapshot = load_snapshot()
equity_df = load_equity()
trades_df = load_trades()

if snapshot:
    result = snapshot.get("result", {})
    col1, col2, col3, col4, col5 = st.columns(5)
    total_return = result.get("total_return", 0)
    benchmark_return = result.get("benchmark_return", 0)
    col1.metric(
        "전략 수익률",
        pct(total_return),
        delta=f"vs B&H {pct(total_return - benchmark_return)}",
    )
    col2.metric("최대낙폭", pct(result.get("max_drawdown", 0)))
    col3.metric("총 거래 수", result.get("trades", 0))
    col4.metric("승률", pct(result.get("win_rate", 0)))
    col5.metric("최종 자산", f"${result.get('final_equity', 0):,.2f}")

    generated = snapshot.get("generated_at_utc", "")[:16].replace("T", " ")
    st.caption(
        f"기간: {snapshot.get('period', '')} | "
        f"티커: {snapshot.get('tickers', 0)}개 | "
        f"생성: {generated}"
    )
else:
    st.info("baseline_snapshot.json 없음. `python -m src.generate_baseline_snapshot` 실행 필요")

# 에쿼티 커브 차트
if not equity_df.empty:
    st.subheader("에쿼티 커브")
    chart_df = equity_df.set_index("date")[["equity", "benchmark_equity"]].rename(
        columns={"equity": "전략", "benchmark_equity": "B&H 벤치마크"}
    )
    st.line_chart(chart_df)

# 거래 내역
if not trades_df.empty:
    st.subheader(f"백테스트 거래 내역 (총 {len(trades_df)}건)")
    display_df = trades_df.copy()
    display_df["return_pct"] = (display_df["return_pct"] * 100).round(2).astype(str) + "%"
    display_df["entry_price"] = display_df["entry_price"].round(2)
    display_df["exit_price"] = display_df["exit_price"].round(2)
    st.dataframe(
        display_df[["ticker", "entry_date", "exit_date", "entry_price", "exit_price", "return_pct", "exit_reason"]],
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# ── 3. AI 모델 성능 ─────────────────────────────────────────────────────────
st.header("AI 모델 성능 (Cross-validation)")

ai_metrics = load_ai_metrics()
if not ai_metrics.empty:
    col1, col2, col3 = st.columns(3)
    col1.metric("평균 ROC-AUC", f"{ai_metrics['roc_auc'].mean():.4f}")
    col2.metric("평균 정밀도", f"{ai_metrics['precision'].mean():.4f}")
    col3.metric("평균 재현율", f"{ai_metrics['recall'].mean():.4f}")

    st.subheader("Fold별 지표")
    display_metrics = ai_metrics.copy()
    for col in ["accuracy", "precision", "recall", "roc_auc"]:
        display_metrics[col] = display_metrics[col].round(4)
    st.dataframe(display_metrics, use_container_width=True, hide_index=True)
else:
    st.info("AI 모델 지표 없음. `python -m src.train_ai_model` 실행 필요")

st.divider()

# ── 4. 실시간 시그널 (마지막 실행 기록) ────────────────────────────────────
st.header("최근 시그널")

signals_df = load_signals()
if not signals_df.empty:
    latest_run = signals_df["timestamp"].max()
    today_signals = signals_df[signals_df["timestamp"] == latest_run].copy()

    st.caption(f"마지막 실행: {latest_run}")

    buy_signals = today_signals[today_signals["signal"] == "BUY"]
    sell_signals = today_signals[today_signals["signal"] == "SELL"]
    hold_signals = today_signals[today_signals["signal"] == "HOLD"]

    col1, col2, col3 = st.columns(3)
    col1.metric("BUY 시그널", len(buy_signals))
    col2.metric("SELL 시그널", len(sell_signals))
    col3.metric("HOLD", len(hold_signals))

    if not buy_signals.empty:
        st.subheader("BUY 시그널 종목")
        st.dataframe(buy_signals, use_container_width=True, hide_index=True)

    st.subheader("전체 시그널")
    st.dataframe(today_signals, use_container_width=True, hide_index=True)
else:
    st.info("시그널 로그 없음. `python -m src.main` 실행 후 생성됩니다.")

# ── 5. 주문 내역 ────────────────────────────────────────────────────────────
orders_df = load_orders()
if not orders_df.empty:
    st.header(f"최근 주문 내역 (최근 20건)")
    recent_orders = orders_df.sort_values("timestamp", ascending=False).head(20)
    st.dataframe(recent_orders, use_container_width=True, hide_index=True)

st.divider()

# ── 6. 전략 설정 요약 ──────────────────────────────────────────────────────
with st.expander("전략 설정 상세 보기"):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
| 파라미터 | 값 |
|---|---|
| 티커 수 | {len(settings.tickers)}개 |
| MA Fast / Slow | {settings.ma_fast} / {settings.ma_slow} |
| RSI 매수 한도 | {settings.rsi_buy_limit} |
| 최대 포지션 수 | {settings.max_total_positions} |
| 포지션 비중 | {settings.max_position_pct * 100:.0f}% |
| 1회 최대 주문 | ${settings.max_test_order_amount:,.0f} |
        """)
    with col2:
        st.markdown(f"""
| 파라미터 | 값 |
|---|---|
| AI Score | {'활성' if settings.use_ai_score else '비활성'} |
| AI 임계값 | {settings.ai_score_buy_threshold} |
| 볼륨 필터 | {'활성' if settings.volume_filter_enabled else '비활성'} |
| 일일 주문 한도 | ${settings.max_daily_order_amount:,.0f} |
| 매수 쿨다운 | {settings.buy_cooldown_days}일 |
| 시장 레짐 필터 | {'활성' if settings.market_regime_filter_enabled else '비활성'} |
        """)

    st.markdown("**보유 티커 목록**")
    ticker_cols = st.columns(10)
    for i, ticker in enumerate(settings.tickers):
        ticker_cols[i % 10].caption(ticker)
