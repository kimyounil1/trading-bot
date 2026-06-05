"""
Trading Bot Dashboard — src/dashboard.py (Visual & Detailed Analytics)
실행: PYTHONPATH=. .venv/bin/streamlit run src/dashboard.py
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import subprocess

import pandas as pd
import streamlit as st

from src.settings import load_settings, apply_dynamic_profile
from src.market_clock import get_market_clock
from src.portfolio_backtester import run_portfolio_backtest, build_ai_score_frame
from src.ml_model import load_ai_score_model
from src.macro_loader import load_macro_data
from src.data_loader import load_price_data_batch
from src.candidate_cache import get_dynamic_universe

# ── 유틸 및 환경 설정 ────────────────────────────────────────────────────────
env = os.environ.copy()
env["PYTHONPATH"] = "."

STRATEGY_DESC = {
    "AGGRESSIVE": "🔥 **수익 극대화 모드**: 상승장에서 소수 종목(3종목)에 집중 투자(33%씩)하여 수익을 퀀텀 점프시킵니다.",
    "BALANCED": "⚖️ **균형 성장 모드**: 시장 상황에 맞춰 적절히 분산(8종목) 투자하며 안정적인 수익을 추구합니다.",
    "DEFENSIVE": "🛡️ **자산 보호 모드**: 하락장에서 많은 종목(15종목)으로 넓게 분산(5%씩)하여 내 돈을 지키는 데 집중합니다.",
    "AUTO (레짐 자동)": "🤖 **AI 자동 전환**: 시장의 온도를 AI가 분석하여 위 3가지 모드 중 최적의 모드를 스스로 선택합니다."
}

# ── 경로 상수 ──────────────────────────────────────────────────────────────
BASELINE_DIR = Path("logs/baselines/current_strategy")
TRADES_PATH = BASELINE_DIR / "portfolio_trades.csv"
ORDER_LOG_PATH = Path("logs/orders.csv")
SIGNAL_LOG_PATH = Path("logs/signals.csv")
AI_METRICS_PATH = Path("logs/ml/ai_model_metrics.csv")

# ── 공통 시뮬레이션 엔진 ──────────────────────────────────────────────────
def run_and_display_simulation(s_period, s_max_pos, s_pos_pct, s_ai_thr, s_use_ai, s_leverage, s_sl, s_tp, s_dyn_exit):
    with st.spinner("과거 데이터를 기반으로 시뮬레이션 엔진 가동 중..."):
        # 1. 데이터 준비
        settings = load_settings()
        tickers = list(settings.tickers)
        if getattr(settings, "dynamic_universe_enabled", False):
            tickers = get_dynamic_universe(tickers, limit=50)
        
        all_tk = list(dict.fromkeys(tickers + ["SPY", "^VIX"]))
        data = load_price_data_batch(all_tk, period="2y")
        vix, spy, mac = data.get("^VIX"), data.get("SPY"), load_macro_data(period="2y")
        model = load_ai_score_model()
        
        # 2. AI 스코어 계산
        test_scores = {}
        t_start_ts = pd.Timestamp.now() - pd.Timedelta(days=s_period)
        for t in tickers:
            if t in data:
                try: 
                    score_frame = build_ai_score_frame(data[t], model, vix, spy, mac)
                    test_scores[t] = score_frame[pd.to_datetime(score_frame["date"]) >= t_start_ts]
                except: continue
        
        # 3. 테스트 데이터 필터링
        test_data = {t: df[pd.to_datetime(df["date"]) >= t_start_ts] for t, df in data.items() if t in tickers}
        test_vix = vix[pd.to_datetime(vix["date"]) >= t_start_ts]
        test_mac = mac[pd.to_datetime(mac["date"]) >= t_start_ts]

        # 4. 백테스트 실행
        res, equity_df, trades_df = run_portfolio_backtest(
            ticker_data=test_data, initial_cash=10000.0 * s_leverage,
            max_positions=s_max_pos, target_position_pct=s_pos_pct,
            transaction_cost_pct=0.001, 
            use_ai_score=s_use_ai, ai_score_buy_threshold=s_ai_thr,
            stop_loss_pct=s_sl/100.0, take_profit_pct=s_tp/100.0,
            ai_exit_enabled=True, ai_exit_dynamic_enabled=s_dyn_exit,
            vix_df=test_vix, macro_df=test_mac, ai_score_frames=test_scores,
        )

        # 5. 시각화
        st.success("✅ 시뮬레이션 완료!")
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("최종 수익률", f"{res.total_return*100:+.2f}%")
        sc2.metric("최대 낙폭(MDD)", f"{res.max_drawdown*100:.2f}%")
        sc3.metric("샤프 지수", f"{res.sharpe_ratio:.3f}")
        sc4.metric("총 매매 횟수", res.trades)
        
        st.subheader("📈 자산 성장 곡선 (Equity Curve)")
        if not equity_df.empty:
            st.line_chart(equity_df.set_index("date")["equity"])
        
        st.subheader("💰 상세 매매 기록 (Trade Log)")
        if not trades_df.empty:
            # 읽기 쉬운 포맷으로 변환
            display_trades = trades_df.copy()
            # return_pct 컬럼이 있다면 100을 곱해 %로 변환
            if "return_pct" in display_trades.columns:
                display_trades["return_pct"] = (display_trades["return_pct"] * 100).round(2).astype(str) + "%"
            if "pnl_pct" in display_trades.columns:
                display_trades["pnl_pct"] = (display_trades["pnl_pct"] * 100).round(2).astype(str) + "%"
            st.dataframe(display_trades, use_container_width=True, hide_index=True)
        else:
            st.info("해당 기간 동안 발생한 매매가 없습니다.")

# ── 데이터 로더 ──────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_live_data():
    try:
        from src.brokers import broker_account_snapshot
        from src.settings import load_settings
        settings = load_settings()
        return broker_account_snapshot(settings.broker_provider)
    except: return None, []

@st.cache_data(ttl=300)
def load_intelligence():
    try:
        data = load_price_data_batch(["SPY", "^VIX"], period="1y")
        from src.market_regime import compute_daily_regime
        regimes = compute_daily_regime(data["SPY"], data["^VIX"])
        regime = str(regimes.iloc[-1])
    except: regime = "UNKNOWN"
    ai_metrics = pd.read_csv(AI_METRICS_PATH) if AI_METRICS_PATH.exists() else pd.DataFrame()
    return regime, ai_metrics

# ── UI 구성 ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Trading Command Center", page_icon="🤖", layout="wide")

with st.sidebar:
    st.title("🤖 AI 트레이더")
    clock = get_market_clock()
    if clock and clock.is_open: st.success(f"🟢 시장 거래 중")
    else:
        next_open_dt = pd.to_datetime(clock.next_open) if clock else None
        st.error(f"🔴 시장 폐장 (오픈: {next_open_dt.strftime('%m/%d %H:%M') if next_open_dt else 'N/A'})")
    st.divider()
    if st.button("📊 데이터 즉시 갱신", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.title("🚀 AI 트레이딩 커맨드 센터")
regime, ai_metrics = load_intelligence()
account, positions = load_live_data()
settings = load_settings()

if account:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 자산 (Portfolio)", f"${account['portfolio_value']:,.2f}")
    m2.metric("실제 누적 수익 (P&L)", f"${account['portfolio_value'] - 100000.0:,.2f}", delta=f"{((account['portfolio_value']-100000)/100000)*100:.2f}%")
    m3.metric("시장 상태 (Regime)", regime)
    _, p_name = apply_dynamic_profile(settings, regime)
    m4.metric("활성 프로필", p_name)

st.divider()
tab1, tab2, tab3 = st.tabs(["📺 실시간 모니터링", "🧠 지능형 전략 센터", "📊 분석 및 검증 센터"])

# ── TAB 1: 실시간 모니터링 ────────────────────────────────────────────────
with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("🤖 자동 매매 엔진 상태")
        auto_col1, auto_col2, auto_col3 = st.columns([1, 1, 2])
        timer_check = subprocess.run(["systemctl", "--user", "is-active", "trading-bot.timer"], capture_output=True, text=True)
        is_active = timer_check.stdout.strip() == "active"
        with auto_col1:
            if is_active:
                st.success("✅ 가동 중")
                if st.button("🛑 중단", use_container_width=True): subprocess.run(["systemctl", "--user", "stop", "trading-bot.timer"]); st.rerun()
            else:
                st.error("❌ 중단됨")
                if st.button("🚀 시작", use_container_width=True): subprocess.run(["systemctl", "--user", "start", "trading-bot.timer"]); st.rerun()
        with auto_col2:
            timer_info = subprocess.run(["systemctl", "--user", "list-timers", "trading-bot.timer", "--no-legend"], capture_output=True, text=True)
            st.caption("다음 매매 예정:"); st.write(timer_info.stdout.split("KST")[0].strip() + " KST" if timer_info.stdout else "N/A")
        with auto_col3: st.info("🕒 **미국 시간 기준**: 09:35(매수), 15:45(매도)")
        st.divider()
        st.subheader("📦 현재 보유 포지션")
        if positions:
            pos_df = pd.DataFrame(positions)
            pos_df["unrealized_plpc"] = (pos_df["unrealized_plpc"].astype(float) * 100).round(2).astype(str) + "%"
            pos_df["market_value"] = pos_df["market_value"].astype(float).apply(lambda x: f"${x:,.0f}")
            st.dataframe(pos_df[["symbol", "qty", "market_value", "unrealized_plpc"]], use_container_width=True, hide_index=True)
        else: st.info("보유 종목 없음")
    with col2:
        st.subheader("🎯 오늘의 AI 시그널 & 분석")
        
        # 버튼 2개를 나란히 배치
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("🔍 시그널 스캔", use_container_width=True, help="단순히 종목별 AI 점수와 매수/매도 신호만 최신화합니다."):
                with st.spinner("AI 분석 중..."):
                    subprocess.run([".venv/bin/python", "src/main.py"], env=env, capture_output=True, text=True)
                    st.cache_data.clear()
                    st.rerun()
        
        with btn_col2:
            if st.button("🚀 실전 드라이런", use_container_width=True, help="실제 매매 로직(비중 계산, 리스크 체크 등)을 포함한 전 과정을 가상 실행합니다."):
                with st.spinner("가상 매매 시뮬레이션 중..."):
                    result = subprocess.run([".venv/bin/python", "src/main.py"], env=env, capture_output=True, text=True)
                    st.session_state['dry_run_log'] = result.stdout
                    st.rerun()

        # 드라이런 로그가 세션에 있으면 출력
        if 'dry_run_log' in st.session_state:
            with st.expander("📝 가상 매매 실행 로그 (방금 실행됨)", expanded=True):
                st.code(st.session_state['dry_run_log'])
                if st.button("❌ 로그 닫기"):
                    del st.session_state['dry_run_log']
                    st.rerun()

        st.divider()
        signals = pd.read_csv(SIGNAL_LOG_PATH) if SIGNAL_LOG_PATH.exists() else pd.DataFrame()
        if not signals.empty:
            signals["timestamp"] = pd.to_datetime(signals["timestamp"])
            latest = signals[signals["timestamp"] >= (signals["timestamp"].max() - pd.Timedelta(minutes=10))].sort_values("ai_score", ascending=False)
            
            # 요약 정보
            st.write(f"⏱️ **마지막 분석**: {signals['timestamp'].max().strftime('%H:%M:%S')}")
            buys = latest[latest['signal'] == 'BUY']['ticker'].tolist()
            if buys:
                st.success(f"✅ **매수 추천**: {', '.join(buys)}")
            
            st.dataframe(latest[["ticker", "signal", "ai_score", "close", "rsi"]].head(30), use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ 아직 분석된 데이터가 없습니다. 스캔 버튼을 눌러주세요.")

# ── TAB 2: 지능형 전략 센터 ──────────────────────────────────────────────
with tab2:
    st.subheader("🛡️ 전략 제어판")
    with st.expander("🛠️ 전략 프로필 설정", expanded=True):
        profiles_path = Path("config/strategy_profiles.json")
        if profiles_path.exists():
            with open(profiles_path, "r", encoding="utf-8") as f: p_data = json.load(f)
            c1, c2 = st.columns(2)
            with c1:
                options = ["AUTO (레짐 자동)"] + list(p_data["profiles"].keys())
                new_choice = st.selectbox("전략 모드", options, index=(options.index(p_data.get("manual_override")) if p_data.get("manual_override") in options else 0))
                st.info(STRATEGY_DESC.get(new_choice, ""))
                if st.button("💾 설정 저장"):
                    p_data["manual_override"] = None if new_choice == "AUTO (레짐 자동)" else new_choice
                    with open(profiles_path, "w", encoding="utf-8") as f: json.dump(p_data, f, indent=2)
                    st.success("저장 완료!"); st.cache_data.clear(); st.rerun()
            with c2: st.json({"최대 종목": settings.max_total_positions, "비중": f"{settings.max_position_pct*100:.1f}%", "AI 문턱": settings.ai_score_buy_threshold})

# ── TAB 3: 분석 및 검증 센터 ──────────────────────────────────────────────
with tab3:
    st.subheader("🧪 전략 시뮬레이션")
    st.info("💡 **원클릭 버튼**을 누르면 대표 시나리오로, **샌드박스**에서 직접 설정하여 테스트할 수 있습니다.")
    
    # 1. 빠른 시뮬레이션
    with st.expander("🏃 빠른 시나리오 실행", expanded=True):
        b1, b2, b3 = st.columns(3)
        if b1.button("🔥 공격형(ULTRA) 5개월 테스트", use_container_width=True):
            run_and_display_simulation(150, 3, 0.33, 0.40, True, 1.0, 12, 30, True)
        if b2.button("⚖️ 중립형(Balanced) 5개월 테스트", use_container_width=True):
            run_and_display_simulation(150, 8, 0.125, 0.50, True, 1.0, 5, 15, True)
        if b3.button("🔄 AI 모델 재학습", use_container_width=True):
            with st.spinner("학습 중..."): subprocess.run([".venv/bin/python", "src/train_ai_model.py"], env=env); st.success("완료!")

    # 2. 커스텀 샌드박스
    st.divider()
    st.subheader("🛠️ 나만의 전략 시뮬레이터 (샌드박스)")
    with st.form("custom_test_form"):
        c1, c2, c3 = st.columns(3)
        with c1: s_period = st.slider("기간 (일)", 30, 730, 150); s_max_pos = st.number_input("최대 종목", 1, 30, 3); s_pos_pct = st.slider("비중", 0.05, 1.0, 0.33)
        with c2: s_ai_thr = st.slider("AI 문턱", 0.1, 0.9, 0.40); s_leverage = st.number_input("레버리지", 1.0, 4.0, 1.0)
        with c3: s_sl = st.slider("손절 (%)", 1, 30, 12); s_tp = st.slider("익절 (%)", 5, 100, 30); s_dyn_exit = st.checkbox("VIX 유동 익절", value=True)
        if st.form_submit_button("🚀 커스텀 시뮬레이션 시작", use_container_width=True):
            run_and_display_simulation(s_period, s_max_pos, s_pos_pct, s_ai_thr, True, s_leverage, s_sl, s_tp, s_dyn_exit)

    st.divider()
    with st.expander("📝 전체 매매 히스토리 보기"):
        trades = pd.read_csv(TRADES_PATH) if TRADES_PATH.exists() else pd.DataFrame()
        if not trades.empty: st.dataframe(trades.sort_values("exit_date", ascending=False), use_container_width=True)
        else: st.write("기록 없음")
