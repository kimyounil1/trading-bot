# Agent Review Packet - Run: phase20_promotion_v2

## Implementation Agent
cursor

## Task Description
holdout fix: challenger trained without last 6mo; OOS on holdout slice only

## Changed Files
- logs/ml/ai_model_metrics.csv
- logs/retrain_history.csv
- models/ai_score_model.joblib
- src/ml_model.py
- src/portfolio_backtest_validation.py
- src/train_ai_model.py
- tests/test_model_governance.py
- tests/test_portfolio_backtest_gate.py

## Git Diff Summary
```
 logs/ml/ai_model_metrics.csv          |  10 +-
 logs/retrain_history.csv              |   1 +
 models/ai_score_model.joblib          | Bin 1757990 -> 1758310 bytes
 src/ml_model.py                       | 123 +++++++++++++++++++++++--
 src/portfolio_backtest_validation.py  |  52 ++++++++---
 src/train_ai_model.py                 | 168 +++++++++++++++++++++++++++++++++-
 tests/test_model_governance.py        |  65 ++++++++++++-
 tests/test_portfolio_backtest_gate.py |  12 +++
 8 files changed, 400 insertions(+), 31 deletions(-)
```

## Test Execution Results (runtime_harness.log)
```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/kimyo/trading-bot
plugins: anyio-4.13.0
collected 7 items

tests/test_report_performance.py .                                       [ 14%]
tests/test_reappraise_regime.py ...                                      [ 57%]
tests/test_portfolio_backtest_golden.py ...                              [100%]

=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/websockets/legacy/__init__.py:6
  /home/kimyo/trading-bot/.venv/lib/python3.12/site-packages/websockets/legacy/__init__.py:6: DeprecationWarning: websockets.legacy is deprecated; see https://websockets.readthedocs.io/en/stable/howto/upgrade.html for upgrade instructions
    warnings.warn(  # deprecated in 14.0 - 2024-11-09

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
========================= 7 passed, 1 warning in 0.55s =========================
```

