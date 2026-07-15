# Agent Review Packet - Run: phase30_final

## Implementation Agent
cursor

## Task Description
Phase 30: JSON merge apply preserves tickers

## Changed Files
- TODO.md
- docs/TODO_ARCHIVE.md
- docs/runbook.md
- logs/crowding_paper/go_no_go_checklist.json
- logs/llm_advisory/latest_summary.json
- scripts/run_paper_ops_bootstrap.sh
- scripts/run_pass_complete.sh
- src/crowding_paper_gate.py
- tests/test_crowding_paper_gate.py
- tests/test_portfolio_backtest_gate.py

## Git Diff Summary
```
 TODO.md                                     |  26 +++-----
 docs/TODO_ARCHIVE.md                        |   4 +-
 docs/runbook.md                             |   5 +-
 logs/crowding_paper/go_no_go_checklist.json |   8 ++-
 logs/llm_advisory/latest_summary.json       |   6 +-
 scripts/run_paper_ops_bootstrap.sh          |  53 ++++++++++++---
 scripts/run_pass_complete.sh                |   3 +-
 src/crowding_paper_gate.py                  | 100 +++++++++++++++++++++++++++-
 tests/test_crowding_paper_gate.py           |  51 ++++++++++++++
 tests/test_portfolio_backtest_gate.py       |   2 +-
 10 files changed, 224 insertions(+), 34 deletions(-)
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
======================== 45 passed, 1 warning in 3.10s =========================
```

## Git Patch
```diff
diff --git a/TODO.md b/TODO.md
index 70e5dd2..0d6460e 100644
--- a/TODO.md
+++ b/TODO.md
@@ -5,7 +5,7 @@
 1. **코드** — 요구사항 반영, 프로젝트 스타일 준수
 2. **테스트** — 관련 pytest 추가·통과
 3. **운영** — 필요 시 백테스트/리포트·runbook 반영
-4. **리뷰** — `RUN_ID=<pass> SKIP_CODEX=1 bash scripts/run_pass_complete.sh` ([`docs/codex_review_policy.md`](docs/codex_review_policy.md))
+4. **리뷰** — `RUN_ID=<pass> bash scripts/run_pass_complete.sh` ([`docs/codex_review_policy.md`](docs/codex_review_policy.md))
 
 ---
 
@@ -14,36 +14,28 @@
 | 문서 | 역할 |
 |------|------|
 | **`TODO.md`** | 활성 로드맵 (다음 Phase만) |
-| **`docs/TODO_ARCHIVE.md`** | Phase 0–29 요약 |
+| **`docs/TODO_ARCHIVE.md`** | Phase 0–30 요약 |
 
 ---
 
-## Current Status (2026-05-31)
+## Current Status (2026-06-01)
 
 | 영역 | 상태 |
 |------|------|
 | **ML 백테스트** | **+96.8%** vs B&H **+65.0%** (gap +31.8pp), `beats_benchmark` |
-| **LLM** | `llm_advisory_only: true` — 주문 차단 없음, audit만 |
-| **Crowding** | `crowding_guard_enabled: false` — paper gate **NO_GO** (Sharpe Δ) |
-| **챔피언** | 로컬 `models/`; 승격 시 벤치 이상 필수 |
+| **LLM** | `llm_advisory_only: true` — audit 1667 rows, advisory report 갱신 |
+| **Crowding** | gate **NO_GO** — `crowding_guard_enabled: false` 유지 (proposal 미적용) |
+| **Paper ops** | `logs/paper_ops/latest_summary.json` (bootstrap 2026-06-01) |
 
-**Phase 29 완료** → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)
-
----
-
-## Phase 30 — Paper ops (유지보수)
-
-- [ ] 주기: `bash scripts/run_paper_ops_bootstrap.sh` (dry-run + 리포트)
-- [ ] paper에서 `execution_audit`·`data/llm_cache.json` 누적 후 `run_llm_advisory_report.sh`로 따름/무시 비교
-- [ ] Crowding: `bash scripts/run_crowding_paper_gate.sh` 재실행 후 **GO**일 때만 `config/crowding_paper_proposal.json` 값을 `strategy_config`에 반영
+**Phase 30 완료** → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)
 
 ---
 
 ## Quick commands
 
 ```bash
