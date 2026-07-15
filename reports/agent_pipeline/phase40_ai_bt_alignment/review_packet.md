# Agent Review Packet - Run: phase40_ai_bt_alignment

## Implementation Agent
codex

## Task Description
Task details not found

## Changed Files
- .env.example
- README.md
- TODO.md
- app/streamlit_app.py
- config/instrument_registry.json
- config/margin_leverage_paper_proposal.json
- config/strategy_config.json
- logs/crowding_paper/go_no_go_checklist.json
- logs/crowding_paper/reassessment.json
- logs/llm_advisory/latest_summary.json
- logs/llm_advisory/precision.json
- logs/paper_validation/history.jsonl
- logs/paper_validation/latest_summary.json
- logs/paper_validation/trend_summary.json
- scripts/llm_retro_scoring.py
- scripts/run_weekly_gap_attribution.sh
- src/alpaca_client.py
- src/brokers/alpaca.py
- src/brokers/base.py
- src/brokers/paper.py
- src/brokers/toss.py
- src/buy_guards.py
- src/candidate_cache.py
- src/features.py
- src/instrument_meta.py
- src/llm_analyst.py
- src/ml_model.py
- src/portfolio_backtest_settings.py
- src/portfolio_backtester.py
- src/rank_ai_gate.py
- src/rank_leaderboard.py
- src/risk_manager.py
- src/run_portfolio_backtest.py
- src/settings.py
- src/sleeve_rebalance.py
- src/trading/buy_pipeline.py
- src/trading/exit_pipeline.py
- src/trading/run_context.py
- src/trading/sleeve_rebalance_pipeline.py
- src/trading/tournament_buy_pipeline.py
- tests/fixtures/ml_quality/golden_fold_stability_report.json
- tests/fixtures/ml_quality/golden_model_calibration_report.json
- tests/test_alpaca_safe_qty.py
- tests/test_broker_adapter.py
- tests/test_candidate_cache_and_risk.py
- tests/test_instrument_meta.py
- tests/test_main_e2e.py
- tests/test_rank_leaderboard.py
- tests/test_recent_changes.py
- tests/test_settings.py
- tests/test_sleeve_rebalance.py
- tests/test_sleeve_rebalance_pipeline.py

## Git Diff Summary
```
 .env.example                                       |   9 +
 README.md                                          |  10 +
 TODO.md                                            |  31 +-
 app/streamlit_app.py                               | 150 +++++++-
 config/instrument_registry.json                    |  40 +-
 config/margin_leverage_paper_proposal.json         |   2 +-
 config/strategy_config.json                        |  18 +-
 logs/crowding_paper/go_no_go_checklist.json        |   2 +-
 logs/crowding_paper/reassessment.json              |   6 +-
 logs/llm_advisory/latest_summary.json              |   8 +-
 logs/llm_advisory/precision.json                   | 156 ++++++--
 logs/paper_validation/history.jsonl                |  22 ++
 logs/paper_validation/latest_summary.json          | 426 ++++++++++++---------
 logs/paper_validation/trend_summary.json           | 119 +++---
 scripts/llm_retro_scoring.py                       |  62 ++-
 scripts/run_weekly_gap_attribution.sh              |   0
 src/alpaca_client.py                               | 240 +++++++++++-
 src/brokers/alpaca.py                              |  53 ++-
 src/brokers/base.py                                |  17 +
 src/brokers/paper.py                               |   3 +-
 src/brokers/toss.py                                | 145 ++++++-
 src/buy_guards.py                                  |   3 +-
 src/candidate_cache.py                             |  35 ++
 src/features.py                                    |  52 +++
 src/instrument_meta.py                             | 138 ++++++-
 src/llm_analyst.py                                 |  17 +-
 src/ml_model.py                                    |  53 ++-
 src/portfolio_backtest_settings.py                 |  40 ++
 src/portfolio_backtester.py                        | 404 ++++++++++++++++---
 src/rank_ai_gate.py                                | 160 +++++++-
 src/rank_leaderboard.py                            |   4 +-
 src/risk_manager.py                                |  20 +
 src/run_portfolio_backtest.py                      | 110 +++++-
 src/settings.py                                    |   6 +
 src/sleeve_rebalance.py                            |  65 +++-
 src/trading/buy_pipeline.py                        | 140 ++++++-
 src/trading/exit_pipeline.py                       | 323 ++++++++++++----
 src/trading/run_context.py                         |   6 +-
 src/trading/sleeve_rebalance_pipeline.py           | 116 +++++-
 src/trading/tournament_buy_pipeline.py             |  62 ++-
 .../ml_quality/golden_fold_stability_report.json   |   2 +-
 .../golden_model_calibration_report.json           |   2 +-
 tests/test_alpaca_safe_qty.py                      |  11 +-
 tests/test_broker_adapter.py                       | 157 +++++++-
 tests/test_candidate_cache_and_risk.py             |   3 +-
 tests/test_instrument_meta.py                      |  42 ++
 tests/test_main_e2e.py                             |   3 +
 tests/test_rank_leaderboard.py                     |  33 +-
 tests/test_recent_changes.py                       | 160 +++++++-
 tests/test_settings.py                             |   9 +-
 tests/test_sleeve_rebalance.py                     |   8 +
 tests/test_sleeve_rebalance_pipeline.py            |  56 ++-
 52 files changed, 3171 insertions(+), 588 deletions(-)
```

## Test Execution Results (runtime_harness.log)
```
============================= test session starts ==============================
platform linux -- Python 3.12.8, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/kimyo/trading-bot
plugins: anyio-4.13.0
collected 45 items

tests/test_report_performance.py .....                                   [ 11%]
tests/test_reappraise_regime.py ...                                      [ 17%]
tests/test_portfolio_backtest_golden.py ...                              [ 24%]
tests/test_portfolio_backtest_gate.py .....                              [ 35%]
tests/test_daily_audit_summary.py ....                                   [ 44%]
tests/test_daily_audit_summary_schema.py ....                            [ 53%]
tests/test_retrain_notifications.py ....                                 [ 62%]
tests/test_llm_cache_report_schema.py ..                                 [ 66%]
tests/test_leverage_stress_report.py ...                                 [ 73%]
tests/test_guard_impact_report.py ..                                     [ 77%]
tests/test_check_audit_daily_summary.py ...                              [ 84%]
tests/test_fold_variance_report.py .                                     [ 86%]
tests/test_promotion_summary.py ..                                       [ 91%]
tests/test_benchmark_gap_report.py .                                     [ 93%]
tests/test_champion_promotion_governance.py ...                          [100%]

=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/websockets/legacy/__init__.py:6
  /home/kimyo/trading-bot/.venv/lib/python3.12/site-packages/websockets/legacy/__init__.py:6: DeprecationWarning: websockets.legacy is deprecated; see https://websockets.readthedocs.io/en/stable/howto/upgrade.html for upgrade instructions
    warnings.warn(  # deprecated in 14.0 - 2024-11-09

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 45 passed, 1 warning in 4.85s =========================
```

## Git Patch
```diff
diff --git a/.env.example b/.env.example
index 94cc6bd..7b6d8b6 100644
--- a/.env.example
+++ b/.env.example
@@ -21,3 +21,12 @@ GEMINI_API_KEY=
 # LLM_VLLM_MODEL=gemma4-26B
 # LLM_VLLM_TIMEOUT=120
 # LLM_VLLM_MAX_TOKENS=512
+
+# Toss Securities Open API (https://openapi.tossinvest.com)
+# OAuth2 client_credentials keys from Toss WTS → 설정 → Open API
+TOSS_CLIENT_ID=
+TOSS_SECRET_KEY=
+# X-Tossinvest-Account seq (blank = auto-resolve first account)
+TOSS_ACCOUNT=
+# TOSS_API_BASE=https://openapi.tossinvest.com
+# TOSS_TIMEOUT=15
diff --git a/README.md b/README.md
index 11e4466..b5b4ca4 100644
--- a/README.md
+++ b/README.md
@@ -39,6 +39,11 @@
   - 시뮬-페이퍼 갭 어트리뷰션 주간 (`logs/sim_paper_gap/`) — 가드별 기회비용, 슬리브 예산 완화 판정 규칙(8주 연속) 사전 등록
 - **리서치 결론 (2026-06/07)**: 유니버스 확대·피처 추가(실적/뉴스/gap_vol)·레짐 게이트 전부 게이트 기각 — 남은 수익 레버는 자본 배치 판단(~09월). 상세: [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)
 
+### 7. 운영 정렬 백테스트
+- 운영과 백테스트가 같은 **당일 인과적 AI 피처 + 날짜별 point-in-time 레짐** 점수 경로를 사용합니다.
+- 현재 설정의 core/tournament/cash 예산, 직접 2배 상품 라우팅과 본주 fallback, 노출·상관·crowding·sector guard, 부분익절, 현금 하한을 일봉 기준으로 재현합니다.
+- 실행 결과에는 `monthly_attribution.csv`와 `monthly_review_queue.md`가 생성됩니다. 손실/벤치마크 미달 월은 원인 분석과 forward 검증 전에는 설정을 자동 변경하지 않습니다.
+
 ## 📂 프로젝트 구조
 
 ```text
@@ -149,6 +154,11 @@ bash scripts/run_sleeve_performance_report.sh                       # 슬리브
 bash scripts/run_portfolio_pnl_report.sh                            # paper P&L (FIFO realized)
 PYTHONPATH=. .venv/bin/python -m src.market_regime_snapshot         # 레짐 스냅샷 (데일리 자동)
 bash scripts/run_weekly_gap_attribution.sh                          # 갭 어트리뷰션 (일 18:00 ET 타이머)