## Git Patch
```diff
diff --git a/logs/ml/ai_model_metrics.csv b/logs/ml/ai_model_metrics.csv
index 0638196..f5a77ad 100644
--- a/logs/ml/ai_model_metrics.csv
+++ b/logs/ml/ai_model_metrics.csv
@@ -1,6 +1,6 @@
 fold,accuracy,precision,recall,roc_auc,test_positive_rate,prediction_positive_rate,train_size,test_size
-1,0.5244384996934738,0.5484398737875423,0.5012817773979918,0.5286340670919325,0.5217633617566739,0.47689906927492615,17946,17943
-2,0.4494789054227275,0.6544431509507179,0.2940714908456844,0.5158509944937936,0.639246502814468,0.2872429359638856,35889,17943
-3,0.5586022404280221,0.5981134772045162,0.7847365460341271,0.5298942819902608,0.5944379423730702,0.779914172657861,53832,17943
-4,0.46853926322242656,0.5456267409470752,0.4729116368903911,0.4732537359173688,0.5771052778242212,0.500195062141225,71775,17943
-5,0.5130134314217244,0.5579873646209387,0.5064509522834323,0.51604461357988,0.5442791060580728,0.4940088056623753,89718,17943
+1,0.528979045920642,0.5457911357944027,0.5393306790057032,0.5316021297826623,0.5178889879625501,0.5117588051716451,17944,17944
+2,0.45692153366027644,0.6543549218347363,0.33001212961358517,0.5026369607790756,0.6432233615693268,0.32439812750780206,35888,17944
+3,0.5665960766830138,0.6093773110486614,0.7675826734979041,0.5460608256136901,0.5982501114578689,0.7535666518056174,53832,17944
+4,0.451627284886313,0.5284319356691557,0.44508950169327527,0.4455734853749122,0.5759585376727597,0.4851203744984396,71776,17944
+5,0.5106442264823896,0.5542609092986064,0.4986126811221868,0.5146206734442764,0.5422982612572448,0.4878510922871155,89720,17944
diff --git a/logs/retrain_history.csv b/logs/retrain_history.csv
index 9e73b35..8e1e7f7 100644
--- a/logs/retrain_history.csv
+++ b/logs/retrain_history.csv
@@ -2,3 +2,4 @@ timestamp,status,avg_roc_auc,avg_precision,elapsed_sec
 2026-05-26T13:35:17Z,success,0.4985,0.5439,13.9
 2026-05-26T13:51:32Z,success,0.5103,0.5616,19.3
 2026-05-26T14:22:04Z,success,0.5127,0.5809,19.1
+2026-05-30T09:28:07Z,success,0.5081,0.5784,93.5
diff --git a/models/ai_score_model.joblib b/models/ai_score_model.joblib
index 4cc580d..a7de37d 100644
Binary files a/models/ai_score_model.joblib and b/models/ai_score_model.joblib differ
diff --git a/src/ml_model.py b/src/ml_model.py
index e0c664b..2561599 100644
--- a/src/ml_model.py
+++ b/src/ml_model.py
@@ -290,25 +290,132 @@ def restore_archived_champion(
     return model_path, metadata_path
 
 
+def bundle_to_model_wrapper(bundle: dict[str, Any]) -> RegimeAwareModelWrapper:
+    return RegimeAwareModelWrapper(
+        bundle["models"],
+        bundle["feature_columns"],
+        bundle["prediction_horizon"],
+        bundle["target_return_threshold"],
+    )
+
+
+def _portfolio_oos_rank_key(snapshot: dict[str, Any]) -> tuple[float, float, float]:
+    return (
+        float(snapshot["sharpe_ratio"]),
+        float(snapshot["total_return"]),
+        -abs(float(snapshot["max_drawdown"])),
+    )
+
+
+def portfolio_oos_beats_champion(
+    challenger: dict[str, Any],
+    champion: dict[str, Any],
+) -> bool:
+    """True when challenger ranks higher on Sharpe, then return, then drawdown."""
+    return _portfolio_oos_rank_key(challenger) > _portfolio_oos_rank_key(champion)
+
+
 def build_promotion_report(
     challenger_metadata: dict[str, Any],
     champion_metadata: dict[str, Any] | None,
+    *,
+    challenger_portfolio: dict[str, Any] | None = None,
+    champion_portfolio: dict[str, Any] | None = None,
+    portfolio_thresholds: Any | None = None,
+    require_portfolio_oos: bool = True,
 ) -> dict[str, Any]:
+    from src.portfolio_backtest_validation import (
+        PortfolioBacktestThresholds,
+        check_portfolio_summary_thresholds,
+    )
+
+    thresholds = portfolio_thresholds or PortfolioBacktestThresholds()
     challenger_auc = float(challenger_metadata.get("oos_metrics", {}).get("avg_roc_auc", 0.0))
-    champion_auc = float(champion_metadata.get("oos_metrics", {}).get("avg_roc_auc", 0.0)) if champion_metadata else None
-    promote = champion_metadata is None or challenger_auc > champion_auc
-    return {
+    champion_auc = (
+        float(champion_metadata.get("oos_metrics", {}).get("avg_roc_auc", 0.0))
+        if champion_metadata
+        else None
+    )
+    auc_ok = champion_metadata is None or challenger_auc > champion_auc
+
+    portfolio_gate = None
+    portfolio_gate_ok = True
+    portfolio_vs_ok = True
+
+    if require_portfolio_oos:
+        if challenger_portfolio is None:
+            portfolio_gate_ok = False
+            portfolio_vs_ok = False
+        else:
+            portfolio_gate = check_portfolio_summary_thresholds(
+                challenger_portfolio, thresholds
+            )
+            portfolio_gate_ok = portfolio_gate.passed
+
+            if champion_portfolio is None and champion_metadata is not None:
+                stored = champion_metadata.get("portfolio_oos")
+                if isinstance(stored, dict):
+                    champion_portfolio = stored
+
+            if champion_portfolio is not None:
+                portfolio_vs_ok = portfolio_oos_beats_champion(
+                    challenger_portfolio, champion_portfolio
+                )
+
+    promote = auc_ok and portfolio_gate_ok and portfolio_vs_ok
+
+    reasons: list[str] = []
+    if champion_metadata is None:
+        reasons.append("no existing champion metadata")
+    elif not auc_ok:
+        reasons.append(
+            f"challenger_avg_roc_auc={challenger_auc:.4f} vs champion_avg_roc_auc={champion_auc:.4f}"
+        )
+    if require_portfolio_oos and challenger_portfolio is None:
+        reasons.append("missing challenger portfolio OOS evaluation")
+    elif require_portfolio_oos and portfolio_gate is not None and not portfolio_gate_ok:
+        reasons.append("portfolio gates failed: " + "; ".join(portfolio_gate.failures))
+    elif (
+        require_portfolio_oos
+        and champion_portfolio is not None
+        and challenger_portfolio is not None
+        and not portfolio_vs_ok
+    ):
+        c, h = challenger_portfolio, champion_portfolio
+        reasons.append(
+            "portfolio OOS did not beat champion "
+            f"(sharpe {float(c['sharpe_ratio']):.4f} vs {float(h['sharpe_ratio']):.4f}, "
+            f"return {float(c['total_return']):.4f} vs {float(h['total_return']):.4f})"
+        )
+
+    if promote:
+        reason = (
+            "no existing champion; challenger passes portfolio OOS gates"
+            if champion_metadata is None
+            else "challenger passes AUC and portfolio OOS criteria"
+        )
+    else:
+        reason = "; ".join(reasons) if reasons else "challenger retained"
+
+    report: dict[str, Any] = {
         "generated_at": _utc_now_iso(),
         "champion_exists": champion_metadata is not None,
         "champion_avg_roc_auc": champion_auc,
         "challenger_avg_roc_auc": challenger_auc,
+        "auc_gate_passed": auc_ok,
+        "portfolio_gate_passed": portfolio_gate_ok,
+        "portfolio_vs_champion_passed": portfolio_vs_ok,
         "decision": "PROMOTE" if promote else "RETAIN_CHAMPION",
-        "reason": (
-            "no existing champion metadata"
-            if champion_metadata is None
-            else f"challenger_avg_roc_auc={'{:.4f}'.format(challenger_auc)} vs champion_avg_roc_auc={'{:.4f}'.format(champion_auc)}"
-        ),
+        "reason": reason,
     }
+    if challenger_portfolio is not None:
+        report["challenger_portfolio_oos"] = challenger_portfolio
+    if champion_portfolio is not None:
+        report["champion_portfolio_oos"] = champion_portfolio
+    if portfolio_gate is not None:
+        report["portfolio_gate_failures"] = portfolio_gate.failures
+        report["portfolio_gate_warnings"] = portfolio_gate.warnings
+    return report
 
 
 def train_ai_score_model(
diff --git a/src/portfolio_backtest_validation.py b/src/portfolio_backtest_validation.py
index 658e495..7d6d539 100644
--- a/src/portfolio_backtest_validation.py
+++ b/src/portfolio_backtest_validation.py
@@ -165,23 +165,13 @@ class PortfolioBacktestThresholdResult:
     warnings: list[str]
 
 
-def check_portfolio_backtest_thresholds(
-    output_dir: str | Path,
-    thresholds: PortfolioBacktestThresholds | None = None,
-    *,
-    validate_schema: bool = True,
-) -> PortfolioBacktestThresholdResult:
-    """Apply portfolio-level gates after schema validation."""
-    thresholds = thresholds or PortfolioBacktestThresholds()
+def _apply_portfolio_thresholds_to_summary(
+    summary: dict[str, Any],
+    thresholds: PortfolioBacktestThresholds,
+) -> tuple[list[str], list[str]]:
     failures: list[str] = []
     warnings: list[str] = []
 
-    if validate_schema:
-        result = validate_portfolio_backtest_dir(output_dir, min_equity_rows=2)
-        summary = result["summary"]
-    else:
-        summary = load_summary_row(Path(output_dir) / "portfolio_summary.csv")
-
     max_dd = float(summary["max_drawdown"])
     if max_dd < thresholds.max_drawdown_floor:
         failures.append(
@@ -204,6 +194,40 @@ def check_portfolio_backtest_thresholds(
         if sharpe < thresholds.min_sharpe:
             failures.append(f"sharpe_ratio {sharpe:.4f} < min {thresholds.min_sharpe:.4f}")
 
+    return failures, warnings
+
+
+def check_portfolio_summary_thresholds(
+    summary: dict[str, Any],
+    thresholds: PortfolioBacktestThresholds | None = None,
+) -> PortfolioBacktestThresholdResult:
+    """Apply portfolio-level gates to an in-memory summary row (retrain promotion)."""
+    thresholds = thresholds or PortfolioBacktestThresholds()
+    failures, warnings = _apply_portfolio_thresholds_to_summary(summary, thresholds)
+    return PortfolioBacktestThresholdResult(
+        summary=summary,
+        passed=not failures,
+        failures=failures,
+        warnings=warnings,
+    )
+
+
+def check_portfolio_backtest_thresholds(
+    output_dir: str | Path,
+    thresholds: PortfolioBacktestThresholds | None = None,
+    *,
+    validate_schema: bool = True,
+) -> PortfolioBacktestThresholdResult:
+    """Apply portfolio-level gates after schema validation."""
+    thresholds = thresholds or PortfolioBacktestThresholds()
+
+    if validate_schema:
+        result = validate_portfolio_backtest_dir(output_dir, min_equity_rows=2)
+        summary = result["summary"]
+    else:
+        summary = load_summary_row(Path(output_dir) / "portfolio_summary.csv")
+
+    failures, warnings = _apply_portfolio_thresholds_to_summary(summary, thresholds)
     return PortfolioBacktestThresholdResult(
         summary=summary,
         passed=not failures,
diff --git a/src/train_ai_model.py b/src/train_ai_model.py
index 0091776..f250ae1 100644
--- a/src/train_ai_model.py
+++ b/src/train_ai_model.py
@@ -16,7 +16,9 @@ from src.ml_model import (
     archive_current_champion,
     build_model_bundle,
     build_promotion_report,
+    bundle_to_model_wrapper,
     find_latest_archived_champion,
+    load_ai_score_model,
     load_model_metadata,
     restore_archived_champion,
     save_challenger_bundle,
@@ -24,8 +26,17 @@ from src.ml_model import (
     train_ai_score_model,
 )
 from src.macro_loader import load_macro_data
+from src.retrain_holdout import (
+    exclude_holdout_from_ticker_data,
+    portfolio_holdout_window,
+    slice_ticker_data_to_holdout,
+)
 from src.notifier import notify_info
-from src.portfolio_backtester import run_portfolio_backtest
+from src.portfolio_backtester import (
+    PortfolioBacktestResult,
+    build_ai_score_frames,
+    run_portfolio_backtest,
+)
 
 VIX_TICKER = "^VIX"
 RETRAIN_LOG_PATH = Path("logs/retrain_history.csv")
@@ -332,6 +343,114 @@ def _score_threshold_row(row: dict) -> tuple[float, float, float, float]:
     )
 
 
+def _portfolio_oos_snapshot(
+    result: PortfolioBacktestResult,
+    eval_start: pd.Timestamp,
+    eval_end: pd.Timestamp,
+) -> dict:
+    return {
+        "evaluation_start": eval_start.strftime("%Y-%m-%d"),
+        "evaluation_end": eval_end.strftime("%Y-%m-%d"),
+        "total_return": float(result.total_return),
+        "benchmark_return": float(result.benchmark_return),
+        "max_drawdown": float(result.max_drawdown),
+        "sharpe_ratio": float(result.sharpe_ratio),
+        "trades": int(result.trades),
+        "win_rate": float(result.win_rate),
+    }
+
+
+def _run_retrain_oos_portfolio(
+    *,
+    settings,
+    ticker_data: dict[str, pd.DataFrame],
+    vix_df: pd.DataFrame | None,
+    macro_df: pd.DataFrame | None,
+    model_wrapper,
+    eval_start: pd.Timestamp,
+    eval_end: pd.Timestamp,
+) -> dict:
+    """Portfolio backtest on holdout-only price data for model promotion."""
+    benchmark_df = (
+        ticker_data.get(settings.market_regime_ticker)
+        if settings.market_regime_filter_enabled
+        else None
+    )
+    relative_strength_benchmark_df = (
+        ticker_data.get(settings.relative_strength_benchmark_ticker)
+        if settings.relative_strength_filter_enabled
+        else None
+    )
+    spy_df = ticker_data.get("SPY")
+
+    ai_score_frames = None
+    if settings.use_ai_score:
+        ai_score_frames = build_ai_score_frames(
+            ticker_data,
+            ai_model_bundle=model_wrapper,
+            vix_df=vix_df,
+            spy_df=spy_df,
+            macro_df=macro_df,
+        )
+
+    result, _, _ = run_portfolio_backtest(
+        ticker_data=ticker_data,
+        benchmark_df=benchmark_df,
+        relative_strength_benchmark_df=relative_strength_benchmark_df,
+        initial_cash=10000.0,
+        max_positions=settings.max_total_positions,
+        target_position_pct=settings.max_position_pct,
+        transaction_cost_pct=0.001,
+        ma_fast=settings.ma_fast,
+        ma_slow=settings.ma_slow,
+        rsi_buy_limit=settings.rsi_buy_limit,
+        use_ai_score=settings.use_ai_score,
+        ai_score_buy_threshold=settings.ai_score_buy_threshold,
+        market_regime_filter_enabled=settings.market_regime_filter_enabled,
+        market_regime_ma_fast=settings.market_regime_ma_fast,
+        market_regime_ma_slow=settings.market_regime_ma_slow,
+        relative_strength_filter_enabled=settings.relative_strength_filter_enabled,
+        relative_strength_lookback_days=settings.relative_strength_lookback_days,
+        relative_strength_min_excess_return=settings.relative_strength_min_excess_return,
+        volume_filter_enabled=settings.volume_filter_enabled,
+        volume_lookback_days=settings.volume_lookback_days,
+        min_volume_ratio=settings.min_volume_ratio,
+        volatility_filter_enabled=settings.volatility_filter_enabled,
+        volatility_lookback_days=settings.volatility_lookback_days,
+        max_volatility=settings.max_volatility,
+        rank_trend_weight=settings.rank_trend_weight,
+        rank_ai_weight=settings.rank_ai_weight,
+        rank_momentum_weight=settings.rank_momentum_weight,
+        rank_volatility_weight=settings.rank_volatility_weight,
+        ai_exit_enabled=getattr(settings, "ai_exit_enabled", False),
+        ai_exit_threshold=(
+            settings.ai_exit_threshold_bear
+            if getattr(settings, "ai_exit_dynamic_enabled", False)
+            else settings.ai_exit_threshold
+        ),
+        ai_exit_dynamic_enabled=getattr(settings, "ai_exit_dynamic_enabled", False),
+        ai_exit_vix_low=getattr(settings, "ai_exit_vix_low", 15.0),
+        ai_exit_vix_high=getattr(settings, "ai_exit_vix_high", 25.0),
+        ai_exit_threshold_bull=getattr(settings, "ai_exit_threshold_bull", 0.22),
+        ai_exit_threshold_bear=getattr(settings, "ai_exit_threshold_bear", 0.50),
+        vix_df=vix_df,
+        macro_df=macro_df,
+        ai_score_frames=ai_score_frames,
+        evaluation_start_date=eval_start,
+        evaluation_end_date=eval_end,
+    )
+    return _portfolio_oos_snapshot(result, eval_start, eval_end)
+
+
+def _load_champion_model_wrapper():
+    if not MODEL_PATH.exists():
+        return None
+    try:
+        return load_ai_score_model()
+    except (FileNotFoundError, ValueError):
+        return None
+
+
 def _run_threshold_retune(
     settings,
     ticker_data: dict[str, pd.DataFrame],
@@ -464,9 +583,19 @@ def main() -> None:
     else:
         print(f"  Macro data: {len(macro_df)} rows, columns: {list(macro_df.columns)}")
 
+    holdout_start, holdout_end = portfolio_holdout_window(training_data)
+    training_data_fit = exclude_holdout_from_ticker_data(training_data, holdout_start)
+    holdout_ticker_data = slice_ticker_data_to_holdout(
+        training_data, holdout_start, holdout_end
+    )
+    print(
+        f"Portfolio promotion holdout: {holdout_start.strftime('%Y-%m-%d')} "
+        f"to {holdout_end.strftime('%Y-%m-%d')} (excluded from challenger training)"
+    )
+
     print("Training model with LightGBM + enhanced features (21 features)...")
     model, metrics_df = train_ai_score_model(
-        training_data=training_data,
+        training_data=training_data_fit,
         prediction_horizon=20,
         target_return_threshold=0.0,
         vix_df=vix_df,
@@ -536,11 +665,46 @@ def main() -> None:
         target_return_threshold=model.target_return_threshold,
     )
 
+    challenger_portfolio = None
+    champion_portfolio = None
+    if settings.use_ai_score:
+        if not holdout_ticker_data:
+            raise ValueError(
+                "Portfolio holdout slice is empty; cannot score promotion gates"
+            )
+        print("Running holdout-only portfolio evaluation for promotion gates...")
+        challenger_portfolio = _run_retrain_oos_portfolio(
+            settings=settings,
+            ticker_data=holdout_ticker_data,
+            vix_df=vix_df,
+            macro_df=macro_df,
+            model_wrapper=bundle_to_model_wrapper(bundle),
+            eval_start=holdout_start,
+            eval_end=holdout_end,
+        )
+        challenger_portfolio["holdout_excluded_from_training"] = True
+        bundle["metadata"]["portfolio_oos"] = challenger_portfolio
+        champion_wrapper = _load_champion_model_wrapper()
+        if champion_wrapper is not None:
+            champion_portfolio = _run_retrain_oos_portfolio(
+                settings=settings,
+                ticker_data=holdout_ticker_data,
+                vix_df=vix_df,
+                macro_df=macro_df,
+                model_wrapper=champion_wrapper,
+                eval_start=holdout_start,
+                eval_end=holdout_end,
+            )
+            champion_portfolio["holdout_excluded_from_training"] = True
+
     challenger_model_path, challenger_metadata_path = save_challenger_bundle(bundle)
     champion_metadata = load_model_metadata()
     promotion_report = build_promotion_report(
         challenger_metadata=bundle["metadata"],
         champion_metadata=champion_metadata,
+        challenger_portfolio=challenger_portfolio,
+        champion_portfolio=champion_portfolio,
+        require_portfolio_oos=settings.use_ai_score,
     )
     promotion_report.update(
         {
diff --git a/tests/test_model_governance.py b/tests/test_model_governance.py
index 37ff928..32b3bff 100644
--- a/tests/test_model_governance.py
+++ b/tests/test_model_governance.py
@@ -10,9 +10,11 @@ from src.ml_model import (
     build_promotion_report,
     find_latest_archived_champion,
     load_model_metadata,
+    portfolio_oos_beats_champion,
     restore_archived_champion,
     save_model_bundle,
 )
+from src.portfolio_backtest_validation import PortfolioBacktestThresholds
 from src.train_ai_model import _evaluate_rollback_need
 
 
@@ -53,10 +55,69 @@ class ModelGovernanceTest(unittest.TestCase):
         challenger_metadata = {"oos_metrics": {"avg_roc_auc": 0.63}}
         champion_metadata = {"oos_metrics": {"avg_roc_auc": 0.60}}
 
-        report = build_promotion_report(challenger_metadata, champion_metadata)
+        report = build_promotion_report(
+            challenger_metadata,
+            champion_metadata,
+            require_portfolio_oos=False,
+        )
+
+        self.assertEqual(report["decision"], "PROMOTE")
+        self.assertTrue(report["auc_gate_passed"])
+
+    def test_build_promotion_report_requires_portfolio_gates(self) -> None:
+        challenger_metadata = {"oos_metrics": {"avg_roc_auc": 0.63}}
+        champion_metadata = {"oos_metrics": {"avg_roc_auc": 0.60}}
+        weak_portfolio = {
+            "total_return": 0.02,
+            "benchmark_return": 0.20,
+            "max_drawdown": -0.30,
+            "sharpe_ratio": -0.2,
+        }
+        strong_portfolio = {
+            "total_return": 0.15,
+            "benchmark_return": 0.10,
+            "max_drawdown": -0.08,
+            "sharpe_ratio": 1.1,
+        }
+
+        report = build_promotion_report(
+            challenger_metadata,
+            champion_metadata,
+            challenger_portfolio=weak_portfolio,
+            champion_portfolio=strong_portfolio,
+            portfolio_thresholds=PortfolioBacktestThresholds(max_drawdown_floor=-0.20),
+        )
+
+        self.assertEqual(report["decision"], "RETAIN_CHAMPION")
+        self.assertTrue(report["auc_gate_passed"])
+        self.assertFalse(report["portfolio_gate_passed"])
+
+    def test_build_promotion_report_promotes_on_auc_and_portfolio(self) -> None:
+        challenger_metadata = {"oos_metrics": {"avg_roc_auc": 0.63}}
+        champion_metadata = {"oos_metrics": {"avg_roc_auc": 0.60}}
+        challenger_portfolio = {
+            "total_return": 0.12,
+            "benchmark_return": 0.10,
+            "max_drawdown": -0.08,
+            "sharpe_ratio": 1.2,
+        }
+        champion_portfolio = {
+            "total_return": 0.08,
+            "benchmark_return": 0.10,
+            "max_drawdown": -0.10,
+            "sharpe_ratio": 0.9,
+        }
+
+        report = build_promotion_report(
+            challenger_metadata,
+            champion_metadata,
+            challenger_portfolio=challenger_portfolio,
+            champion_portfolio=champion_portfolio,
+        )
 
         self.assertEqual(report["decision"], "PROMOTE")
-        self.assertIn("challenger_avg_roc_auc", report["reason"])
+        self.assertTrue(report["portfolio_vs_champion_passed"])
+        self.assertTrue(portfolio_oos_beats_champion(challenger_portfolio, champion_portfolio))
 
     def test_save_model_bundle_persists_metadata_json(self) -> None:
         bundle = {
diff --git a/tests/test_portfolio_backtest_gate.py b/tests/test_portfolio_backtest_gate.py
index 520a2a7..3ad0db1 100644
--- a/tests/test_portfolio_backtest_gate.py
+++ b/tests/test_portfolio_backtest_gate.py
@@ -8,6 +8,7 @@ import pytest
 from src.portfolio_backtest_validation import (
     PortfolioBacktestThresholds,
     check_portfolio_backtest_thresholds,
+    check_portfolio_summary_thresholds,
 )
 
 
@@ -34,6 +35,17 @@ def _write_minimal_bundle(dir_path: Path, summary_row: dict) -> None:
     ).to_csv(dir_path / "portfolio_trades.csv", index=False)
 
 
+def test_summary_thresholds_pass_in_memory():
+    summary = {
+        "total_return": 0.10,
+        "benchmark_return": 0.12,
+        "max_drawdown": -0.08,
+        "sharpe_ratio": 1.2,
+    }
+    result = check_portfolio_summary_thresholds(summary)
+    assert result.passed
+
+
 def test_thresholds_pass(tmp_path: Path):
     _write_minimal_bundle(
         tmp_path,
```