-bash scripts/run_paper_ops_bootstrap.sh
+bash scripts/run_paper_ops_bootstrap.sh              # full (model 필요 시 guard refresh)
+SKIP_ALPHA=1 bash scripts/run_paper_ops_bootstrap.sh # paper audit/advisory/crowding only
 bash scripts/run_alpha_pipeline.sh
 bash scripts/warm_llm_cache_from_backtest.sh   # 선택: 캐시 재충전
-RUN_ID=phase30 SKIP_CODEX=1 bash scripts/run_pass_complete.sh
 ```
diff --git a/docs/TODO_ARCHIVE.md b/docs/TODO_ARCHIVE.md
index 63d0699..09a3d1b 100644
--- a/docs/TODO_ARCHIVE.md
+++ b/docs/TODO_ARCHIVE.md
@@ -1,4 +1,4 @@
-# TODO Archive (Phase 0–23)
+# TODO Archive (Phase 0–30)
 
 완료된 로드맵 요약. 상세 체크리스트는 git history의 `TODO.md` 참고.
 
@@ -28,6 +28,7 @@
 | 27 | Universe + instrument meta | Master CSV, UNIVERSE_PROFILE, leveraged ETF registry and buy gates |
 | 28 | Margin leverage paper | Stress go/no-go gate, proposal caps, main buy block |
 | 29 | Beat benchmark (alpha) | Promotion ≥ bench, EW benchmark fix, alpha/operational pipelines, LLM advisory-only, cache warmup |
+| 30 | Paper ops maintenance | Bootstrap script, LLM advisory report wiring, crowding `--apply-config` (GO only), paper_ops summary |
 
 **Milestones**
 - **2026-05-27:** Phase 0–19 closed (code + pytest + runbook).
@@ -38,3 +39,4 @@
 - **2026-05-30:** Phase 27 closed; universe master/smoke/research profiles, instrument registry, leverage ETF gates.
 - **2026-05-30:** Phase 28 closed; margin leverage paper gate wired to leverage stress + main.
 - **2026-05-31:** Phase 29 closed; +96.8% vs B&H +65%, LLM advisory (no block), crowding paper gate NO_GO.
+- **2026-06-01:** Phase 30 closed; paper ops bootstrap, advisory impact report, crowding apply-on-GO guard, `logs/paper_ops/latest_summary.json`.
diff --git a/docs/runbook.md b/docs/runbook.md
index 61d7e2e..62795a4 100644
--- a/docs/runbook.md
+++ b/docs/runbook.md
@@ -84,7 +84,8 @@ LIVE_LLM=1 bash scripts/run_operational_alpha_validation.sh   # cache miss 시 G
 워밍업은 진입일 키(`{티커}_{YYYY-MM-DD}`)로 저장. 당일 yfinance에 기사가 없으면 **현재 헤드라인 fallback**으로 Gemini 호출(완전한 과거 뉴스 아카이브는 아님). paper `main.py` 실행 시 같은 키로 캐시가 계속 쌓임.
 
 ```bash
-bash scripts/run_paper_ops_bootstrap.sh   # dry-run + advisory + alpha + operational summaries
+bash scripts/run_paper_ops_bootstrap.sh   # dry-run + advisory + alpha + operational + crowding gate
+SKIP_ALPHA=1 bash scripts/run_paper_ops_bootstrap.sh   # model/alpha 없을 때 paper audit·crowding만
 ```
 
 ### 2.3.2 Crowding guard (paper)
@@ -94,6 +95,8 @@ bash scripts/run_paper_ops_bootstrap.sh   # dry-run + advisory + alpha + operati
 ```bash
 bash scripts/run_guard_impact_report.sh
 bash scripts/run_crowding_paper_gate.sh   # writes logs/crowding_paper/go_no_go_checklist.json
