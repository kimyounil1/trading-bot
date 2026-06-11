"""Aggregate paper ops bootstrap artifacts into one summary JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.settings import load_settings

DEFAULT_OUTPUT_DIR = Path("logs/paper_ops")
DEFAULT_AUDIT_PATH = Path("logs/execution_audit.csv")
DEFAULT_LLM_CACHE_PATH = Path("data/llm_cache.json")
DEFAULT_LLM_ADVISORY_PATH = Path("logs/llm_advisory/latest_summary.json")
DEFAULT_CROWDING_GATE_PATH = Path("logs/crowding_paper/go_no_go_checklist.json")
DEFAULT_CROWDING_LIVE_PATH = Path("logs/crowding_live/latest_summary.json")
DEFAULT_CROWDING_REASSESS_PATH = Path("logs/crowding_paper/reassessment.json")
DEFAULT_EXTENDED_FILL_PATH = Path("logs/paper_ops/extended_hours_fill_report.json")
DEFAULT_RANK_AI_GATE_PATH = Path("logs/rank_ai_gate/latest_summary.json")
DEFAULT_PAPER_VALIDATION_PATH = Path("logs/paper_validation/latest_summary.json")
DEFAULT_PAPER_VALIDATION_TREND_PATH = Path("logs/paper_validation/trend_summary.json")
DEFAULT_GUARD_REGIME_STUDY_PATH = Path("logs/guard_regime_study/latest_summary.json")
DEFAULT_RESEARCH_GATES_PATH = Path("logs/research_promotion_gates/latest_summary.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def build_paper_ops_summary(
    *,
    audit_path: Path = DEFAULT_AUDIT_PATH,
    llm_cache_path: Path = DEFAULT_LLM_CACHE_PATH,
    llm_advisory_path: Path = DEFAULT_LLM_ADVISORY_PATH,
    crowding_gate_path: Path = DEFAULT_CROWDING_GATE_PATH,
    crowding_live_path: Path = DEFAULT_CROWDING_LIVE_PATH,
    crowding_reassess_path: Path = DEFAULT_CROWDING_REASSESS_PATH,
    extended_fill_path: Path = DEFAULT_EXTENDED_FILL_PATH,
    rank_ai_gate_path: Path = DEFAULT_RANK_AI_GATE_PATH,
    paper_validation_path: Path = DEFAULT_PAPER_VALIDATION_PATH,
    paper_validation_trend_path: Path = DEFAULT_PAPER_VALIDATION_TREND_PATH,
    guard_regime_study_path: Path = DEFAULT_GUARD_REGIME_STUDY_PATH,
    research_gates_path: Path = DEFAULT_RESEARCH_GATES_PATH,
) -> dict[str, Any]:
    llm_advisory = _load_json_if_exists(llm_advisory_path) or {}
    rank_ai_gate = _load_json_if_exists(rank_ai_gate_path) or {}
    paper_validation = _load_json_if_exists(paper_validation_path) or {}
    paper_validation_trend = _load_json_if_exists(paper_validation_trend_path) or {}
    guard_regime_study = _load_json_if_exists(guard_regime_study_path) or {}
    research_gates = _load_json_if_exists(research_gates_path) or {}
    crowding_gate = _load_json_if_exists(crowding_gate_path) or {}
    crowding_live = _load_json_if_exists(crowding_live_path) or {}
    crowding_reassess = _load_json_if_exists(crowding_reassess_path) or {}
    extended_fill = _load_json_if_exists(extended_fill_path) or {}

    llm_cache_keys = 0
    if llm_cache_path.is_file():
        cache_payload = json.loads(llm_cache_path.read_text(encoding="utf-8"))
        if isinstance(cache_payload, dict):
            llm_cache_keys = len(cache_payload)

    audit_rows = 0
    if audit_path.is_file():
        audit_rows = max(0, sum(1 for _ in audit_path.open(encoding="utf-8")) - 1)

    config_apply = crowding_gate.get("config_apply") or {}
    settings = load_settings()
    crowding_enabled_in_config = bool(getattr(settings, "crowding_guard_enabled", False))
    rank_gate_cfg = rank_ai_gate.get("gate") or {}
    rank_audit = rank_ai_gate.get("execution_audit") or {}
    rank_cache = rank_ai_gate.get("candidate_cache") or {}
    return {
        "generated_at": _utc_now_iso(),
        "execution_audit_path": str(audit_path),
        "execution_audit_rows": audit_rows,
        "llm_cache_path": str(llm_cache_path),
        "llm_cache_keys": llm_cache_keys,
        "llm_advisory_path": str(llm_advisory_path),
        "llm_advisory": {
            "rows": llm_advisory.get("rows", 0),
            "advisory_would_reject": llm_advisory.get("advisory_would_reject", 0),
            "buy_submitted": llm_advisory.get("buy_submitted", 0),
            "buy_submitted_despite_llm_reject": llm_advisory.get(
                "buy_submitted_despite_llm_reject", 0
            ),
        },
        "crowding_gate_path": str(crowding_gate_path),
        "crowding_decision": crowding_gate.get("decision"),
        "crowding_guard_enabled_in_config": crowding_enabled_in_config,
        "crowding_gate_last_apply_attempted": bool(config_apply.get("applied", False)),
        "crowding_config_applied": crowding_enabled_in_config,
        "crowding_live_path": str(crowding_live_path),
        "crowding_reassessment_path": str(crowding_reassess_path),
        "crowding_live": {
            "lookback_days": crowding_live.get("live", {}).get("lookback_days"),
            "crowding_skip_count": crowding_live.get("live", {}).get("crowding_skip_count", 0),
            "skip_buy_count": crowding_live.get("live", {}).get("skip_buy_count", 0),
            "crowding_skip_rate_of_skips": crowding_live.get("live", {}).get(
                "crowding_skip_rate_of_skips", 0.0
            ),
            "by_kind": crowding_live.get("live", {}).get("by_kind", {}),
            "top_tickers": dict(
                list(
                    sorted(
                        (crowding_live.get("live", {}).get("by_ticker") or {}).items(),
                        key=lambda item: item[1],
                        reverse=True,
                    )
                )[:10]
            ),
            "alignment_notes": crowding_live.get("alignment", {}).get("notes", []),
        },
        "crowding_reassessment": {
            "recommendation": crowding_reassess.get("recommendation"),
            "rationale": crowding_reassess.get("rationale", []),
        },
        "extended_hours_fill_path": str(extended_fill_path),
        "extended_hours_fill": {
            "extended_limit_orders": extended_fill.get("extended_limit_orders", 0),
            "filled": extended_fill.get("filled", 0),
            "open_pending": extended_fill.get("open_pending", 0),
            "fill_rate_terminal": extended_fill.get("fill_rate_terminal"),
            "status": extended_fill.get("status"),
        },
        "rank_ai_gate_path": str(rank_ai_gate_path),
        "rank_ai_gate": {
            "enabled": rank_gate_cfg.get("enabled", getattr(settings, "rank_ai_buy_gate_enabled", False)),
            "min_score_quantile": rank_gate_cfg.get("min_score_quantile"),
            "skip_buy_rank_blocked": rank_audit.get("skip_buy_rank_blocked", 0),
            "buy_submitted": rank_audit.get("buy_submitted", 0),
            "cache_rank_blocked_rows": rank_cache.get("rank_blocked_rows", 0),
            "cache_rank_passed_rows": rank_cache.get("rank_passed_rows", 0),
        },
        "paper_validation_path": str(paper_validation_path),
        "paper_validation_trend_path": str(paper_validation_trend_path),
        "paper_validation": {
            "agreement_pct": (paper_validation.get("llm_ai_agreement") or {}).get(
                "agreement_pct"
            ),
            "skip_ai_score": (paper_validation.get("audit_buy_paths") or {}).get(
                "skip_ai_score_layer"
            ),
            "skip_llm_block": (paper_validation.get("audit_buy_paths") or {}).get(
                "skip_llm_block_layer"
            ),
            "skip_rank_gate": (paper_validation.get("audit_buy_paths") or {}).get(
                "skip_rank_gate_layer"
            ),
            "ai_pass_llm_block": (paper_validation.get("audit_buy_paths") or {}).get(
                "ai_pass_llm_block"
            ),
            "rank_gate_ready": (paper_validation.get("rank_gate_paper_tracker") or {}).get(
                "gate_ready"
            ),
            "rank_calendar_days": (
                paper_validation.get("rank_gate_paper_tracker") or {}
            ).get("calendar_days_with_rank_events"),
            "trend_rows": paper_validation_trend.get("rows", 0),
            "trend_alerts": paper_validation_trend.get("alerts", []),
        },
        "guard_regime_study_path": str(guard_regime_study_path),
        "guard_regime_study": {
            "generated_at": guard_regime_study.get("generated_at"),
            "current_regime_hint": (guard_regime_study.get("recommendations") or {}).get(
                "current_regime_hint"
            ),
            "bull_preferred": (
                (guard_regime_study.get("recommendations") or {}).get("bull_market") or {}
            ).get("preferred_scenario"),
            "bear_preferred": (
                (guard_regime_study.get("recommendations") or {}).get("bear_market") or {}
            ).get("preferred_scenario"),
            "llm_context_ko": guard_regime_study.get("llm_context_ko"),
            "policy_path": guard_regime_study.get("policy_path"),
        },
        "research_gates_path": str(research_gates_path),
        "research_promotion_gates": {
            "verdict_ko": research_gates.get("verdict_ko"),
            "rank_passed_count": (research_gates.get("rank_label_sweep") or {}).get(
                "passed_count"
            ),
            "paper_rank_gate_passed": (research_gates.get("paper_rank_gate") or {}).get(
                "paper_gate_passed"
            ),
            "blockers": research_gates.get("blockers") or [],
        },
        "notes": [
            "Run via: bash scripts/run_paper_ops_bootstrap.sh",
            "Crowding proposal merges only with: APPLY_CROWDING_CONFIG=1 bash scripts/run_paper_ops_bootstrap.sh",
            "crowding_config_applied reflects strategy_config.json (not stale gate config_apply).",
            "After dry-run: bash scripts/run_crowding_live_impact_report.sh for SKIP_BUY crowding monitoring.",
            "Guard regime study: bash scripts/run_guard_regime_study.sh (bull/bear guard comparison).",
            "Research gates: bash scripts/run_research_promotion_gates.sh (rank sweep + policy).",
        ],
    }


def write_paper_ops_summary(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    **kwargs: Any,
) -> Path:
    report = build_paper_ops_summary(**kwargs)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "latest_summary.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Write paper ops bootstrap summary JSON")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    path = write_paper_ops_summary(Path(args.output_dir))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
