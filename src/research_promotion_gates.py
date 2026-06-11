"""Consolidate research artifacts into operator promotion / policy gates.

Reads rank-label sweep summaries, guard-regime policy JSON, and recent
exit/timing backtest verdicts. Does not promote champion models.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.guard_regime_study import load_guard_regime_policy

DEFAULT_ML_DIR = Path("logs/ml")
DEFAULT_OUTPUT_DIR = Path("logs/research_promotion_gates")
RANK_LABEL_GLOB = "rank_label_experiment*/latest_summary.json"
GUARD_POLICY_PATH = Path("data/research/guard_regime_policy.json")
REGIME_STOP_PATH = Path("logs/regime_stop_backtest/latest_summary.json")
INTRADAY_TIMING_PATH = Path("logs/intraday_timing_2w/latest_summary.json")
PAPER_RANK_EXPERIMENT_ID = "rank_label_experiment_h20_top15_q85"
PAPER_RANK_MODEL_PATH = f"logs/ml/{PAPER_RANK_EXPERIMENT_ID}/rank_models.joblib"

RESEARCH_PROMOTION_KEYS = (
    "generated_at",
    "rank_label_sweep",
    "guard_regime_policy",
    "exit_timing_research",
    "paper_rank_gate",
    "blockers",
    "recommendations",
    "verdict_ko",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _experiment_id_from_path(path: Path) -> str:
    parent = path.parent.name
    if parent.startswith("rank_label_experiment"):
        return parent.removeprefix("rank_label_experiment").lstrip("_") or "default"
    return parent


def scan_rank_label_experiments(ml_dir: Path = DEFAULT_ML_DIR) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(ml_dir.glob(RANK_LABEL_GLOB)):
        report = _read_json(path)
        if not report:
            continue
        label = report.get("label") or {}
        portfolio = report.get("portfolio_oos") or {}
        gate = report.get("gate") or {}
        exp_id = _experiment_id_from_path(path)
        rows.append(
            {
                "experiment_id": exp_id,
                "path": str(path),
                "prediction_horizon": label.get("prediction_horizon"),
                "top_bucket_pct": label.get("top_bucket_pct"),
                "min_score_quantile": label.get("min_score_quantile"),
                "gate_passed": bool(gate.get("passed")),
                "gap_pct": portfolio.get("gap_pct"),
                "sharpe_ratio": portfolio.get("sharpe_ratio"),
                "max_drawdown": portfolio.get("max_drawdown"),
                "turnover_proxy": portfolio.get("turnover_proxy"),
                "top_bucket_auc": (report.get("metrics") or {}).get("top_bucket_auc"),
                "recommendation": report.get("recommendation"),
            }
        )
    return sorted(
        rows,
        key=lambda r: (
            not r["gate_passed"],
            -(float(r["gap_pct"]) if r.get("gap_pct") is not None else -999.0),
        ),
    )


def _pick_best_passed_rank(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    passed = [r for r in rows if r.get("gate_passed")]
    if not passed:
        return None
    return max(passed, key=lambda r: float(r.get("gap_pct") or -999.0))


def _paper_rank_gate_status(
    rows: list[dict[str, Any]],
    *,
    paper_experiment_id: str = PAPER_RANK_EXPERIMENT_ID,
    paper_model_path: str = PAPER_RANK_MODEL_PATH,
) -> dict[str, Any]:
    paper_row = next(
        (r for r in rows if r["experiment_id"] == paper_experiment_id.removeprefix("rank_label_experiment_")),
        None,
    )
    if paper_row is None:
        paper_row = next(
            (r for r in rows if paper_experiment_id in str(r.get("path", ""))),
            None,
        )
    best = _pick_best_passed_rank(rows)
    model_exists = Path(paper_model_path).is_file()
    aligned_with_best = (
        best is not None
        and paper_row is not None
        and paper_row.get("experiment_id") == best.get("experiment_id")
    )
    return {
        "paper_experiment_id": paper_experiment_id,
        "paper_model_path": paper_model_path,
        "paper_model_exists": model_exists,
        "paper_gate_passed": bool(paper_row and paper_row.get("gate_passed")),
        "aligned_with_best_oos": aligned_with_best,
        "best_passed_experiment_id": best.get("experiment_id") if best else None,
        "best_passed_gap_pct": best.get("gap_pct") if best else None,
        "tier": "tier1_rank_buy_gate_paper",
        "champion_promotion_allowed": False,
    }


def build_research_promotion_gates_report(
    *,
    ml_dir: Path = DEFAULT_ML_DIR,
    guard_policy_path: Path = GUARD_POLICY_PATH,
    regime_stop_path: Path = REGIME_STOP_PATH,
    intraday_path: Path = INTRADAY_TIMING_PATH,
) -> dict[str, Any]:
    rank_rows = scan_rank_label_experiments(ml_dir)
    guard_policy = load_guard_regime_policy(guard_policy_path) or _read_json(guard_policy_path)
    regime_stop = _read_json(regime_stop_path)
    intraday = _read_json(intraday_path)

    guard_rec = (guard_policy.get("recommendations") or {}) if guard_policy else {}
    regime_rec = regime_stop.get("recommendations") or {}
    intraday_rec = intraday.get("recommendations") or {}

    paper_rank = _paper_rank_gate_status(rank_rows)

    blockers: list[str] = []
    if not rank_rows:
        blockers.append("rank_label_sweep_missing: no rank_label_experiment*/latest_summary.json")
    elif not any(r.get("gate_passed") for r in rank_rows):
        blockers.append("rank_label_oos: no experiment passed portfolio gate")
    if paper_rank["paper_gate_passed"] and not paper_rank["paper_model_exists"]:
        blockers.append(f"paper rank model missing: {paper_rank['paper_model_path']}")

    recommendations = [
        "Champion (`models/ai_score_model.joblib`) promotion remains blocked per ai_authority_gates Tier 0.",
        (
            "Rank AI Tier-1 paper gate: use h20/top15%/q85 candidate only; "
            "complete ≥2 weeks paper observation before live default."
        ),
        (
            f"Guard policy ({guard_policy_path}): "
            f"current_regime={guard_rec.get('current_regime_hint', '—')}; "
            f"bull→{((guard_rec.get('bull_market') or {}).get('preferred_scenario'))}, "
            f"bear→{((guard_rec.get('bear_market') or {}).get('preferred_scenario'))}."
        ),
        (
            "Do not relax guards while rank_ai_buy_gate paper observation is active "
            "(see guard policy do_not_relax_guards_when)."
        ),
    ]
    if regime_rec.get("verdict_ko"):
        recommendations.append(f"Regime stop research: {regime_rec['verdict_ko']}")
    if intraday_rec.get("verdict_ko"):
        recommendations.append(f"Intraday timing research: {intraday_rec['verdict_ko']}")

    passed_count = sum(1 for r in rank_rows if r.get("gate_passed"))
    verdict_ko = (
        f"리서치 게이트: rank OOS 통과 {passed_count}건 · paper rank gate "
        f"{'OK' if paper_rank['paper_gate_passed'] else 'BLOCKED'} · "
        f"champion 승격 불가"
    )

    report = {
        "generated_at": _utc_now_iso(),
        "rank_label_sweep": {
            "count": len(rank_rows),
            "passed_count": passed_count,
            "experiments": rank_rows,
            "best_passed": _pick_best_passed_rank(rank_rows),
        },
        "guard_regime_policy": {
            "path": str(guard_policy_path),
            "loaded": bool(guard_policy),
            "recommendations": guard_rec,
            "do_not_relax_when": guard_rec.get("do_not_relax_guards_when") or [],
        },
        "exit_timing_research": {
            "regime_stop_verdict": regime_rec.get("verdict_ko"),
            "intraday_timing_verdict": intraday_rec.get("verdict_ko"),
            "regime_stop_path": str(regime_stop_path) if regime_stop else None,
            "intraday_timing_path": str(intraday_path) if intraday else None,
        },
        "paper_rank_gate": paper_rank,
        "blockers": blockers,
        "recommendations": recommendations,
        "verdict_ko": verdict_ko,
    }
    validate_research_promotion_gates_report(report)
    return report


def validate_research_promotion_gates_report(report: dict[str, Any]) -> dict[str, Any]:
    missing = [k for k in RESEARCH_PROMOTION_KEYS if k not in report]
    if missing:
        raise ValueError(f"Missing research promotion gates keys: {missing}")
    return report


def format_research_promotion_gates_summary(report: dict[str, Any]) -> str:
    lines = [
        "=== Research promotion gates ===",
        report.get("verdict_ko", ""),
        "",
        f"Rank label experiments: {report['rank_label_sweep']['count']} "
        f"({report['rank_label_sweep']['passed_count']} passed OOS gate)",
    ]
    best = report["rank_label_sweep"].get("best_passed") or {}
    if best:
        lines.append(
            f"  Best passed: {best.get('experiment_id')} gap={best.get('gap_pct')}pp "
            f"Sharpe={best.get('sharpe_ratio')}"
        )
    paper = report.get("paper_rank_gate") or {}
    lines.append(
        f"Paper rank gate: {paper.get('paper_experiment_id')} "
        f"model_exists={paper.get('paper_model_exists')} gate_passed={paper.get('paper_gate_passed')}"
    )
    guard = report.get("guard_regime_policy") or {}
    if guard.get("loaded"):
        rec = guard.get("recommendations") or {}
        lines.append(
            f"Guard regime: hint={rec.get('current_regime_hint')} "
            f"bull={((rec.get('bull_market') or {}).get('preferred_scenario'))} "
            f"bear={((rec.get('bear_market') or {}).get('preferred_scenario'))}"
        )
    exit_timing = report.get("exit_timing_research") or {}
    if exit_timing.get("regime_stop_verdict"):
        lines.append(f"Regime stop: {exit_timing['regime_stop_verdict']}")
    if exit_timing.get("intraday_timing_verdict"):
        lines.append(f"Intraday: {exit_timing['intraday_timing_verdict']}")
    blockers = report.get("blockers") or []
    if blockers:
        lines.extend(["", "Blockers:"])
        lines.extend(f"  - {b}" for b in blockers)
    lines.extend(["", "Recommendations:"])
    lines.extend(f"  - {r}" for r in report.get("recommendations") or [])
    return "\n".join(lines)


def write_research_promotion_gates_artifacts(
    report: dict[str, Any],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "latest_summary.json"
    md_path = output_dir / "latest_summary.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(format_research_promotion_gates_summary(report), encoding="utf-8")
    return json_path


def main() -> None:
    report = build_research_promotion_gates_report()
    path = write_research_promotion_gates_artifacts(report)
    print(format_research_promotion_gates_summary(report))
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