+# strategy_config 반영은 guard impact **갱신 직후** 또는 APPLY_CROWDING_CONFIG=1 일 때만:
+bash scripts/run_crowding_paper_gate.sh --apply-config
 ```
 
 2026-05-31 gate 결과: **NO_GO** (Sharpe delta below floor). **GO** 전까지 prod config에 crowding 켜지 않음.
diff --git a/logs/crowding_paper/go_no_go_checklist.json b/logs/crowding_paper/go_no_go_checklist.json
index a15a61d..c9f4550 100644
--- a/logs/crowding_paper/go_no_go_checklist.json
+++ b/logs/crowding_paper/go_no_go_checklist.json
@@ -21,8 +21,14 @@
       "pass": true
     }
   ],
+  "config_apply": {
+    "applied": false,
+    "config_path": "config/strategy_config.json",
+    "decision": "NO_GO",
+    "reason": "gate not GO_PAPER \u2014 strategy_config unchanged"
+  },
   "decision": "NO_GO",
-  "generated_at": "2026-05-31T14:15:57Z",
+  "generated_at": "2026-06-01T01:32:23Z",
   "guard_impact_path": "logs/guard_impact/latest_summary.json",
   "metrics": {
     "baseline": {
diff --git a/logs/llm_advisory/latest_summary.json b/logs/llm_advisory/latest_summary.json
index 8e02d90..8383a25 100644
--- a/logs/llm_advisory/latest_summary.json
+++ b/logs/llm_advisory/latest_summary.json
@@ -1,10 +1,10 @@
 {
-  "generated_at": "2026-05-31T14:15:36Z",
+  "generated_at": "2026-06-01T01:32:22Z",
   "audit_path": "logs/execution_audit.csv",
   "lookback_days": 90,
-  "rows": 117,
+  "rows": 1667,
   "advisory_would_reject": 0,
-  "buy_submitted": 0,
+  "buy_submitted": 9,
   "buy_submitted_despite_llm_reject": 0,
   "buy_blocked_by_llm": 0,
   "sample_would_reject": [],
diff --git a/scripts/run_paper_ops_bootstrap.sh b/scripts/run_paper_ops_bootstrap.sh
index c53223c..3d0db79 100755
--- a/scripts/run_paper_ops_bootstrap.sh
+++ b/scripts/run_paper_ops_bootstrap.sh
@@ -1,20 +1,57 @@
 #!/usr/bin/env bash
-# One-shot paper ops bootstrap: dry-run bot, advisory report, alpha + operational summaries.
+# One-shot paper ops bootstrap: dry-run bot, advisory report, alpha + operational summaries,
+# crowding gate refresh, and optional proposal apply (GO only).
 set -euo pipefail
 ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
 cd "$ROOT"
 export PYTHONPATH=.
+mkdir -p logs/paper_ops
 
-echo "=== [1/4] Bot dry-run (execution_audit + signals) ==="
+echo "=== [1/6] Bot dry-run (execution_audit + signals) ==="
 bash scripts/run_bot_once.sh dry-run
 
-echo "=== [2/4] LLM advisory report ==="
+echo "=== [2/6] LLM advisory report ==="
 bash scripts/run_llm_advisory_report.sh
 
-echo "=== [3/4] Alpha pipeline ==="
-bash scripts/run_alpha_pipeline.sh
+if [[ "${SKIP_ALPHA:-}" == "1" ]]; then
+  echo "=== [3/6] Alpha pipeline — SKIP_ALPHA=1 ==="
+  echo "=== [4/6] Operational in-loop — SKIP_ALPHA=1 ==="
+else
+  echo "=== [3/6] Alpha pipeline ==="
+  bash scripts/run_alpha_pipeline.sh
 
-echo "=== [4/4] Operational in-loop (cache replay) ==="
-bash scripts/run_operational_alpha_validation.sh
+  echo "=== [4/6] Operational in-loop (cache replay) ==="
+  bash scripts/run_operational_alpha_validation.sh
+fi
 
-echo "Done. See logs/execution_audit.csv and logs/*/latest_summary.json"
+echo "=== [5/6] Guard impact + crowding gate (apply proposal on GO only) ==="
+GUARD_IMPACT="logs/guard_impact/latest_summary.json"
+SKIP_CROWDING_GATE=0
+GUARD_REFRESHED=0
+
+if [[ -f models/ai_score_model.joblib ]] && [[ "${SKIP_GUARD_REFRESH:-}" != "1" ]]; then
+  bash scripts/run_guard_impact_report.sh
+  GUARD_REFRESHED=1
+elif [[ -f "$GUARD_IMPACT" ]]; then
+  echo "Using existing ${GUARD_IMPACT} (skip guard_impact refresh; gate report only)"
+elif [[ "${SKIP_ALPHA:-}" == "1" ]]; then
+  echo "WARN: ${GUARD_IMPACT} missing and model unavailable — skipping crowding gate."
+  echo "      Restore baseline: git checkout -- ${GUARD_IMPACT}"
+  SKIP_CROWDING_GATE=1
+else
+  echo "ERROR: ${GUARD_IMPACT} missing. Train model or restore baseline." >&2
+  exit 1
+fi
+
+if [[ "$SKIP_CROWDING_GATE" != "1" ]]; then
+  if [[ "$GUARD_REFRESHED" == "1" ]] || [[ "${APPLY_CROWDING_CONFIG:-}" == "1" ]]; then
+    bash scripts/run_crowding_paper_gate.sh --apply-config
+  else
+    bash scripts/run_crowding_paper_gate.sh
+  fi
+fi
+
+echo "=== [6/6] Paper ops summary ==="
+.venv/bin/python -m src.paper_ops_summary
+
+echo "Done. See logs/paper_ops/latest_summary.json, logs/execution_audit.csv, logs/llm_advisory/latest_summary.json"
diff --git a/scripts/run_pass_complete.sh b/scripts/run_pass_complete.sh
index cee8120..94bf49b 100755
--- a/scripts/run_pass_complete.sh
+++ b/scripts/run_pass_complete.sh
@@ -61,7 +61,8 @@ else
     tests/test_champion_promotion_governance.py \
     tests/test_equal_weight_benchmark.py \
     tests/test_promotion_beat_benchmark.py \
-    tests/test_llm_backtest_impact.py
+    tests/test_llm_backtest_impact.py \
+    tests/test_paper_ops_summary.py
 fi
 
 echo "=== [2/3] post-workflow / Codex ==="
diff --git a/src/crowding_paper_gate.py b/src/crowding_paper_gate.py
index c66442c..a651763 100644
--- a/src/crowding_paper_gate.py
+++ b/src/crowding_paper_gate.py
@@ -9,9 +9,20 @@ from datetime import datetime, timezone
 from pathlib import Path
 from typing import Any
 
+from src.settings import _validate_strategy_settings_payload
+
 DEFAULT_GUARD_IMPACT_PATH = Path("logs/guard_impact/latest_summary.json")
 DEFAULT_OUTPUT_DIR = Path("logs/crowding_paper")
 PROPOSAL_PATH = Path("config/crowding_paper_proposal.json")
+DEFAULT_STRATEGY_CONFIG_PATH = Path("config/strategy_config.json")
+
+CROWDING_PROPOSAL_KEYS = (
+    "crowding_guard_enabled",
+    "crowding_lookback_days",
+    "crowding_max_positions",
+    "crowding_momentum_threshold",
+    "crowding_trend_gap_threshold",
+)
 
 CROWDING_GATE_REPORT_KEYS = (
     "generated_at",
@@ -125,13 +136,78 @@ def write_crowding_gate_artifacts(
     return path
 
 
+def load_crowding_paper_proposal(path: Path = PROPOSAL_PATH) -> dict[str, Any]:
+    if not path.is_file():
+        raise FileNotFoundError(f"Crowding paper proposal missing: {path}")
+    payload = json.loads(path.read_text(encoding="utf-8"))
+    if not isinstance(payload, dict):
+        raise ValueError(f"{path} must contain a top-level JSON object")
+    return payload
+
+
+def apply_crowding_paper_proposal_if_go(
+    gate_report: dict[str, Any],
+    *,
+    config_path: Path = DEFAULT_STRATEGY_CONFIG_PATH,
+    proposal_path: Path = PROPOSAL_PATH,
+    dry_run: bool = False,
+) -> dict[str, Any]:
+    """Merge proposal crowding keys into strategy_config only when gate decision is GO_PAPER."""
+    decision = str(gate_report.get("decision", ""))
+    if decision != "GO_PAPER":
+        return {
+            "applied": False,
+            "decision": decision,
+            "config_path": str(config_path),
+            "reason": "gate not GO_PAPER — strategy_config unchanged",
+        }
+
+    proposal = load_crowding_paper_proposal(proposal_path)
+    overrides = {
+        key: proposal[key]
+        for key in CROWDING_PROPOSAL_KEYS
+        if key in proposal
+    }
+    if not overrides:
+        raise ValueError(f"No crowding keys found in proposal: {proposal_path}")
+
+    raw = json.loads(config_path.read_text(encoding="utf-8"))
+    if not isinstance(raw, dict):
+        raise ValueError(f"{config_path} must contain a top-level JSON object")
+    raw.update(overrides)
+    _validate_strategy_settings_payload(raw, config_path)
+    if not dry_run:
+        config_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
+
+    return {
+        "applied": True,
+        "decision": decision,
+        "config_path": str(config_path),
+        "proposal_path": str(proposal_path),
+        "overrides": overrides,
+        "dry_run": dry_run,
+    }
+
+
 def run_crowding_paper_gate(
     guard_impact_path: Path = DEFAULT_GUARD_IMPACT_PATH,
     output_dir: Path = DEFAULT_OUTPUT_DIR,
+    *,
+    apply_config: bool = False,
+    config_path: Path = DEFAULT_STRATEGY_CONFIG_PATH,
+    proposal_path: Path = PROPOSAL_PATH,
+    dry_run: bool = False,
 ) -> dict[str, Any]:
     guard_report = load_guard_impact_summary(guard_impact_path)
     report = validate_crowding_gate_report(evaluate_crowding_paper_gate(guard_report))
     report["guard_impact_path"] = str(guard_impact_path)
+    if apply_config:
+        report["config_apply"] = apply_crowding_paper_proposal_if_go(
+            report,
+            config_path=config_path,
+            proposal_path=proposal_path,
+            dry_run=dry_run,
+        )
     write_crowding_gate_artifacts(report, output_dir)
     return report
 
@@ -140,9 +216,31 @@ def main() -> None:
     parser = argparse.ArgumentParser(description="Crowding guard paper go/no-go checklist")
     parser.add_argument("--guard-impact", default=str(DEFAULT_GUARD_IMPACT_PATH))
     parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
+    parser.add_argument(
+        "--apply-config",
+        action="store_true",
+        help="When decision is GO_PAPER, merge config/crowding_paper_proposal.json into strategy_config",
+    )
+    parser.add_argument("--config-path", default=str(DEFAULT_STRATEGY_CONFIG_PATH))
+    parser.add_argument("--proposal-path", default=str(PROPOSAL_PATH))
+    parser.add_argument(
+        "--dry-run",
+        action="store_true",
+        help="With --apply-config, report overrides without writing strategy_config",
+    )
     args = parser.parse_args()
-    report = run_crowding_paper_gate(Path(args.guard_impact), Path(args.output_dir))
+    report = run_crowding_paper_gate(
+        Path(args.guard_impact),
+        Path(args.output_dir),
+        apply_config=args.apply_config,
+        config_path=Path(args.config_path),
+        proposal_path=Path(args.proposal_path),
+        dry_run=args.dry_run,
+    )
     print(format_crowding_gate_report(report))
+    apply_result = report.get("config_apply")
+    if apply_result:
+        print(f"Config apply: applied={apply_result['applied']} ({apply_result.get('reason', apply_result.get('overrides'))})")
 
 
 if __name__ == "__main__":
diff --git a/tests/test_crowding_paper_gate.py b/tests/test_crowding_paper_gate.py
index 8e6f68e..038ec26 100644
--- a/tests/test_crowding_paper_gate.py
+++ b/tests/test_crowding_paper_gate.py
@@ -1,10 +1,14 @@
 from pathlib import Path
 
+import json
+
 from src.crowding_paper_gate import (
+    apply_crowding_paper_proposal_if_go,
     evaluate_crowding_paper_gate,
     load_guard_impact_summary,
     validate_crowding_gate_report,
 )
+from src.settings import load_settings
 
 FIXTURE = Path(__file__).resolve().parent / "fixtures" / "guard_impact" / "latest_summary.json"
 
@@ -15,3 +19,50 @@ def test_crowding_paper_gate_go():
     )
     assert report["decision"] == "GO_PAPER"
     assert all(item["pass"] for item in report["checklist"])
+
+
+def test_apply_crowding_proposal_on_go(tmp_path, monkeypatch):
+    config_path = tmp_path / "strategy_config.json"
+    proposal_path = tmp_path / "crowding_paper_proposal.json"
+    config_path.write_text(
+        json.dumps({"tickers": ["AAPL", "MSFT"], "crowding_guard_enabled": False}),
+        encoding="utf-8",
+    )
+    proposal_path.write_text(
+        json.dumps(
+            {
+                "crowding_guard_enabled": True,
+                "crowding_lookback_days": 45,
+                "crowding_max_positions": 3,
+                "crowding_momentum_threshold": 0.12,
+                "crowding_trend_gap_threshold": 0.04,
+            }
+        ),
+        encoding="utf-8",
+    )
+    monkeypatch.setenv("UNIVERSE_PROFILE", "smoke")
+    result = apply_crowding_paper_proposal_if_go(
+        {"decision": "GO_PAPER"},
+        config_path=config_path,
+        proposal_path=proposal_path,
+    )
+    assert result["applied"] is True
+    updated = json.loads(config_path.read_text(encoding="utf-8"))
+    assert updated["tickers"] == ["AAPL", "MSFT"]
+    assert updated["crowding_guard_enabled"] is True
+    assert updated["crowding_lookback_days"] == 45
+
+
+def test_apply_crowding_proposal_skipped_on_no_go(tmp_path):
+    config_path = tmp_path / "strategy_config.json"
+    proposal_path = tmp_path / "crowding_paper_proposal.json"
+    config_path.write_text(json.dumps({"tickers": ["AAPL"], "crowding_guard_enabled": False}), encoding="utf-8")
+    before = config_path.read_text(encoding="utf-8")
+    proposal_path.write_text(json.dumps({"crowding_guard_enabled": True}), encoding="utf-8")
+    result = apply_crowding_paper_proposal_if_go(
+        {"decision": "NO_GO"},
+        config_path=config_path,
+        proposal_path=proposal_path,
+    )
+    assert result["applied"] is False
+    assert config_path.read_text(encoding="utf-8") == before
diff --git a/tests/test_portfolio_backtest_gate.py b/tests/test_portfolio_backtest_gate.py
index 3ad0db1..00c89b9 100644
--- a/tests/test_portfolio_backtest_gate.py
+++ b/tests/test_portfolio_backtest_gate.py
@@ -132,4 +132,4 @@ def test_cli_exit_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
         env=env,
         check=False,
     )
-    assert ok.returncode == 0
+    assert ok.returncode == 0
\ No newline at end of file
```