+
+# 운영 정렬 백테스트 (슬리브 설정이 켜져 있으면 자동 분리 실행)
+PYTHONPATH=. .venv/bin/python -m src.run_portfolio_backtest \
+  --start 2026-01-01 --end 2026-07-14 \
+  --outdir logs/portfolio_backtest_aligned
 ```
 
 Live execute (double confirm): `TRADING_ENV=live CONFIRM_LIVE_TRADING=YES_I_UNDERSTAND PYTHONPATH=. .venv/bin/python src/main.py --execute`
diff --git a/TODO.md b/TODO.md
index 086586f..eaea4b2 100644
--- a/TODO.md
+++ b/TODO.md
@@ -26,7 +26,36 @@
 
 ---
 
-## Current Status (2026-07-07)
+## Current Status (2026-07-14)
+
+### AI/백테스트 정렬 작업 (07-14)
+
+| # | 항목 | 상태 | 비고 |
+|---|------|------|------|
+| AI-BT-1 | **운영 AI 점수와 백테스터를 당일 인과적 피처·당일 레짐으로 단일화** | [x] 완료 (07-14) | 기존 운영의 label horizon 20거래일 지연과 기존 BT의 마지막 레짐 과거 전체 적용 제거. 단일 inference 경로·point-in-time 레짐 및 전체 회귀 테스트 통과 |
+| AI-BT-2 | **운영형 백테스트 parity** | [x] 완료 (07-14) | 직접 2배 상품→본주 fallback, VIX/노출 제한, 상관·crowding·sector guard의 as-of 데이터, 부분익절, 현금 하한, non-fractionable, 동적 유니버스/Rank 횡단면, core/tournament/cash 예산 분리 반영 |
+| AI-BT-3 | **월별 성과 원인 분석 자동화** | [x] 완료 (07-14) | 매 BT 저장 시 `monthly_attribution.csv` + `monthly_review_queue.md` 생성. 손실/벤치마크 미달 월은 최악 종목·슬리브·청산 사유·2배/본주 실현손익을 기록 |
+
+#### 07-14 정렬 백테스트 관찰 (자동 설정 변경 금지)
+
+- 2026-01-01~07-14 현재 운영 조합: Rank ON + 슬리브 + 조건부 2배 **+1.79%, MDD -19.75%**, Buy & Hold **+15.72%**.
+- 같은 구간 Rank OFF: 슬리브 + 조건부 2배 **+21.61%, MDD -16.77%**. 다만 Rank 공식 OOS(2025-12-01~2026-05-01)는 Rank ON **+10.89% / B&H +9.73%**, OFF **+3.70%**로 반대 결과.
+- 해석: Rank 모델 단독 OOS가 아니라 MA·AI·슬리브·2배 라우팅과의 조합 및 시작 포지션 경로에 민감하다. 단일 구간 결과로 Rank를 켜거나 끄지 않는다.
+- 수정 후보 TODO: 월별 Rank 통과/차단군 forward return, 슬리브별 Rank 기여, 2배/본주 미실현 포함 기여를 최소 8주 누적한 뒤 `Rank ON`, `OFF`, `레짐 조건부`를 동일 비용·동일 유니버스로 walk-forward 비교한다.
+
+### 월별 손익 리뷰 — 반복 TODO
+
+월별 리뷰는 결과를 보고 즉시 설정을 바꾸는 절차가 아니다. 원인 확인 → 수정안 백테스트 → 미사용 기간/forward 검증 → 채택 또는 기각 기록 순서를 지킨다.
+
+| 주기 | TODO | 완료 조건 |
+|------|------|----------|
+| 매월 첫 거래일 | 전월 수익률·Buy & Hold 대비·MDD·슬리브별 손익 확인 | `monthly_attribution.csv`와 실제 paper P&L 대조 |
+| 손실 월 발생 시 | 시장 하락 동반 여부, 손절 연속 구간, 최악 종목/섹터, AI·Rank 점수 구간, 2배 상품과 본주 차이 분석 | `monthly_review_queue.md`의 원인 확인 체크 |
+| 수정안 생성 시 | 진입 cutoff, 레짐 필터, 손절/익절, 보유기간, leverage fallback 중 원인과 직접 관련된 변경만 후보화 | 변경 이유·예상 부작용·비교 기준 기록 |
+| 수정안 검증 시 | 같은 기간 재최적화에 그치지 않고 OOS 또는 다음 forward 기간 검증 | 수익·MDD·Sharpe·회전율·Buy & Hold gap 동시 비교 |
+| 판단 완료 시 | 채택/기각과 근거를 월별 queue 및 archive에 기록 | 단일 손실 월만으로 자동 채택 금지 |
+
+남은 fidelity 점검: 과거 LLM/뉴스 판단 데이터의 완전성, cross-sleeve 동일 종목/주문 경합, 장중·확장시간 체결, 실제 브로커 주문 거절·미체결을 별도 execution replay에서 검증한다.
 
 | 영역 | 상태 |
 |------|------|
diff --git a/app/streamlit_app.py b/app/streamlit_app.py
index 851357d..00272fc 100644
--- a/app/streamlit_app.py
+++ b/app/streamlit_app.py
@@ -13,7 +13,7 @@ ROOT_DIR = Path(__file__).resolve().parents[1]
 sys.path.insert(0, str(ROOT_DIR))
 
 from src.broker_adapter import get_broker_adapter
-from src.brokers import broker_account_snapshot
+from src.brokers import broker_account_snapshot, toss_client
 from src.execution_audit_io import read_execution_audit_csv
 from src.market_clock import get_market_clock, MarketClock
 from src.settings import load_settings, CONFIG_PATH
@@ -3621,6 +3621,151 @@ def render_portfolio_pnl() -> None:
     )
 
 
+@st.cache_data(ttl=30, show_spinner=False)
+def _load_toss_snapshot(closed_limit: int = 50):
+    """Read-only Toss snapshot: (account_seq, buying_power, positions, open, closed)."""
+    adapter = get_broker_adapter("toss")
+    seq = toss_client.resolve_account_seq()
+    buying_power: dict[str, dict] = {}
+    for currency in ("USD", "KRW"):
+        try:
+            buying_power[currency] = toss_client.get_buying_power(currency)
+        except Exception as exc:  # noqa: BLE001 - surface per-currency errors in UI
+            buying_power[currency] = {"error": str(exc)}
+    positions = adapter.get_positions()
+    open_orders = adapter.get_open_orders(limit=100)
+    closed_orders = adapter.get_recent_closed_orders(limit=int(closed_limit))
+    return seq, buying_power, positions, open_orders, closed_orders
+
+
+@st.cache_data(ttl=30, show_spinner=False)
+def _load_toss_us_prices(symbols: tuple[str, ...]):
+    """Live US quotes for the configured trading universe (read-only)."""
+    if not symbols:
+        return []
+    return toss_client.get_prices(list(symbols))
+
+
+def _toss_buying_power_value(data: dict) -> str:
+    if not isinstance(data, dict):
+        return "-"
+    if "error" in data:
+        return "오류"
+    for key in ("cashBuyingPower", "buyingPower", "cash", "amount"):
+        if data.get(key) not in (None, ""):
+            return str(data[key])
+    return "-"
+
+
+def render_toss_account() -> None:
+    st.header("토스증권 계좌 (조회 전용)")
+
+    if not toss_client.credentials_available():
+        st.warning(
+            "TOSS_CLIENT_ID / TOSS_SECRET_KEY 가 설정되지 않았습니다. "
+            ".env에 키를 넣은 뒤 새로고침하세요. (조회 전용, 주문 미지원)"
+        )
+        return
+
+    st.caption(
+        f"API: {toss_client.api_base()} · 조회 전용 (매수/매도/취소 비활성) · "
+        "국장·미장 통합 단일 계좌 (미장 매매 기준: USD)"
+    )
+
+    col_refresh, col_limit = st.columns([1, 3])
+    if col_refresh.button("토스 새로고침", type="primary", key="refresh_toss"):
+        st.cache_data.clear()
+        st.rerun()
+    closed_limit = col_limit.number_input(
+        "최근 종료 주문 조회 수",
+        min_value=10,
+        max_value=200,
+        value=50,
+        step=10,
+        key="toss_closed_limit",
+    )
+
+    try:
+        seq, buying_power, positions, open_orders, closed_orders = _load_toss_snapshot(
+            int(closed_limit)
+        )
+    except Exception as exc:  # noqa: BLE001 - show fetch failure to operator
+        st.error(f"토스 조회 실패: {exc}")
+        return
+
+    m1, m2, m3, m4 = st.columns(4)
+    m1.metric("USD 매수가능 (미장)", _toss_buying_power_value(buying_power.get("USD", {})))
+    m2.metric("KRW 매수가능 (국장)", _toss_buying_power_value(buying_power.get("KRW", {})))
+    m3.metric("보유 종목", len(positions))
+    m4.metric("계좌 seq", str(seq or "-"))
+
+    for currency, data in buying_power.items():
+        if isinstance(data, dict) and "error" in data:
+            st.caption(f"{currency} 매수가능 조회 오류: {data['error']}")
+
+    st.subheader("보유 종목")
+    if positions:
+        pos_df = pd.DataFrame(
+            [{k: v for k, v in p.items() if k != "_raw"} for p in positions]
+        )
+        st.dataframe(pos_df, width="stretch", hide_index=True)
+    else:
+        st.info("보유 종목이 없습니다. (미장 종목 매수 시 여기에 표시됩니다)")
+
+    st.subheader("주문 현황")
+    tab_open, tab_closed = st.tabs(["미체결 / 대기 (OPEN)", "종료 (CLOSED)"])
+    with tab_open:
+        if open_orders:
+            st.dataframe(pd.DataFrame(open_orders), width="stretch", hide_index=True)
+        else:
+            st.info("미체결 주문이 없습니다.")
+    with tab_closed:
+        if closed_orders:
+            st.dataframe(pd.DataFrame(closed_orders), width="stretch", hide_index=True)
+        else:
+            st.info("종료된 주문이 없습니다.")
+
+    st.subheader("미장 실시간 시세 (트레이딩 유니버스)")
+    settings = load_settings()
+    universe = [str(t).strip().upper() for t in getattr(settings, "tickers", []) if str(t).strip()]
+    default_n = min(20, len(universe))
+    watch_n = st.slider(
+        "표시 종목 수",
+        min_value=1,
+        max_value=max(1, len(universe)),
+        value=max(1, default_n),
+        key="toss_us_watch_n",
+    )
+    watch_symbols = tuple(universe[:watch_n])
+    if watch_symbols:
+        try:
+            prices = _load_toss_us_prices(watch_symbols)
+        except Exception as exc:  # noqa: BLE001 - surface quote errors in UI
+            st.error(f"미장 시세 조회 실패: {exc}")
+        else:
+            if prices:
+                st.dataframe(pd.DataFrame(prices), width="stretch", hide_index=True)
+            else:
+                st.info("시세 결과가 없습니다.")
+    else:
+        st.info("설정된 트레이딩 종목이 없습니다.")
+
+    with st.expander("종목 직접 조회 (symbols)"):
+        symbols_text = st.text_input(
+            "심볼 (쉼표 구분, 예: AAPL, TSLA, 005930)", key="toss_quote_symbols"
+        )
+        if st.button("시세 조회", key="toss_quote_btn") and symbols_text.strip():
+            try:
+                prices = toss_client.get_prices(symbols_text.split(","))
+            except Exception as exc:  # noqa: BLE001 - surface quote errors in UI
+                st.error(f"시세 조회 실패: {exc}")
+            else:
+                if prices:
+                    st.dataframe(pd.DataFrame(prices), width="stretch", hide_index=True)
+                else:
+                    st.info("결과가 없습니다.")
+
+
 def main() -> None:
     sidebar_settings_editor()
 
@@ -3643,6 +3788,7 @@ def main() -> None:
             "Telegram",
             "AI 모델",
             "운영 · 가드",
+            "토스 계좌 (조회)",
         ],
     )
 
@@ -3678,6 +3824,8 @@ def main() -> None:
         render_ai_model()
     elif page == "운영 · 가드":
         render_ops_dashboard()
+    elif page == "토스 계좌 (조회)":
+        render_toss_account()
 
 
 if __name__ == "__main__":
diff --git a/config/instrument_registry.json b/config/instrument_registry.json
index 2e31a98..bd52886 100644
--- a/config/instrument_registry.json
+++ b/config/instrument_registry.json
@@ -24,5 +24,43 @@
   "FAS": { "kind": "leveraged_etf", "multiple": 3, "underlying": "XLF", "direction": "long" },
   "FAZ": { "kind": "leveraged_etf", "multiple": 3, "underlying": "XLF", "direction": "short" },
   "TNA": { "kind": "leveraged_etf", "multiple": 3, "underlying": "IWM", "direction": "long" },
-  "TZA": { "kind": "leveraged_etf", "multiple": 3, "underlying": "IWM", "direction": "short" }
+  "TZA": { "kind": "leveraged_etf", "multiple": 3, "underlying": "IWM", "direction": "short" },
+  "AAPB": { "kind": "leveraged_etf", "multiple": 2, "underlying": "AAPL", "direction": "long" },
+  "AMDL": { "kind": "leveraged_etf", "multiple": 2, "underlying": "AMD", "direction": "long" },
+  "AMZZ": { "kind": "leveraged_etf", "multiple": 2, "underlying": "AMZN", "direction": "long" },
+  "AVGU": { "kind": "leveraged_etf", "multiple": 2, "underlying": "AVGO", "direction": "long" },
+  "BBUL": { "kind": "leveraged_etf", "multiple": 2, "underlying": "BB", "direction": "long" },
+  "CONL": { "kind": "leveraged_etf", "multiple": 2, "underlying": "COIN", "direction": "long" },
+  "CRWL": { "kind": "leveraged_etf", "multiple": 2, "underlying": "CRWD", "direction": "long" },
+  "FBL": { "kind": "leveraged_etf", "multiple": 2, "underlying": "META", "direction": "long" },
+  "GOU": { "kind": "leveraged_etf", "multiple": 2, "underlying": "GOOGL", "direction": "long" },
+  "INTW": { "kind": "leveraged_etf", "multiple": 2, "underlying": "INTC", "direction": "long" },
+  "LNOK": { "kind": "leveraged_etf", "multiple": 2, "underlying": "NOK", "direction": "long" },
+  "MRAL": { "kind": "leveraged_etf", "multiple": 2, "underlying": "MARA", "direction": "long" },
+  "MSFL": { "kind": "leveraged_etf", "multiple": 2, "underlying": "MSFT", "direction": "long" },
+  "MULL": { "kind": "leveraged_etf", "multiple": 2, "underlying": "MU", "direction": "long" },
+  "NVDL": { "kind": "leveraged_etf", "multiple": 2, "underlying": "NVDA", "direction": "long" },
+  "PTIR": { "kind": "leveraged_etf", "multiple": 2, "underlying": "PLTR", "direction": "long" },
+  "QCML": { "kind": "leveraged_etf", "multiple": 2, "underlying": "QCOM", "direction": "long" },
+  "RVNL": { "kind": "leveraged_etf", "multiple": 2, "underlying": "RIVN", "direction": "long" },
+  "TSLR": { "kind": "leveraged_etf", "multiple": 2, "underlying": "TSLA", "direction": "long" },
+  "TSMU": { "kind": "leveraged_etf", "multiple": 2, "underlying": "TSM", "direction": "long" },
+  "AMAU": { "kind": "leveraged_etf", "multiple": 2, "underlying": "AMAT", "direction": "long" },
+  "ARMG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "ARM", "direction": "long" },
+  "ASMG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "ASML", "direction": "long" },
+  "AXPG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "AXP", "direction": "long" },
+  "BOEG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "BA", "direction": "long" },
+  "COTG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "COST", "direction": "long" },
+  "GRAG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "GRAB", "direction": "long" },
+  "HONG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "HON", "direction": "long" },
+  "KLAG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "KLAC", "direction": "long" },
+  "LULG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "LULU", "direction": "long" },
+  "NEMG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "NEM", "direction": "long" },
+  "NETG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "NET", "direction": "long" },
+  "OPEG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "OPEN", "direction": "long" },
+  "PANG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "PANW", "direction": "long" },
+  "PLUL": { "kind": "leveraged_etf", "multiple": 2, "underlying": "PLUG", "direction": "long" },
+  "PYPG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "PYPL", "direction": "long" },
+  "UNHG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "UNH", "direction": "long" },
+  "UPSG": { "kind": "leveraged_etf", "multiple": 2, "underlying": "UPS", "direction": "long" }
 }
diff --git a/config/margin_leverage_paper_proposal.json b/config/margin_leverage_paper_proposal.json
index 5e901fe..dc6f2ae 100644
--- a/config/margin_leverage_paper_proposal.json
+++ b/config/margin_leverage_paper_proposal.json
@@ -2,7 +2,7 @@
   "description": "Paper-only margin leverage (not leveraged ETFs). Enable only after margin_leverage_paper_gate GO.",
   "leverage_factor": 2.0,
   "max_gross_exposure_pct": 2.0,
-  "max_test_order_amount": 500.0,
+  "max_test_order_amount": 0.0,
   "max_orders_per_run": 2,
   "max_daily_order_amount": 1500.0,
   "max_total_positions": 6
diff --git a/config/strategy_config.json b/config/strategy_config.json
index 1cee9f4..df9681c 100644
--- a/config/strategy_config.json
+++ b/config/strategy_config.json
@@ -184,14 +184,22 @@
   "crowding_trend_gap_threshold": 0.05,
   "dynamic_universe_enabled": true,
   "dynamic_count": 50,
-  "allow_leveraged_etfs": false,
-  "leveraged_etf_allowlist": [],
-  "max_leveraged_etf_positions": 1,
+  "allow_leveraged_etfs": true,
+  "prefer_leveraged_products": true,
+  "auto_discover_leveraged_products": true,
+  "leveraged_etf_allowlist": [
+    "AAPB", "AMDL", "AMZZ", "AVGU", "BBUL", "CONL", "CRWL", "FBL",
+    "GOU", "INTW", "LNOK", "MRAL", "MSFL", "MULL", "NVDL", "PTIR", "QCML",
+    "RVNL", "TSLR", "TSMU", "AMAU", "ARMG", "ASMG", "AXPG", "BOEG",
+    "COTG", "GRAG", "HONG", "KLAG", "LULG", "NEMG", "NETG", "OPEG",
+    "PANG", "PLUL", "PYPG", "UNHG", "UPSG"
+  ],
+  "max_leveraged_etf_positions": 6,
   "max_effective_leverage_exposure_pct": 1.25,
   "block_leveraged_etfs_vix_above": 28.0,
-  "margin_leverage_paper_enabled": true,
+  "margin_leverage_paper_enabled": false,
   "margin_leverage_stress_gate_required": true,
-  "conditional_margin_leverage_enabled": true,
+  "conditional_margin_leverage_enabled": false,
   "conditional_margin_leverage_bull_factor": 2.0,
   "conditional_margin_leverage_defensive_factor": 1.0,
   "conditional_margin_leverage_vix_max": 22.0,
diff --git a/logs/crowding_paper/go_no_go_checklist.json b/logs/crowding_paper/go_no_go_checklist.json
index 201a788..a18d234 100644
--- a/logs/crowding_paper/go_no_go_checklist.json
+++ b/logs/crowding_paper/go_no_go_checklist.json
@@ -22,7 +22,7 @@
     }
   ],
   "decision": "NO_GO",
-  "generated_at": "2026-06-12T01:47:21Z",
+  "generated_at": "2026-07-14T01:46:28Z",
   "guard_impact_path": "logs/guard_impact/latest_summary.json",
   "metrics": {
     "baseline": {
diff --git a/logs/crowding_paper/reassessment.json b/logs/crowding_paper/reassessment.json
index 4146181..74efd0b 100644
--- a/logs/crowding_paper/reassessment.json
+++ b/logs/crowding_paper/reassessment.json
@@ -1,5 +1,5 @@
 {
-  "generated_at": "2026-06-12T01:47:21Z",
+  "generated_at": "2026-07-14T01:46:28Z",
   "go_no_go_path": "logs/crowding_paper/go_no_go_checklist.json",
   "live_impact_path": "logs/crowding_live/latest_summary.json",
   "decision": "NO_GO",
@@ -8,8 +8,8 @@
     "blocked_trades": 0,
     "sharpe_delta": -0.7253,
     "total_return_delta_pct": -58.3771,
-    "live_crowding_skip_count": 347,
-    "live_crowding_skip_rate_of_skips": 0.1318
+    "live_crowding_skip_count": 1163,
+    "live_crowding_skip_rate_of_skips": 0.3048
   },
   "criteria": {
     "min_live_skip_rate": 0.01,
diff --git a/logs/llm_advisory/latest_summary.json b/logs/llm_advisory/latest_summary.json
index 3c5bf1a..fa4e691 100644
--- a/logs/llm_advisory/latest_summary.json
+++ b/logs/llm_advisory/latest_summary.json
@@ -1,12 +1,12 @@
 {
-  "generated_at": "2026-06-12T01:46:11Z",
+  "generated_at": "2026-07-14T01:45:52Z",
   "audit_path": "logs/execution_audit.csv",
   "lookback_days": 90,
-  "rows": 8268,
+  "rows": 22995,
   "advisory_would_reject": 53,
-  "buy_submitted": 69,
+  "buy_submitted": 159,
   "buy_submitted_despite_llm_reject": 0,
-  "buy_blocked_by_llm": 44,
+  "buy_blocked_by_llm": 367,
   "sample_would_reject": [
     {
       "timestamp": "2026-06-01T12:32:18",
diff --git a/logs/llm_advisory/precision.json b/logs/llm_advisory/precision.json
index 2ec8688..5a40c6d 100644
--- a/logs/llm_advisory/precision.json
+++ b/logs/llm_advisory/precision.json
@@ -1,64 +1,154 @@
 {
-  "generated_at": "2026-06-12T01:46:13Z",
+  "generated_at": "2026-07-14T01:45:55Z",
   "lookback_days": 90,
   "horizon_days": 20,
   "short_horizon_days": 5,
   "price_period": "2y",
-  "audit_rows": 8268,
+  "audit_rows": 22995,
   "events_used": {
-    "llm_reject": 16,
-    "llm_accept": 96
+    "llm_reject": 135,
+    "llm_accept": 643
   },
   "events_by_type": {
-    "SKIP_BUY": 220,
-    "BUY_SUBMITTED": 12,
+    "SKIP_BUY": 1009,
+    "BUY_SUBMITTED": 17,
     "LLM_ADVISORY": 9
   },
   "forward_return": {
     "llm_reject": {
-      "n": 0,
-      "mean_return": null,
-      "median_return": null,
-      "hit_rate": null
+      "n": 40,
+      "mean_return": -0.019241089420332882,
+      "median_return": -0.002890593766865346,
+      "hit_rate": 0.5
     },
     "llm_accept": {
-      "n": 0,
-      "mean_return": null,
-      "median_return": null,
-      "hit_rate": null
+      "n": 177,
+      "mean_return": 0.014080160589787874,
+      "median_return": 0.029630863082503067,
+      "hit_rate": 0.5988700564971752
     },
-    "delta_mean_accept_minus_reject": null,
-    "delta_hit_rate_accept_minus_reject": null
+    "delta_mean_accept_minus_reject": 0.033321250010120755,
+    "delta_hit_rate_accept_minus_reject": 0.09887005649717517
   },
   "forward_return_short": {
     "llm_reject": {
-      "n": 16,
-      "mean_return": -0.021341407105715297,
-      "median_return": -0.028863523192168672,
-      "hit_rate": 0.4375
+      "n": 135,
+      "mean_return": 0.0011663794509715816,
+      "median_return": 0.005379585826590816,
+      "hit_rate": 0.5333333333333333
     },
     "llm_accept": {
-      "n": 96,
-      "mean_return": -0.012157764027584275,
-      "median_return": 0.007641977086173868,
-      "hit_rate": 0.5729166666666666
+      "n": 643,
+      "mean_return": 0.004050088866871658,
+      "median_return": 0.008216567752969306,
+      "hit_rate": 0.5707620528771384
     },
-    "delta_mean_accept_minus_reject": 0.009183643078131022,
-    "delta_hit_rate_accept_minus_reject": 0.13541666666666663
+    "delta_mean_accept_minus_reject": 0.0028837094159000765,
+    "delta_hit_rate_accept_minus_reject": 0.03742871954380511
   },
   "excluded_rows": {
     "missing_price_data": 0,
-    "insufficient_forward_bars": 217,
-    "other": 24
+    "insufficient_forward_bars": 803,
+    "other": 15
   },
   "excluded_rows_short": {
     "missing_price_data": 0,
-    "insufficient_forward_bars": 105,
-    "other": 24
+    "insufficient_forward_bars": 242,
+    "other": 15
   },
-  "sample": [],
+  "sample": [
+    {
+      "ticker": "AAPL",
+      "timestamp": "2026-05-27T17:58:55Z",
+      "llm_side": "ACCEPT",
+      "forward_return": -0.11484642594841332
+    },
+    {
+      "ticker": "AAPL",
+      "timestamp": "2026-05-29T11:52:51Z",
+      "llm_side": "ACCEPT",
+      "forward_return": -0.09716082664047854
+    },
+    {
+      "ticker": "HOOD",
+      "timestamp": "2026-06-01T12:32:18Z",
+      "llm_side": "REJECT",
+      "forward_return": 0.10525730264544819
+    },
+    {
+      "ticker": "ORCL",
+      "timestamp": "2026-06-01T12:49:39Z",
+      "llm_side": "REJECT",
+      "forward_return": -0.4094297571875566
+    },
+    {
+      "ticker": "SMCI",
+      "timestamp": "2026-06-01T12:50:47Z",
+      "llm_side": "REJECT",
+      "forward_return": -0.37436008414141364
+    },
+    {
+      "ticker": "PATH",
+      "timestamp": "2026-06-01T12:51:19Z",
+      "llm_side": "REJECT",
+      "forward_return": -0.17022904053232213
+    },
+    {
+      "ticker": "GM",
+      "timestamp": "2026-06-01T12:52:26Z",
+      "llm_side": "REJECT",
+      "forward_return": -0.06571016682429232
+    },
+    {
+      "ticker": "AAL",
+      "timestamp": "2026-06-01T12:59:06Z",
+      "llm_side": "REJECT",
+      "forward_return": 0.2601115413212314
+    },
+    {
+      "ticker": "QQQ",
+      "timestamp": "2026-06-01T13:00:40Z",
+      "llm_side": "REJECT",
+      "forward_return": -0.007446386853765863
+    },
+    {
+      "ticker": "NKE",
+      "timestamp": "2026-06-01T13:06:20Z",
+      "llm_side": "REJECT",
+      "forward_return": -0.10624866178294612
+    },
+    {
+      "ticker": "SOFI",
+      "timestamp": "2026-06-01T13:08:55Z",
+      "llm_side": "ACCEPT",
+      "forward_return": -0.0349838332184782
+    },
+    {
+      "ticker": "GE",
+      "timestamp": "2026-06-01T13:08:55Z",
+      "llm_side": "ACCEPT",
+      "forward_return": 0.1513555501983339
+    },
+    {
+      "ticker": "PFE",
+      "timestamp": "2026-06-01T13:08:55Z",
+      "llm_side": "ACCEPT",
+      "forward_return": -0.06047597689481121
+    },
+    {
+      "ticker": "MDB",
+      "timestamp": "2026-06-01T13:08:55Z",
+      "llm_side": "ACCEPT",
+      "forward_return": -0.1683173471438697
+    },
+    {
+      "ticker": "LIN",
+      "timestamp": "2026-06-01T13:08:55Z",
+      "llm_side": "ACCEPT",
+      "forward_return": 0.04658330580131942
+    }
+  ],
   "notes": [
-    "events_used counts matured forward returns at the 5d horizon (shortest configured); primary-horizon stats fill in as events age.",
-    "One side has zero usable forward returns at the primary horizon; increase lookback or accumulate more advisory decisions."
+    "events_used counts matured forward returns at the 5d horizon (shortest configured); primary-horizon stats fill in as events age."
   ]
 }
\ No newline at end of file
diff --git a/logs/paper_validation/history.jsonl b/logs/paper_validation/history.jsonl
index 6f3a5db..2c69339 100644
--- a/logs/paper_validation/history.jsonl
+++ b/logs/paper_validation/history.jsonl
@@ -7,3 +7,25 @@
 {"agreement_pct": 64.4, "buy_submitted": 61, "date": "2026-06-10", "generated_at": "2026-06-10T01:46:08Z", "rank_calendar_days": 9, "rank_gate_ready": false, "skip_ai_score": 28, "skip_llm_block": 34, "skip_rank_gate": 241}
 {"agreement_pct": 64.5, "buy_submitted": 61, "date": "2026-06-11", "generated_at": "2026-06-11T01:46:24Z", "rank_calendar_days": 10, "rank_gate_ready": false, "skip_ai_score": 58, "skip_llm_block": 36, "skip_rank_gate": 304}
 {"agreement_pct": 62.0, "buy_submitted": 69, "date": "2026-06-12", "generated_at": "2026-06-12T01:46:14Z", "rank_calendar_days": 11, "rank_gate_ready": false, "skip_ai_score": 80, "skip_llm_block": 44, "skip_rank_gate": 363}
+{"agreement_pct": 59.9, "buy_submitted": 69, "date": "2026-06-13", "generated_at": "2026-06-13T01:46:28Z", "rank_calendar_days": 12, "rank_gate_ready": false, "skip_ai_score": 85, "skip_llm_block": 44, "skip_rank_gate": 430}
+{"agreement_pct": 57.8, "buy_submitted": 72, "date": "2026-06-16", "generated_at": "2026-06-16T01:48:29Z", "rank_calendar_days": 14, "rank_gate_ready": true, "skip_ai_score": 85, "skip_llm_block": 86, "skip_rank_gate": 585}
+{"agreement_pct": 57.8, "buy_submitted": 73, "date": "2026-06-17", "generated_at": "2026-06-17T01:49:43Z", "rank_calendar_days": 15, "rank_gate_ready": true, "skip_ai_score": 85, "skip_llm_block": 100, "skip_rank_gate": 700}
+{"agreement_pct": 56.4, "buy_submitted": 73, "date": "2026-06-18", "generated_at": "2026-06-18T01:52:18Z", "rank_calendar_days": 16, "rank_gate_ready": true, "skip_ai_score": 85, "skip_llm_block": 114, "skip_rank_gate": 840}
+{"agreement_pct": 55.5, "buy_submitted": 74, "date": "2026-06-19", "generated_at": "2026-06-19T01:51:59Z", "rank_calendar_days": 17, "rank_gate_ready": true, "skip_ai_score": 91, "skip_llm_block": 130, "skip_rank_gate": 990}
+{"agreement_pct": 55.0, "buy_submitted": 74, "date": "2026-06-20", "generated_at": "2026-06-20T01:53:01Z", "rank_calendar_days": 18, "rank_gate_ready": true, "skip_ai_score": 101, "skip_llm_block": 138, "skip_rank_gate": 1116}
+{"agreement_pct": 54.4, "buy_submitted": 74, "date": "2026-06-23", "generated_at": "2026-06-23T01:52:41Z", "rank_calendar_days": 20, "rank_gate_ready": true, "skip_ai_score": 113, "skip_llm_block": 155, "skip_rank_gate": 1292}
+{"agreement_pct": 54.3, "buy_submitted": 82, "date": "2026-06-24", "generated_at": "2026-06-24T01:52:31Z", "rank_calendar_days": 21, "rank_gate_ready": true, "skip_ai_score": 116, "skip_llm_block": 160, "skip_rank_gate": 1484}
+{"agreement_pct": 54.4, "buy_submitted": 88, "date": "2026-06-25", "generated_at": "2026-06-25T01:50:06Z", "rank_calendar_days": 22, "rank_gate_ready": true, "skip_ai_score": 119, "skip_llm_block": 163, "skip_rank_gate": 1620}
+{"agreement_pct": 54.9, "buy_submitted": 93, "date": "2026-06-26", "generated_at": "2026-06-26T01:49:40Z", "rank_calendar_days": 23, "rank_gate_ready": true, "skip_ai_score": 119, "skip_llm_block": 168, "skip_rank_gate": 1731}
+{"agreement_pct": 54.5, "buy_submitted": 96, "date": "2026-06-27", "generated_at": "2026-06-27T01:49:20Z", "rank_calendar_days": 24, "rank_gate_ready": true, "skip_ai_score": 119, "skip_llm_block": 175, "skip_rank_gate": 1815}
+{"agreement_pct": 55.3, "buy_submitted": 98, "date": "2026-06-30", "generated_at": "2026-06-30T01:50:03Z", "rank_calendar_days": 26, "rank_gate_ready": true, "skip_ai_score": 123, "skip_llm_block": 177, "skip_rank_gate": 1881}
+{"agreement_pct": 54.8, "buy_submitted": 107, "date": "2026-07-01", "generated_at": "2026-07-01T01:50:08Z", "rank_calendar_days": 27, "rank_gate_ready": true, "skip_ai_score": 133, "skip_llm_block": 189, "skip_rank_gate": 1989}
+{"agreement_pct": 55.1, "buy_submitted": 112, "date": "2026-07-02", "generated_at": "2026-07-02T01:49:15Z", "rank_calendar_days": 28, "rank_gate_ready": true, "skip_ai_score": 147, "skip_llm_block": 200, "skip_rank_gate": 2081}
+{"agreement_pct": 55.1, "buy_submitted": 115, "date": "2026-07-03", "generated_at": "2026-07-03T01:50:32Z", "rank_calendar_days": 29, "rank_gate_ready": true, "skip_ai_score": 152, "skip_llm_block": 201, "skip_rank_gate": 2121}
+{"agreement_pct": 54.8, "buy_submitted": 115, "date": "2026-07-04", "generated_at": "2026-07-04T01:49:46Z", "rank_calendar_days": 29, "rank_gate_ready": true, "skip_ai_score": 152, "skip_llm_block": 201, "skip_rank_gate": 2121}
+{"agreement_pct": 55.4, "buy_submitted": 125, "date": "2026-07-07", "generated_at": "2026-07-07T01:49:05Z", "rank_calendar_days": 31, "rank_gate_ready": true, "skip_ai_score": 164, "skip_llm_block": 210, "skip_rank_gate": 2215}
+{"agreement_pct": 54.4, "buy_submitted": 134, "date": "2026-07-08", "generated_at": "2026-07-08T01:51:18Z", "rank_calendar_days": 32, "rank_gate_ready": true, "skip_ai_score": 182, "skip_llm_block": 235, "skip_rank_gate": 2309}
+{"agreement_pct": 53.8, "buy_submitted": 139, "date": "2026-07-09", "generated_at": "2026-07-09T01:53:00Z", "rank_calendar_days": 33, "rank_gate_ready": true, "skip_ai_score": 193, "skip_llm_block": 265, "skip_rank_gate": 2445}
+{"agreement_pct": 53.1, "buy_submitted": 144, "date": "2026-07-10", "generated_at": "2026-07-10T01:50:41Z", "rank_calendar_days": 34, "rank_gate_ready": true, "skip_ai_score": 196, "skip_llm_block": 286, "skip_rank_gate": 2488}
+{"agreement_pct": 52.7, "buy_submitted": 147, "date": "2026-07-11", "generated_at": "2026-07-11T01:52:24Z", "rank_calendar_days": 35, "rank_gate_ready": true, "skip_ai_score": 200, "skip_llm_block": 306, "skip_rank_gate": 2551}
+{"agreement_pct": 51.6, "buy_submitted": 159, "date": "2026-07-14", "generated_at": "2026-07-14T01:45:55Z", "rank_calendar_days": 37, "rank_gate_ready": true, "skip_ai_score": 211, "skip_llm_block": 367, "skip_rank_gate": 2624}
diff --git a/logs/paper_validation/latest_summary.json b/logs/paper_validation/latest_summary.json
index abf5a57..f0c25ec 100644
--- a/logs/paper_validation/latest_summary.json
+++ b/logs/paper_validation/latest_summary.json
@@ -1,22 +1,22 @@
 {
-  "generated_at": "2026-06-12T01:46:14Z",
+  "generated_at": "2026-07-14T01:45:55Z",
   "lookback_days": 90,
   "llm_advisory_only": false,
   "rank_ai_buy_gate_enabled": true,
   "llm_ai_agreement": {
-    "generated_at": "2026-06-12T01:46:14Z",
+    "generated_at": "2026-07-14T01:45:55Z",
     "ai_score_buy_threshold": 0.4,
     "llm_cache_path": "data/llm_cache.json",
-    "llm_cache_entries": 186,
-    "comparable_with_ai_score": 184,
-    "agreement_rate": 0.6195652173913043,
-    "agreement_pct": 62.0,
-    "score_llm_corr": -0.09841380779514758,
+    "llm_cache_entries": 827,
+    "comparable_with_ai_score": 730,
+    "agreement_rate": 0.5164383561643836,
+    "agreement_pct": 51.6,
+    "score_llm_corr": -0.024016064467121196,
     "confusion": {
-      "both_pass": 114,
-      "both_fail": 0,
-      "ai_pass_llm_reject": 66,
-      "ai_fail_llm_pass": 4
+      "both_pass": 375,
+      "both_fail": 2,
+      "ai_pass_llm_reject": 347,
+      "ai_fail_llm_pass": 6
     },
     "disagreements_sample": [
       {
@@ -47,157 +47,157 @@
         "llm_category": "Guidance"
       },
       {
-        "ticker": "UNH",
-        "date": "2026-06-01",
-        "ai_score": 0.9256,
+        "ticker": "BRK-B",
+        "date": "2026-07-14",
+        "ai_score": 0.9422,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Fraud"
+        "llm_category": "Guidance"
       },
       {
-        "ticker": "CRM",
-        "date": "2026-06-11",
-        "ai_score": 0.921,
+        "ticker": "BRK-B",
+        "date": "2026-07-02",
+        "ai_score": 0.9322,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Guidance"
+        "llm_category": "Other"
       },
       {
-        "ticker": "UPS",
-        "date": "2026-06-11",
-        "ai_score": 0.9161,
+        "ticker": "UNH",
+        "date": "2026-06-01",
+        "ai_score": 0.9256,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Guidance"
+        "llm_category": "Fraud"
       },
       {
-        "ticker": "ANET",
-        "date": "2026-06-11",
-        "ai_score": 0.8941,
+        "ticker": "XLF",
+        "date": "2026-07-09",
+        "ai_score": 0.921,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Other (Operational/Supply Chain)"
+        "llm_category": "Other"
       },
       {
-        "ticker": "PLTR",
+        "ticker": "CRM",
         "date": "2026-06-11",
-        "ai_score": 0.8854,
+        "ai_score": 0.921,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Product Failure"
+        "llm_category": "Guidance"
       },
       {
-        "ticker": "FCX",
-        "date": "2026-06-08",
-        "ai_score": 0.8854,
+        "ticker": "BRK-B",
+        "date": "2026-06-16",
+        "ai_score": 0.9166,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Guidance"
+        "llm_category": "Financials"
       },
       {
-        "ticker": "HD",
-        "date": "2026-06-08",
-        "ai_score": 0.8846,
+        "ticker": "UPS",
+        "date": "2026-06-11",
+        "ai_score": 0.9161,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
         "llm_category": "Guidance"
       },
       {
-        "ticker": "WFC",
-        "date": "2026-06-08",
-        "ai_score": 0.8623,
+        "ticker": "DUK",
+        "date": "2026-06-25",
+        "ai_score": 0.9146,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Other"
+        "llm_category": "Guidance"
       },
       {
-        "ticker": "NKE",
-        "date": "2026-06-11",
-        "ai_score": 0.8124,
+        "ticker": "LMT",
+        "date": "2026-06-15",
+        "ai_score": 0.8996,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Guidance"
+        "llm_category": "Other"
       },
       {
-        "ticker": "MRK",
-        "date": "2026-06-02",
-        "ai_score": 0.7978,
+        "ticker": "BRK-B",
+        "date": "2026-06-19",
+        "ai_score": 0.8978,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
         "llm_category": "Other"
       },
       {
-        "ticker": "TSLA",
-        "date": "2026-06-11",
-        "ai_score": 0.795,
+        "ticker": "XLF",
+        "date": "2026-06-20",
+        "ai_score": 0.8971,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Guidance"
+        "llm_category": "None"
       },
       {
-        "ticker": "TGT",
-        "date": "2026-06-08",
-        "ai_score": 0.7943,
+        "ticker": "WBD",
+        "date": "2026-07-14",
+        "ai_score": 0.8961,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Other"
+        "llm_category": "Lawsuit"
       },
       {
-        "ticker": "ONDS",
-        "date": "2026-06-10",
-        "ai_score": 0.7864,
+        "ticker": "BRK-B",
+        "date": "2026-07-08",
+        "ai_score": 0.8948,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
         "llm_category": "Financials"
       },
       {
-        "ticker": "QQQ",
-        "date": "2026-06-01",
-        "ai_score": 0.7855,
+        "ticker": "ANET",
+        "date": "2026-06-11",
+        "ai_score": 0.8941,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Other (Concentration risk/Correlation)."
+        "llm_category": "Other (Operational/Supply Chain)"
       },
       {
-        "ticker": "LYG",
-        "date": "2026-06-11",
-        "ai_score": 0.7827,
+        "ticker": "XLF",
+        "date": "2026-07-01",
+        "ai_score": 0.8883,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Other"
+        "llm_category": "None"
       },
       {
-        "ticker": "IWM",
-        "date": "2026-06-08",
-        "ai_score": 0.7476,
+        "ticker": "PLTR",
+        "date": "2026-06-11",
+        "ai_score": 0.8854,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Other"
+        "llm_category": "Product Failure"
       },
       {
-        "ticker": "SOFI",
+        "ticker": "FCX",
         "date": "2026-06-08",
-        "ai_score": 0.7474,
+        "ai_score": 0.8854,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Lawsuit"
+        "llm_category": "Guidance"
       }
     ],
     "llm_advisory_audit_rows": 53,
@@ -207,20 +207,76 @@
     ],
     "candidate_buy": {
       "path": "logs/candidate_cache/latest_buy.csv",
-      "as_of_date": "2026-06-12",
-      "buy_signal_rows": 74,
-      "in_llm_cache": 4,
-      "agreement_rate": 0.75,
+      "as_of_date": "2026-07-14",
+      "buy_signal_rows": 82,
+      "in_llm_cache": 14,
+      "agreement_rate": 0.42857142857142855,
       "confusion": {
-        "both_pass": 3,
-        "both_fail": 0,
-        "ai_pass_llm_reject": 1,
+        "both_pass": 5,
+        "both_fail": 1,
+        "ai_pass_llm_reject": 8,
         "ai_fail_llm_pass": 0
       },
       "disagreements": [
         {
-          "ticker": "LYG",
-          "ai_score": 0.6569835277327515,
+          "ticker": "NEE",
+          "ai_score": 0.7975490409257358,
+          "ai_ok": true,
+          "llm_ok": false,
+          "agree": false,
+          "in_llm_cache": true
+        },
+        {
+          "ticker": "MARA",
+          "ai_score": 0.6459456766667171,
+          "ai_ok": true,
+          "llm_ok": false,
+          "agree": false,
+          "in_llm_cache": true
+        },
+        {
+          "ticker": "SNPS",
+          "ai_score": 0.7263089324242059,
+          "ai_ok": true,
+          "llm_ok": false,
+          "agree": false,
+          "in_llm_cache": true
+        },
+        {
+          "ticker": "GM",
+          "ai_score": 0.692266431386092,
+          "ai_ok": true,
+          "llm_ok": false,
+          "agree": false,
+          "in_llm_cache": true
+        },
+        {
+          "ticker": "WBD",
+          "ai_score": 0.8458966368426794,
+          "ai_ok": true,
+          "llm_ok": false,
+          "agree": false,
+          "in_llm_cache": true
+        },
+        {
+          "ticker": "COST",
+          "ai_score": 0.6828158091160799,
+          "ai_ok": true,
+          "llm_ok": false,
+          "agree": false,
+          "in_llm_cache": true
+        },
+        {
+          "ticker": "VZ",
+          "ai_score": 0.6282251235831854,
+          "ai_ok": true,
+          "llm_ok": false,
+          "agree": false,
+          "in_llm_cache": true
+        },
+        {
+          "ticker": "BRK-B",
+          "ai_score": 0.9421610130784204,
           "ai_ok": true,
           "llm_ok": false,
           "agree": false,
@@ -230,14 +286,14 @@
     }
   },
   "llm_advisory_impact": {
-    "generated_at": "2026-06-12T01:46:14Z",
+    "generated_at": "2026-07-14T01:45:56Z",
     "audit_path": "logs/execution_audit.csv",
     "lookback_days": 90,
-    "rows": 8268,
+    "rows": 22995,
     "advisory_would_reject": 53,
-    "buy_submitted": 69,
+    "buy_submitted": 159,
     "buy_submitted_despite_llm_reject": 0,
-    "buy_blocked_by_llm": 44,
+    "buy_blocked_by_llm": 367,
     "sample_would_reject": [
       {
         "timestamp": "2026-06-01T12:32:18",
@@ -637,151 +693,151 @@
     ]
   },
   "audit_buy_paths": {
-    "rows": 8268,
+    "rows": 22995,
     "llm_advisory_only": false,
     "ai_score_buy_threshold": 0.4,
-    "skip_buy_total": 7544,
+    "skip_buy_total": 21689,
     "skip_by_layer": {
-      "other": 7056,
-      "ai_score": 80,
-      "llm_block": 44,
-      "rank_gate": 363,
-      "rank_missing": 1
+      "other": 18462,
+      "ai_score": 211,
+      "llm_block": 367,
+      "rank_gate": 2624,
+      "rank_missing": 25
     },
-    "skip_ai_score_layer": 80,
-    "skip_llm_block_layer": 44,
-    "skip_rank_gate_layer": 363,
-    "skip_rank_missing_layer": 1,
-    "skip_other_layer": 7056,
-    "ai_pass_llm_block": 44,
-    "ai_fail_or_low_score": 595,
-    "buy_submitted": 69,
-    "buy_submitted_llm_accept": 40,
+    "skip_ai_score_layer": 211,
+    "skip_llm_block_layer": 367,
+    "skip_rank_gate_layer": 2624,
+    "skip_rank_missing_layer": 25,
+    "skip_other_layer": 18462,
+    "ai_pass_llm_block": 364,
+    "ai_fail_or_low_score": 1499,
+    "buy_submitted": 159,
+    "buy_submitted_llm_accept": 51,
     "buy_submitted_llm_reject_verdict": 0,
-    "buy_submitted_no_llm_verdict": 29,
+    "buy_submitted_no_llm_verdict": 108,
     "llm_advisory_would_reject_ai_passed": 53,
     "interpretation": "Blocking mode (llm_advisory_only=false): ai_pass_llm_block counts SKIP_BUY where AI score passed but LLM blocked. submitted_llm_reject_verdict should be ~0."
   },
   "rank_gate_paper_tracker": {
     "min_calendar_days_required": 14,
-    "calendar_days_with_rank_events": 11,
-    "audit_span_calendar_days": 17,
+    "calendar_days_with_rank_events": 37,
+    "audit_span_calendar_days": 49,
     "first_date": "2026-05-27",
-    "last_date": "2026-06-12",
-    "total_skip_buy_rank_blocked": 363,
-    "total_skip_buy_rank_missing": 1,
-    "total_buy_submitted": 69,
-    "gate_ready": false,
+    "last_date": "2026-07-14",
+    "total_skip_buy_rank_blocked": 2624,
+    "total_skip_buy_rank_missing": 25,
+    "total_buy_submitted": 159,
+    "gate_ready": true,
     "daily_tail": [
       {
-        "date": "2026-05-28",
-        "events": 652,
-        "skip_buy": 631,
-        "rank_blocked": 0,
+        "date": "2026-06-29",
+        "events": 384,
+        "skip_buy": 365,
+        "rank_blocked": 22,
         "rank_missing": 0,
-        "buy_submitted": 0
+        "buy_submitted": 1
       },
       {
-        "date": "2026-05-29",
-        "events": 328,
-        "skip_buy": 258,
-        "rank_blocked": 0,
+        "date": "2026-06-30",
+        "events": 637,
+        "skip_buy": 601,
+        "rank_blocked": 79,
         "rank_missing": 0,
         "buy_submitted": 7
       },
       {
-        "date": "2026-05-30",
-        "events": 136,
-        "skip_buy": 129,
-        "rank_blocked": 0,
+        "date": "2026-07-01",
+        "events": 635,
+        "skip_buy": 598,
+        "rank_blocked": 114,
         "rank_missing": 0,
-        "buy_submitted": 0
+        "buy_submitted": 5
       },
       {
-        "date": "2026-06-01",
-        "events": 2381,
-        "skip_buy": 2136,
-        "rank_blocked": 0,
+        "date": "2026-07-02",
+        "events": 629,
+        "skip_buy": 598,
+        "rank_blocked": 69,
         "rank_missing": 0,
-        "buy_submitted": 20
+        "buy_submitted": 5
       },
       {
-        "date": "2026-06-02",
-        "events": 961,
-        "skip_buy": 883,
-        "rank_blocked": 47,
-        "rank_missing": 0,
-        "buy_submitted": 15
+        "date": "2026-07-03",
+        "events": 634,
+        "skip_buy": 621,
+        "rank_blocked": 22,
+        "rank_missing": 1,
+        "buy_submitted": 1
       },
       {
-        "date": "2026-06-03",
-        "events": 390,
-        "skip_buy": 380,
+        "date": "2026-07-04",
+        "events": 257,
+        "skip_buy": 250,
         "rank_blocked": 0,
         "rank_missing": 0,
         "buy_submitted": 0
       },
       {
-        "date": "2026-06-04",
-        "events": 382,
-        "skip_buy": 370,
-        "rank_blocked": 20,
-        "rank_missing": 0,
-        "buy_submitted": 4
+        "date": "2026-07-06",
+        "events": 392,
+        "skip_buy": 364,
+        "rank_blocked": 48,
+        "rank_missing": 3,
+        "buy_submitted": 5
       },
       {
-        "date": "2026-06-05",
-        "events": 411,
-        "skip_buy": 373,
-        "rank_blocked": 0,
-        "rank_missing": 0,
-        "buy_submitted": 5
+        "date": "2026-07-07",
+        "events": 654,
+        "skip_buy": 611,
+        "rank_blocked": 72,
+        "rank_missing": 5,
+        "buy_submitted": 10
       },
       {
-        "date": "2026-06-06",
-        "events": 262,
-        "skip_buy": 254,
-        "rank_blocked": 0,
-        "rank_missing": 0,
-        "buy_submitted": 0
+        "date": "2026-07-08",
+        "events": 626,
+        "skip_buy": 608,
+        "rank_blocked": 107,
+        "rank_missing": 4,
+        "buy_submitted": 7
       },
       {
-        "date": "2026-06-08",
-        "events": 612,
-        "skip_buy": 511,
-        "rank_blocked": 35,
-        "rank_missing": 0,
-        "buy_submitted": 8
+        "date": "2026-07-09",
+        "events": 630,
+        "skip_buy": 617,
+        "rank_blocked": 114,
+        "rank_missing": 4,
+        "buy_submitted": 4
       },
       {
-        "date": "2026-06-09",
-        "events": 523,
-        "skip_buy": 495,
-        "rank_blocked": 92,
-        "rank_missing": 0,
-        "buy_submitted": 0
+        "date": "2026-07-10",
+        "events": 634,
+        "skip_buy": 614,
+        "rank_blocked": 39,
+        "rank_missing": 2,
+        "buy_submitted": 5
       },
       {
-        "date": "2026-06-10",
-        "events": 372,
-        "skip_buy": 371,
-        "rank_blocked": 67,
-        "rank_missing": 0,
-        "buy_submitted": 0
+        "date": "2026-07-11",
+        "events": 254,
+        "skip_buy": 248,
+        "rank_blocked": 50,
+        "rank_missing": 2,
+        "buy_submitted": 1
       },
       {
-        "date": "2026-06-11",
-        "events": 439,
-        "skip_buy": 371,
-        "rank_blocked": 53,
-        "rank_missing": 1,
-        "buy_submitted": 7
+        "date": "2026-07-13",
+        "events": 793,
+        "skip_buy": 734,
+        "rank_blocked": 59,
+        "rank_missing": 0,
+        "buy_submitted": 11
       },
       {
-        "date": "2026-06-12",
-        "events": 267,
-        "skip_buy": 257,
-        "rank_blocked": 49,
+        "date": "2026-07-14",
+        "events": 397,
+        "skip_buy": 384,
+        "rank_blocked": 14,
         "rank_missing": 0,
         "buy_submitted": 1
       }
diff --git a/logs/paper_validation/trend_summary.json b/logs/paper_validation/trend_summary.json
index 7df39a9..50aa45d 100644
--- a/logs/paper_validation/trend_summary.json
+++ b/logs/paper_validation/trend_summary.json
@@ -1,85 +1,82 @@
 {
-  "generated_at": "2026-06-12T03:58:39Z",
+  "generated_at": "2026-07-14T01:45:57Z",
   "history_path": "logs/paper_validation/history.jsonl",
-  "rows": 9,
+  "rows": 31,
   "rolling_days": 7,
   "latest": {
-    "date": "2026-06-12",
-    "agreement_pct": 62.0,
-    "skip_ai_score": 80,
-    "skip_llm_block": 44,
-    "skip_rank_gate": 363,
-    "buy_submitted": 69,
-    "rank_calendar_days": 11,
-    "rank_gate_ready": false
+    "date": "2026-07-14",
+    "agreement_pct": 51.6,
+    "skip_ai_score": 211,
+    "skip_llm_block": 367,
+    "skip_rank_gate": 2624,
+    "buy_submitted": 159,
+    "rank_calendar_days": 37,
+    "rank_gate_ready": true
   },
   "rolling": {
-    "agreement_pct_mean": 66.14285714285714,
-    "skip_ai_score_mean": 35.142857142857146,
-    "skip_llm_block_mean": 27.571428571428573,
-    "skip_rank_gate_mean": 183.42857142857142,
-    "buy_submitted_mean": 57.285714285714285
+    "agreement_pct_mean": 53.68571428571429,
+    "skip_ai_score_mean": 185.42857142857142,
+    "skip_llm_block_mean": 267.14285714285717,
+    "skip_rank_gate_mean": 2393.285714285714,
+    "buy_submitted_mean": 137.57142857142858
   },
-  "alerts": [
-    "skip_llm_block_spike",
-    "skip_rank_gate_spike"
-  ],
+  "alerts": [],
   "tail": [
     {
-      "date": "2026-06-04",
-      "agreement_pct": 69.2,
-      "skip_llm_block": 15,
-      "skip_rank_gate": 67,
-      "buy_submitted": 48,
-      "rank_gate_ready": false
+      "date": "2026-07-04",
+      "agreement_pct": 54.8,
+      "skip_llm_block": 201,
+      "skip_rank_gate": 2121,
+      "buy_submitted": 115,
+      "rank_gate_ready": true
     },
     {
-      "date": "2026-06-05",
-      "agreement_pct": 69.2,
-      "skip_llm_block": 15,
-      "skip_rank_gate": 67,
-      "buy_submitted": 48,
-      "rank_gate_ready": false
+      "date": "2026-07-07",
+      "agreement_pct": 55.4,
+      "skip_llm_block": 210,
+      "skip_rank_gate": 2215,
+      "buy_submitted": 125,
+      "rank_gate_ready": true
     },
     {
-      "date": "2026-06-06",
-      "agreement_pct": 69.2,
-      "skip_llm_block": 15,
-      "skip_rank_gate": 67,
-      "buy_submitted": 53,
-      "rank_gate_ready": false
+      "date": "2026-07-08",
+      "agreement_pct": 54.4,
+      "skip_llm_block": 235,
+      "skip_rank_gate": 2309,
+      "buy_submitted": 134,
+      "rank_gate_ready": true
     },
     {
-      "date": "2026-06-09",
-      "agreement_pct": 64.5,
-      "skip_llm_block": 34,
-      "skip_rank_gate": 175,
-      "buy_submitted": 61,
-      "rank_gate_ready": false
+      "date": "2026-07-09",
+      "agreement_pct": 53.8,
+      "skip_llm_block": 265,
+      "skip_rank_gate": 2445,
+      "buy_submitted": 139,
+      "rank_gate_ready": true
     },
     {
-      "date": "2026-06-10",
-      "agreement_pct": 64.4,
-      "skip_llm_block": 34,
-      "skip_rank_gate": 241,
-      "buy_submitted": 61,
-      "rank_gate_ready": false
+      "date": "2026-07-10",
+      "agreement_pct": 53.1,
+      "skip_llm_block": 286,
+      "skip_rank_gate": 2488,
+      "buy_submitted": 144,
+      "rank_gate_ready": true
     },
     {
-      "date": "2026-06-11",
-      "agreement_pct": 64.5,
-      "skip_llm_block": 36,
-      "skip_rank_gate": 304,
-      "buy_submitted": 61,
-      "rank_gate_ready": false
+      "date": "2026-07-11",
+      "agreement_pct": 52.7,
+      "skip_llm_block": 306,
+      "skip_rank_gate": 2551,
+      "buy_submitted": 147,
+      "rank_gate_ready": true
     },
     {
-      "date": "2026-06-12",
-      "agreement_pct": 62.0,
-      "skip_llm_block": 44,
-      "skip_rank_gate": 363,
-      "buy_submitted": 69,
-      "rank_gate_ready": false
+      "date": "2026-07-14",
+      "agreement_pct": 51.6,
+      "skip_llm_block": 367,
+      "skip_rank_gate": 2624,
+      "buy_submitted": 159,
+      "rank_gate_ready": true
     }
   ]
 }
\ No newline at end of file
diff --git a/scripts/llm_retro_scoring.py b/scripts/llm_retro_scoring.py
index d5db553..f97d37b 100644
--- a/scripts/llm_retro_scoring.py
+++ b/scripts/llm_retro_scoring.py
@@ -18,12 +18,14 @@ Work is ordered by date so partial runs still yield complete cross-sections.
 
 Usage:
   .venv/bin/python -m scripts.llm_retro_scoring --months 6 --max-calls 1000
+  .venv/bin/python -m scripts.llm_retro_scoring --provider vllm --max-calls 500
 """
 
 from __future__ import annotations
 
 import argparse
 import json
+import os
 import re
 import time
 from datetime import datetime, timezone
@@ -108,19 +110,32 @@ def _build_work_items(tickers: list[str], cutoff: pd.Timestamp) -> list[dict]:
     return items
 
 
-def _score_item(item: dict, *, model: str | None = None) -> dict:
+def _score_item(
+    item: dict,
+    *,
+    model: str | None = None,
+    provider: str = "auto",
+) -> dict:
     from src.llm_analyst import _generate_llm_text_with_provider, parse_llm_decision
+    from src.llm_vllm import vllm_model_name
 
     news_context = "\n".join(f"- {h}" for h in item["headlines"])
     prompt = PROMPT_TEMPLATE.format(
         ticker=item["ticker"], date=item["date"], news_context=news_context
     )
-    text, provider = _generate_llm_text_with_provider(prompt, model=model)
+    force_provider = provider if provider != "auto" else None
+    text, used_provider = _generate_llm_text_with_provider(
+        prompt, model=model, force_provider=force_provider
+    )
     approved, category, reason = parse_llm_decision(text)
     outlook = None
     match = _OUTLOOK_RE.search(text)
     if match:
         outlook = max(-5, min(5, int(match.group(1))))
+    if used_provider == "vllm":
+        model_name = model or vllm_model_name()
+    else:
+        model_name = model or "default"
     return {
         "key": f"{item['ticker']}_{item['date']}",
         "ticker": item["ticker"],
@@ -129,8 +144,8 @@ def _score_item(item: dict, *, model: str | None = None) -> dict:
         "category": category,
         "outlook": outlook,
         "n_headlines": len(item["headlines"]),
-        "provider": provider,
-        "model": model or "default",
+        "provider": used_provider,
+        "model": model_name,
         "reason": reason,
         "scored_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
     }
@@ -144,19 +159,42 @@ def main() -> None:
     ap.add_argument("--tickers", default="", help="comma-separated subset (default: all)")
     ap.add_argument(
         "--model",
-        default="gemini-2.5-flash-lite",
-        help="Gemini model; per-model free-tier quota is separate from the live "
-        "veto's gemini-2.5-flash, so the default avoids starving live trading",
+        default="",
+        help="LLM model id (Gemini model name or vLLM served-model-name). "
+        "Default: gemini-2.5-flash-lite for auto/gemini, LLM_VLLM_MODEL for vllm",
+    )
+    ap.add_argument(
+        "--provider",
+        choices=("auto", "gemini", "vllm"),
+        default="auto",
+        help="LLM backend: auto (Gemini then vLLM fallback), gemini, or vllm only",
+    )
+    ap.add_argument(
+        "--vllm-url",
+        default="http://192.168.219.116:11434/v1",
+        help="OpenAI-compatible vLLM base URL when --provider vllm",
     )
     args = ap.parse_args()
 
+    if args.provider == "vllm":
+        os.environ.setdefault("LLM_VLLM_ENABLED", "1")
+        os.environ.setdefault("LLM_VLLM_BASE_URL", args.vllm_url.rstrip("/"))
+
     import src.config  # noqa: F401  (load_dotenv side effect for GEMINI_API_KEY)
     from src.llm_analyst import llm_backend_available
+    from src.llm_vllm import vllm_base_url, vllm_model_name
     from src.settings import load_settings
 
-    if not llm_backend_available():
+    if args.provider == "vllm":
+        if not vllm_base_url():
+            raise SystemExit("vLLM base URL missing (set LLM_VLLM_BASE_URL or --vllm-url)")
+    elif not llm_backend_available():
         raise SystemExit("No LLM backend available (GEMINI_API_KEY / vLLM missing)")
 
+    model = args.model.strip() or None
+    if model is None and args.provider in {"auto", "gemini"}:
+        model = "gemini-2.5-flash-lite"
+
     if args.tickers:
         tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
     else:
@@ -170,9 +208,13 @@ def main() -> None:
         for it in _build_work_items(tickers, cutoff)
         if f"{it['ticker']}_{it['date']}" not in scored
     ]
+    backend = args.provider
+    if backend == "vllm":
+        backend = f"vllm ({vllm_model_name()} @ {vllm_base_url()})"
     print(
         f"Work: {len(items):,} unscored ticker-days (cutoff {cutoff.date()}, "
-        f"already scored {len(scored):,}); this run caps at {args.max_calls:,} calls"
+        f"already scored {len(scored):,}); backend={backend}; "
+        f"this run caps at {args.max_calls:,} calls"
     )
 
     done = failures = consecutive_failures = 0
@@ -182,7 +224,7 @@ def main() -> None:
             if done + failures >= args.max_calls:
                 break
             try:
-                record = _score_item(item, model=args.model)
+                record = _score_item(item, model=model, provider=args.provider)
                 consecutive_failures = 0
             except Exception as exc:
                 failures += 1
diff --git a/scripts/run_weekly_gap_attribution.sh b/scripts/run_weekly_gap_attribution.sh
old mode 100644
new mode 100755
diff --git a/src/alpaca_client.py b/src/alpaca_client.py
index 0d264fb..7dda5ad 100644
--- a/src/alpaca_client.py
+++ b/src/alpaca_client.py
@@ -1,18 +1,30 @@
 from __future__ import annotations
 
-import math
+import json
+import re
+import threading
 import time
+from decimal import Decimal, ROUND_DOWN
+from pathlib import Path
 from typing import Optional
 from requests.exceptions import RequestException
 from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
 
 from alpaca.trading.client import TradingClient
 from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest, ClosePositionRequest, GetOrdersRequest
-from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
+from alpaca.trading.requests import GetAssetsRequest
+from alpaca.trading.enums import AssetClass, AssetStatus, OrderSide, TimeInForce, QueryOrderStatus
 
 from src.config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_PAPER
 
 
+_ASSET_CATALOG_TTL_SEC = 6 * 60 * 60
+ASSET_CATALOG_CACHE_PATH = Path("data/runtime/alpaca_asset_catalog.json")
+_asset_catalog_lock = threading.Lock()
+_asset_catalog_cache: list[dict] | None = None
+_asset_catalog_expiry_epoch = 0.0
+
+
 def _safe_order_qty(qty: float) -> float:
     """Truncate qty down to 6 decimals so sell orders never exceed holdings."""
     safe = safe_order_qty_or_none(qty)
@@ -21,12 +33,20 @@ def _safe_order_qty(qty: float) -> float:
     return safe
 
 
-def safe_order_qty_or_none(qty: float) -> float | None:
-    """Return truncated qty, or None when dust-sized holdings round to zero."""
-    scaled = math.floor(float(qty) * 1_000_000)
-    if scaled <= 0:
+def safe_order_qty_or_none(qty: float, *, decimal_places: int = 6) -> float | None:
+    """Return a downward-rounded qty, or None when it rounds to zero."""
+    if decimal_places < 0:
+        raise ValueError("decimal_places must be non-negative")
+    quantum = Decimal(1).scaleb(-decimal_places)
+    safe = Decimal(str(qty)).quantize(quantum, rounding=ROUND_DOWN)
+    if safe <= 0:
         return None
-    return scaled / 1_000_000
+    return float(safe)
+
+
+def safe_full_close_qty_or_none(qty: float) -> float | None:
+    """Preserve Alpaca's 9-decimal fractional position precision for full exits."""
+    return safe_order_qty_or_none(qty, decimal_places=9)
 
 
 def get_trading_client() -> TradingClient:
@@ -114,6 +134,149 @@ def get_positions_summary() -> list[dict]:
     ]
 
 
+@retry(
+    stop=stop_after_attempt(3),
+    wait=wait_exponential(multiplier=1, min=2, max=10),
+    retry=retry_if_exception_type((RequestException, ConnectionError)),
+    reraise=True,
+)
+def get_asset_summary(ticker: str) -> dict:
+    client = get_trading_client()
+    symbol = str(ticker).strip().upper()
+    try:
+        asset = client.get_asset(symbol)
+    except RequestException as exc:
+        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc
+    return {
+        "symbol": symbol,
+        "active": str(asset.status).upper().endswith("ACTIVE"),
+        "tradable": bool(asset.tradable),
+        "fractionable": bool(asset.fractionable),
+        "marginable": bool(asset.marginable),
+        "name": str(asset.name),
+    }
+
+
+def reset_asset_catalog_cache() -> None:
+    global _asset_catalog_cache, _asset_catalog_expiry_epoch
+    with _asset_catalog_lock:
+        _asset_catalog_cache = None
+        _asset_catalog_expiry_epoch = 0.0
+
+
+def _read_asset_catalog_cache(now: float) -> tuple[list[dict], float] | None:
+    path = ASSET_CATALOG_CACHE_PATH
+    if not path.is_file():
+        return None
+    try:
+        payload = json.loads(path.read_text(encoding="utf-8"))
+        fetched_at = float(payload["fetched_at"])
+        assets = payload["assets"]
+    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
+        raise ValueError(f"Invalid Alpaca asset catalog cache {path}: {exc}") from exc
+    if not isinstance(assets, list) or any(not isinstance(row, dict) for row in assets):
+        raise ValueError(f"Invalid Alpaca asset catalog cache rows in {path}")
+    expiry = fetched_at + _ASSET_CATALOG_TTL_SEC
+    if now >= expiry:
+        return None
+    return assets, expiry
+
+
+def _write_asset_catalog_cache(assets: list[dict], fetched_at: float) -> None:
+    path = ASSET_CATALOG_CACHE_PATH
+    path.parent.mkdir(parents=True, exist_ok=True)
+    temp_path = path.with_suffix(f"{path.suffix}.tmp")
+    try:
+        temp_path.write_text(
+            json.dumps({"fetched_at": fetched_at, "assets": assets}) + "\n",
+            encoding="utf-8",
+        )
+        temp_path.replace(path)
+    except OSError as exc:
+        raise OSError(f"Unable to persist Alpaca asset catalog cache: {exc}") from exc
+
+
+@retry(
+    stop=stop_after_attempt(3),
+    wait=wait_exponential(multiplier=1, min=2, max=10),
+    retry=retry_if_exception_type((RequestException, ConnectionError)),
+    reraise=True,
+)
+def get_active_us_equity_assets(*, force_refresh: bool = False) -> list[dict]:
+    """Return a bounded-TTL normalized Alpaca US-equity asset catalog."""
+    global _asset_catalog_cache, _asset_catalog_expiry_epoch
+    now = time.time()
+    with _asset_catalog_lock:
+        if (
+            not force_refresh
+            and _asset_catalog_cache is not None
+            and now < _asset_catalog_expiry_epoch
+        ):
+            return list(_asset_catalog_cache)
+        if not force_refresh:
+            try:
+                disk_cache = _read_asset_catalog_cache(now)
+            except ValueError as exc:
+                print(f"Warning: {exc}; refreshing from Alpaca")
+                disk_cache = None
+            if disk_cache is not None:
+                cached_assets, expiry = disk_cache
+                _asset_catalog_cache = list(cached_assets)
+                _asset_catalog_expiry_epoch = expiry
+                return list(cached_assets)
+
+        client = get_trading_client()
+        try:
+            assets = client.get_all_assets(
+                GetAssetsRequest(
+                    status=AssetStatus.ACTIVE,
+                    asset_class=AssetClass.US_EQUITY,
+                )
+            )
+        except RequestException as exc:
+            raise ConnectionError(f"Unable to reach Alpaca asset catalog API: {exc}") from exc
+
+        normalized = [
+            {
+                "symbol": str(asset.symbol).upper(),
+                "name": str(asset.name or ""),
+                "active": str(asset.status).upper().endswith("ACTIVE"),
+                "tradable": bool(asset.tradable),
+                "fractionable": bool(asset.fractionable),
+                "marginable": bool(asset.marginable),
+            }
+            for asset in assets
+        ]
+        _asset_catalog_cache = normalized
+        _asset_catalog_expiry_epoch = now + _ASSET_CATALOG_TTL_SEC
+        _write_asset_catalog_cache(normalized, now)
+        return list(normalized)
+
+
+def discover_leveraged_long_assets(underlying: str) -> list[dict]:
+    """Find exact-name direct 2x-long ETF candidates for one underlying."""
+    source = str(underlying).strip().upper()
+    if not source:
+        return []
+    token = re.escape(source)
+    patterns = (
+        re.compile(rf"\b2X\s+LONG\s+{token}(?:\s+DAILY|\s+ETF|\b)", re.IGNORECASE),
+        re.compile(rf"\bDAILY\s+{token}\s+BULL\s+2X\b", re.IGNORECASE),
+        re.compile(rf"\bDAILY\s+{token}\s+LONG\s+2X\b", re.IGNORECASE),
+    )
+    candidates = []
+    for asset in get_active_us_equity_assets():
+        name = str(asset.get("name") or "")
+        if "ETF" not in name.upper():
+            continue
+        if not any(pattern.search(name) for pattern in patterns):
+            continue
+        if not bool(asset.get("active")) or not bool(asset.get("tradable")):
+            continue
+        candidates.append(dict(asset))
+    return sorted(candidates, key=lambda row: str(row.get("symbol") or ""))
+
+
 def _optional_str(value) -> str:
     if value is None:
         return ""
@@ -243,7 +406,8 @@ def get_order_summary(order_id: str) -> dict:
 def cancel_order_by_id(order_id: str) -> dict:
     client = get_trading_client()
     try:
-        order = client.cancel_order_by_id(order_id)
+        client.cancel_order_by_id(order_id)
+        order = client.get_order_by_id(order_id)
     except RequestException as exc:
         raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc
     return serialize_alpaca_order(order)
@@ -279,6 +443,42 @@ def submit_market_buy_notional_order(
         raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc
 
 
+@retry(
+    stop=stop_after_attempt(3),
+    wait=wait_exponential(multiplier=1, min=2, max=10),
+    retry=retry_if_exception_type((RequestException, ConnectionError)),
+    reraise=True,
+)
+def submit_market_buy_qty_order(
+    ticker: str,
+    notional: float,
+    *,
+    reference_price: float,
+    client_order_id: Optional[str] = None,
+):
+    """Submit whole-share market buy for non-fractionable leveraged products."""
+    if notional <= 0:
+        raise ValueError("notional must be positive")
+    if reference_price <= 0:
+        raise ValueError("reference_price must be positive")
+    qty = int(float(notional) // float(reference_price))
+    if qty <= 0:
+        raise ValueError("notional is below one whole share")
+
+    client = get_trading_client()
+    order_request = MarketOrderRequest(
+        symbol=ticker,
+        qty=qty,
+        side=OrderSide.BUY,
+        time_in_force=TimeInForce.DAY,
+        client_order_id=client_order_id,
+    )
+    try:
+        return client.submit_order(order_data=order_request)
+    except RequestException as exc:
+        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc
+
+
 @retry(
     stop=stop_after_attempt(3),
     wait=wait_exponential(multiplier=1, min=2, max=10),
@@ -292,6 +492,7 @@ def submit_limit_buy_notional_order(
     slippage_pct: float = 0.005,
     client_order_id: Optional[str] = None,
     extended_hours: bool = False,
+    whole_shares: bool = False,
 ):
     """지정가 매수 주문. limit_price 기준으로 수량을 계산해 제출한다.
 
@@ -304,7 +505,13 @@ def submit_limit_buy_notional_order(
         raise ValueError("limit_price must be positive")
 
     effective_limit = round(limit_price * (1 + slippage_pct), 2)
-    qty = _safe_order_qty(notional / effective_limit)
+    qty = (
+        int(float(notional) // effective_limit)
+        if whole_shares
+        else _safe_order_qty(notional / effective_limit)
+    )
+    if qty <= 0:
+        raise ValueError("notional is below one whole share")
 
     client = get_trading_client()
     order_request = LimitOrderRequest(
@@ -336,6 +543,7 @@ def submit_limit_sell_qty_order(
     slippage_pct: float = 0.005,
     client_order_id: Optional[str] = None,
     extended_hours: bool = False,
+    close_all: bool = False,
 ):
     if qty <= 0:
         raise ValueError("qty must be positive")
@@ -347,12 +555,17 @@ def submit_limit_sell_qty_order(
         raise ValueError("effective limit price must be positive")
 
     client = get_trading_client()
-    safe_qty = safe_order_qty_or_none(qty)
+    safe_qty = (
+        safe_full_close_qty_or_none(qty)
+        if close_all
+        else safe_order_qty_or_none(qty)
+    )
     if safe_qty is None:
         return close_position_by_symbol(
             ticker,
             qty=None,
             client_order_id=client_order_id,
+            close_all=True,
         )
 
     order_request = LimitOrderRequest(
@@ -380,10 +593,14 @@ def submit_limit_sell_qty_order(
 def close_position_by_symbol(
     ticker: str, 
     qty: Optional[float] = None, 
-    client_order_id: Optional[str] = None
+    client_order_id: Optional[str] = None,
+    close_all: bool = False,
 ):
     client = get_trading_client()
     try:
+        if close_all:
+            return client.close_position(ticker)
+
         # If client_order_id is provided, we use submit_order for idempotency.
         # Note: close_position API (DELETE /positions) does not support client_order_id.
         if client_order_id:
@@ -508,4 +725,3 @@ def get_position_entry_date(ticker: str) -> Optional[datetime]:
     except Exception as exc:
         print(f"Warning: Failed to fetch entry date for {ticker}: {exc}")
         return None
-
diff --git a/src/brokers/alpaca.py b/src/brokers/alpaca.py
index 4350add..de1abc8 100644
--- a/src/brokers/alpaca.py
+++ b/src/brokers/alpaca.py
@@ -2,6 +2,7 @@
 
 from __future__ import annotations
 
+from math import floor
 from typing import Any, Optional
 
 from src.brokers.base import BrokerAdapter, OrderSubmission
@@ -21,6 +22,19 @@ class AlpacaBrokerAdapter(BrokerAdapter):
 
         return get_positions_summary()
 
+    def get_asset_info(self, ticker: str) -> dict[str, Any]:
+        from src.alpaca_client import get_asset_summary
+
+        return get_asset_summary(ticker)
+
+    def discover_leveraged_long_products(
+        self,
+        underlying: str,
+    ) -> list[dict[str, Any]]:
+        from src.alpaca_client import discover_leveraged_long_assets
+
+        return discover_leveraged_long_assets(underlying)
+
     def get_open_orders(self, *, limit: int = 100) -> list[dict[str, Any]]:
         from src.alpaca_client import get_open_orders
 
@@ -67,16 +81,30 @@ class AlpacaBrokerAdapter(BrokerAdapter):
         client_order_id: Optional[str] = None,
     ) -> OrderSubmission:
         from src.alpaca_client import (
+            get_asset_summary,
             submit_limit_buy_notional_order,
+            submit_market_buy_qty_order,
             submit_market_buy_notional_order,
         )
 
-        if market_clock.is_regular_session:
+        asset = get_asset_summary(ticker)
+        if not asset["active"] or not asset["tradable"]:
+            raise ValueError(f"Asset is not tradable: {ticker}")
+        fractionable = bool(asset["fractionable"])
+
+        if market_clock.is_regular_session and fractionable:
             order = submit_market_buy_notional_order(
                 ticker,
                 notional,
                 client_order_id=client_order_id,
             )
+        elif market_clock.is_regular_session:
+            order = submit_market_buy_qty_order(
+                ticker,
+                notional,
+                reference_price=limit_price,
+                client_order_id=client_order_id,
+            )
         else:
             order = submit_limit_buy_notional_order(
                 ticker,
@@ -85,6 +113,7 @@ class AlpacaBrokerAdapter(BrokerAdapter):
                 slippage_pct=slippage_pct,
                 client_order_id=client_order_id,
                 extended_hours=True,
+                whole_shares=not fractionable,
             )
         return OrderSubmission(
             order_id=str(order.id),
@@ -102,14 +131,31 @@ class AlpacaBrokerAdapter(BrokerAdapter):
         market_clock: MarketClock,
         slippage_pct: float,
         client_order_id: Optional[str] = None,
+        close_all: bool = False,
     ) -> OrderSubmission:
-        from src.alpaca_client import close_position_by_symbol, submit_limit_sell_qty_order
+        from src.alpaca_client import (
+            close_position_by_symbol,
+            get_asset_summary,
+            submit_limit_sell_qty_order,
+        )
+
+        if not close_all:
+            asset = get_asset_summary(ticker)
+            if not asset["active"] or not asset["tradable"]:
+                raise ValueError(f"Asset is not tradable: {ticker}")
+            if not bool(asset["fractionable"]):
+                qty = float(floor(qty))
+                if qty <= 0:
+                    raise ValueError(
+                        f"Non-fractionable sell quantity is below one share: {ticker}"
+                    )
 
         if market_clock.is_regular_session:
             order = close_position_by_symbol(
                 ticker,
-                qty=qty,
+                qty=None if close_all else qty,
                 client_order_id=client_order_id,
+                close_all=close_all,
             )
         else:
             order = submit_limit_sell_qty_order(
@@ -119,6 +165,7 @@ class AlpacaBrokerAdapter(BrokerAdapter):
                 slippage_pct=slippage_pct,
                 client_order_id=client_order_id,
                 extended_hours=True,
+                close_all=close_all,
             )
         if order is None:
             raise ValueError(f"No sell order submitted for {ticker}")
diff --git a/src/brokers/base.py b/src/brokers/base.py
index 1baf7f8..a40370f 100644
--- a/src/brokers/base.py
+++ b/src/brokers/base.py
@@ -33,6 +33,22 @@ class BrokerAdapter(ABC):
     def get_open_symbols(self) -> set[str]:
         return {str(position["symbol"]).upper() for position in self.get_positions()}
 
+    def get_asset_info(self, ticker: str) -> dict[str, Any]:
+        """Return broker asset capabilities used by product routing."""
+        return {
+            "symbol": str(ticker).strip().upper(),
+            "active": True,
+            "tradable": True,
+            "fractionable": True,
+        }
+
+    def discover_leveraged_long_products(
+        self,
+        underlying: str,
+    ) -> list[dict[str, Any]]:
+        """Return broker-validated direct 2x-long product candidates, if supported."""
+        return []
+
     @abstractmethod
     def get_open_orders(self, *, limit: int = 100) -> list[dict[str, Any]]:
         raise NotImplementedError
@@ -72,6 +88,7 @@ class BrokerAdapter(ABC):
         market_clock: MarketClock,
         slippage_pct: float,
         client_order_id: Optional[str] = None,
+        close_all: bool = False,
     ) -> OrderSubmission:
         raise NotImplementedError
 
diff --git a/src/brokers/paper.py b/src/brokers/paper.py
index 3734790..6afe21c 100644
--- a/src/brokers/paper.py
+++ b/src/brokers/paper.py
@@ -233,6 +233,7 @@ class PaperBrokerAdapter(BrokerAdapter):
         market_clock: MarketClock,
         slippage_pct: float,
         client_order_id: Optional[str] = None,
+        close_all: bool = False,
     ) -> OrderSubmission:
         if self.fail_submit:
             raise ConnectionError("paper broker submit failure (test)")
@@ -253,7 +254,7 @@ class PaperBrokerAdapter(BrokerAdapter):
         pos = self.positions.get(symbol)
         if pos is None or qty <= 0:
             raise ValueError(f"No position to sell for {ticker}")
-        sell_qty = min(qty, pos.qty)
+        sell_qty = pos.qty if close_all else min(qty, pos.qty)
         price = self._price(ticker, limit_price)
         pos.qty -= sell_qty
         if pos.qty <= 1e-9:
diff --git a/src/brokers/toss.py b/src/brokers/toss.py
index 32164a7..baf1af0 100644
--- a/src/brokers/toss.py
+++ b/src/brokers/toss.py
@@ -1,44 +1,158 @@
-"""Toss Securities Open API placeholder."""
+"""Toss Securities Open API broker adapter — read-only phase.
+
+Read paths (account, holdings, orders, quotes) are wired to the live Toss
+Open API via src.brokers.toss_client. Order mutations (submit/cancel) remain
+guarded stubs so the adapter cannot place a live order until explicitly built
+and reviewed. is_live_capable() stays False until then.
+"""
 
 from __future__ import annotations
 
 from typing import Any, Optional
 
 from src.brokers.base import BrokerAdapter, OrderSubmission
+from src.brokers.toss_client import (
+    get_buying_power,
+    get_holdings,
+    get_order,
+    get_orders,
+    get_stocks,
+    resolve_account_seq,
+)
 from src.market_clock import MarketClock
 
-_STUB_MSG = (
-    "Toss Securities Open API is not wired yet. "
-    "Set broker_provider='alpaca' until Toss integration lands."
+_ORDER_STUB_MSG = (
+    "Toss order mutation is not implemented (read-only phase). "
+    "Reads (account/holdings/orders/quotes) are live; order submit/cancel are "
+    "intentionally disabled until the order path is built and reviewed."
 )
 
+_OPEN_ORDER_STATUS = "OPEN"
+_CLOSED_ORDER_STATUS = "CLOSED"
+
+
+def _first(mapping: dict[str, Any], *keys: str, default: Any = None) -> Any:
+    for key in keys:
+        if mapping.get(key) not in (None, ""):
+            return mapping[key]
+    return default
+
+
+def _amount(value: Any) -> Any:
+    """Toss money fields may be a scalar or {'amount': ...} object."""
+    if isinstance(value, dict):
+        return _first(value, "amount", "value")
+    return value
+
 
 class TossBrokerAdapter(BrokerAdapter):
     provider = "toss"
 
     def is_live_capable(self) -> bool:
+        # Reads are live, but order submission is not implemented yet.
         return False
 
-    def _stub(self) -> None:
-        raise NotImplementedError(_STUB_MSG)
-
     def get_account(self) -> dict[str, Any]:
-        self._stub()
+        account_seq = resolve_account_seq()
+        buying_power = get_buying_power()
+        return {
+            "provider": "toss",
+            "account_seq": account_seq,
+            "buying_power": buying_power,
+        }
 
     def get_positions(self) -> list[dict[str, Any]]:
-        self._stub()
+        positions: list[dict[str, Any]] = []
+        for holding in get_holdings():
+            symbol = _first(holding, "symbol", "ticker", "stockCode", "code", default="")
+            qty = _first(holding, "quantity", "qty", "balanceQuantity", "holdingQuantity", default=0)
+            avg_price = _first(
+                holding,
+                "averagePurchasePrice",
+                "averagePrice",
+                "avgPrice",
+                "purchasePrice",
+            )
+            profit_loss = holding.get("profitLoss")
+            positions.append(
+                {
+                    "symbol": str(symbol).upper(),
+                    "market": _first(holding, "marketCountry", "market", default=""),
+                    "currency": _first(holding, "currency", default=""),
+                    "qty": qty,
+                    "avg_price": avg_price,
+                    "last_price": _first(holding, "lastPrice", "currentPrice"),
+                    "market_value": _amount(
+                        _first(holding, "marketValue", "evaluationAmount", "valuation")
+                    ),
+                    "pnl": _amount(profit_loss) if profit_loss is not None else None,
+                    "pnl_rate": profit_loss.get("rate") if isinstance(profit_loss, dict) else None,
+                    "_raw": holding,
+                }
+            )
+        return positions
+
+    def get_asset_info(self, ticker: str) -> dict[str, Any]:
+        symbol = str(ticker).strip().upper()
+        rows = get_stocks([symbol])
+        if not rows:
+            return {
+                "symbol": symbol,
+                "active": False,
+                "tradable": False,
+                "fractionable": False,
+            }
+        row = rows[0]
+        status = str(row.get("status") or "").upper()
+        leverage_raw = row.get("leverageFactor")
+        try:
+            leverage_factor = float(leverage_raw) if leverage_raw not in (None, "") else 1.0
+        except (TypeError, ValueError):
+            leverage_factor = 1.0
+        return {
+            "symbol": symbol,
+            "name": str(row.get("englishName") or row.get("name") or ""),
+            "active": status == "ACTIVE",
+            "tradable": status == "ACTIVE",
+            "fractionable": False,
+            "marginable": False,
+            "security_type": str(row.get("securityType") or "").upper(),
+            "leverage_factor": leverage_factor,
+            "market": str(row.get("market") or ""),
+        }
+
+    def discover_leveraged_long_products(
+        self,
+        underlying: str,
+    ) -> list[dict[str, Any]]:
+        # Toss can validate known symbols but cannot enumerate its stock master.
+        # Use Alpaca's US-equity catalog for discovery, then verify every result
+        # against Toss's live /stocks metadata before returning it.
+        from src.alpaca_client import discover_leveraged_long_assets
+
+        verified: list[dict[str, Any]] = []
+        for candidate in discover_leveraged_long_assets(underlying):
+            info = self.get_asset_info(str(candidate["symbol"]))
+            if (
+                info.get("active")
+                and info.get("tradable")
+                and info.get("security_type") == "ETF"
+                and float(info.get("leverage_factor") or 0.0) == 2.0
+            ):
+                verified.append({**candidate, **info})
+        return verified
 
     def get_open_orders(self, *, limit: int = 100) -> list[dict[str, Any]]:
-        self._stub()
+        return get_orders(status=_OPEN_ORDER_STATUS, limit=limit)
 
     def get_recent_closed_orders(self, *, limit: int = 50) -> list[dict[str, Any]]:
-        self._stub()
+        return get_orders(status=_CLOSED_ORDER_STATUS, limit=limit)
 
     def get_order_status(self, order_id: str) -> dict[str, Any]:
-        self._stub()
+        return get_order(order_id)
 
     def cancel_order(self, order_id: str) -> dict[str, Any]:
-        self._stub()
+        raise NotImplementedError(_ORDER_STUB_MSG)
 
     def submit_buy_notional(
         self,
@@ -50,7 +164,7 @@ class TossBrokerAdapter(BrokerAdapter):
         slippage_pct: float,
         client_order_id: Optional[str] = None,
     ) -> OrderSubmission:
-        self._stub()
+        raise NotImplementedError(_ORDER_STUB_MSG)
 
     def submit_sell_qty(
         self,
@@ -61,5 +175,6 @@ class TossBrokerAdapter(BrokerAdapter):
         market_clock: MarketClock,
         slippage_pct: float,
         client_order_id: Optional[str] = None,
+        close_all: bool = False,
     ) -> OrderSubmission:
-        self._stub()
+        raise NotImplementedError(_ORDER_STUB_MSG)
diff --git a/src/buy_guards.py b/src/buy_guards.py
index 37c87a0..6c985b6 100644
--- a/src/buy_guards.py
+++ b/src/buy_guards.py
@@ -51,6 +51,7 @@ def apply_shared_buy_guards(
     open_symbols: set[str],
     ticker_data: dict[str, pd.DataFrame],
     vix_df: pd.DataFrame | None,
+    instrument_ticker: str | None = None,
     macro_risk_active: bool = False,
     macro_risk_reason: str = "",
     margin_leverage_block_active: bool = False,
@@ -88,7 +89,7 @@ def apply_shared_buy_guards(
         return BuyGuardResult(False, sector_reason, 0.0, llm_is_ok, llm_reason)
 
     inst_ok, inst_reason = check_instrument_buy_allowed(
-        ticker,
+        instrument_ticker or ticker,
         open_symbols,
         allow_leveraged_etfs=bool(getattr(settings, "allow_leveraged_etfs", False)),
         leveraged_etf_allowlist=list(
diff --git a/src/candidate_cache.py b/src/candidate_cache.py
index 3d2c162..a4ba488 100644
--- a/src/candidate_cache.py
+++ b/src/candidate_cache.py
@@ -60,6 +60,7 @@ from src.strategy import add_indicators, generate_signal
 CACHE_DIR = Path("logs/candidate_cache")
 LATEST_META_PATH = CACHE_DIR / "latest_meta.json"
 UNIVERSE_META_PATH = CACHE_DIR / "universe_meta.json"
+UNIVERSE_HISTORY_PATH = CACHE_DIR / "universe_history.jsonl"
 LATEST_BUY_PATH = CACHE_DIR / "latest_buy.csv"
 LATEST_EXIT_PATH = CACHE_DIR / "latest_exit.csv"
 LATEST_QUALITY_PATH = CACHE_DIR / "latest_quality.csv"
@@ -82,6 +83,40 @@ def _write_universe_meta(meta: dict) -> None:
     """Persist dynamic-universe snapshot without clobbering full candidate-cache meta."""
     CACHE_DIR.mkdir(parents=True, exist_ok=True)
     UNIVERSE_META_PATH.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
+    history_path = UNIVERSE_META_PATH.with_name(UNIVERSE_HISTORY_PATH.name)
+    try:
+        with history_path.open("a", encoding="utf-8") as handle:
+            handle.write(json.dumps(meta, sort_keys=True) + "\n")
+    except OSError as exc:
+        print(f"Warning: failed to append dynamic-universe history: {exc}")
+
+
+def load_dynamic_universe_history(
+    path: Path = UNIVERSE_HISTORY_PATH,
+) -> dict[pd.Timestamp, list[str]]:
+    """Load point-in-time universe snapshots for operational backtests."""
+    if not path.is_file():
+        return {}
+    snapshots: dict[pd.Timestamp, list[str]] = {}
+    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
+        if not raw.strip():
+            continue
+        try:
+            payload = json.loads(raw)
+            generated_at = pd.Timestamp(payload["generated_at"]).tz_localize(None)
+            tickers = payload["tickers"]
+            if not isinstance(tickers, list):
+                raise ValueError("tickers must be a list")
+        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
+            raise ValueError(
+                f"Invalid universe history row {line_number} in {path}: {exc}"
+            ) from exc
+        snapshots[generated_at.normalize()] = [
+            str(ticker).strip().upper()
+            for ticker in tickers
+            if str(ticker).strip()
+        ]
+    return snapshots
 
 
 def _build_dynamic_universe_meta(
diff --git a/src/features.py b/src/features.py
index b9d43ad..495ce50 100644
--- a/src/features.py
+++ b/src/features.py
@@ -191,3 +191,55 @@ def build_features(
         raise ValueError("Feature frame is empty after indicator construction")
 
     return feature_df
+
+
+def build_inference_features(
+    df: pd.DataFrame,
+    prediction_horizon: int = 5,
+    target_return_threshold: float = 0.0,
+    vix_df: pd.DataFrame | None = None,
+    spy_df: pd.DataFrame | None = None,
+    macro_df: pd.DataFrame | None = None,
+) -> pd.DataFrame:
+    """Build causal features through the latest completed price row.
+
+    ``build_features`` also creates forward-return labels and therefore removes
+    the last ``prediction_horizon`` rows. Inference must not lag by that label
+    horizon. Flat synthetic rows keep those rows during feature construction;
+    they are removed before this function returns and none of their values are
+    used by the causal feature columns.
+    """
+    if df.empty:
+        raise ValueError("empty price frame")
+
+    working = df.copy().sort_values("date").reset_index(drop=True)
+    original_last_date = pd.to_datetime(working["date"], errors="coerce").max()
+    if pd.isna(original_last_date):
+        raise ValueError("price frame has no valid dates")
+
+    last = working.iloc[-1].copy()
+    synthetic_rows = []
+    for offset in range(1, prediction_horizon + 1):
+        row = last.copy()
+        row["date"] = original_last_date + pd.Timedelta(days=offset)
+        synthetic_rows.append(row)
+    if synthetic_rows:
+        working = pd.concat(
+            [working, pd.DataFrame(synthetic_rows)],
+            ignore_index=True,
+        )
+
+    features = build_features(
+        working,
+        prediction_horizon=prediction_horizon,
+        target_return_threshold=target_return_threshold,
+        vix_df=vix_df,
+        spy_df=spy_df,
+        macro_df=macro_df,
+    )
+    features = features[
+        pd.to_datetime(features["date"], errors="coerce") <= original_last_date
+    ].reset_index(drop=True)
+    if features.empty:
+        raise ValueError("Inference feature frame is empty")
+    return features
diff --git a/src/instrument_meta.py b/src/instrument_meta.py
index 6b18adc..62d82db 100644
--- a/src/instrument_meta.py
+++ b/src/instrument_meta.py
@@ -8,6 +8,7 @@ from pathlib import Path
 from typing import Any
 
 REGISTRY_PATH = Path("config/instrument_registry.json")
+DISCOVERED_REGISTRY_PATH = Path("data/runtime/discovered_instruments.json")
 
 DEFAULT_META = {
     "kind": "stock",
@@ -61,6 +62,86 @@ def load_instrument_registry(path: Path = REGISTRY_PATH) -> dict[str, Instrument
 
 
 _registry_cache: dict[str, InstrumentMeta] | None = None
+_discovered_registry_cache: dict[str, InstrumentMeta] | None = None
+
+
+def load_discovered_instrument_registry(
+    path: Path | None = None,
+) -> dict[str, InstrumentMeta]:
+    target = path or DISCOVERED_REGISTRY_PATH
+    if not target.is_file():
+        return {}
+    try:
+        payload = json.loads(target.read_text(encoding="utf-8"))
+    except (OSError, json.JSONDecodeError) as exc:
+        raise ValueError(f"Invalid discovered instrument registry {target}: {exc}") from exc
+    if not isinstance(payload, dict):
+        raise ValueError(f"{target} must be a JSON object")
+    registry: dict[str, InstrumentMeta] = {}
+    for ticker, meta in payload.items():
+        if not isinstance(meta, dict):
+            raise ValueError(f"Discovered registry entry for {ticker} must be an object")
+        registry[str(ticker).strip().upper()] = _parse_meta(meta)
+    return registry
+
+
+def _discovered_registry() -> dict[str, InstrumentMeta]:
+    global _discovered_registry_cache
+    if _discovered_registry_cache is None:
+        _discovered_registry_cache = load_discovered_instrument_registry()
+    return _discovered_registry_cache
+
+
+def register_discovered_leveraged_product(
+    symbol: str,
+    underlying: str,
+    *,
+    multiple: float = 2.0,
+    path: Path | None = None,
+) -> None:
+    """Persist broker-validated metadata so later runs keep safe exit/risk mapping."""
+    global _discovered_registry_cache
+    product = str(symbol).strip().upper()
+    source = str(underlying).strip().upper()
+    if not product or not source or float(multiple) <= 1.0:
+        raise ValueError("discovered leveraged product metadata is invalid")
+
+    target = path or DISCOVERED_REGISTRY_PATH
+    discovered = load_discovered_instrument_registry(target)
+    meta = InstrumentMeta(
+        kind="leveraged_etf",
+        multiple=float(multiple),
+        underlying=source,
+        direction="long",
+    )
+    if discovered.get(product) == meta:
+        _discovered_registry_cache = discovered
+        return
+    discovered[product] = meta
+    payload = {
+        ticker: {
+            "kind": meta.kind,
+            "multiple": meta.multiple,
+            "underlying": meta.underlying,
+            "direction": meta.direction,
+        }
+        for ticker, meta in sorted(discovered.items())
+    }
+    target.parent.mkdir(parents=True, exist_ok=True)
+    temp_path = target.with_suffix(f"{target.suffix}.tmp")
+    try:
+        temp_path.write_text(
+            json.dumps(payload, indent=2, sort_keys=True) + "\n",
+            encoding="utf-8",
+        )
+        temp_path.replace(target)
+    except OSError as exc:
+        raise OSError(f"Unable to persist discovered instrument {product}: {exc}") from exc
+    _discovered_registry_cache = discovered
+
+
+def is_discovered_instrument(ticker: str) -> bool:
+    return str(ticker).strip().upper() in _discovered_registry()
 
 
 def get_instrument(ticker: str, registry: dict[str, InstrumentMeta] | None = None) -> InstrumentMeta:
@@ -71,18 +152,67 @@ def get_instrument(ticker: str, registry: dict[str, InstrumentMeta] | None = Non
     key = str(ticker).strip().upper()
     if key in reg:
         return reg[key]
+    if registry is None and key in _discovered_registry():
+        return _discovered_registry()[key]
     return _parse_meta(DEFAULT_META)
 
 
 def clear_instrument_registry_cache() -> None:
-    global _registry_cache
+    global _registry_cache, _discovered_registry_cache
     _registry_cache = None
+    _discovered_registry_cache = None
 
 
 def count_leveraged_etf_positions(open_symbols: set[str]) -> int:
     return sum(1 for sym in open_symbols if get_instrument(sym).is_leveraged_etf)
 
 
+def preferred_leveraged_long_product(
+    underlying: str,
+    *,
+    allowlist: list[str] | None = None,
+    registry: dict[str, InstrumentMeta] | None = None,
+) -> str | None:
+    """Return the preferred direct 2x-long product for an underlying ticker."""
+    source = str(underlying).strip().upper()
+    reg = registry if registry is not None else {
+        **_discovered_registry(),
+        **load_instrument_registry(),
+    }
+    candidates = {
+        symbol
+        for symbol, meta in reg.items()
+        if meta.is_leveraged_etf
+        and meta.direction == "long"
+        and meta.abs_multiple == 2.0
+        and meta.underlying == source
+    }
+    if not candidates:
+        return None
+
+    preferred = [
+        str(symbol).strip().upper()
+        for symbol in (allowlist or [])
+        if str(symbol).strip()
+    ]
+    if preferred:
+        allowlisted = next((symbol for symbol in preferred if symbol in candidates), None)
+        if allowlisted is not None:
+            return allowlisted
+        discovered = sorted(symbol for symbol in candidates if is_discovered_instrument(symbol))
+        return discovered[0] if discovered else None
+    return sorted(candidates)[0]
+
+
+def signal_source_ticker(ticker: str) -> str:
+    """Use the underlying signal for a direct long leveraged product."""
+    symbol = str(ticker).strip().upper()
+    meta = get_instrument(symbol)
+    if meta.is_leveraged_etf and meta.direction == "long" and meta.underlying:
+        return meta.underlying
+    return symbol
+
+
 def current_effective_leverage_exposure(
     positions_by_symbol: dict[str, dict[str, Any]],
 ) -> float:
@@ -139,7 +269,11 @@ def check_instrument_buy_allowed(
             for symbol in (leveraged_etf_allowlist or [])
             if str(symbol).strip()
         }
-        if allowed_symbols and str(ticker).strip().upper() not in allowed_symbols:
+        if (
+            allowed_symbols
+            and str(ticker).strip().upper() not in allowed_symbols
+            and not is_discovered_instrument(ticker)
+        ):
             return (
                 False,
                 f"{kind_tag}; leveraged ETF not in allowlist",
diff --git a/src/llm_analyst.py b/src/llm_analyst.py
index fbb0f36..3b13c98 100644
--- a/src/llm_analyst.py
+++ b/src/llm_analyst.py
@@ -211,8 +211,21 @@ def _generate_gemini_text(prompt: str, *, model: str | None = None) -> str:
     return _call_with_retry(_call)
 
 
-def _generate_llm_text_with_provider(prompt: str, *, model: str | None = None) -> Tuple[str, str]:
-    """Return (text, provider) where provider is 'gemini' or 'vllm'."""
+def _generate_llm_text_with_provider(
+    prompt: str,
+    *,
+    model: str | None = None,
+    force_provider: str | None = None,
+) -> Tuple[str, str]:
+    """Return (text, provider) where provider is 'gemini' or 'vllm'.
+
+    force_provider: 'gemini' or 'vllm' skips auto/fallback routing (batch jobs).
+    """
+    if force_provider == "vllm":
+        return generate_vllm_text(prompt, model=model), "vllm"
+    if force_provider == "gemini":
+        return _generate_gemini_text(prompt, model=model), "gemini"
+
     gemini_error: BaseException | None = None
     if _resolve_api_key():
         try:
diff --git a/src/ml_model.py b/src/ml_model.py
index 617d9b4..b56976d 100644
--- a/src/ml_model.py
+++ b/src/ml_model.py
@@ -14,7 +14,7 @@ from xgboost import XGBClassifier
 from sklearn.metrics import accuracy_score, brier_score_loss, precision_score, recall_score, roc_auc_score
 from sklearn.model_selection import TimeSeriesSplit
 
-from src.features import FEATURE_COLUMNS, build_features
+from src.features import FEATURE_COLUMNS, build_features, build_inference_features
 from src.market_regime import compute_daily_regime, get_current_regime
 from src.ai_score_calibration import calibrate_ai_score
 from src.settings import load_settings
@@ -86,7 +86,7 @@ class RegimeAwareModelWrapper(BaseModel):
         spy_df: pd.DataFrame | None = None,
         macro_df: pd.DataFrame | None = None,
     ) -> pd.DataFrame:
-        return build_features(
+        return build_inference_features(
             df,
             prediction_horizon=self.prediction_horizon,
             target_return_threshold=self.target_return_threshold,
@@ -95,6 +95,25 @@ class RegimeAwareModelWrapper(BaseModel):
             macro_df=macro_df,
         )
 
+    def _feature_regimes(
+        self,
+        feature_df: pd.DataFrame,
+        spy_df: pd.DataFrame | None,
+        vix_df: pd.DataFrame | None,
+    ) -> pd.Series:
+        """Return the market regime known on each feature row's date."""
+        if spy_df is None or vix_df is None:
+            return pd.Series("NEUTRAL", index=feature_df.index, dtype="object")
+        regimes = compute_daily_regime(spy_df, vix_df)
+        if regimes.empty:
+            return pd.Series("NEUTRAL", index=feature_df.index, dtype="object")
+        regimes = regimes.copy()
+        regimes.index = pd.to_datetime(regimes.index, errors="coerce")
+        regimes = regimes[~regimes.index.isna()].sort_index()
+        dates = pd.to_datetime(feature_df["date"], errors="coerce")
+        aligned = regimes.reindex(pd.DatetimeIndex(dates), method="ffill")
+        return pd.Series(aligned.fillna("NEUTRAL").to_numpy(), index=feature_df.index)
+
     def _get_model_for_regime(self, spy_df, vix_df):
         regime = get_current_regime(spy_df, vix_df)
         # Fallback to NEUTRAL if specific regime model missing
@@ -108,17 +127,17 @@ class RegimeAwareModelWrapper(BaseModel):
         macro_df: pd.DataFrame | None = None,
     ) -> pd.Series:
         feature_df = self._prepare_features(df, vix_df=vix_df, spy_df=spy_df, macro_df=macro_df)
-        model = self._get_model_for_regime(spy_df, vix_df)
-        
         available_cols = [c for c in self.feature_columns if c in feature_df.columns]
         X = feature_df[available_cols]
-        
-        # SoftVotingEnsemble 또는 일반 모델 호환성 유지
-        if hasattr(model, "predict_proba"):
-            proba = model.predict_proba(X)
-            return pd.Series(proba[:, 1], index=feature_df.index)
-        
-        return pd.Series([0.5] * len(X), index=feature_df.index)
+        regimes = self._feature_regimes(feature_df, spy_df, vix_df)
+        output = pd.Series(0.5, index=feature_df.index, dtype=float)
+        for regime, row_index in regimes.groupby(regimes).groups.items():
+            model = self.models.get(str(regime), self.models.get("NEUTRAL"))
+            if model is None or not hasattr(model, "predict_proba"):
+                continue
+            proba = model.predict_proba(X.loc[row_index])
+            output.loc[row_index] = proba[:, 1]
+        return output
 
     def predict(
         self,
@@ -128,12 +147,16 @@ class RegimeAwareModelWrapper(BaseModel):
         macro_df: pd.DataFrame | None = None,
     ) -> pd.Series:
         feature_df = self._prepare_features(df, vix_df=vix_df, spy_df=spy_df, macro_df=macro_df)
-        model = self._get_model_for_regime(spy_df, vix_df)
-        
         available_cols = [c for c in self.feature_columns if c in feature_df.columns]
         X = feature_df[available_cols]
-        pred = model.predict(X)
-        return pd.Series(pred, index=feature_df.index)
+        regimes = self._feature_regimes(feature_df, spy_df, vix_df)
+        output = pd.Series(0, index=feature_df.index, dtype=int)
+        for regime, row_index in regimes.groupby(regimes).groups.items():
+            model = self.models.get(str(regime), self.models.get("NEUTRAL"))
+            if model is None:
+                continue
+            output.loc[row_index] = model.predict(X.loc[row_index])
+        return output
 
 
 def _utc_now_iso() -> str:
diff --git a/src/portfolio_backtest_settings.py b/src/portfolio_backtest_settings.py
index e6f8b97..03d5cda 100644
--- a/src/portfolio_backtest_settings.py
+++ b/src/portfolio_backtest_settings.py
@@ -21,6 +21,15 @@ def portfolio_backtest_kwargs(
     evaluation_end_date=None,
     initial_cash: float = 10000.0,
     transaction_cost_pct: float = 0.001,
+    leveraged_product_data: dict | None = None,
+    leveraged_product_routes: dict[str, str] | None = None,
+    historical_universe_by_date: dict | None = None,
+    base_universe: set[str] | list[str] | None = None,
+    benchmark_universe: set[str] | list[str] | None = None,
+    rank_ai_score_history: dict | None = None,
+    fractionable_symbols: set[str] | None = None,
+    cash_reserve_pct: float | None = None,
+    include_external_filters: bool = False,
 ) -> dict[str, Any]:
     """Single source of truth for portfolio backtest parameters from config."""
     return {
@@ -69,6 +78,21 @@ def portfolio_backtest_kwargs(
         "ai_score_frames": ai_score_frames,
         "evaluation_start_date": evaluation_start_date,
         "evaluation_end_date": evaluation_end_date,
+        "crowding_guard_enabled": settings.crowding_guard_enabled,
+        "max_sector_positions": settings.max_sector_positions,
+        "correlation_guard_enabled": settings.correlation_guard_enabled,
+        "max_correlation_threshold": settings.max_correlation_threshold,
+        "max_portfolio_avg_correlation_threshold": settings.max_portfolio_avg_correlation_threshold,
+        "correlation_lookback_days": settings.correlation_lookback_days,
+        "regime_adaptive_stop_enabled": settings.regime_adaptive_stop_enabled,
+        "regime_stop_spy_df": benchmark_df,
+        "llm_filter_enabled": bool(
+            include_external_filters and not settings.llm_advisory_only
+        ),
+        "news_sentiment_filter_enabled": bool(
+            include_external_filters and settings.news_sentiment_enabled
+        ),
+        "news_sentiment_threshold": settings.news_sentiment_threshold,
         "rank_ai_buy_gate_enabled": settings.rank_ai_buy_gate_enabled,
         "rank_ai_buy_top_k_enabled": getattr(settings, "rank_ai_buy_top_k_enabled", True),
         "max_orders_per_run": settings.max_orders_per_run,
@@ -78,4 +102,20 @@ def portfolio_backtest_kwargs(
         "max_leveraged_etf_positions": settings.max_leveraged_etf_positions,
         "max_effective_leverage_exposure_pct": settings.max_effective_leverage_exposure_pct,
         "block_leveraged_etfs_vix_above": settings.block_leveraged_etfs_vix_above,
+        "prefer_leveraged_products": settings.prefer_leveraged_products,
+        "leveraged_product_data": leveraged_product_data,
+        "leveraged_product_routes": leveraged_product_routes,
+        "historical_universe_by_date": historical_universe_by_date,
+        "base_universe": base_universe,
+        "benchmark_universe": benchmark_universe,
+        "rank_ai_score_history": rank_ai_score_history,
+        "take_profit_partial_pct": settings.take_profit_partial_pct,
+        "partial_exit_ratio": settings.partial_exit_ratio,
+        "minimum_order_notional": max(10.0, settings.dust_position_min_usd),
+        "fractionable_symbols": fractionable_symbols,
+        "cash_reserve_pct": (
+            settings.min_cash_buffer_pct
+            if cash_reserve_pct is None
+            else cash_reserve_pct
+        ),
     }
diff --git a/src/portfolio_backtester.py b/src/portfolio_backtester.py
index 7e699db..534d79b 100644
--- a/src/portfolio_backtester.py
+++ b/src/portfolio_backtester.py
@@ -1,20 +1,31 @@
 from __future__ import annotations
 
 from dataclasses import dataclass
+import math
 from pathlib import Path
+from types import SimpleNamespace
 from typing import Any
+import warnings
 
 import pandas as pd
 
 from src.strategy import add_indicators, build_market_regime_frame
-from src.features import FEATURE_COLUMNS, build_features
+from src.features import FEATURE_COLUMNS, build_inference_features
 from src.ml_model import load_ai_score_model
 from src.portfolio_optimizer import compute_candidate_weights
 from src.llm_analyst import evaluate_ticker_consensus
 from src.news_sentiment import get_ticker_sentiment
 from src.risk_manager import apply_factor_crowding_limits
+from src.correlation_guard import is_correlation_allowed
+from src.partial_exit_policy import (
+    compute_partial_exit_thresholds,
+    evaluate_partial_exit,
+)
 from src.regime_stop_policy import RegimeStopProfile, resolve_regime_stop_params
-from src.rank_ai_gate import build_rank_ai_gate_scores, rank_ai_gate_effective_cutoff
+from src.rank_ai_gate import (
+    build_rank_ai_gate_score_history,
+    rank_ai_gate_effective_cutoff,
+)
 from src.rank_buy_allocator import (
     attach_rank_gate_scores_to_day_df,
     max_rank_new_buys_per_run,
@@ -26,6 +37,7 @@ from src.instrument_meta import (
     adjust_position_cap_for_instrument,
     count_leveraged_etf_positions,
     get_instrument,
+    preferred_leveraged_long_product,
 )
 
 
@@ -64,7 +76,7 @@ def _prepare_ticker_frame(
     df = df.sort_values("date").reset_index(drop=True)
 
     df["ticker"] = ticker
-    df["ai_score"] = None
+    df["ai_score"] = float("nan")
     df["relative_return"] = df["close"].pct_change(relative_strength_lookback_days)
     df["volume_ratio"] = df["volume"] / df["volume"].rolling(volume_lookback_days).mean()
     df["volatility"] = df["close"].pct_change().rolling(volatility_lookback_days).std()
@@ -91,7 +103,7 @@ def _prepare_ticker_frame(
                 df = df.drop(columns=["ai_score_model"])
 
         except Exception:
-            df["ai_score"] = None
+            df["ai_score"] = float("nan")
 
     base_buy_signal = (df["ma_fast"] > df["ma_slow"]) & (df["rsi"] < rsi_buy_limit)
 
@@ -142,7 +154,7 @@ def build_ai_score_frame(
     spy_df: pd.DataFrame | None = None,
     macro_df: pd.DataFrame | None = None,
 ) -> pd.DataFrame:
-    feature_df = build_features(
+    feature_df = build_inference_features(
         df,
         prediction_horizon=ai_model_bundle.prediction_horizon,
         target_return_threshold=ai_model_bundle.target_return_threshold,
@@ -150,10 +162,16 @@ def build_ai_score_frame(
         spy_df=spy_df,
         macro_df=macro_df,
     )
-    score_df = feature_df[["date"]].copy()
-    score_df["ai_score"] = ai_model_bundle.predict_proba(
+    scores = ai_model_bundle.predict_proba(
         df, vix_df=vix_df, spy_df=spy_df, macro_df=macro_df
-    ).values
+    )
+    if len(scores) != len(feature_df):
+        raise ValueError(
+            "AI inference score/date length mismatch: "
+            f"scores={len(scores)}, features={len(feature_df)}"
+        )
+    score_df = feature_df[["date"]].copy()
+    score_df["ai_score"] = scores.to_numpy()
     return score_df[["date", "ai_score"]]
 
 
@@ -168,9 +186,23 @@ def build_ai_score_frames(
         ai_model_bundle = load_ai_score_model()
 
     score_frames = {}
+    skipped: dict[str, str] = {}
     for ticker, df in ticker_data.items():
-        score_frames[ticker] = build_ai_score_frame(
-            df, ai_model_bundle, vix_df=vix_df, spy_df=spy_df, macro_df=macro_df
+        try:
+            score_frames[ticker] = build_ai_score_frame(
+                df, ai_model_bundle, vix_df=vix_df, spy_df=spy_df, macro_df=macro_df
+            )
+        except ValueError as exc:
+            skipped[str(ticker).upper()] = str(exc)
+    if not score_frames:
+        detail = "; ".join(f"{ticker}: {reason}" for ticker, reason in skipped.items())
+        raise ValueError(f"No ticker produced AI score history. {detail}")
+    if skipped:
+        warnings.warn(
+            "Skipped AI score history for insufficient/invalid ticker data: "
+            + ", ".join(sorted(skipped)),
+            RuntimeWarning,
+            stacklevel=2,
         )
     return score_frames
 
@@ -256,10 +288,56 @@ def _build_benchmark_relative_return_frame(
     frame = benchmark_df[["date", "close"]].copy()
     frame["date"] = pd.to_datetime(frame["date"])
     frame = frame.sort_values("date").reset_index(drop=True)
-    frame["benchmark_relative_return"] = frame["close"].pct_change(lookback_days)
+    frame["benchmark_relative_return"] = frame["close"].pct_change(
+        lookback_days,
+        fill_method=None,
+    )
     return frame[["date", "benchmark_relative_return"]]
 
 
+def _build_price_lookup(
+    ticker_frames: dict[str, pd.DataFrame] | None,
+) -> dict[str, dict[pd.Timestamp, float]]:
+    lookup: dict[str, dict[pd.Timestamp, float]] = {}
+    for ticker, frame in (ticker_frames or {}).items():
+        if frame is None or frame.empty or "date" not in frame.columns:
+            continue
+        close_col = "adj_close" if "adj_close" in frame.columns else "close"
+        if close_col not in frame.columns:
+            continue
+        work = frame[["date", close_col]].copy()
+        work["date"] = pd.to_datetime(work["date"], errors="coerce")
+        work[close_col] = pd.to_numeric(work[close_col], errors="coerce")
+        work = work.dropna(subset=["date", close_col])
+        lookup[str(ticker).upper()] = {
+            pd.Timestamp(date): float(close)
+            for date, close in zip(work["date"], work[close_col])
+            if float(close) > 0
+        }
+    return lookup
+
+
+def _active_universe_for_date(
+    historical_universe_by_date: dict[Any, list[str]] | None,
+    current_date: pd.Timestamp,
+    fallback_universe: set[str] | None = None,
+) -> set[str] | None:
+    if not historical_universe_by_date:
+        return None
+    normalized = {
+        pd.Timestamp(date).normalize(): {
+            str(ticker).strip().upper()
+            for ticker in tickers
+            if str(ticker).strip()
+        }
+        for date, tickers in historical_universe_by_date.items()
+    }
+    eligible_dates = [date for date in normalized if date <= current_date.normalize()]
+    if not eligible_dates:
+        return fallback_universe
+    return normalized[max(eligible_dates)]
+
+
 def _apply_relative_strength_filter(
     market_df: pd.DataFrame,
     benchmark_df: pd.DataFrame,
@@ -340,6 +418,10 @@ def run_portfolio_backtest(
     llm_cache_only: bool = True,
     news_sentiment_filter_enabled: bool = False,
     news_sentiment_threshold: float = -0.30,
+    correlation_guard_enabled: bool = False,
+    max_correlation_threshold: float = 0.85,
+    max_portfolio_avg_correlation_threshold: float = 0.70,
+    correlation_lookback_days: int = 60,
     operational_settings: Any | None = None,
     rank_ai_buy_gate_enabled: bool = False,
     rank_ai_buy_top_k_enabled: bool = True,
@@ -352,6 +434,18 @@ def run_portfolio_backtest(
     max_leveraged_etf_positions: int = 1,
     max_effective_leverage_exposure_pct: float = 1.25,
     block_leveraged_etfs_vix_above: float = 0.0,
+    prefer_leveraged_products: bool = False,
+    leveraged_product_data: dict[str, pd.DataFrame] | None = None,
+    leveraged_product_routes: dict[str, str] | None = None,
+    historical_universe_by_date: dict[Any, list[str]] | None = None,
+    base_universe: set[str] | list[str] | None = None,
+    benchmark_universe: set[str] | list[str] | None = None,
+    rank_ai_score_history: dict[Any, dict[str, Any]] | None = None,
+    take_profit_partial_pct: float = 0.0,
+    partial_exit_ratio: float = 0.5,
+    minimum_order_notional: float = 0.0,
+    fractionable_symbols: set[str] | None = None,
+    cash_reserve_pct: float = 0.0,
     leverage_factor: float = 1.0,
     annual_margin_interest_rate: float = 0.0,
 ) -> tuple[PortfolioBacktestResult, pd.DataFrame, pd.DataFrame]:
@@ -379,6 +473,16 @@ def run_portfolio_backtest(
         raise ValueError("max_effective_leverage_exposure_pct must be positive")
     if block_leveraged_etfs_vix_above < 0:
         raise ValueError("block_leveraged_etfs_vix_above must be non-negative")
+    if correlation_lookback_days <= 0:
+        raise ValueError("correlation_lookback_days must be positive")
+    if take_profit_partial_pct < 0:
+        raise ValueError("take_profit_partial_pct must be non-negative")
+    if not 0 < partial_exit_ratio <= 1:
+        raise ValueError("partial_exit_ratio must be between 0 and 1")
+    if minimum_order_notional < 0:
+        raise ValueError("minimum_order_notional must be non-negative")
+    if not 0 <= cash_reserve_pct < 1:
+        raise ValueError("cash_reserve_pct must be between 0 and 1")
     if leverage_factor < 1.0:
         raise ValueError("leverage_factor must be at least 1.0")
     if annual_margin_interest_rate < 0:
@@ -478,6 +582,56 @@ def run_portfolio_backtest(
         close_col = "adj_close" if "adj_close" in _vix_tmp.columns else "close"
         _vix_by_date = dict(zip(_vix_tmp["date"], _vix_tmp[close_col]))
 
+    product_price_lookup = _build_price_lookup(leveraged_product_data)
+    route_map = {
+        str(source).strip().upper(): str(product).strip().upper()
+        for source, product in (leveraged_product_routes or {}).items()
+        if str(source).strip() and str(product).strip()
+    }
+    if prefer_leveraged_products and not route_map:
+        route_map = {
+            str(source).upper(): product
+            for source in ticker_data
+            if (
+                product := preferred_leveraged_long_product(
+                    source,
+                    allowlist=leveraged_etf_allowlist,
+                )
+            )
+        }
+    fractionable = (
+        {str(symbol).strip().upper() for symbol in fractionable_symbols}
+        if fractionable_symbols is not None
+        else None
+    )
+    _rank_score_history = rank_ai_score_history
+    if (
+        rank_ai_buy_gate_enabled
+        and operational_settings is not None
+        and _rank_score_history is None
+    ):
+        try:
+            _rank_score_history = build_rank_ai_gate_score_history(
+                ticker_data,
+                operational_settings,
+                vix_df=vix_df,
+                spy_df=spy_df,
+                macro_df=macro_df,
+                historical_universe_by_date=historical_universe_by_date,
+                base_universe=base_universe,
+            )
+        except Exception:
+            _rank_score_history = {}
+    normalized_rank_history = {
+        pd.Timestamp(date): scores
+        for date, scores in (_rank_score_history or {}).items()
+    }
+    normalized_base_universe = (
+        {str(ticker).strip().upper() for ticker in base_universe}
+        if base_universe is not None
+        else None
+    )
+
     cash = initial_cash
     positions: dict[str, dict] = {}
     cumulative_margin_interest = 0.0
@@ -505,16 +659,26 @@ def run_portfolio_backtest(
             row["ticker"]: float(row["close"])
             for _, row in day_df.iterrows()
         }
+        for product, prices in product_price_lookup.items():
+            product_close = prices.get(pd.Timestamp(current_date))
+            if product_close is not None:
+                day_prices[product] = float(product_close)
+
+        pre_exit_equity = cash + sum(
+            pos["qty"] * day_prices.get(ticker, pos["last_price"])
+            for ticker, pos in positions.items()
+        )
 
         for ticker in list(positions.keys()):
-            ticker_row = day_df[day_df["ticker"] == ticker]
+            position = positions[ticker]
+            signal_ticker = str(position.get("signal_ticker") or ticker).upper()
+            ticker_row = day_df[day_df["ticker"] == signal_ticker]
 
-            if ticker_row.empty:
+            if ticker_row.empty or ticker not in day_prices:
                 continue
 
             row = ticker_row.iloc[0]
-            close = float(row["close"])
-            position = positions[ticker]
+            close = float(day_prices[ticker])
             position["highest_price"] = max(
                 float(position.get("highest_price", position["entry_price"])),
                 close,
@@ -570,6 +734,55 @@ def run_portfolio_backtest(
             elif take_profit_pct > 0 and gross_return_pct >= take_profit_pct:
                 exit_reason = "TAKE_PROFIT"
 
+            if (
+                exit_reason is None
+                and take_profit_partial_pct > 0
+                and gross_return_pct >= take_profit_partial_pct
+                and not bool(position.get("partial_exit_taken"))
+            ):
+                position_value = float(position["qty"]) * close
+                partial_qty = float(position["qty"]) * partial_exit_ratio
+                partial_notional = partial_qty * close
+                partial_settings = operational_settings or SimpleNamespace(
+                    max_position_pct=target_position_pct,
+                    partial_exit_ratio=partial_exit_ratio,
+                )
+                thresholds = compute_partial_exit_thresholds(
+                    portfolio_value=pre_exit_equity,
+                    settings=partial_settings,
+                    dust_min_usd=max(minimum_order_notional, 0.0),
+                )
+                partial_allowed, _ = evaluate_partial_exit(
+                    position_market_value=position_value,
+                    sell_notional=partial_notional,
+                    thresholds=thresholds,
+                    already_taken=False,
+                )
+                if partial_allowed and partial_qty > 0:
+                    gross_value = partial_qty * close
+                    net_value = gross_value * (1.0 - transaction_cost_pct)
+                    cost_basis = float(position["cost_basis"]) * partial_exit_ratio
+                    cash += net_value
+                    position["qty"] -= partial_qty
+                    position["cost_basis"] -= cost_basis
+                    position["partial_exit_taken"] = True
+                    trades.append(
+                        {
+                            "ticker": ticker,
+                            "signal_ticker": signal_ticker,
+                            "leveraged": bool(position.get("leveraged")),
+                            "entry_date": position["entry_date"],
+                            "exit_date": current_date,
+                            "entry_price": position["entry_price"],
+                            "exit_price": close,
+                            "qty": partial_qty,
+                            "cost_basis": cost_basis,
+                            "exit_value": net_value,
+                            "return_pct": (net_value / cost_basis) - 1.0,
+                            "exit_reason": "PARTIAL_TAKE_PROFIT",
+                        }
+                    )
+
             if exit_reason is not None:
                 position = positions.pop(ticker)
                 qty = position["qty"]
@@ -586,6 +799,8 @@ def run_portfolio_backtest(
                 trades.append(
                     {
                         "ticker": ticker,
+                        "signal_ticker": signal_ticker,
+                        "leveraged": bool(position.get("leveraged")),
                         "entry_date": entry_date,
                         "exit_date": current_date,
                         "entry_price": entry_price,
@@ -607,10 +822,28 @@ def run_portfolio_backtest(
         slots_left = max_positions - len(positions)
 
         if slots_left > 0:
+            held_signal_tickers = {
+                str(pos.get("signal_ticker") or symbol).upper()
+                for symbol, pos in positions.items()
+            }
+            active_universe = _active_universe_for_date(
+                historical_universe_by_date,
+                pd.Timestamp(current_date),
+                normalized_base_universe,
+            )
+            asof_ticker_data = truncate_ticker_frames_asof(
+                ticker_data,
+                current_date,
+                min_rows=1,
+            )
             buy_candidates = day_df[
                 (day_df["buy_signal"]) &
-                (~day_df["ticker"].isin(positions.keys()))
+                (~day_df["ticker"].isin(held_signal_tickers))
             ].copy()
+            if active_universe is not None:
+                buy_candidates = buy_candidates[
+                    buy_candidates["ticker"].isin(active_universe)
+                ].copy()
 
             if not buy_candidates.empty:
                 leveraged_mask = buy_candidates["ticker"].map(
@@ -653,33 +886,10 @@ def run_portfolio_backtest(
             if buy_candidates.empty:
                 selected = buy_candidates
             elif use_rank_gate:
-                trunc = truncate_ticker_frames_asof(ticker_data, current_date)
-                vix_asof = None
-                if vix_df is not None and not vix_df.empty:
-                    vix_tmp = vix_df.copy()
-                    vix_tmp["date"] = pd.to_datetime(vix_tmp["date"])
-                    vix_asof = vix_tmp[vix_tmp["date"] <= pd.Timestamp(current_date)]
-                spy_asof = None
-                spy_source = ticker_data.get("SPY")
-                if spy_source is not None and not spy_source.empty:
-                    spy_tmp = spy_source.copy()
-                    spy_tmp["date"] = pd.to_datetime(spy_tmp["date"])
-                    spy_asof = spy_tmp[spy_tmp["date"] <= pd.Timestamp(current_date)]
-                macro_asof = None
-                if macro_df is not None and not macro_df.empty:
-                    macro_tmp = macro_df.copy()
-                    macro_tmp["date"] = pd.to_datetime(macro_tmp["date"])
-                    macro_asof = macro_tmp[macro_tmp["date"] <= pd.Timestamp(current_date)]
-                try:
-                    rank_scores = build_rank_ai_gate_scores(
-                        trunc,
-                        ops_settings,
-                        vix_df=vix_asof,
-                        spy_df=spy_asof,
-                        macro_df=macro_asof,
-                    )
-                except Exception:
-                    rank_scores = {}
+                rank_scores = normalized_rank_history.get(
+                    pd.Timestamp(current_date),
+                    {},
+                )
                 cutoff = rank_ai_gate_effective_cutoff(ops_settings)
                 buy_candidates = attach_rank_gate_scores_to_day_df(
                     buy_candidates,
@@ -755,8 +965,33 @@ def run_portfolio_backtest(
                 total_to_deploy = None  # use original target_position_pct per ticker
 
             for _, row in selected.iterrows():
-                ticker = row["ticker"]
+                signal_ticker = str(row["ticker"]).upper()
+                ticker = signal_ticker
                 close = float(row["close"])
+
+                product = route_map.get(signal_ticker) if prefer_leveraged_products else None
+                if product and product in day_prices and allow_leveraged_etfs:
+                    current_vix = None
+                    if _vix_by_date:
+                        past_vix = {
+                            date: value
+                            for date, value in _vix_by_date.items()
+                            if date <= pd.Timestamp(current_date)
+                        }
+                        current_vix = past_vix[max(past_vix)] if past_vix else None
+                    vix_blocked = (
+                        current_vix is not None
+                        and block_leveraged_etfs_vix_above > 0
+                        and float(current_vix) >= block_leveraged_etfs_vix_above
+                    )
+                    leverage_slots_full = (
+                        count_leveraged_etf_positions(set(positions))
+                        >= max_leveraged_etf_positions
+                    )
+                    if not vix_blocked and not leverage_slots_full:
+                        ticker = product
+                        close = float(day_prices[product])
+
                 instrument = get_instrument(ticker)
 
                 if close <= 0:
@@ -771,17 +1006,29 @@ def run_portfolio_backtest(
 
                 if crowding_guard_enabled:
                     crowding = apply_factor_crowding_limits(
-                        ticker=ticker,
-                        open_symbols=set(positions.keys()),
-                        ticker_data=ticker_data,
+                        ticker=signal_ticker,
+                        open_symbols=held_signal_tickers,
+                        ticker_data=asof_ticker_data,
                     )
                     if not crowding.allowed:
                         continue
 
+                if correlation_guard_enabled:
+                    correlation_ok, _ = is_correlation_allowed(
+                        signal_ticker,
+                        held_signal_tickers,
+                        asof_ticker_data,
+                        max_corr=max_correlation_threshold,
+                        max_portfolio_avg_corr=max_portfolio_avg_correlation_threshold,
+                        lookback_days=correlation_lookback_days,
+                    )
+                    if not correlation_ok:
+                        continue
+
                 if max_sector_positions is not None and max_sector_positions > 0:
                     sector_ok, _ = is_sector_allowed(
-                        ticker,
-                        set(positions.keys()),
+                        signal_ticker,
+                        held_signal_tickers,
                         max_sector_positions=max_sector_positions,
                     )
                     if not sector_ok:
@@ -792,7 +1039,7 @@ def run_portfolio_backtest(
 
                 if llm_filter_enabled:
                     llm_ok, _ = evaluate_ticker_consensus(
-                        ticker,
+                        signal_ticker,
                         settings=ops_settings,
                         as_of_date=entry_day,
                         cache_only=llm_cache_only,
@@ -801,7 +1048,7 @@ def run_portfolio_backtest(
                         continue
 
                 if news_sentiment_filter_enabled:
-                    sentiment = get_ticker_sentiment(ticker, as_of_date=entry_day)
+                    sentiment = get_ticker_sentiment(signal_ticker, as_of_date=entry_day)
                     if sentiment is not None and sentiment < news_sentiment_threshold:
                         continue
 
@@ -866,13 +1113,21 @@ def run_portfolio_backtest(
                     current_account_equity * leverage_factor
                     - current_gross_exposure,
                 )
+                reserve_value = current_account_equity * cash_reserve_pct
+                reserve_adjusted_capacity = max(
+                    0.0,
+                    current_account_equity * max(leverage_factor - 1.0, 0.0)
+                    + cash
+                    - reserve_value,
+                )
                 available_value = min(
                     target_value,
                     effective_capacity,
                     margin_capacity,
+                    reserve_adjusted_capacity,
                 )
 
-                if available_value <= 0:
+                if available_value <= 0 or available_value < minimum_order_notional:
                     continue
 
                 cost = available_value * transaction_cost_pct
@@ -882,16 +1137,28 @@ def run_portfolio_backtest(
                     continue
 
                 qty = net_investment / close
+                if fractionable is not None and ticker not in fractionable:
+                    qty = math.floor(qty)
+                    if qty <= 0:
+                        continue
+                    net_investment = qty * close
+                    available_value = net_investment / (1.0 - transaction_cost_pct)
+                    if available_value < minimum_order_notional:
+                        continue
                 cash -= available_value
 
                 positions[ticker] = {
+                    "signal_ticker": signal_ticker,
+                    "leveraged": instrument.is_leveraged_etf,
                     "qty": qty,
                     "entry_price": close,
                     "entry_date": current_date,
                     "cost_basis": available_value,
                     "last_price": close,
                     "highest_price": close,
+                    "partial_exit_taken": False,
                 }
+                held_signal_tickers.add(signal_ticker)
 
         for ticker, pos in positions.items():
             if ticker in day_prices:
@@ -916,6 +1183,15 @@ def run_portfolio_backtest(
                 "cumulative_margin_interest": cumulative_margin_interest,
                 "positions_count": len(positions),
                 "open_symbols": ",".join(sorted(positions.keys())),
+                "open_signal_symbols": ",".join(
+                    sorted(
+                        str(pos.get("signal_ticker") or symbol).upper()
+                        for symbol, pos in positions.items()
+                    )
+                ),
+                "leveraged_positions_count": count_leveraged_etf_positions(
+                    set(positions)
+                ),
             }
         )
 
@@ -941,9 +1217,23 @@ def run_portfolio_backtest(
     else:
         win_rate = 0.0
 
+    benchmark_data = ticker_data
+    if benchmark_universe is not None:
+        allowed_benchmark = {
+            str(ticker).strip().upper()
+            for ticker in benchmark_universe
+            if str(ticker).strip()
+        }
+        benchmark_data = {
+            str(ticker).upper(): frame
+            for ticker, frame in ticker_data.items()
+            if str(ticker).upper() in allowed_benchmark
+        }
+        if not benchmark_data:
+            raise ValueError("benchmark_universe contains no loaded ticker data")
     benchmark_values = _build_equal_weight_benchmark_values(
         equity_df["date"],
-        ticker_data,
+        benchmark_data,
         initial_cash,
     )
     equity_df["benchmark_equity"] = benchmark_values
@@ -998,3 +1288,11 @@ def save_portfolio_backtest_outputs(
     summary_df.to_csv(output_dir / "portfolio_summary.csv", index=False)
     equity_df.to_csv(output_dir / "portfolio_equity.csv", index=False)
     trades_df.to_csv(output_dir / "portfolio_trades.csv", index=False)
+    from src.monthly_backtest_review import write_monthly_backtest_review
+
+    write_monthly_backtest_review(
+        output_dir,
+        equity_df,
+        trades_df,
+        initial_cash=result.initial_cash,
+    )
diff --git a/src/rank_ai_gate.py b/src/rank_ai_gate.py
index 3b4bba7..30ecea3 100644
--- a/src/rank_ai_gate.py
+++ b/src/rank_ai_gate.py
@@ -9,7 +9,7 @@ from typing import Any
 import joblib
 import pandas as pd
 
-from src.features import FEATURE_COLUMNS, build_features
+from src.features import FEATURE_COLUMNS, MAX_FEATURE_LOOKBACK, build_inference_features
 
 
 @dataclass(frozen=True)
@@ -85,30 +85,15 @@ def _build_latest_inference_features(
 
     if df.empty:
         raise ValueError("empty price frame")
-    working = df.copy().sort_values("date").reset_index(drop=True)
-    last = working.iloc[-1].copy()
-    last_date = pd.to_datetime(last["date"])
-    synthetic_rows = []
-    for offset in range(1, prediction_horizon + 1):
-        row = last.copy()
-        row["date"] = last_date + pd.Timedelta(days=offset)
-        synthetic_rows.append(row)
-    if synthetic_rows:
-        working = pd.concat([working, pd.DataFrame(synthetic_rows)], ignore_index=True)
-
-    features = build_features(
-        working,
+    features = build_inference_features(
+        df,
         prediction_horizon=prediction_horizon,
         target_return_threshold=0.0,
         vix_df=vix_df,
         spy_df=spy_df,
         macro_df=macro_df,
     )
-    original_last_date = pd.to_datetime(df["date"]).max()
-    latest_features = features[pd.to_datetime(features["date"]) <= original_last_date]
-    if latest_features.empty:
-        raise ValueError("no current inference feature row")
-    return latest_features.tail(1)
+    return features.tail(1)
 
 
 def build_rank_ai_gate_scores(
@@ -189,6 +174,143 @@ def build_rank_ai_gate_scores(
     return scores
 
 
+def build_rank_ai_gate_score_history(
+    ticker_data: dict[str, pd.DataFrame],
+    settings: Any,
+    *,
+    vix_df: pd.DataFrame | None = None,
+    spy_df: pd.DataFrame | None = None,
+    macro_df: pd.DataFrame | None = None,
+    historical_universe_by_date: dict[Any, list[str]] | None = None,
+    base_universe: set[str] | list[str] | None = None,
+) -> dict[pd.Timestamp, dict[str, RankAIGateScore]]:
+    """Precompute causal daily rank scores for point-in-time backtests.
+
+    Every feature row uses only data available through that row's date. Ranking
+    is then performed cross-sectionally within each date, matching repeated
+    calls to :func:`build_rank_ai_gate_scores` without reloading the model and
+    rebuilding the full feature history on every simulated trading day.
+    """
+    if not _rank_gate_enabled(settings):
+        return {}
+
+    path = _model_path(settings)
+    if not path.is_file():
+        if bool(getattr(settings, "rank_ai_buy_gate_fail_closed", True)):
+            raise FileNotFoundError(f"rank AI gate model not found: {path}")
+        return {}
+
+    bundle = joblib.load(path)
+    classifier = bundle["classifier"]
+    regressor = bundle["regressor"]
+    config = bundle.get("config") or {}
+    horizon = int(
+        getattr(
+            settings,
+            "rank_ai_buy_gate_prediction_horizon",
+            config.get("prediction_horizon", 20),
+        )
+    )
+    minimum_observations = MAX_FEATURE_LOOKBACK + horizon
+    records: list[pd.DataFrame] = []
+
+    for ticker, frame in ticker_data.items():
+        symbol = str(ticker).upper()
+        if symbol.startswith("^") or symbol == "SPY" or frame is None or frame.empty:
+            continue
+        try:
+            ordered = frame.copy()
+            ordered["date"] = pd.to_datetime(ordered["date"])
+            ordered = ordered.sort_values("date").drop_duplicates("date", keep="last")
+            if len(ordered) < minimum_observations:
+                continue
+            feature_frame = build_inference_features(
+                ordered,
+                prediction_horizon=horizon,
+                target_return_threshold=0.0,
+                vix_df=vix_df,
+                spy_df=spy_df,
+                macro_df=macro_df,
+            )
+            feature_frame = feature_frame[
+                pd.to_datetime(feature_frame["date"])
+                >= pd.Timestamp(ordered.iloc[minimum_observations - 1]["date"])
+            ].copy()
+            if feature_frame.empty:
+                continue
+            x = feature_frame[FEATURE_COLUMNS]
+            clf_score = classifier.predict_proba(x)[:, 1]
+            reg_score = pd.Series(regressor.predict(x), index=feature_frame.index).clip(0.0, 1.0)
+            scored = feature_frame[["date"]].copy()
+            scored["ticker"] = symbol
+            scored["score"] = (clf_score + reg_score.to_numpy()) / 2.0
+            records.append(scored)
+        except Exception:
+            continue
+
+    if not records:
+        if bool(getattr(settings, "rank_ai_buy_gate_fail_closed", True)):
+            raise ValueError("rank AI gate produced no historical scores")
+        return {}
+
+    score_df = pd.concat(records, ignore_index=True)
+    score_df["date"] = pd.to_datetime(score_df["date"])
+    if historical_universe_by_date:
+        snapshots = {
+            pd.Timestamp(date).normalize(): {
+                str(ticker).strip().upper()
+                for ticker in tickers
+                if str(ticker).strip()
+            }
+            for date, tickers in historical_universe_by_date.items()
+        }
+        fallback = (
+            {str(ticker).strip().upper() for ticker in base_universe}
+            if base_universe is not None
+            else set(ticker_data)
+        )
+        snapshot_dates = sorted(snapshots)
+
+        def active_symbols(current_date: pd.Timestamp) -> set[str]:
+            eligible = [date for date in snapshot_dates if date <= current_date.normalize()]
+            return snapshots[max(eligible)] if eligible else fallback
+
+        score_df = pd.concat(
+            [
+                rows[rows["ticker"].isin(active_symbols(pd.Timestamp(current_date)))]
+                for current_date, rows in score_df.groupby("date", sort=False)
+            ],
+            ignore_index=True,
+        )
+        if score_df.empty:
+            raise ValueError("rank AI history is empty after point-in-time universe filter")
+    score_df["percentile"] = score_df.groupby("date")["score"].rank(
+        pct=True,
+        method="average",
+    )
+    cutoff = rank_ai_gate_effective_cutoff(settings, config)
+    history: dict[pd.Timestamp, dict[str, RankAIGateScore]] = {}
+    for current_date, rows in score_df.groupby("date", sort=True):
+        daily: dict[str, RankAIGateScore] = {}
+        for row in rows.itertuples(index=False):
+            percentile = float(row.percentile)
+            score = float(row.score)
+            allowed = percentile >= cutoff
+            status = "passed" if allowed else "blocked"
+            daily[str(row.ticker)] = RankAIGateScore(
+                ticker=str(row.ticker),
+                score=score,
+                percentile=percentile,
+                allowed=allowed,
+                reason=(
+                    f"rank ai gate {status} "
+                    f"(pct={percentile:.3f}, cutoff={cutoff:.3f})"
+                ),
+            )
+        history[pd.Timestamp(current_date)] = daily
+    return history
+
+
 def apply_rank_ai_buy_gate(
     *,
     ticker: str,
diff --git a/src/rank_leaderboard.py b/src/rank_leaderboard.py
index 73fc20b..f351de9 100644
--- a/src/rank_leaderboard.py
+++ b/src/rank_leaderboard.py
@@ -129,7 +129,9 @@ def build_rank_leaderboard_live(settings: Any, positions: list[dict[str, Any]] |
     }
     tickers = list(settings.tickers)
     ticker_data = _load_cache_ticker_data(tickers, settings)
-    vix_df = ticker_data.get("^VIX") or ticker_data.get("VIX")
+    vix_df = ticker_data.get("^VIX")
+    if vix_df is None or vix_df.empty:
+        vix_df = ticker_data.get("VIX")
     spy_df = ticker_data.get("SPY")
     macro_df = (
         load_macro_data(period="2y") if getattr(settings, "use_ai_score", False) else None
diff --git a/src/risk_manager.py b/src/risk_manager.py
index 32df144..f752f0e 100644
--- a/src/risk_manager.py
+++ b/src/risk_manager.py
@@ -302,6 +302,26 @@ def apply_portfolio_exposure_limits(
     projected_position_value = max(current_position_value, 0.0) + order_amount
     projected_single_name_loss = projected_position_value * stop_loss_pct
     if projected_single_name_loss > max_single_name_loss:
+        if stop_loss_pct <= 0:
+            return RiskDecision(
+                False,
+                f"single-name max loss exceeded for {ticker}",
+                0.0,
+            )
+        max_position_value = max_single_name_loss / stop_loss_pct
+        allowed_amount = max(
+            0.0,
+            max_position_value - max(current_position_value, 0.0),
+        )
+        if allowed_amount > 0:
+            return RiskDecision(
+                True,
+                (
+                    f"single-name max loss capped order for {ticker} "
+                    f"(max_position=${max_position_value:.2f})"
+                ),
+                min(order_amount, allowed_amount),
+            )
         return RiskDecision(
             False,
             f"single-name max loss exceeded for {ticker} (projected=${projected_single_name_loss:.2f}, max=${max_single_name_loss:.2f})",
diff --git a/src/run_portfolio_backtest.py b/src/run_portfolio_backtest.py
index e6c0020..6eb29cc 100644
--- a/src/run_portfolio_backtest.py
+++ b/src/run_portfolio_backtest.py
@@ -1,13 +1,18 @@
 import argparse
 from pathlib import Path
 
+import pandas as pd
+
 from src.settings import load_settings
 from src.data_loader import load_price_data_batch
+from src.candidate_cache import load_dynamic_universe_history
+from src.instrument_meta import preferred_leveraged_long_product
 from src.portfolio_backtest_settings import portfolio_backtest_kwargs
 from src.portfolio_backtester import (
     run_portfolio_backtest,
     save_portfolio_backtest_outputs,
 )
+from src.sleeved_portfolio_backtester import run_sleeved_portfolio_backtest
 from src.macro_loader import load_macro_data
 
 
@@ -23,11 +28,51 @@ def main() -> None:
         default="equal_weight",
         help="Position sizing method",
     )
+    parser.add_argument("--start", default=None, help="Evaluation start date")
+    parser.add_argument("--end", default=None, help="Evaluation end date")
+    parser.add_argument("--initial-cash", type=float, default=10_000.0)
+    parser.add_argument("--force-refresh", action="store_true")
+    parser.add_argument(
+        "--use-universe-history",
+        action=argparse.BooleanOptionalAction,
+        default=True,
+        help="Use recorded point-in-time dynamic-universe snapshots when available",
+    )
+    parser.add_argument(
+        "--include-external-filters",
+        action="store_true",
+        help="Replay cached LLM/news filters; disabled by default when history is incomplete",
+    )
+    parser.add_argument("--outdir", type=Path, default=Path("logs/portfolio_backtest"))
     args = parser.parse_args()
 
     settings = load_settings()
     print(f"Loading {len(settings.tickers)} tickers...")
-    tickers_to_load = list(settings.tickers)
+    historical_universe = (
+        load_dynamic_universe_history() if args.use_universe_history else {}
+    )
+    dynamic_symbols = sorted(
+        {
+            ticker
+            for date, tickers in historical_universe.items()
+            if (args.start is None or date >= pd.Timestamp(args.start))
+            and (args.end is None or date <= pd.Timestamp(args.end))
+            for ticker in tickers
+        }
+    )
+    signal_tickers = list(dict.fromkeys([*settings.tickers, *dynamic_symbols]))
+    product_routes = {
+        ticker: product
+        for ticker in signal_tickers
+        if (
+            product := preferred_leveraged_long_product(
+                ticker,
+                allowlist=list(settings.leveraged_etf_allowlist),
+            )
+        )
+    }
+    tickers_to_load = list(signal_tickers)
+    tickers_to_load.extend(product_routes.values())
     if settings.market_regime_filter_enabled:
         tickers_to_load.append(settings.market_regime_ticker)
     if settings.relative_strength_filter_enabled:
@@ -35,8 +80,17 @@ def main() -> None:
     if settings.use_ai_score and "^VIX" not in tickers_to_load:
         tickers_to_load.append("^VIX")
     tickers_to_load = list(dict.fromkeys(tickers_to_load))
-    loaded_data = load_price_data_batch(tickers_to_load, period="2y")
-    ticker_data = {ticker: loaded_data[ticker] for ticker in settings.tickers}
+    loaded_data = load_price_data_batch(
+        list(dict.fromkeys(tickers_to_load)),
+        period="2y",
+        force_refresh=args.force_refresh,
+    )
+    ticker_data = {ticker: loaded_data[ticker] for ticker in signal_tickers}
+    leveraged_product_data = {
+        product: loaded_data[product]
+        for product in product_routes.values()
+        if product in loaded_data
+    }
     vix_df = loaded_data.get("^VIX")
     macro_df = load_macro_data(period="2y") if settings.use_ai_score else None
     benchmark_df = (
@@ -50,18 +104,46 @@ def main() -> None:
         else None
     )
 
-    bt_kwargs = portfolio_backtest_kwargs(
-        settings,
-        ticker_data=ticker_data,
-        benchmark_df=benchmark_df,
-        relative_strength_benchmark_df=relative_strength_benchmark_df,
-        vix_df=vix_df,
-        macro_df=macro_df,
-        allocation_method=args.allocation,
-    )
-    result, equity_df, trades_df = run_portfolio_backtest(**bt_kwargs)
+    if settings.portfolio_sleeves_enabled:
+        result, equity_df, trades_df = run_sleeved_portfolio_backtest(
+            settings,
+            ticker_data=ticker_data,
+            benchmark_df=benchmark_df,
+            relative_strength_benchmark_df=relative_strength_benchmark_df,
+            vix_df=vix_df,
+            macro_df=macro_df,
+            initial_cash=args.initial_cash,
+            evaluation_start_date=args.start,
+            evaluation_end_date=args.end,
+            leveraged_product_data=leveraged_product_data,
+            leveraged_product_routes=product_routes,
+            historical_universe_by_date=historical_universe,
+            base_universe=set(settings.tickers),
+            benchmark_universe=set(settings.tickers),
+            include_external_filters=args.include_external_filters,
+        )
+    else:
+        bt_kwargs = portfolio_backtest_kwargs(
+            settings,
+            ticker_data=ticker_data,
+            benchmark_df=benchmark_df,
+            relative_strength_benchmark_df=relative_strength_benchmark_df,
+            vix_df=vix_df,
+            macro_df=macro_df,
+            allocation_method=args.allocation,
+            evaluation_start_date=args.start,
+            evaluation_end_date=args.end,
+            initial_cash=args.initial_cash,
+            leveraged_product_data=leveraged_product_data,
+            leveraged_product_routes=product_routes,
+            historical_universe_by_date=historical_universe,
+            base_universe=set(settings.tickers),
+            benchmark_universe=set(settings.tickers),
+            include_external_filters=args.include_external_filters,
+        )
+        result, equity_df, trades_df = run_portfolio_backtest(**bt_kwargs)
 
-    output_dir = Path("logs/portfolio_backtest")
+    output_dir = args.outdir
     save_portfolio_backtest_outputs(
         output_dir=output_dir,
         result=result,
diff --git a/src/settings.py b/src/settings.py
index 6a01fc5..6da797a 100644
--- a/src/settings.py
+++ b/src/settings.py
@@ -139,6 +139,8 @@ class StrategySettings(StrategyProfile):
     dynamic_universe_enabled: bool = False
     dynamic_count: int = 50
     allow_leveraged_etfs: bool = False
+    prefer_leveraged_products: bool = False
+    auto_discover_leveraged_products: bool = False
     leveraged_etf_allowlist: List[str] = field(default_factory=list)
     max_leveraged_etf_positions: int = 1
     max_effective_leverage_exposure_pct: float = 1.25
@@ -377,6 +379,10 @@ def validate_settings(settings: StrategySettings) -> StrategySettings:
         raise ValueError(
             "leveraged_etf_allowlist must not be empty when leveraged ETFs are enabled"
         )
+    if settings.prefer_leveraged_products and not settings.allow_leveraged_etfs:
+        raise ValueError(
+            "allow_leveraged_etfs must be true when leveraged products are preferred"
+        )
     if settings.max_leveraged_etf_positions <= 0:
         raise ValueError("max_leveraged_etf_positions must be positive")
     if settings.max_effective_leverage_exposure_pct <= 0:
diff --git a/src/sleeve_rebalance.py b/src/sleeve_rebalance.py
index f23c780..fc85e01 100644
--- a/src/sleeve_rebalance.py
+++ b/src/sleeve_rebalance.py
@@ -3,6 +3,7 @@
 from __future__ import annotations
 
 from dataclasses import dataclass
+from decimal import Decimal, ROUND_DOWN
 from typing import Any
 
 from src.portfolio_sleeves import (
@@ -87,7 +88,16 @@ def _plan_trim_from_sleeve(
         if price <= 0 or qty <= 0 or market_value <= 0:
             continue
         sell_value = min(remaining, market_value)
-        sell_qty = round(min(qty, sell_value / price), 4)
+        requested_qty = min(qty, sell_value / price)
+        if requested_qty >= qty:
+            sell_qty = qty
+        else:
+            sell_qty = float(
+                Decimal(str(requested_qty)).quantize(
+                    Decimal("0.000000001"),
+                    rounding=ROUND_DOWN,
+                )
+            )
         if sell_qty <= 0:
             continue
         actions.append(
@@ -187,7 +197,6 @@ def build_sleeve_rebalance_actions(
     if not snapshot.enabled:
         return []
 
-    actions: list[SleeveRebalanceAction] = []
     cash_min = min_cash_raise_usd if not allocation_mode else max(25.0, min_cash_raise_usd * 0.5)
     excess_min = min_excess_usd if not allocation_mode else max(25.0, min_excess_usd * 0.5)
 
@@ -198,36 +207,56 @@ def build_sleeve_rebalance_actions(
     cash_raise_needed = cash_budget is not None and (
         cash_budget.rebalance_needed if not allocation_mode else cash_deficit >= cash_min
     )
-    if cash_raise_needed and cash_deficit >= cash_min:
-        actions.extend(
-            _plan_trim_from_sleeve(
-                positions=positions,
-                sleeve_id=CORE_SLEEVE_ID,
-                sleeve_position_map=sleeve_position_map,
-                excess_notional=cash_deficit,
-                dust_min_usd=dust_min_usd,
-                reason_prefix="sleeve cash raise",
-            )
-        )
+    cash_trim_notional = (
+        cash_deficit if cash_raise_needed and cash_deficit >= cash_min else 0.0
+    )
 
+    excess_trim_by_sleeve: dict[str, float] = {}
     for sleeve_id in (CORE_SLEEVE_ID, TOURNAMENT_SLEEVE_ID):
         budget = snapshot.sleeves.get(sleeve_id)
         if budget is None:
             continue
         excess = budget.current_notional - budget.target_notional
+        excess_trim_notional = 0.0
         if allocation_mode:
-            if excess < excess_min:
-                continue
-        elif not budget.rebalance_needed or excess < excess_min:
+            if excess >= excess_min:
+                excess_trim_notional = excess
+        elif budget.rebalance_needed and excess >= excess_min:
+            excess_trim_notional = excess
+        excess_trim_by_sleeve[sleeve_id] = excess_trim_notional
+
+    # Any overweight trim also restores cash. Only add a core trim for the part
+    # of the cash deficit not already covered by core/tournament overweight.
+    planned_overweight_trim = sum(excess_trim_by_sleeve.values())
+    additional_cash_trim = max(0.0, cash_trim_notional - planned_overweight_trim)
+    if additional_cash_trim > 0:
+        excess_trim_by_sleeve[CORE_SLEEVE_ID] = (
+            excess_trim_by_sleeve.get(CORE_SLEEVE_ID, 0.0) + additional_cash_trim
+        )
+
+    actions: list[SleeveRebalanceAction] = []
+    for sleeve_id in (CORE_SLEEVE_ID, TOURNAMENT_SLEEVE_ID):
+        trim_notional = excess_trim_by_sleeve.get(sleeve_id, 0.0)
+        if trim_notional <= 0:
             continue
+
+        excess_trim_notional = trim_notional - (
+            additional_cash_trim if sleeve_id == CORE_SLEEVE_ID else 0.0
+        )
+        if additional_cash_trim > 0 and sleeve_id == CORE_SLEEVE_ID and excess_trim_notional > 0:
+            reason_prefix = "sleeve cash raise / core overweight trim"
+        elif additional_cash_trim > 0 and sleeve_id == CORE_SLEEVE_ID:
+            reason_prefix = "sleeve cash raise"
+        else:
+            reason_prefix = f"sleeve {sleeve_id} overweight trim"
         actions.extend(
             _plan_trim_from_sleeve(
                 positions=positions,
                 sleeve_id=sleeve_id,
                 sleeve_position_map=sleeve_position_map,
-                excess_notional=excess,
+                excess_notional=trim_notional,
                 dust_min_usd=dust_min_usd,
-                reason_prefix=f"sleeve {sleeve_id} overweight trim",
+                reason_prefix=reason_prefix,
             )
         )
 
diff --git a/src/trading/buy_pipeline.py b/src/trading/buy_pipeline.py
index 4cb3249..29fa8f0 100644
--- a/src/trading/buy_pipeline.py
+++ b/src/trading/buy_pipeline.py
@@ -5,6 +5,7 @@ from __future__ import annotations
 from src.buy_guards import apply_sector_score_bonus, apply_shared_buy_guards
 from src.instrument_meta import (
     adjust_position_cap_for_instrument,
+    check_instrument_buy_allowed,
     format_audit_reason,
     get_instrument,
 )
@@ -38,6 +39,7 @@ from src.trading.bot_helpers import (
     order_is_filled,
 )
 from src.trading.run_context import TradingRunContext
+from src.trading.leveraged_product_routing import resolve_leveraged_product_route
 from src.trading.tournament_buy_pipeline import run_tournament_buy_pipeline
 
 
@@ -98,12 +100,23 @@ def run_buy_pipeline(ctx: TradingRunContext) -> None:
             conviction = conviction_adjustments(ctx.settings, ai_score)
             if conviction.label != "neutral":
                 print(f"{ticker}: sizing {conviction.label}")
+
+            # Run the expensive broker/data product check only after the
+            # underlying has passed its normal signal and ranking gates.
+            route = resolve_leveraged_product_route(
+                ctx,
+                ticker,
+                signal="HOLD",
+                fallback_price=float(latest["close"]),
+            )
+            execution_ticker = ticker
     
             llm_is_ok = None
             llm_reason = ""
     
             held_position = effective_position(
-                ctx.positions_by_symbol.get(ticker), min_usd=ctx.dust_min_usd
+                ctx.positions_by_symbol.get(execution_ticker),
+                min_usd=ctx.dust_min_usd,
             )
             if held_position is not None:
                 # 13-A: 이미 보유 중인 종목이라도 목표 비중에 미달하면 추가 매수 (Averaging up/down)
@@ -112,7 +125,7 @@ def run_buy_pipeline(ctx: TradingRunContext) -> None:
                     cash=ctx.cash,
                     portfolio_value=float(ctx.account["portfolio_value"]),
                     current_position_value=float(held_position["market_value"]),
-                    ticker=ticker,
+                    ticker=execution_ticker,
                     position_mult=conviction.position_mult,
                     cash_buffer_mult=conviction.cash_buffer_mult,
                     settings=ctx.settings,
@@ -132,7 +145,7 @@ def run_buy_pipeline(ctx: TradingRunContext) -> None:
                     cash=ctx.cash,
                     current_positions_count=ctx.meaningful_positions_count,
                     portfolio_value=float(ctx.account["portfolio_value"]),
-                    ticker=ticker,
+                    ticker=execution_ticker,
                     position_mult=conviction.position_mult,
                     cash_buffer_mult=conviction.cash_buffer_mult,
                     settings=ctx.settings,
@@ -167,6 +180,7 @@ def run_buy_pipeline(ctx: TradingRunContext) -> None:
                 open_symbols=ctx.guard_open_symbols,
                 ticker_data=ctx.ticker_data,
                 vix_df=ctx.vix_df,
+                instrument_ticker=execution_ticker,
                 macro_risk_active=macro_risk_active,
                 macro_risk_reason=macro_risk_reason,
                 margin_leverage_block_active=ctx.margin_leverage_block_active,
@@ -190,6 +204,109 @@ def run_buy_pipeline(ctx: TradingRunContext) -> None:
             risk_allowed = rank_gate.risk_allowed
             risk_reason = rank_gate.risk_reason
             target_amount = rank_gate.target_amount
+
+            if risk_allowed:
+                route = resolve_leveraged_product_route(
+                    ctx,
+                    ticker,
+                    signal=signal,
+                    fallback_price=float(latest["close"]),
+                )
+                execution_ticker = route.execution_ticker
+                if not route.route_allowed:
+                    risk_allowed = False
+                    risk_reason = route.reason
+                    target_amount = 0.0
+                    print(f"{ticker}: leveraged product routing blocked ({route.reason})")
+                elif route.leveraged:
+                    print(
+                        f"{ticker}: leveraged product route -> {execution_ticker} "
+                        f"({route.reason})"
+                    )
+                    held_position = effective_position(
+                        ctx.positions_by_symbol.get(execution_ticker),
+                        min_usd=ctx.dust_min_usd,
+                    )
+                    if held_position is not None:
+                        product_risk = check_additional_buy_allowed(
+                            signal=signal,
+                            cash=ctx.cash,
+                            portfolio_value=float(ctx.account["portfolio_value"]),
+                            current_position_value=float(held_position["market_value"]),
+                            ticker=execution_ticker,
+                            position_mult=conviction.position_mult,
+                            cash_buffer_mult=conviction.cash_buffer_mult,
+                            settings=ctx.settings,
+                        )
+                    else:
+                        product_risk = check_buy_allowed(
+                            signal=signal,
+                            cash=ctx.cash,
+                            current_positions_count=ctx.meaningful_positions_count,
+                            portfolio_value=float(ctx.account["portfolio_value"]),
+                            ticker=execution_ticker,
+                            position_mult=conviction.position_mult,
+                            cash_buffer_mult=conviction.cash_buffer_mult,
+                            settings=ctx.settings,
+                        )
+                    if not product_risk.allowed:
+                        risk_allowed = False
+                        risk_reason = product_risk.reason
+                        target_amount = 0.0
+                    else:
+                        target_amount = product_risk.target_amount
+                        instrument_ok, instrument_reason = check_instrument_buy_allowed(
+                            execution_ticker,
+                            ctx.guard_open_symbols,
+                            allow_leveraged_etfs=bool(
+                                getattr(ctx.settings, "allow_leveraged_etfs", False)
+                            ),
+                            leveraged_etf_allowlist=list(
+                                getattr(ctx.settings, "leveraged_etf_allowlist", [])
+                            ),
+                            max_leveraged_etf_positions=int(
+                                getattr(ctx.settings, "max_leveraged_etf_positions", 1)
+                            ),
+                            block_leveraged_etfs_vix_above=float(
+                                getattr(
+                                    ctx.settings,
+                                    "block_leveraged_etfs_vix_above",
+                                    0.0,
+                                )
+                            ),
+                            vix_df=ctx.vix_df,
+                        )
+                        if not instrument_ok:
+                            risk_allowed = False
+                            risk_reason = instrument_reason
+                            target_amount = 0.0
+                elif bool(getattr(ctx.settings, "auto_discover_leveraged_products", False)):
+                    print(f"{ticker}: ordinary-stock fallback ({route.reason})")
+
+            equivalent_existing_value = (
+                float(held_position["market_value"])
+                if held_position is not None
+                else 0.0
+            )
+            if risk_allowed and route.leveraged:
+                source_position = effective_position(
+                    ctx.positions_by_symbol.get(ticker),
+                    min_usd=ctx.dust_min_usd,
+                )
+                source_value = (
+                    float(source_position["market_value"])
+                    if source_position is not None
+                    else 0.0
+                )
+                source_equivalent = source_value / get_instrument(
+                    execution_ticker
+                ).abs_multiple
+                equivalent_existing_value += source_equivalent
+                target_amount = max(0.0, target_amount - source_equivalent)
+                if target_amount < 10.0:
+                    risk_allowed = False
+                    risk_reason = "combined underlying/product target allocation reached"
+                    target_amount = 0.0
     
             if risk_allowed and held_position is None and llm_is_ok is False:
                 llm_advisory_only = bool(getattr(ctx.settings, "llm_advisory_only", True))
@@ -217,7 +334,7 @@ def run_buy_pipeline(ctx: TradingRunContext) -> None:
     
             if risk_allowed:
                 safety = apply_buy_safety_limits(
-                    ticker=ticker,
+                    ticker=execution_ticker,
                     order_amount=order_amount,
                     submitted_notional_today=ctx.submitted_notional_today,
                     recent_buy_symbols=ctx.recent_buy_symbols,
@@ -230,7 +347,7 @@ def run_buy_pipeline(ctx: TradingRunContext) -> None:
     
             if risk_allowed:
                 exposure = apply_portfolio_exposure_limits(
-                    ticker=ticker,
+                    ticker=execution_ticker,
                     order_amount=order_amount,
                     cash=float(ctx.cash),
                     portfolio_value=float(ctx.account["portfolio_value"]),
@@ -246,7 +363,7 @@ def run_buy_pipeline(ctx: TradingRunContext) -> None:
     
             if risk_allowed:
                 leverage_cap = apply_effective_leverage_exposure_limits(
-                    ticker=ticker,
+                    ticker=execution_ticker,
                     order_amount=order_amount,
                     portfolio_value=float(ctx.account["portfolio_value"]),
                     positions_by_symbol=ctx.positions_by_symbol,
@@ -276,7 +393,7 @@ def run_buy_pipeline(ctx: TradingRunContext) -> None:
             )
     
             print(
-                f"{ticker}: signal={signal}, "
+                f"{ticker}{'->' + execution_ticker if route.leveraged else ''}: signal={signal}, "
                 f"risk_allowed={risk_allowed}, "
                 f"reason='{risk_reason}', "
                 f"target_amount={target_amount:.2f}, "
@@ -315,7 +432,9 @@ def run_buy_pipeline(ctx: TradingRunContext) -> None:
     
             if risk_allowed:
                 approved_buys.append({
-                    "ticker": ticker,
+                    "ticker": execution_ticker,
+                    "signal_ticker": ticker,
+                    "route_reason": route.reason,
                     "order_amount": order_amount,
                     "ai_score": ai_score,
                     "rank_ai_score": rank_gate.score,
@@ -323,13 +442,14 @@ def run_buy_pipeline(ctx: TradingRunContext) -> None:
                     "risk_reason": risk_reason,
                     "signal": signal,
                     "llm_verdict": format_llm_verdict(llm_is_ok, llm_reason),
-                    "limit_price": float(latest["close"]),
+                    "limit_price": route.reference_price,
                     "is_new_position": held_position is None,
                     "current_position_value": (
                         float(held_position["market_value"])
                         if held_position is not None
                         else 0.0
                     ),
+                    "equivalent_existing_value": equivalent_existing_value,
                 })
     
         except Exception as exc:
@@ -421,7 +541,7 @@ def run_buy_pipeline(ctx: TradingRunContext) -> None:
         )
         remaining_cap = max(
             0.0,
-            position_cap - float(candidate.get("current_position_value", 0.0)),
+            position_cap - float(candidate.get("equivalent_existing_value", 0.0)),
         )
         candidate["order_amount"] = min(
             float(candidate["order_amount"]), remaining_cap
diff --git a/src/trading/exit_pipeline.py b/src/trading/exit_pipeline.py
index 42c8070..37497e8 100644
--- a/src/trading/exit_pipeline.py
+++ b/src/trading/exit_pipeline.py
@@ -18,10 +18,208 @@ from src.trading.bot_helpers import (
     execution_block_label,
     execution_reference_price,
     get_signal_for_ticker,
+    order_is_filled,
     resolve_full_exit_reason,
 )
 from src.regime_stop_policy import resolve_exit_stop_params_from_settings
 from src.trading.run_context import TradingRunContext
+from src.instrument_meta import get_instrument, signal_source_ticker
+
+
+def _find_open_sell_order(ctx: TradingRunContext, ticker: str) -> dict | None:
+    symbol = str(ticker).upper()
+    open_orders = getattr(getattr(ctx, "sleeve_ctx", None), "open_orders", [])
+    for order in open_orders or []:
+        order_symbol = str(order.get("symbol") or "").upper()
+        order_side = str(order.get("side") or "").upper()
+        if order_symbol == symbol and order_side.endswith("SELL"):
+            return order
+    return None
+
+
+def _remember_open_sell_order(
+    ctx: TradingRunContext,
+    *,
+    ticker: str,
+    order_id: str,
+    status: str,
+) -> None:
+    open_orders = getattr(getattr(ctx, "sleeve_ctx", None), "open_orders", None)
+    if open_orders is None or _find_open_sell_order(ctx, ticker) is not None:
+        return
+    open_orders.append(
+        {
+            "id": str(order_id),
+            "symbol": str(ticker).upper(),
+            "side": "SELL",
+            "status": str(status),
+        }
+    )
+
+
+def _drop_dust_from_run_context(ctx: TradingRunContext, ticker: str) -> None:
+    ctx.positions_by_symbol.pop(ticker, None)
+    ctx.open_symbols.discard(ticker)
+    ctx.guard_open_symbols.discard(ticker)
+    ctx.partial_exit_taken.pop(ticker, None)
+
+
+def _cleanup_dust_position(
+    ctx: TradingRunContext,
+    position: dict,
+    *,
+    phase: str = "initial",
+) -> bool:
+    """Handle one dust position and return True when normal exit logic should skip it."""
+    if not is_dust_position(position, min_usd=ctx.dust_min_usd):
+        return False
+
+    ticker = str(position["symbol"]).upper()
+    dust_mv = float(position["market_value"])
+    dust_reason = f"dust position cleanup (<${ctx.dust_min_usd:g} market value)"
+    print(
+        f"{ticker}: DUST position qty={position['qty']}, "
+        f"market_value={dust_mv:.6f} — scheduling close"
+    )
+    ctx.exit_summary_rows.append(
+        f"{ticker}: DUST exit, market_value=${dust_mv:.6f}"
+    )
+
+    pending_order = _find_open_sell_order(ctx, ticker)
+    if pending_order is not None:
+        pending_status = str(pending_order.get("status") or "OPEN")
+        pending_id = str(pending_order.get("id") or "")
+        print(
+            f"  DUST_CLOSE_PENDING: {ticker}, order_id={pending_id}, "
+            f"status={pending_status} — duplicate skipped"
+        )
+        audit_log(
+            ctx.audit_ctx,
+            event_type="DUST_EXIT",
+            ticker=ticker,
+            action="CLOSE",
+            status="PENDING",
+            reason=f"{dust_reason}; existing sell order",
+            profile_name=ctx.profile_name,
+            regime=ctx.current_regime,
+            order_id=pending_id,
+        )
+        _drop_dust_from_run_context(ctx, ticker)
+        return True
+
+    audit_log(
+        ctx.audit_ctx,
+        event_type="DUST_EXIT",
+        ticker=ticker,
+        action="CLOSE",
+        status="SUBMITTED" if ctx.can_submit_orders else "DRY_RUN",
+        reason=dust_reason,
+        profile_name=ctx.profile_name,
+        regime=ctx.current_regime,
+    )
+    if not ctx.can_submit_orders:
+        print(f"  DRY_RUN: would close dust position {ticker}")
+        _drop_dust_from_run_context(ctx, ticker)
+        return True
+
+    try:
+        dust_submission = ctx.broker_adapter.submit_sell_qty(
+            ticker,
+            float(position["qty"]),
+            limit_price=float(position.get("current_price") or 0.0),
+            market_clock=ctx.market_clock,
+            slippage_pct=ctx.extended_slippage,
+            client_order_id=f"dust_{ctx.run_id}_{phase}_{ticker}",
+            close_all=True,
+        )
+        ctx.live_order_count += 1
+        log_order(
+            ticker=ticker,
+            notional=0.0,
+            order_id=dust_submission.order_id,
+            status=dust_submission.status,
+            side=dust_submission.side,
+            order_type=dust_submission.order_type,
+            reason=dust_reason,
+        )
+        checked_order = ctx.broker_adapter.wait_for_order_status(
+            dust_submission.order_id
+        )
+        checked_order_type = checked_order.get("type") or dust_submission.order_type
+        checked_status = str(checked_order["status"])
+        log_order_status(
+            ticker=ticker,
+            order_id=str(checked_order["id"]),
+            status=checked_status,
+            side=str(checked_order["side"]),
+            order_type=str(checked_order_type),
+            filled_qty=checked_order.get("filled_qty"),
+            filled_avg_price=checked_order.get("filled_avg_price"),
+            reason=dust_reason,
+        )
+        audit_log(
+            ctx.audit_ctx,
+            event_type="DUST_EXIT_STATUS",
+            ticker=ticker,
+            action="CLOSE",
+            status=checked_status,
+            reason=dust_reason,
+            profile_name=ctx.profile_name,
+            regime=ctx.current_regime,
+            order_id=str(checked_order["id"]),
+            order_type=str(checked_order_type),
+            side=str(checked_order["side"]),
+            filled_qty=checked_order.get("filled_qty"),
+            filled_avg_price=checked_order.get("filled_avg_price"),
+        )
+        if order_is_filled(checked_status):
+            print(
+                f"  PAPER_DUST_CLOSED: {ticker}, "
+                f"order_id={checked_order['id']}, status={checked_status}"
+            )
+            notify_info(
+                "🧹 Dust position closed",
+                f"{ticker}: closed negligible position (${dust_mv:.4f})",
+            )
+            ctx.sleeve_ctx.record_exit(ticker)
+        else:
+            print(
+                f"  PAPER_DUST_PENDING: {ticker}, "
+                f"order_id={checked_order['id']}, status={checked_status}"
+            )
+            _remember_open_sell_order(
+                ctx,
+                ticker=ticker,
+                order_id=str(checked_order["id"]),
+                status=checked_status,
+            )
+    except Exception as exc:
+        print(f"  Dust close error for {ticker}: {exc}")
+        ctx.api_error_count += 1
+        if isinstance(exc, ConnectionError) and ctx.execute_orders:
+            notify_error(
+                f"CRITICAL: Network error during dust close for {ticker}",
+                exc,
+            )
+
+    _drop_dust_from_run_context(ctx, ticker)
+    return True
+
+
+def _run_followup_dust_cleanup(ctx: TradingRunContext) -> None:
+    """Catch fractional remnants created by fills during the same run."""
+    if not ctx.can_submit_orders:
+        return
+    try:
+        refreshed_positions = ctx.broker_adapter.get_positions()
+        ctx.sleeve_ctx.open_orders = ctx.broker_adapter.get_open_orders()
+    except Exception as exc:
+        print(f"Warning: follow-up dust snapshot failed: {exc}")
+        ctx.api_error_count += 1
+        return
+
+    for position in refreshed_positions:
+        _cleanup_dust_position(ctx, position, phase="followup")
 
 
 def run_exit_pipeline(ctx: TradingRunContext) -> None:
@@ -32,80 +230,13 @@ def run_exit_pipeline(ctx: TradingRunContext) -> None:
     
         for position in ctx.positions:
             ticker = str(position["symbol"]).upper()
+            signal_ticker = signal_source_ticker(ticker)
             try:
-                if is_dust_position(position, min_usd=ctx.dust_min_usd):
-                    dust_reason = (
-                        f"dust position cleanup (<${ctx.dust_min_usd:g} market value)"
-                    )
-                    dust_mv = float(position["market_value"])
-                    print(
-                        f"{ticker}: DUST position qty={position['qty']}, "
-                        f"market_value={dust_mv:.6f} — scheduling close"
-                    )
-                    ctx.exit_summary_rows.append(
-                        f"{ticker}: DUST exit, market_value=${dust_mv:.6f}"
-                    )
-                    audit_log(
-                        ctx.audit_ctx,
-                        event_type="DUST_EXIT",
-                        ticker=ticker,
-                        action="CLOSE",
-                        status="SUBMITTED" if ctx.can_submit_orders else "DRY_RUN",
-                        reason=dust_reason,
-                        profile_name=ctx.profile_name,
-                        regime=ctx.current_regime,
-                    )
-                    if ctx.can_submit_orders:
-                        try:
-                            dust_qty = float(position["qty"])
-                            dust_submission = ctx.broker_adapter.submit_sell_qty(
-                                ticker,
-                                dust_qty,
-                                limit_price=float(position.get("current_price") or 0.0),
-                                market_clock=ctx.market_clock,
-                                slippage_pct=ctx.extended_slippage,
-                                client_order_id=f"dust_{ctx.run_id}_{ticker}",
-                            )
-                            ctx.live_order_count += 1
-                            log_order(
-                                ticker=ticker,
-                                notional=0.0,
-                                order_id=dust_submission.order_id,
-                                status=dust_submission.status,
-                                side=dust_submission.side,
-                                order_type=dust_submission.order_type,
-                                reason=dust_reason,
-                            )
-                            print(
-                                f"  PAPER_DUST_CLOSE: {ticker}, "
-                                f"order_id={dust_submission.order_id}, "
-                                f"status={dust_submission.status}"
-                            )
-                            notify_info(
-                                "🧹 Dust position closed",
-                                f"{ticker}: closed negligible position (${dust_mv:.4f})",
-                            )
-                        except Exception as e:
-                            print(f"  Dust close error for {ticker}: {e}")
-                            ctx.api_error_count += 1
-                            if isinstance(e, ConnectionError) and ctx.execute_orders:
-                                notify_error(
-                                    f"CRITICAL: Network error during dust close for {ticker}",
-                                    e,
-                                )
-                    else:
-                        print(f"  DRY_RUN: would close dust position {ticker}")
-                    ctx.positions_by_symbol.pop(ticker, None)
-                    ctx.open_symbols.discard(ticker)
-                    ctx.guard_open_symbols.discard(ticker)
-                    ctx.partial_exit_taken.pop(ticker, None)
-                    ctx.meaningful_positions_count = max(
-                        0, ctx.meaningful_positions_count - 1
-                    )
+                if _cleanup_dust_position(ctx, position):
                     continue
     
                 data_fresh, data_reason = ctx.price_data_freshness.get(
-                    ticker,
+                    signal_ticker,
                     (False, "price data not loaded"),
                 )
                 if not data_fresh:
@@ -132,8 +263,8 @@ def run_exit_pipeline(ctx: TradingRunContext) -> None:
                     ctx.peaks[ticker] = current_price
     
                 signal, latest, ai_score = get_signal_for_ticker(
-                    ticker,
-                    ctx.ticker_data[ticker],
+                    signal_ticker,
+                    ctx.ticker_data[signal_ticker],
                     ctx.settings,
                     ai_model_bundle=ctx.ai_model_bundle,
                     market_regime_bullish=ctx.market_regime_bullish,
@@ -185,8 +316,13 @@ def run_exit_pipeline(ctx: TradingRunContext) -> None:
                     atr_val = float(latest["atr"])
                     if atr_val > 0 and peak_price > 0:
                         multiplier = float(getattr(ctx.settings, "atr_multiplier", 3.0))
-                        # ATR 기반의 변동성을 백분율로 변환 (ATR * Multiplier 만큼 하락 시 스탑)
-                        trailing_pct = (atr_val * multiplier) / peak_price
+                        signal_price = float(latest["close"])
+                        leverage_multiple = get_instrument(ticker).abs_multiple
+                        # Underlying ATR drives a direct leveraged product's stop,
+                        # scaled by its daily leverage multiple.
+                        trailing_pct = (
+                            atr_val * multiplier * leverage_multiple / signal_price
+                        )
                         # 합리적 범위 내에서 제한 (예: 최소 2% ~ 최대 20%)
                         trailing_pct = max(0.02, min(0.20, trailing_pct))
     
@@ -426,6 +562,29 @@ def run_exit_pipeline(ctx: TradingRunContext) -> None:
                         ai_score=ai_score,
                     )
                     continue
+
+                pending_order = _find_open_sell_order(ctx, ticker)
+                if pending_order is not None:
+                    pending_id = str(pending_order.get("id") or "")
+                    pending_status = str(pending_order.get("status") or "OPEN")
+                    print(
+                        f"  CLOSE_PENDING: {ticker}, order_id={pending_id}, "
+                        f"status={pending_status} — duplicate skipped"
+                    )
+                    audit_log(
+                        ctx.audit_ctx,
+                        event_type="SKIP_EXIT",
+                        ticker=ticker,
+                        action="CLOSE",
+                        status="PENDING",
+                        reason="existing sell order pending",
+                        profile_name=ctx.profile_name,
+                        regime=ctx.current_regime,
+                        signal=signal,
+                        ai_score=ai_score,
+                        order_id=pending_id,
+                    )
+                    continue
     
                 exit_qty = float(position["qty"])
                 exit_submission = ctx.broker_adapter.submit_sell_qty(
@@ -438,6 +597,7 @@ def run_exit_pipeline(ctx: TradingRunContext) -> None:
                     market_clock=ctx.market_clock,
                     slippage_pct=ctx.extended_slippage,
                     client_order_id=f"exit_{ctx.run_id}_{ticker}",
+                    close_all=True,
                 )
                 ctx.live_order_count += 1
     
@@ -517,8 +677,17 @@ def run_exit_pipeline(ctx: TradingRunContext) -> None:
                     filled_qty=checked_order["filled_qty"],
                     filled_avg_price=checked_order["filled_avg_price"],
                 )
-    
-                if ticker in ctx.open_symbols:
+
+                exit_filled = order_is_filled(str(checked_order["status"]))
+                if not exit_filled:
+                    _remember_open_sell_order(
+                        ctx,
+                        ticker=ticker,
+                        order_id=str(checked_order["id"]),
+                        status=str(checked_order["status"]),
+                    )
+
+                if exit_filled and ticker in ctx.open_symbols:
                     ctx.open_symbols.remove(ticker)
                     ctx.positions_by_symbol.pop(ticker, None)
                     ctx.partial_exit_taken.pop(ticker, None)
@@ -543,4 +712,6 @@ def run_exit_pipeline(ctx: TradingRunContext) -> None:
                     regime=ctx.current_regime,
                 )
                 notify_error(f"{ticker} exit check error", exc)
+
+    _run_followup_dust_cleanup(ctx)
     
diff --git a/src/trading/run_context.py b/src/trading/run_context.py
index 8450c70..5701e12 100644
--- a/src/trading/run_context.py
+++ b/src/trading/run_context.py
@@ -44,6 +44,7 @@ from src.sleeve_runtime import SleeveRunContext, init_sleeve_run_context
 from src.strategy import is_bullish_market_regime
 from src.partial_exit_policy import load_partial_exit_state
 from src.trading.bot_helpers import load_peaks, offline_account_summary
+from src.instrument_meta import signal_source_ticker
 from src.trading_config_guard import (
     apply_environment_profile,
     resolve_trading_environment,
@@ -294,7 +295,10 @@ def build_trading_run_context(*, execute_orders: bool) -> TradingRunContext:
             limit=int(getattr(settings, "dynamic_count", 50))
         )
     
-    tickers_to_load = list(dict.fromkeys([*settings.tickers, *open_symbols]))
+    held_signal_sources = [signal_source_ticker(symbol) for symbol in open_symbols]
+    tickers_to_load = list(
+        dict.fromkeys([*settings.tickers, *open_symbols, *held_signal_sources])
+    )
     # Always include SPY and ^VIX for live market regime calculation
     if "SPY" not in tickers_to_load:
         tickers_to_load.append("SPY")
diff --git a/src/trading/sleeve_rebalance_pipeline.py b/src/trading/sleeve_rebalance_pipeline.py
index 2eaf71e..c03a6c8 100644
--- a/src/trading/sleeve_rebalance_pipeline.py
+++ b/src/trading/sleeve_rebalance_pipeline.py
@@ -2,6 +2,9 @@
 
 from __future__ import annotations
 
+from dataclasses import replace
+from math import floor
+
 from src.logger import log_order, log_order_status
 from src.notifier import notify_error, notify_info, notify_order
 from src.sleeve_rebalance import (
@@ -24,6 +27,58 @@ from src.trading.bot_helpers import (
 from src.trading.run_context import TradingRunContext
 
 
+def _find_open_sell_order(ctx: TradingRunContext, ticker: str) -> dict | None:
+    symbol = str(ticker).upper()
+    for order in getattr(ctx.sleeve_ctx, "open_orders", []) or []:
+        order_symbol = str(order.get("symbol") or "").upper()
+        order_side = str(order.get("side") or "").upper()
+        if order_symbol == symbol and order_side.endswith("SELL"):
+            return order
+    return None
+
+
+def _remember_open_sell_order(
+    ctx: TradingRunContext,
+    *,
+    ticker: str,
+    order_id: str,
+    status: str,
+) -> None:
+    if _find_open_sell_order(ctx, ticker) is not None:
+        return
+    open_orders = getattr(ctx.sleeve_ctx, "open_orders", None)
+    if open_orders is None:
+        return
+    open_orders.append(
+        {
+            "id": str(order_id),
+            "symbol": str(ticker).upper(),
+            "side": "SELL",
+            "status": str(status),
+        }
+    )
+
+
+def _coalesce_sell_actions(
+    actions: list[SleeveRebalanceAction],
+) -> list[SleeveRebalanceAction]:
+    """Collapse overlapping plans without adding their quantities twice."""
+    merged: dict[str, SleeveRebalanceAction] = {}
+    for action in actions:
+        ticker = str(action.ticker).upper()
+        existing = merged.get(ticker)
+        if existing is None:
+            merged[ticker] = replace(action, ticker=ticker)
+            continue
+        reasons = list(dict.fromkeys([existing.reason, action.reason]))
+        merged[ticker] = replace(
+            existing,
+            sell_qty=max(existing.sell_qty, action.sell_qty),
+            reason="; ".join(reasons),
+        )
+    return list(merged.values())
+
+
 def _apply_retag_actions(ctx: TradingRunContext, actions: list[SleeveRetagAction]) -> None:
     for action in actions:
         ctx.sleeve_ctx.record_retag(action.ticker, to_sleeve_id=action.to_sleeve_id)
@@ -50,15 +105,25 @@ def _execute_sell_actions(
     *,
     event_prefix: str,
 ) -> None:
+    actions = _coalesce_sell_actions(actions)
     if not actions:
         return
 
     print(f"{event_prefix}: {len(actions)} trim action(s) planned")
-    for action in actions:
+    for action_index, action in enumerate(actions, start=1):
         ticker = action.ticker
         if action.sell_qty <= 0:
             continue
 
+        pending_order = _find_open_sell_order(ctx, ticker)
+        if pending_order is not None:
+            pending_status = str(pending_order.get("status") or "OPEN")
+            ctx.exit_summary_rows.append(
+                f"{ticker}: {event_prefix}_SKIP existing sell order "
+                f"status={pending_status}"
+            )
+            continue
+
         if not ctx.can_submit_orders:
             label = execution_block_label(ctx.execute_orders, ctx.market_clock)
             ctx.exit_summary_rows.append(
@@ -80,8 +145,15 @@ def _execute_sell_actions(
         position = ctx.positions_by_symbol.get(ticker) or {}
         try:
             current_price = float(position.get("current_price") or 0.0)
+            current_qty = float(position.get("qty") or 0.0)
         except (TypeError, ValueError):
             current_price = 0.0
+            current_qty = 0.0
+        if current_qty <= 0:
+            ctx.exit_summary_rows.append(
+                f"{ticker}: {event_prefix}_SKIP no position quantity"
+            )
+            continue
         if current_price <= 0:
             ctx.exit_summary_rows.append(
                 f"{ticker}: {event_prefix}_SKIP no current price for limit order"
@@ -100,18 +172,35 @@ def _execute_sell_actions(
             continue
 
         try:
+            sell_qty = min(float(action.sell_qty), current_qty)
+            close_tolerance = max(1e-9, current_qty * 1e-9)
+            close_all = sell_qty >= current_qty - close_tolerance
+            if close_all:
+                sell_qty = current_qty
+            else:
+                asset = ctx.broker_adapter.get_asset_info(ticker)
+                if not bool(asset.get("fractionable", True)):
+                    sell_qty = float(floor(sell_qty))
+                    if sell_qty <= 0:
+                        ctx.exit_summary_rows.append(
+                            f"{ticker}: {event_prefix}_SKIP non-fractionable qty "
+                            f"below one share"
+                        )
+                        continue
+
             submission = ctx.broker_adapter.submit_sell_qty(
                 ticker=ticker,
-                qty=action.sell_qty,
+                qty=sell_qty,
                 limit_price=execution_reference_price(None, fallback=current_price),
                 market_clock=ctx.market_clock,
                 slippage_pct=ctx.extended_slippage,
-                client_order_id=f"slev_{ctx.run_id}_{ticker}",
+                client_order_id=f"slev_{ctx.run_id}_{ticker}_{action_index}",
+                close_all=close_all,
             )
             ctx.live_order_count += 1
             log_order(
                 ticker=ticker,
-                notional=round(action.sell_qty * current_price, 2),
+                notional=round(sell_qty * current_price, 2),
                 order_id=submission.order_id,
                 status=submission.status,
                 side=submission.side,
@@ -143,7 +232,7 @@ def _execute_sell_actions(
             )
             ctx.exit_summary_rows.append(
                 f"{ticker}: {event_prefix} status={checked['status']} "
-                f"qty={action.sell_qty} reason={action.reason}"
+                f"qty={sell_qty} reason={action.reason}"
             )
             if order_is_filled(checked["status"]):
                 notify_order(
@@ -155,9 +244,22 @@ def _execute_sell_actions(
                     filled_qty=checked["filled_qty"],
                     filled_avg_price=checked["filled_avg_price"],
                 )
-                remaining_qty = float(ctx.positions_by_symbol.get(ticker, {}).get("qty") or 0.0)
-                if remaining_qty <= action.sell_qty + 1e-6:
+                try:
+                    filled_qty = float(checked.get("filled_qty") or sell_qty)
+                except (TypeError, ValueError):
+                    filled_qty = sell_qty
+                remaining_qty = max(0.0, current_qty - filled_qty)
+                position["qty"] = remaining_qty
+                position["market_value"] = remaining_qty * current_price
+                if remaining_qty <= close_tolerance:
                     ctx.sleeve_ctx.record_exit(ticker)
+            else:
+                _remember_open_sell_order(
+                    ctx,
+                    ticker=ticker,
+                    order_id=str(checked["id"]),
+                    status=str(checked["status"]),
+                )
         except Exception as exc:
             if isinstance(exc, ConnectionError) and ctx.execute_orders:
                 notify_error(
diff --git a/src/trading/tournament_buy_pipeline.py b/src/trading/tournament_buy_pipeline.py
index 3644720..aacb18e 100644
--- a/src/trading/tournament_buy_pipeline.py
+++ b/src/trading/tournament_buy_pipeline.py
@@ -22,6 +22,7 @@ from src.trading.bot_helpers import (
     order_is_filled,
 )
 from src.trading.run_context import TradingRunContext
+from src.trading.leveraged_product_routing import resolve_leveraged_product_route
 from src.trading_config_guard import load_named_profile_overlay
 
 
@@ -134,8 +135,33 @@ def run_tournament_buy_pipeline(ctx: TradingRunContext) -> None:
             )
             continue
 
-        instrument_ok, instrument_reason = check_instrument_buy_allowed(
+        route = resolve_leveraged_product_route(
+            ctx,
             ticker,
+            signal=signal,
+            fallback_price=float(latest["close"]),
+        )
+        if not route.route_allowed:
+            ctx.buy_summary_rows.append(
+                f"{ticker}: TOURNAMENT_NOT_ALLOWED {route.reason}"
+            )
+            continue
+        execution_ticker = route.execution_ticker
+        if effective_position(
+            ctx.positions_by_symbol.get(execution_ticker),
+            min_usd=ctx.dust_min_usd,
+        ):
+            continue
+        if route.leveraged:
+            print(
+                f"{ticker}: tournament leveraged product route -> "
+                f"{execution_ticker}"
+            )
+        elif bool(getattr(ctx.settings, "auto_discover_leveraged_products", False)):
+            print(f"{ticker}: tournament ordinary-stock fallback ({route.reason})")
+
+        instrument_ok, instrument_reason = check_instrument_buy_allowed(
+            execution_ticker,
             ctx.guard_open_symbols,
             allow_leveraged_etfs=bool(
                 getattr(tournament_settings, "allow_leveraged_etfs", False)
@@ -177,7 +203,10 @@ def run_tournament_buy_pipeline(ctx: TradingRunContext) -> None:
             continue
 
         position_pct = float(getattr(tournament_settings, "max_position_pct", 0.35))
-        position_pct = adjust_position_cap_for_instrument(position_pct, ticker)
+        position_pct = adjust_position_cap_for_instrument(
+            position_pct,
+            execution_ticker,
+        )
         target_amount = min(sleeve_cash, portfolio_value * position_pct)
         if target_amount < 10.0:
             ctx.buy_summary_rows.append(
@@ -196,7 +225,7 @@ def run_tournament_buy_pipeline(ctx: TradingRunContext) -> None:
             tournament_settings,
         )
         leverage_cap = apply_effective_leverage_exposure_limits(
-            ticker=ticker,
+            ticker=execution_ticker,
             order_amount=order_amount,
             portfolio_value=portfolio_value,
             positions_by_symbol=ctx.positions_by_symbol,
@@ -236,19 +265,16 @@ def run_tournament_buy_pipeline(ctx: TradingRunContext) -> None:
             )
             continue
 
-        limit_price = execution_reference_price(
-            latest.to_dict() if hasattr(latest, "to_dict") else None,
-            fallback=float(latest["close"]),
-        )
+        limit_price = route.reference_price
         budget_before = ctx.sleeve_ctx.budget_remaining.get(TOURNAMENT_SLEEVE_ID)
         buy_intent = build_buy_intent(
             run_id=ctx.run_id,
-            ticker=ticker,
+            ticker=execution_ticker,
             notional=order_amount,
             signal=signal,
             ai_score=ai_score,
             risk_reason=alpha.reason,
-            client_order_id=f"tour_{ctx.run_id}_{ticker}",
+            client_order_id=f"tour_{ctx.run_id}_{execution_ticker}",
             **ctx.sleeve_ctx.buy_intent_sleeve_kwargs(
                 order_amount,
                 sleeve_id=TOURNAMENT_SLEEVE_ID,
@@ -258,7 +284,7 @@ def run_tournament_buy_pipeline(ctx: TradingRunContext) -> None:
 
         try:
             submission = ctx.broker_adapter.submit_buy_notional(
-                ticker=ticker,
+                ticker=execution_ticker,
                 notional=order_amount,
                 limit_price=limit_price,
                 market_clock=ctx.market_clock,
@@ -269,7 +295,7 @@ def run_tournament_buy_pipeline(ctx: TradingRunContext) -> None:
             ctx.orders_submitted += 1
             pending_tournament_buys += 1
             ctx.submitted_notional_today += order_amount
-            ctx.guard_open_symbols.add(ticker)
+            ctx.guard_open_symbols.add(execution_ticker)
             ctx.sleeve_ctx.consume_submit_budget(
                 order_amount,
                 sleeve_id=TOURNAMENT_SLEEVE_ID,
@@ -277,7 +303,7 @@ def run_tournament_buy_pipeline(ctx: TradingRunContext) -> None:
             audit_log(
                 ctx.audit_ctx,
                 event_type="BUY_SUBMITTED",
-                ticker=ticker,
+                ticker=execution_ticker,
                 action="BUY",
                 status=submission.status,
                 reason=alpha.reason,
@@ -296,15 +322,19 @@ def run_tournament_buy_pipeline(ctx: TradingRunContext) -> None:
             )
             checked = ctx.broker_adapter.wait_for_order_status(submission.order_id)
             if order_is_filled(checked["status"]):
-                ctx.sleeve_ctx.record_fill(ticker, sleeve_id=TOURNAMENT_SLEEVE_ID)
+                ctx.sleeve_ctx.record_fill(
+                    execution_ticker,
+                    sleeve_id=TOURNAMENT_SLEEVE_ID,
+                )
                 filled = filled_notional(checked, order_amount)
                 if filled > 0:
                     ctx.cash -= filled
                     ctx.current_gross_exposure += filled
-                    ctx.guard_open_symbols.add(ticker)
-                    ctx.open_symbols.add(ticker)
+                    ctx.guard_open_symbols.add(execution_ticker)
+                    ctx.open_symbols.add(execution_ticker)
             ctx.buy_summary_rows.append(
-                f"{ticker}: TOURNAMENT_BUY status={checked['status']} "
+                f"{ticker}->{execution_ticker}: TOURNAMENT_BUY "
+                f"status={checked['status']} "
                 f"alpha={alpha.alpha_score:.3f} notional=${order_amount:.2f}"
             )
         except Exception as exc:
diff --git a/tests/fixtures/ml_quality/golden_fold_stability_report.json b/tests/fixtures/ml_quality/golden_fold_stability_report.json
index d93d150..35cf254 100644
--- a/tests/fixtures/ml_quality/golden_fold_stability_report.json
+++ b/tests/fixtures/ml_quality/golden_fold_stability_report.json
@@ -20,7 +20,7 @@
     }
   },
   "fold_count": 4,
-  "generated_at": "2026-06-12T00:42:07Z",
+  "generated_at": "2026-07-14T05:30:17Z",
   "high_variance_warning": false,
   "roc_auc": {
     "coefficient_of_variation": 0.01359820733051054,
diff --git a/tests/fixtures/ml_quality/golden_model_calibration_report.json b/tests/fixtures/ml_quality/golden_model_calibration_report.json
index f67b779..108c0c9 100644
--- a/tests/fixtures/ml_quality/golden_model_calibration_report.json
+++ b/tests/fixtures/ml_quality/golden_model_calibration_report.json
@@ -1,6 +1,6 @@
 {
   "bin_count": 20,
-  "generated_at": "2026-06-12T00:42:07Z",
+  "generated_at": "2026-07-14T05:30:17Z",
   "overall_avg_brier_score": 0.25,
   "regimes": {
     "BEAR": {
diff --git a/tests/test_alpaca_safe_qty.py b/tests/test_alpaca_safe_qty.py
index 966330a..421cf7e 100644
--- a/tests/test_alpaca_safe_qty.py
+++ b/tests/test_alpaca_safe_qty.py
@@ -1,6 +1,10 @@
 import pytest
 
-from src.alpaca_client import safe_order_qty_or_none, _safe_order_qty
+from src.alpaca_client import (
+    _safe_order_qty,
+    safe_full_close_qty_or_none,
+    safe_order_qty_or_none,
+)
 
 
 def test_safe_order_qty_or_none_dust():
@@ -14,3 +18,8 @@ def test_safe_order_qty_or_none_normal():
 def test_safe_order_qty_raises_on_dust():
     with pytest.raises(ValueError, match="positive after truncation"):
         _safe_order_qty(0.0000001)
+
+
+def test_full_close_qty_preserves_nine_decimal_position_precision():
+    assert safe_full_close_qty_or_none(0.000000497) == pytest.approx(0.000000497)
+    assert safe_full_close_qty_or_none(15.8465388) == pytest.approx(15.8465388)
diff --git a/tests/test_broker_adapter.py b/tests/test_broker_adapter.py
index 1b50932..4f88330 100644
--- a/tests/test_broker_adapter.py
+++ b/tests/test_broker_adapter.py
@@ -3,6 +3,7 @@ from unittest.mock import MagicMock, patch
 
 from src.broker_adapter import AlpacaBrokerAdapter, OrderSubmission, get_broker_adapter
 from src.brokers.paper import PaperBrokerAdapter
+from src.brokers.toss import TossBrokerAdapter
 from src.market_clock import MarketClock
 from src.trading_session import TradingSession
 
@@ -49,8 +50,89 @@ class BrokerAdapterTest(unittest.TestCase):
                 slippage_pct=0.005,
             )
 
+    def test_toss_not_live_capable(self) -> None:
+        self.assertFalse(TossBrokerAdapter().is_live_capable())
+
+    def test_toss_cancel_order_blocked(self) -> None:
+        with self.assertRaises(NotImplementedError):
+            TossBrokerAdapter().cancel_order("ord-1")
+
+    @patch("src.brokers.toss.get_holdings")
+    def test_toss_get_positions_normalizes(self, mock_holdings) -> None:
+        mock_holdings.return_value = [
+            {"symbol": "005930", "quantity": 10, "averagePrice": 70000},
+            {"stockCode": "aapl", "qty": 3},
+        ]
+        positions = TossBrokerAdapter().get_positions()
+        self.assertEqual(positions[0]["symbol"], "005930")
+        self.assertEqual(positions[0]["qty"], 10)
+        self.assertEqual(positions[1]["symbol"], "AAPL")
+
+    @patch("src.brokers.toss.get_stocks")
+    def test_toss_asset_info_normalizes_leveraged_etf(self, mock_stocks) -> None:
+        mock_stocks.return_value = [
+            {
+                "symbol": "LNOK",
+                "englishName": "DEFIANCE DAILY TARGET 2X LONG NOK ETF",
+                "status": "ACTIVE",
+                "securityType": "ETF",
+                "leverageFactor": "2",
+                "market": "AMEX",
+            }
+        ]
+
+        info = TossBrokerAdapter().get_asset_info("lnok")
+
+        self.assertTrue(info["active"])
+        self.assertTrue(info["tradable"])
+        self.assertEqual(info["security_type"], "ETF")
+        self.assertEqual(info["leverage_factor"], 2.0)
+
+    @patch("src.alpaca_client.discover_leveraged_long_assets")
+    @patch("src.brokers.toss.get_stocks")
+    def test_toss_discovery_verifies_candidate_metadata(
+        self,
+        mock_stocks,
+        mock_discover,
+    ) -> None:
+        mock_discover.return_value = [
+            {"symbol": "LNOK", "name": "Defiance Daily Target 2X Long NOK ETF"}
+        ]
+        mock_stocks.return_value = [
+            {
+                "symbol": "LNOK",
+                "englishName": "DEFIANCE DAILY TARGET 2X LONG NOK ETF",
+                "status": "ACTIVE",
+                "securityType": "ETF",
+                "leverageFactor": "2",
+            }
+        ]
+
+        products = TossBrokerAdapter().discover_leveraged_long_products("NOK")
+
+        self.assertEqual([row["symbol"] for row in products], ["LNOK"])
+
+    @patch("src.brokers.toss.resolve_account_seq", return_value="1")
+    @patch("src.brokers.toss.get_buying_power", return_value={"cash": 500.0})
+    def test_toss_get_account(self, _mock_bp, _mock_seq) -> None:
+        account = TossBrokerAdapter().get_account()
+        self.assertEqual(account["account_seq"], "1")
+        self.assertEqual(account["buying_power"]["cash"], 500.0)
+
+    @patch("src.brokers.toss.get_orders")
+    def test_toss_open_orders_uses_pending_status(self, mock_orders) -> None:
+        mock_orders.return_value = [{"orderId": "o1"}]
+        TossBrokerAdapter().get_open_orders(limit=25)
+        mock_orders.assert_called_once_with(status="OPEN", limit=25)
+
     @patch("src.alpaca_client.submit_limit_buy_notional_order")
-    def test_alpaca_extended_buy_uses_limit(self, mock_limit) -> None:
+    @patch("src.alpaca_client.get_asset_summary")
+    def test_alpaca_extended_buy_uses_limit(self, mock_asset, mock_limit) -> None:
+        mock_asset.return_value = {
+            "active": True,
+            "tradable": True,
+            "fractionable": True,
+        }
         mock_limit.return_value = MagicMock(
             id="ord_1",
             status="accepted",
@@ -77,6 +159,79 @@ class BrokerAdapterTest(unittest.TestCase):
         self.assertEqual(submission.order_id, "ord_1")
         self.assertEqual(submission.order_type, "limit")
 
+    @patch("src.alpaca_client.submit_limit_buy_notional_order")
+    @patch("src.alpaca_client.get_asset_summary")
+    def test_alpaca_nonfractionable_extended_buy_uses_whole_shares(
+        self,
+        mock_asset,
+        mock_limit,
+    ) -> None:
+        mock_asset.return_value = {
+            "active": True,
+            "tradable": True,
+            "fractionable": False,
+        }
+        mock_limit.return_value = MagicMock(
+            id="ord_2",
+            status="accepted",
+            side="buy",
+            type="limit",
+        )
+        clock = MarketClock(
+            is_open=False,
+            timestamp="2026-06-02T08:00:00-04:00",
+            next_open="",
+            next_close="",
+            session=TradingSession.PRE_MARKET,
+            orders_allowed=True,
+        )
+        AlpacaBrokerAdapter().submit_buy_notional(
+            "PLUL",
+            1000.0,
+            limit_price=8.0,
+            market_clock=clock,
+            slippage_pct=0.005,
+        )
+        self.assertTrue(mock_limit.call_args.kwargs["whole_shares"])
+
+    @patch("src.alpaca_client.close_position_by_symbol")
+    @patch("src.alpaca_client.get_asset_summary")
+    def test_alpaca_nonfractionable_partial_sell_uses_whole_shares(
+        self,
+        mock_asset,
+        mock_close,
+    ) -> None:
+        mock_asset.return_value = {
+            "active": True,
+            "tradable": True,
+            "fractionable": False,
+        }
+        mock_close.return_value = MagicMock(
+            id="ord_3",
+            status="filled",
+            side="sell",
+            type="market",
+        )
+        clock = MarketClock(
+            is_open=True,
+            timestamp="2026-07-13T15:45:00-04:00",
+            next_open="",
+            next_close="",
+            session=TradingSession.REGULAR,
+            orders_allowed=True,
+        )
+
+        AlpacaBrokerAdapter().submit_sell_qty(
+            "PLUL",
+            100.75,
+            limit_price=8.94,
+            market_clock=clock,
+            slippage_pct=0.005,
+            client_order_id="slev_test_PLUL_1",
+        )
+
+        self.assertEqual(mock_close.call_args.kwargs["qty"], 100.0)
+
 
 if __name__ == "__main__":
     unittest.main()
diff --git a/tests/test_candidate_cache_and_risk.py b/tests/test_candidate_cache_and_risk.py
index eb6388b..a869b6b 100644
--- a/tests/test_candidate_cache_and_risk.py
+++ b/tests/test_candidate_cache_and_risk.py
@@ -293,8 +293,9 @@ class CandidateCacheAndRiskTest(unittest.TestCase):
         self.assertTrue(cash_buffer.allowed)
         self.assertIn("cash buffer", cash_buffer.reason)
         self.assertEqual(cash_buffer.target_amount, 100.0)
-        self.assertFalse(single_name.allowed)
+        self.assertTrue(single_name.allowed)
         self.assertIn("single-name max loss", single_name.reason)
+        self.assertEqual(single_name.target_amount, 200.0)
 
     def test_apply_factor_crowding_limits_blocks_overcrowded_momentum_trade(self) -> None:
         settings = StrategySettings(
diff --git a/tests/test_instrument_meta.py b/tests/test_instrument_meta.py
index 5611214..fac5fc3 100644
--- a/tests/test_instrument_meta.py
+++ b/tests/test_instrument_meta.py
@@ -1,12 +1,17 @@
 """Instrument registry and leverage gates ([AGY])."""
 
 import pandas as pd
+import src.instrument_meta as instrument_meta
 
 from src.instrument_meta import (
     check_instrument_buy_allowed,
     clear_instrument_registry_cache,
     get_instrument,
+    is_discovered_instrument,
     load_instrument_registry,
+    preferred_leveraged_long_product,
+    register_discovered_leveraged_product,
+    signal_source_ticker,
 )
 from src.risk_manager import apply_effective_leverage_exposure_limits
 
@@ -84,3 +89,40 @@ def test_registry_loads():
     reg = load_instrument_registry()
     assert "SPY" in reg
     assert reg["SPY"].kind == "etf"
+
+
+def test_preferred_direct_2x_product_uses_allowlist_order():
+    assert preferred_leveraged_long_product(
+        "PLUG",
+        allowlist=["PLUL"],
+    ) == "PLUL"
+    assert signal_source_ticker("PLUL") == "PLUG"
+
+
+def test_missing_direct_2x_product_returns_none():
+    assert preferred_leveraged_long_product("RIG", allowlist=["PLUL"]) is None
+
+
+def test_discovered_product_persists_and_bypasses_static_allowlist(
+    tmp_path,
+    monkeypatch,
+):
+    path = tmp_path / "discovered_instruments.json"
+    monkeypatch.setattr(instrument_meta, "DISCOVERED_REGISTRY_PATH", path)
+    clear_instrument_registry_cache()
+
+    register_discovered_leveraged_product("XYZL", "XYZ", multiple=2.0)
+    clear_instrument_registry_cache()
+
+    meta = get_instrument("XYZL")
+    assert meta.is_leveraged_etf
+    assert meta.underlying == "XYZ"
+    assert signal_source_ticker("XYZL") == "XYZ"
+    assert is_discovered_instrument("XYZL") is True
+    allowed, _ = check_instrument_buy_allowed(
+        "XYZL",
+        set(),
+        allow_leveraged_etfs=True,
+        leveraged_etf_allowlist=["PLUL"],
+    )
+    assert allowed is True
diff --git a/tests/test_main_e2e.py b/tests/test_main_e2e.py
index d03c952..88d9ecd 100644
--- a/tests/test_main_e2e.py
+++ b/tests/test_main_e2e.py
@@ -219,6 +219,9 @@ class TestMainE2E(unittest.TestCase):
 
         main()
         mock_broker.return_value.submit_sell_qty.assert_called_once()
+        self.assertTrue(
+            mock_broker.return_value.submit_sell_qty.call_args.kwargs["close_all"]
+        )
         self.exit_error_notify.assert_not_called()
         self.buy_error_notify.assert_not_called()
         print("E2E Time-based Exit Verified")
diff --git a/tests/test_rank_leaderboard.py b/tests/test_rank_leaderboard.py
index 2ed0ecc..c53b318 100644
--- a/tests/test_rank_leaderboard.py
+++ b/tests/test_rank_leaderboard.py
@@ -3,14 +3,45 @@
 from __future__ import annotations
 
 import unittest
+from types import SimpleNamespace
+from unittest.mock import patch
 
 import pandas as pd
 
 from src.rank_ai_gate import RankAIGateScore
-from src.rank_leaderboard import build_rank_leaderboard_frame, format_rank_leaderboard_for_display
+from src.rank_leaderboard import (
+    build_rank_leaderboard_frame,
+    build_rank_leaderboard_live,
+    format_rank_leaderboard_for_display,
+)
 
 
 class TestRankLeaderboard(unittest.TestCase):
+    def test_live_build_accepts_vix_dataframe_without_boolean_coercion(self) -> None:
+        settings = SimpleNamespace(
+            tickers=["AAPL"],
+            use_ai_score=False,
+            rank_ai_buy_gate_min_score_quantile=0.85,
+            rank_ai_buy_gate_top_bucket_pct=0.15,
+        )
+        vix_df = pd.DataFrame({"close": [18.0, 19.0]})
+        spy_df = pd.DataFrame({"close": [100.0, 101.0]})
+        scores = {
+            "AAPL": RankAIGateScore("AAPL", 0.5, 0.9, True, "pass")
+        }
+
+        with patch(
+            "src.candidate_cache._load_cache_ticker_data",
+            return_value={"^VIX": vix_df, "SPY": spy_df},
+        ), patch(
+            "src.rank_leaderboard.build_rank_ai_gate_scores",
+            return_value=scores,
+        ) as build_scores:
+            frame = build_rank_leaderboard_live(settings)
+
+        self.assertEqual(frame["ticker"].tolist(), ["AAPL"])
+        self.assertIs(build_scores.call_args.kwargs["vix_df"], vix_df)
+
     def test_build_and_format_sorted_by_percentile(self) -> None:
         scores = {
             "AAA": RankAIGateScore("AAA", 0.4, 0.9, True, "pass"),
diff --git a/tests/test_recent_changes.py b/tests/test_recent_changes.py
index 0177133..43387f9 100644
--- a/tests/test_recent_changes.py
+++ b/tests/test_recent_changes.py
@@ -1,13 +1,19 @@
 import unittest
+from pathlib import Path
+from types import SimpleNamespace
 from unittest.mock import patch
 
 import numpy as np
 import pandas as pd
 
 from src.data_loader import load_price_data_batch
-from src.features import build_features
+from src.features import build_inference_features
 from src.ml_model import RegimeAwareModelWrapper
-from src.portfolio_backtester import _prepare_ticker_frame
+from src.portfolio_backtester import _prepare_ticker_frame, build_ai_score_frames
+from src.rank_ai_gate import (
+    build_rank_ai_gate_score_history,
+    build_rank_ai_gate_scores,
+)
 
 
 def _sample_price_frame(rows: int = 260) -> pd.DataFrame:
@@ -35,13 +41,33 @@ class DummyClassifier:
         return np.ones(size, dtype=int)
 
 
+class FixedClassifier:
+    def __init__(self, score: float) -> None:
+        self.score = score
+
+    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
+        scores = np.full(len(X), self.score)
+        return np.column_stack([1.0 - scores, scores])
+
+    def predict(self, X: pd.DataFrame) -> np.ndarray:
+        return np.full(len(X), int(self.score >= 0.5), dtype=int)
+
+
+class FixedRegressor:
+    def __init__(self, score: float) -> None:
+        self.score = score
+
+    def predict(self, X: pd.DataFrame) -> np.ndarray:
+        return np.full(len(X), self.score)
+
+
 class DummyModelBundle:
     prediction_horizon = 5
     target_return_threshold = 0.0
 
     def predict_proba(self, df: pd.DataFrame, vix_df=None, spy_df=None, macro_df=None) -> pd.Series:
         size = len(
-            build_features(
+            build_inference_features(
                 df,
                 prediction_horizon=self.prediction_horizon,
                 target_return_threshold=self.target_return_threshold,
@@ -51,6 +77,16 @@ class DummyModelBundle:
 
 
 class RecentChangesTest(unittest.TestCase):
+    def test_inference_features_include_latest_completed_row(self) -> None:
+        raw = _sample_price_frame(280)
+
+        features = build_inference_features(raw, prediction_horizon=20)
+
+        self.assertEqual(
+            pd.Timestamp(features["date"].max()),
+            pd.Timestamp(raw["date"].max()),
+        )
+
     def test_sklearn_wrapper_returns_series_from_numpy_outputs(self) -> None:
         feature_df = pd.DataFrame(
             {
@@ -66,13 +102,47 @@ class RecentChangesTest(unittest.TestCase):
             target_return_threshold=0.0,
         )
 
-        with patch("src.ml_model.build_features", return_value=feature_df):
+        with patch("src.ml_model.build_inference_features", return_value=feature_df):
             proba = wrapper.predict_proba(_sample_price_frame(60))
             pred = wrapper.predict(_sample_price_frame(60))
 
         self.assertEqual(proba.tolist(), [0.1, 0.5, 0.9])
         self.assertEqual(pred.tolist(), [1, 1, 1])
 
+    def test_wrapper_selects_model_using_each_rows_point_in_time_regime(self) -> None:
+        feature_df = pd.DataFrame(
+            {
+                "date": pd.date_range("2026-01-02", periods=3),
+                "feature_a": [1.0, 2.0, 3.0],
+            }
+        )
+        regimes = pd.Series(
+            ["BULL", "BEAR", "BULL"],
+            index=pd.to_datetime(feature_df["date"]),
+        )
+        wrapper = RegimeAwareModelWrapper(
+            {
+                "BULL": FixedClassifier(0.8),
+                "BEAR": FixedClassifier(0.2),
+                "NEUTRAL": FixedClassifier(0.5),
+            },
+            ["feature_a"],
+            prediction_horizon=5,
+            target_return_threshold=0.0,
+        )
+
+        with (
+            patch("src.ml_model.build_inference_features", return_value=feature_df),
+            patch("src.ml_model.compute_daily_regime", return_value=regimes),
+        ):
+            scores = wrapper.predict_proba(
+                _sample_price_frame(60),
+                spy_df=_sample_price_frame(60),
+                vix_df=_sample_price_frame(60),
+            )
+
+        self.assertEqual(scores.tolist(), [0.8, 0.2, 0.8])
+
     def test_prepare_ticker_frame_uses_model_bundle_interface(self) -> None:
         frame = _prepare_ticker_frame(
             "AAPL",
@@ -84,6 +154,88 @@ class RecentChangesTest(unittest.TestCase):
 
         self.assertGreater(frame["ai_score"].notna().sum(), 0)
 
+    def test_ai_score_frames_skip_only_short_history_ticker(self) -> None:
+        with self.assertWarnsRegex(RuntimeWarning, "SHORT"):
+            frames = build_ai_score_frames(
+                {
+                    "AAPL": _sample_price_frame(280),
+                    "SHORT": _sample_price_frame(20),
+                },
+                ai_model_bundle=DummyModelBundle(),
+            )
+
+        self.assertEqual(set(frames), {"AAPL"})
+
+    def test_rank_history_latest_day_matches_live_point_in_time_score(self) -> None:
+        ticker_data = {
+            "AAPL": _sample_price_frame(300),
+            "MSFT": _sample_price_frame(300),
+        }
+        settings = SimpleNamespace(
+            rank_ai_buy_gate_enabled=True,
+            rank_ai_buy_gate_fail_closed=True,
+            rank_ai_buy_gate_prediction_horizon=20,
+            rank_ai_buy_gate_min_score_quantile=0.85,
+            rank_ai_buy_gate_top_bucket_pct=0.15,
+        )
+        bundle = {
+            "classifier": FixedClassifier(0.7),
+            "regressor": FixedRegressor(0.6),
+            "config": {"prediction_horizon": 20},
+        }
+
+        with (
+            patch("src.rank_ai_gate._model_path", return_value=Path(__file__)),
+            patch("src.rank_ai_gate.joblib.load", return_value=bundle),
+        ):
+            history = build_rank_ai_gate_score_history(ticker_data, settings)
+            latest = build_rank_ai_gate_scores(ticker_data, settings)
+
+        latest_date = pd.Timestamp(ticker_data["AAPL"]["date"].max())
+        self.assertIn(latest_date, history)
+        for ticker in ticker_data:
+            self.assertAlmostEqual(
+                history[latest_date][ticker].score,
+                latest[ticker].score,
+            )
+            self.assertAlmostEqual(
+                history[latest_date][ticker].percentile,
+                latest[ticker].percentile,
+            )
+
+    def test_rank_history_uses_point_in_time_universe(self) -> None:
+        ticker_data = {
+            "AAPL": _sample_price_frame(300),
+            "FUTURE": _sample_price_frame(300),
+        }
+        settings = SimpleNamespace(
+            rank_ai_buy_gate_enabled=True,
+            rank_ai_buy_gate_fail_closed=True,
+            rank_ai_buy_gate_prediction_horizon=20,
+            rank_ai_buy_gate_min_score_quantile=0.85,
+            rank_ai_buy_gate_top_bucket_pct=0.15,
+        )
+        bundle = {
+            "classifier": FixedClassifier(0.7),
+            "regressor": FixedRegressor(0.6),
+            "config": {"prediction_horizon": 20},
+        }
+        first_snapshot = pd.Timestamp(ticker_data["AAPL"]["date"].max()) + pd.Timedelta(days=1)
+
+        with (
+            patch("src.rank_ai_gate._model_path", return_value=Path(__file__)),
+            patch("src.rank_ai_gate.joblib.load", return_value=bundle),
+        ):
+            history = build_rank_ai_gate_score_history(
+                ticker_data,
+                settings,
+                historical_universe_by_date={first_snapshot: ["AAPL", "FUTURE"]},
+                base_universe={"AAPL"},
+            )
+
+        latest_date = pd.Timestamp(ticker_data["AAPL"]["date"].max())
+        self.assertEqual(set(history[latest_date]), {"AAPL"})
+
     def test_load_price_data_batch_raises_when_ticker_is_missing(self) -> None:
         with patch("src.data_loader.yf.download", return_value=pd.DataFrame()):
             with self.assertRaisesRegex(ValueError, "Failed to load batch price data"):
diff --git a/tests/test_settings.py b/tests/test_settings.py
index 3adc31c..9c1824c 100644
--- a/tests/test_settings.py
+++ b/tests/test_settings.py
@@ -165,10 +165,11 @@ class SettingsTest(unittest.TestCase):
         self.assertEqual(loaded.ma_fast, 30)
         self.assertEqual(loaded.ma_slow, 200)
         self.assertEqual(loaded.rsi_buy_limit, 100.0)
-        self.assertFalse(loaded.allow_leveraged_etfs)
-        self.assertEqual(loaded.leveraged_etf_allowlist, [])
-        self.assertTrue(loaded.margin_leverage_paper_enabled)
-        self.assertTrue(loaded.conditional_margin_leverage_enabled)
+        self.assertTrue(loaded.allow_leveraged_etfs)
+        self.assertTrue(loaded.prefer_leveraged_products)
+        self.assertIn("PLUL", loaded.leveraged_etf_allowlist)
+        self.assertFalse(loaded.margin_leverage_paper_enabled)
+        self.assertFalse(loaded.conditional_margin_leverage_enabled)
         self.assertEqual(loaded.conditional_margin_leverage_bull_factor, 2.0)
         self.assertEqual(loaded.conditional_margin_leverage_defensive_factor, 1.0)
         self.assertEqual(loaded.conditional_margin_leverage_vix_max, 22.0)
diff --git a/tests/test_sleeve_rebalance.py b/tests/test_sleeve_rebalance.py
index fc62f45..ce5c4a4 100644
--- a/tests/test_sleeve_rebalance.py
+++ b/tests/test_sleeve_rebalance.py
@@ -53,6 +53,14 @@ class SleeveRebalanceTest(unittest.TestCase):
         self.assertTrue(actions)
         self.assertEqual(actions[0].sleeve_id, CORE_SLEEVE_ID)
         self.assertGreater(actions[0].sell_qty, 0)
+        self.assertEqual(
+            len({action.ticker for action in actions}),
+            len(actions),
+        )
+        # $10k core overweight already contributes to the $15k cash deficit;
+        # the planner must sell $15k total, not add both and sell $25k.
+        planned_notional = sum(action.sell_qty * 600.0 for action in actions)
+        self.assertAlmostEqual(planned_notional, 15_000.0, delta=1.0)
 
     def test_all_core_book_gets_proportional_retag(self) -> None:
         settings = StrategySettings(
diff --git a/tests/test_sleeve_rebalance_pipeline.py b/tests/test_sleeve_rebalance_pipeline.py
index 6ba798d..2b78443 100644
--- a/tests/test_sleeve_rebalance_pipeline.py
+++ b/tests/test_sleeve_rebalance_pipeline.py
@@ -20,8 +20,12 @@ class _FakeSubmission(SimpleNamespace):
 
 
 class _FakeBroker:
-    def __init__(self) -> None:
+    def __init__(self, *, fractionable: bool = True) -> None:
         self.calls: list[dict] = []
+        self.fractionable = fractionable
+
+    def get_asset_info(self, ticker: str) -> dict:
+        return {"symbol": ticker, "fractionable": self.fractionable}
 
     def submit_sell_qty(
         self,
@@ -32,9 +36,16 @@ class _FakeBroker:
         market_clock,
         slippage_pct: float,
         client_order_id: Optional[str] = None,
+        close_all: bool = False,
     ):
         self.calls.append(
-            {"ticker": ticker, "qty": qty, "limit_price": limit_price}
+            {
+                "ticker": ticker,
+                "qty": qty,
+                "limit_price": limit_price,
+                "client_order_id": client_order_id,
+                "close_all": close_all,
+            }
         )
         return _FakeSubmission(
             order_id="o1", status="FILLED", side="sell", order_type="limit"
@@ -109,6 +120,47 @@ class SleeveRebalanceSellTest(unittest.TestCase):
         self.assertEqual(ctx.api_error_count, 0)
         self.assertTrue(any("no current price" in row for row in ctx.exit_summary_rows))
 
+    def test_trim_clamps_to_exact_position_and_uses_full_close(self) -> None:
+        held_qty = 9.921550245
+        ctx = _make_ctx({"PANW": {"qty": held_qty, "current_price": 325.91}})
+        actions = [
+            SleeveRebalanceAction(
+                ticker="PANW",
+                sleeve_id="core",
+                sell_qty=9.9216,
+                reason="trim",
+            )
+        ]
+
+        _execute_sell_actions(ctx, actions, event_prefix="SLEEVE_TRIM")
+
+        self.assertEqual(ctx.broker_adapter.calls[0]["qty"], held_qty)
+        self.assertTrue(ctx.broker_adapter.calls[0]["close_all"])
+
+    def test_duplicate_ticker_actions_are_coalesced(self) -> None:
+        ctx = _make_ctx({"PLUG": {"qty": 755.120535, "current_price": 9.5}})
+        actions = [
+            SleeveRebalanceAction("PLUG", "core", 700.0, "cash raise"),
+            SleeveRebalanceAction("PLUG", "core", 500.0, "core trim"),
+        ]
+
+        _execute_sell_actions(ctx, actions, event_prefix="SLEEVE_TRIM")
+
+        self.assertEqual(len(ctx.broker_adapter.calls), 1)
+        self.assertEqual(ctx.broker_adapter.calls[0]["qty"], 700.0)
+
+    def test_nonfractionable_partial_trim_rounds_down_to_whole_share(self) -> None:
+        ctx = _make_ctx({"PLUL": {"qty": 762.0, "current_price": 8.94}})
+        ctx.broker_adapter = _FakeBroker(fractionable=False)
+        actions = [
+            SleeveRebalanceAction("PLUL", "core", 100.75, "cash raise")
+        ]
+
+        _execute_sell_actions(ctx, actions, event_prefix="SLEEVE_TRIM")
+
+        self.assertEqual(ctx.broker_adapter.calls[0]["qty"], 100.0)
+        self.assertFalse(ctx.broker_adapter.calls[0]["close_all"])
+
 
 if __name__ == "__main__":
     unittest.main()
```
