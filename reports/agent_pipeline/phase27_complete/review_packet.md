# Agent Review Packet - Run: phase27_complete

## Implementation Agent
cursor

## Task Description
phase 27 universe and instrument meta

## Changed Files
- TODO.md
- config/strategy_config.json
- docs/TODO_ARCHIVE.md
- docs/runbook.md
- scripts/run_pass_complete.sh
- src/main.py
- src/risk_manager.py
- src/sector.py
- src/settings.py

## Git Diff Summary
```
 TODO.md                      | 17 ++++++++++------
 config/strategy_config.json  |  4 ++++
 docs/TODO_ARCHIVE.md         |  2 ++
 docs/runbook.md              | 25 ++++++++++++++++++++++-
 scripts/run_pass_complete.sh |  2 ++
 src/main.py                  | 36 ++++++++++++++++++++++++++++++++-
 src/risk_manager.py          | 47 +++++++++++++++++++++++++++++++++++++++++++-
 src/sector.py                |  7 ++++++-
 src/settings.py              | 19 +++++++++++++++++-
 9 files changed, 148 insertions(+), 11 deletions(-)
```

## Test Execution Results (runtime_harness.log)
```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0
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
======================== 45 passed, 1 warning in 2.69s =========================
```

## Git Patch
```diff
diff --git a/TODO.md b/TODO.md
index f81a15a..bec411a 100644
--- a/TODO.md
+++ b/TODO.md
@@ -42,7 +42,8 @@ RUN_ID=<phase>_final bash scripts/run_pass_complete.sh "Phase N complete"
 
 | 영역 | 상태 |
 |------|------|
-| **유니버스** | 110 tickers + dynamic universe (`config/strategy_config.json`) |
+| **유니버스** | `UNIVERSE_PROFILE` paper/smoke/research; master **259** (`config/universe_master.csv`) |
+| **종목 메타** | `instrument_registry.json` — 레버리지 ETF 기본 매수 차단 (`allow_leveraged_etfs: false`) |
 | **챔피언 모델** | LGBM+XGB, 로컬 `models/ai_score_model.joblib` (git 미추적) |
 | **최근 retrain** | `logs/retrain_history.csv` — fold ROC-AUC ~0.45–0.55, 평균 ~0.51 근처 |
 | **포트폴리오 백테스트** | return **+50.7%** vs bench **+58.2%**, max DD **-10.2%**, 42 trades (`logs/portfolio_backtest/`) |
@@ -50,19 +51,19 @@ RUN_ID=<phase>_final bash scripts/run_pass_complete.sh "Phase N complete"
 | **관측** | 일별 audit, 주간 slippage, guard/leverage/LLM cache 리포트 스크립트 (`docs/runbook.md`) |
 | **비활성** | `deep_model.py`, `rl_portfolio.py` — `docs/RESEARCH_MODELS.md` |
 
-**완료 로드맵:** Phase 0–26 → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)
+**완료 로드맵:** Phase 0–27 → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)
 
 **우선순위 가이드 (2026 Q2)**
-1. **운영 자동화** — 리포트·audit 타이머, 단일 ops 진입점
+1. **백로그** — 마진 레버리지 paper, crowding 라이브, DL/RL
 2. **알파·승격 품질** — 벤치마크 underperform, fold 편차 완화
-3. **라이브 정합** — paper vs 백테스트·슬리피지 드리프트 (live 미사용이어도 paper 기준 유지)
-4. **백로그** — 레버리지 실거래, DL/RL 연구
+3. **라이브 정합** — paper vs 백테스트·슬리피지 드리프트
+4. **백로그** — 마진 레버리지 paper, DL/RL 연구
 
 ---
 
 ## Backlog (우선순위 낮음 · live 미사용 시 보류 가능) ← **다음**
 
-- [ ] `[Cursor]` 레버리지 > 1.0 paper 소액 실험 + stress 게이트 연동
+- [ ] `[Cursor]` 레버리지 > 1.0 **마진** paper 소액 실험 + stress 게이트 (Phase 27 instrument 레이어 이후)
 - [ ] `[AGY]` Factor/crowding guard **라이브** 영향도 (백테스트 리포트 vs audit 스킵 로그 대조)
 - [ ] `[Cursor]` Transformer / RL — `docs/RESEARCH_MODELS.md` 실험 브랜치만 (프로덕션 연동 없음)
 - [ ] `[Cursor]` Streamlit CMS에 ops 리포트 latest_summary 뷰어
@@ -75,6 +76,10 @@ RUN_ID=<phase>_final bash scripts/run_pass_complete.sh "Phase N complete"
 # 패스 마감
 RUN_ID=phase24_ops bash scripts/run_pass_complete.sh "작업 요약"
 
+# 유니버스 프로필 (기본 paper = strategy_config tickers)
+UNIVERSE_PROFILE=smoke .venv/bin/python -m src.run_portfolio_backtest   # 빠른 스모크
+UNIVERSE_PROFILE=research .venv/bin/python -m src.main --dry-run      # master 259종 스캔
+
 # 운영 리포트 (수동)
 bash scripts/run_ops_reports.sh
 bash scripts/run_ops_reports.sh --weekly
diff --git a/config/strategy_config.json b/config/strategy_config.json
index 2a9c0c3..e849d44 100644
--- a/config/strategy_config.json
+++ b/config/strategy_config.json
@@ -159,6 +159,10 @@
   "leverage_factor": 1.0,
   "dynamic_universe_enabled": true,
   "dynamic_count": 50,
+  "allow_leveraged_etfs": false,
+  "max_leveraged_etf_positions": 1,
+  "max_effective_leverage_exposure_pct": 1.25,
+  "block_leveraged_etfs_vix_above": 28.0,
   "trailing_stop_pct": 0.05,
   "rebalance_threshold_pct": 0.20,
   "sector_rotation_enabled": true
diff --git a/docs/TODO_ARCHIVE.md b/docs/TODO_ARCHIVE.md
index bcd0cff..336d43a 100644
--- a/docs/TODO_ARCHIVE.md
+++ b/docs/TODO_ARCHIVE.md
@@ -25,6 +25,7 @@
 | 24 | Ops automation | `run_ops_reports.sh`, systemd timers, post-workflow audit smoke |
 | 25 | Alpha / promotion quality | Fold variance report, promotion summary CLI, benchmark gap, champion governance |
 | 26 | Live alignment (paper) | Crowding go/no-go, execution vs slippage diff, leverage/LLM cache alerts |
+| 27 | Universe + instrument meta | Master CSV, UNIVERSE_PROFILE, leveraged ETF registry and buy gates |
 
 **Milestones**
 - **2026-05-27:** Phase 0–19 closed (code + pytest + runbook).
@@ -32,3 +33,4 @@
 - **2026-05-30:** Phase 24 closed; ops report batch + CI pytest/gates.
 - **2026-05-30:** Phase 25 closed; promotion docs/CLI, fold variance, benchmark gap decomposition.
 - **2026-05-30:** Phase 26 closed; paper crowding gate, execution alignment, stress/cache Telegram alerts.
+- **2026-05-30:** Phase 27 closed; universe master/smoke/research profiles, instrument registry, leverage ETF gates.
diff --git a/docs/runbook.md b/docs/runbook.md
index ff727dc..8f7f432 100644
--- a/docs/runbook.md
+++ b/docs/runbook.md
@@ -49,7 +49,30 @@
     2. 포트폴리오 구성 종목의 개별 리스크(실적 악화 등) 재평가.
     3. 시장이 안정되었다고 판단되면 `config/strategy_config.json`의 `max_portfolio_drawdown_pct`를 일시적으로 상향 조정하여 가드 해제 가능.
 
-### 2.4 데이터 최신성(Stale Data) 오류
+### 2.4 유니버스 프로필 (`UNIVERSE_PROFILE`)
+
+| 프로필 | 스캔 풀 | 용도 |
+|--------|---------|------|
+| `paper` (기본) | `config/strategy_config.json` tickers | 운영·기본 백테스트 |
+| `smoke` | `config/universe_smoke.json` (~11종) | pytest·빠른 로컬 검증 |
+| `research` | `config/universe_master.csv` (~259종) | 넓은 스캔·retrain 데이터 풀 |
+
+```bash
+# master CSV 일괄 캐시 (로컬, 시간 소요)
+UNIVERSE_PROFILE=research PYTHONPATH=. .venv/bin/python -c "
+from src.settings import load_settings
+from src.data_loader import load_price_data_batch
+s = load_settings()
+load_price_data_batch(s.tickers, period='2y')
+print(len(s.tickers), 'tickers cached')
+"
+```
+
+**레버리지 ETF vs 마진 레버리지**
+- **레버리지 ETF** (`TQQQ`, `SOXL` 등): `config/instrument_registry.json` + `allow_leveraged_etfs` (기본 `false`). 유효 노출 = `Σ(market_value × |multiple|)` ≤ `max_effective_leverage_exposure_pct × portfolio`. 고 VIX 시 차단: `block_leveraged_etfs_vix_above` (기본 28).
+- **마진 `leverage_factor`**: 계좌 배수 — ETF 메타와 별도. paper 실험은 TODO 백로그.
+
+### 2.5 데이터 최신성(Stale Data) 오류
 - **현상**: `SKIP_BUY - stale price data` 로그 발생.
 - **대응**:
     1. 특정 종목의 거래 정지 여부 확인.
diff --git a/scripts/run_pass_complete.sh b/scripts/run_pass_complete.sh
index 1a3ecf9..7701fde 100755
--- a/scripts/run_pass_complete.sh
+++ b/scripts/run_pass_complete.sh
@@ -48,6 +48,8 @@ else
     tests/test_crowding_paper_gate.py \
     tests/test_execution_alignment_report.py \
     tests/test_llm_cache_alerts.py \
+    tests/test_universe_loader.py \
+    tests/test_instrument_meta.py \
     tests/test_guard_impact_report.py \
     tests/test_check_audit_daily_summary.py \
     tests/test_fold_variance_report.py \
diff --git a/src/main.py b/src/main.py
index 0ed9ab2..99fb2ea 100644
--- a/src/main.py
+++ b/src/main.py
@@ -18,6 +18,7 @@ from src.risk_manager import (
     ExitDecision,
     apply_buy_safety_limits,
     apply_factor_crowding_limits,
+    apply_effective_leverage_exposure_limits,
     apply_portfolio_exposure_limits,
     check_additional_buy_allowed,
     check_buy_allowed,
@@ -37,6 +38,7 @@ from src.alpaca_client import (
 from src.market_clock import get_market_clock
 from src.notifier import notify_order, notify_error, notify_run_summary, notify_info
 from src.ml_model import load_ai_score_model, predict_ai_score_from_bundle
+from src.instrument_meta import check_instrument_buy_allowed, format_audit_reason
 from src.sector import is_sector_allowed
 from src.correlation_guard import is_correlation_allowed
 from src.market_regime import get_current_regime
@@ -950,6 +952,7 @@ def main() -> None:
                     signal=signal,
                     cash=cash,
                     current_positions_count=positions_count,
+                    ticker=ticker,
                 )
                 risk_allowed = risk.allowed
                 risk_reason = risk.reason
@@ -992,6 +995,26 @@ def main() -> None:
                     risk_reason = sector_reason
                     target_amount = 0.0
 
+            if risk_allowed and position is None:
+                inst_ok, inst_reason = check_instrument_buy_allowed(
+                    ticker,
+                    open_symbols,
+                    allow_leveraged_etfs=bool(
+                        getattr(settings, "allow_leveraged_etfs", False)
+                    ),
+                    max_leveraged_etf_positions=int(
+                        getattr(settings, "max_leveraged_etf_positions", 1)
+                    ),
+                    block_leveraged_etfs_vix_above=float(
+                        getattr(settings, "block_leveraged_etfs_vix_above", 0.0)
+                    ),
+                    vix_df=vix_df,
+                )
+                if not inst_ok:
+                    risk_allowed = False
+                    risk_reason = inst_reason
+                    target_amount = 0.0
+
             # 상관관계 필터: 기존 보유 종목과 과도한 상관관계 시 매수 차단
             if risk_allowed and position is None and getattr(settings, "correlation_guard_enabled", False):
                 corr_ok, corr_reason = is_correlation_allowed(
@@ -1069,6 +1092,17 @@ def main() -> None:
                 risk_reason = exposure.reason if not exposure.allowed else risk_reason
                 order_amount = exposure.target_amount
 
+            if risk_allowed:
+                leverage_cap = apply_effective_leverage_exposure_limits(
+                    ticker=ticker,
+                    order_amount=order_amount,
+                    portfolio_value=float(account["portfolio_value"]),
+                    positions_by_symbol=positions_by_symbol,
+                )
+                risk_allowed = leverage_cap.allowed
+                risk_reason = leverage_cap.reason if not leverage_cap.allowed else risk_reason
+                order_amount = leverage_cap.target_amount
+
             log_signal(
                 ticker=ticker,
                 signal=signal,
@@ -1102,7 +1136,7 @@ def main() -> None:
                     ticker=ticker,
                     action="BUY",
                     status="SKIPPED",
-                    reason=risk_reason,
+                    reason=format_audit_reason(risk_reason, ticker),
                     profile_name=profile_name,
                     regime=current_regime,
                     signal=signal,
diff --git a/src/risk_manager.py b/src/risk_manager.py
index 7a5d942..9b5a985 100644
--- a/src/risk_manager.py
+++ b/src/risk_manager.py
@@ -27,6 +27,8 @@ def check_buy_allowed(
     signal: str,
     cash: float,
     current_positions_count: int,
+    *,
+    ticker: str | None = None,
 ) -> RiskDecision:
     settings = load_settings()
 
@@ -39,7 +41,13 @@ def check_buy_allowed(
     if cash <= 0:
         return RiskDecision(False, "cash is zero or negative")
 
-    target_amount = cash * settings.max_position_pct
+    position_pct = float(settings.max_position_pct)
+    if ticker:
+        from src.instrument_meta import adjust_position_cap_for_instrument
+
+        position_pct = adjust_position_cap_for_instrument(position_pct, ticker)
+
+    target_amount = cash * position_pct
 
     if target_amount <= 0:
         return RiskDecision(False, "target amount is zero or negative")
@@ -228,6 +236,43 @@ def apply_portfolio_exposure_limits(
     return RiskDecision(True, "portfolio exposure limits passed", order_amount)
 
 
+def apply_effective_leverage_exposure_limits(
+    ticker: str,
+    order_amount: float,
+    portfolio_value: float,
+    positions_by_symbol: dict[str, dict],
+) -> RiskDecision:
+    """Cap sum(market_value * |leverage_multiple|) including the proposed buy."""
+    settings = load_settings()
+
+    if order_amount <= 0:
+        return RiskDecision(False, "target amount is zero or negative", 0.0)
+
+    if portfolio_value <= 0:
+        return RiskDecision(False, "portfolio value is zero or negative", 0.0)
+
+    from src.instrument_meta import current_effective_leverage_exposure, get_instrument
+
+    current_effective = current_effective_leverage_exposure(positions_by_symbol)
+    multiple = get_instrument(ticker).abs_multiple
+    projected = current_effective + (order_amount * multiple)
+    max_effective = portfolio_value * float(
+        getattr(settings, "max_effective_leverage_exposure_pct", 1.25)
+    )
+    if projected > max_effective:
+        return RiskDecision(
+            False,
+            (
+                "effective leverage exposure limit exceeded "
+                f"(projected=${projected:.2f}, max=${max_effective:.2f}, "
+                f"multiple={multiple:.1f})"
+            ),
+            0.0,
+        )
+
+    return RiskDecision(True, "effective leverage exposure ok", order_amount)
+
+
 def _build_crowding_snapshot(
     df: pd.DataFrame,
     lookback_days: int,
diff --git a/src/sector.py b/src/sector.py
index e5e80fe..6da4483 100644
--- a/src/sector.py
+++ b/src/sector.py
@@ -50,6 +50,11 @@ SECTOR_MAP: dict[str, str] = {
     "PLD": "realestate", "AMT": "realestate", "EQIX": "realestate",
     # 광의 ETF (분산된 것으로 간주)
     "SPY": "etf", "QQQ": "etf", "DIA": "etf", "IWM": "etf", "VTI": "etf",
+    # Leveraged / inverse ETFs (sector cap skipped; see instrument_meta gates)
+    "TQQQ": "leveraged_etf", "SQQQ": "leveraged_etf", "QLD": "leveraged_etf", "QID": "leveraged_etf",
+    "UPRO": "leveraged_etf", "SPXU": "leveraged_etf", "SSO": "leveraged_etf", "SDS": "leveraged_etf",
+    "SOXL": "leveraged_etf", "SOXS": "leveraged_etf", "TECL": "leveraged_etf", "TECS": "leveraged_etf",
+    "FAS": "leveraged_etf", "FAZ": "leveraged_etf", "TNA": "leveraged_etf", "TZA": "leveraged_etf",
 }
 
 DEFAULT_MAX_SECTOR_POSITIONS = 2
@@ -79,7 +84,7 @@ def is_sector_allowed(
     """
     sector = get_sector(ticker)
 
-    if sector in ("etf", "unknown"):
+    if sector in ("etf", "leveraged_etf", "unknown"):
         return True, "sector check skipped"
 
     count = count_sector_positions(open_symbols, sector)
diff --git a/src/settings.py b/src/settings.py
index e45e8d7..5c563a3 100644
--- a/src/settings.py
+++ b/src/settings.py
@@ -109,6 +109,10 @@ class StrategySettings(StrategyProfile):
     crowding_trend_gap_threshold: float = 0.05
     dynamic_universe_enabled: bool = False
     dynamic_count: int = 50
+    allow_leveraged_etfs: bool = False
+    max_leveraged_etf_positions: int = 1
+    max_effective_leverage_exposure_pct: float = 1.25
+    block_leveraged_etfs_vix_above: float = 28.0
     trailing_stop_pct: float = 0.05
     adaptive_trailing_stop_enabled: bool = False
     atr_multiplier: float = 3.0
@@ -271,6 +275,12 @@ def validate_settings(settings: StrategySettings) -> StrategySettings:
         raise ValueError("crowding_trend_gap_threshold must be non-negative")
     if settings.dynamic_count <= 0:
         raise ValueError("dynamic_count must be positive")
+    if settings.max_leveraged_etf_positions <= 0:
+        raise ValueError("max_leveraged_etf_positions must be positive")
+    if settings.max_effective_leverage_exposure_pct <= 0:
+        raise ValueError("max_effective_leverage_exposure_pct must be positive")
+    if settings.block_leveraged_etfs_vix_above < 0:
+        raise ValueError("block_leveraged_etfs_vix_above must be non-negative")
     if settings.rebalance_threshold_pct < 0:
         raise ValueError("rebalance_threshold_pct must be non-negative")
     return settings
@@ -279,10 +289,17 @@ def validate_settings(settings: StrategySettings) -> StrategySettings:
 def load_settings(path: Union[str, Path] = CONFIG_PATH) -> StrategySettings:
     """Load the active legacy single-strategy config."""
 
+    from src.universe_loader import resolve_scan_tickers
+
     settings_path = Path(path).expanduser().resolve()
     merged = asdict(DEFAULT_SETTINGS)
     if settings_path.exists():
-        merged.update(_validate_strategy_settings_payload(_read_json_object(settings_path), settings_path))
+        payload = _validate_strategy_settings_payload(_read_json_object(settings_path), settings_path)
+        base_tickers = payload.get("tickers", merged.get("tickers"))
+        payload["tickers"] = resolve_scan_tickers(list(base_tickers))
+        merged.update(payload)
+    else:
+        merged["tickers"] = resolve_scan_tickers(list(merged["tickers"]))
     return validate_settings(StrategySettings(**merged))
 
 
```
