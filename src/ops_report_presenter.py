"""Human-readable summaries for Ops dashboard JSON reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class OpsReportSpec:
    report_id: str
    title: str
    subtitle: str
    paths: tuple[str, ...]
    generate_hint: str
    generate_argv: tuple[str, ...] | None = None


OPS_REPORT_SPECS: tuple[OpsReportSpec, ...] = (
    OpsReportSpec(
        "paper_ops",
        "Paper 운영 한눈에 보기",
        "봇 로그·LLM·몰림(crowding) 차단·야간 주문 체결 요약",
        ("logs/paper_ops/latest_summary.json",),
        "bash scripts/run_paper_ops_bootstrap.sh",
        ("bash", "scripts/run_paper_ops_bootstrap.sh"),
    ),
    OpsReportSpec(
        "audit_daily",
        "오늘 봇이 뭘 했는지",
        "매수 스킵·체결·에러 건수 (execution_audit 집계)",
        ("logs/audit_daily/latest_summary.json",),
        "bash scripts/run_daily_audit_summary.sh",
        ("bash", "scripts/run_daily_audit_summary.sh"),
    ),
    OpsReportSpec(
        "slippage",
        "주문 가격 vs 체결 가격",
        "슬리피지(체결가가 얼마나 밀렸는지) 주간 요약",
        ("logs/slippage_reports/latest_summary.json",),
        "bash scripts/run_weekly_slippage_report.sh",
        ("bash", "scripts/run_weekly_slippage_report.sh"),
    ),
    OpsReportSpec(
        "llm_cache",
        "LLM 뉴스 판단 캐시",
        "종목별 Gemini/vLLM 승인·거절 기록 (API 재호출 줄이기)",
        (
            "logs/llm_monitoring/latest_summary.json",
            "data/llm_cache.json",
        ),
        "bash scripts/run_llm_cache_report.sh",
        ("bash", "scripts/run_llm_cache_report.sh"),
    ),
    OpsReportSpec(
        "execution_alignment",
        "실행 로그끼리 맞는지",
        "audit vs 슬리피지 리포트 숫자가 같은지 교차 확인",
        ("logs/execution_alignment/latest_summary.json",),
        "bash scripts/run_execution_alignment_report.sh (슬리피지 리포트 선행)",
        ("bash", "scripts/run_execution_alignment_report.sh"),
    ),
    OpsReportSpec(
        "benchmark_gap",
        "전략 vs 시장 수익 차이",
        "백테스트 수익이 벤치마크(SPY 등)보다 얼마나 앞섰는지",
        ("logs/benchmark_gap/latest_summary.json",),
        "bash scripts/run_benchmark_gap_report.sh",
        ("bash", "scripts/run_benchmark_gap_report.sh"),
    ),
    OpsReportSpec(
        "guard_impact",
        "가드 켰을 때 백테스트 차이",
        "몰림 가드 ON/OFF 시 수익·샤프·낙폭 비교",
        ("logs/guard_impact/latest_summary.json",),
        "bash scripts/run_guard_impact_report.sh",
        ("bash", "scripts/run_guard_impact_report.sh"),
    ),
    OpsReportSpec(
        "crowding_live",
        "몰림 가드 — 실제 봇 로그",
        "최근 dry-run/execute에서 '비슷한 종목 너무 많음'으로 막은 횟수",
        ("logs/crowding_live/latest_summary.json",),
        "bash scripts/run_crowding_live_impact_report.sh",
        ("bash", "scripts/run_crowding_live_impact_report.sh"),
    ),
    OpsReportSpec(
        "crowding_gate",
        "몰림 가드 — paper 켜도 될까?",
        "백테스트 기준 GO/NO-GO 체크리스트",
        ("logs/crowding_paper/go_no_go_checklist.json",),
        "bash scripts/run_crowding_paper_gate.sh",
        ("bash", "scripts/run_crowding_paper_gate.sh"),
    ),
    OpsReportSpec(
        "leverage_stress",
        "레버리지 스트레스",
        "레버리지 올렸을 때 낙폭·마진 시나리오",
        ("logs/leverage_stress/latest_summary.json",),
        "bash scripts/run_leverage_stress_report.sh",
        ("bash", "scripts/run_leverage_stress_report.sh"),
    ),
    OpsReportSpec(
        "fold_variance",
        "모델 fold 안정성",
        "학습 fold마다 성능 편차",
        ("logs/fold_variance/latest_summary.json",),
        "bash scripts/run_fold_variance_report.sh",
        ("bash", "scripts/run_fold_variance_report.sh"),
    ),
    OpsReportSpec(
        "promotion",
        "모델 승격 후보",
        "새 모델이 production 후보보다 나은지",
        ("logs/promotion_summary/latest_summary.json",),
        "alpha 파이프라인 일부 — run_alpha_pipeline.sh",
        None,
    ),
    OpsReportSpec(
        "model_quality",
        "모델 품질 점검",
        "현재 ai_score 모델 메트릭·드리프트",
        ("logs/model_quality/latest_summary.json",),
        "bash scripts/run_model_quality_report.sh",
        ("bash", "scripts/run_model_quality_report.sh"),
    ),
    OpsReportSpec(
        "paper_validation",
        "Paper 매수 검증 (AI+LLM·rank)",
        "execution_audit 스킵 레이어·LLM 일치·rank 2주 트래커",
        ("logs/paper_validation/latest_summary.json",),
        "bash scripts/run_paper_buy_validation.sh",
        ("bash", "scripts/run_paper_buy_validation.sh"),
    ),
)


def load_first_existing_json(root: Path, relative_paths: tuple[str, ...]) -> tuple[dict[str, Any] | None, str | None]:
    for rel in relative_paths:
        path = root / rel
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(payload, dict):
            return payload, rel
    return None, None


def _lines(*parts: str) -> list[str]:
    return [p for p in parts if p]


def summarize_report(report_id: str, data: dict[str, Any], *, source_path: str) -> list[str]:
    """Plain-Korean bullets for CMS; no jargon wall."""
    if report_id == "paper_ops":
        cl = data.get("crowding_live") or {}
        la = data.get("llm_advisory") or {}
        ef = data.get("extended_hours_fill") or {}
        rg = data.get("rank_ai_gate") or {}
        pv = data.get("paper_validation") or {}
        return _lines(
            f"실행 로그 {data.get('execution_audit_rows', 0):,}줄 ({data.get('execution_audit_path', '')})",
            f"몰림 가드: {'켜짐' if data.get('crowding_guard_enabled_in_config') else '꺼짐'} · gate {data.get('crowding_decision', '—')}",
            f"최근 몰림으로 매수 스킵 {cl.get('crowding_skip_count', 0)}건 (전체 스킵 대비 {100 * float(cl.get('crowding_skip_rate_of_skips') or 0):.1f}%)",
            f"LLM: would_reject {la.get('advisory_would_reject', 0)} · 실제 제출 {la.get('buy_submitted', 0)}",
            (
                f"Rank AI 매수 gate: {'켜짐' if rg.get('enabled') else '꺼짐'} · "
                f"스킵 {rg.get('skip_buy_rank_blocked', 0)} · 제출 {rg.get('buy_submitted', 0)} · "
                f"캐시 통과 {rg.get('cache_rank_passed_rows', 0)}"
                if rg
                else ""
            ),
            f"야간 지정가: 체결 {ef.get('filled', 0)} / 대기 {ef.get('open_pending', 0)}",
            (
                f"Paper 검증: LLM 일치 {pv.get('agreement_pct')}% · "
                f"rank {pv.get('rank_calendar_days', 0)}/14일 · ready={pv.get('rank_gate_ready')}"
                if pv
                else ""
            ),
        )
    if report_id == "crowding_live":
        live = data.get("live") or data
        back = data.get("backtest") or {}
        return _lines(
            f"최근 {live.get('lookback_days', '?')}일 · 매수 스킵 중 몰림 때문 {live.get('crowding_skip_count', 0)}건 "
            f"({100 * float(live.get('crowding_skip_rate_of_skips') or 0):.1f}%)",
            f"유형: 추세 몰림 { (live.get('by_kind') or {}).get('trend', 0) } · "
            f"급등 몰림 { (live.get('by_kind') or {}).get('momentum', 0) }",
            f"백테스트: 가드 켜면 거래 {back.get('baseline_trades', '—')} → {back.get('guarded_trades', '—')}건",
            *[
                f"· {n}"
                for n in (data.get("alignment") or {}).get("notes") or []
            ][:2],
        )
    if report_id == "crowding_gate":
        decision = data.get("decision", "—")
        checks = data.get("checklist") or []
        ok = sum(1 for c in checks if c.get("pass"))
        return _lines(
            f"판정: {decision} ({ok}/{len(checks)} 항목 통과)",
            *[f"{'✓' if c.get('pass') else '✗'} {c.get('id', '')}: {c.get('detail', '')}" for c in checks],
        )
    if report_id == "guard_impact":
        b = data.get("baseline") or {}
        g = data.get("with_crowding_guard") or {}
        d = data.get("delta") or {}
        return _lines(
            f"가드 없음: 수익 {b.get('total_return_pct', 0):.1f}% · 샤프 {b.get('sharpe_ratio', 0):.2f} · 거래 {b.get('trade_count', 0)}",
            f"몰림 가드 ON: 수익 {g.get('total_return_pct', 0):.1f}% · 샤프 {g.get('sharpe_ratio', 0):.2f} · "
            f"막은 거래 약 {g.get('estimated_crowding_blocked_trades', 0)}건",
            f"차이: 수익 {d.get('total_return_pct', 0):+.1f}%p · 샤프 {d.get('sharpe_ratio', 0):+.2f} · "
            f"낙폭 {d.get('max_drawdown_pct', 0):+.1f}%p",
        )
    if report_id == "benchmark_gap":
        summary = data.get("summary") or {}
        strategy_return = summary.get("total_return")
        benchmark_return = summary.get("benchmark_return")
        max_drawdown = summary.get("max_drawdown")
        sharpe_ratio = summary.get("sharpe_ratio")
        gap_pct = data.get("gap_pct")
        spy = data.get("spy_benchmark") or {}

        def pct(value: Any) -> str:
            if value is None:
                return "—"
            try:
                return f"{100 * float(value):.1f}%"
            except (TypeError, ValueError):
                return "—"

        def pp(value: Any) -> str:
            if value is None:
                return "—"
            try:
                return f"{float(value):+.2f}pp"
            except (TypeError, ValueError):
                return "—"

        return _lines(
            f"전략 {pct(strategy_return)} vs 동일비중 벤치 {pct(benchmark_return)}",
            f"차이 {pp(gap_pct)} · "
            f"{'벤치마크 초과' if data.get('beats_benchmark') else '벤치마크 미달'}",
            f"SPY 대비 {pp(spy.get('gap_pct'))}"
            if spy.get("available")
            else "SPY 대비 —",
            f"최대 낙폭 {pct(max_drawdown)} · 샤프 {float(sharpe_ratio):.2f}"
            if sharpe_ratio is not None
            else f"최대 낙폭 {pct(max_drawdown)} · 샤프 —",
        )
    if report_id == "llm_cache":
        if data.get("entry_count") is not None:
            return _lines(
                f"캐시 {data.get('entry_count', 0)}건 · 종목 {data.get('unique_tickers', 0)} · "
                f"승인 {data.get('approved_count', 0)} / 거절 {data.get('rejected_count', 0)}",
                f"재사용 추정 {100 * float(data.get('estimated_cache_hit_rate') or 0):.0f}%",
            )
        # raw data/llm_cache.json
        n = len(data)
        approved = sum(1 for v in data.values() if isinstance(v, dict) and v.get("is_approved"))
        return _lines(
            f"원본 캐시 파일 ({source_path}): {n}건",
            f"승인 {approved} · 거절 {n - approved}",
            "요약 리포트: bash scripts/run_llm_cache_report.sh",
        )
    if report_id == "audit_daily":
        skips = data.get("skip_by_event") or {}
        return _lines(
            f"기간 {data.get('lookback_days', '?')}일",
            f"SKIP_BUY {skips.get('SKIP_BUY', data.get('skip_buy_count', 0))}건",
            f"체결/제출 BUY {data.get('buy_submitted_count', data.get('buy_submitted', 0))}건",
        )
    if report_id == "slippage":
        return _lines(
            f"분석 주문 {data.get('order_count', data.get('rows', '—'))}건",
            f"평균 슬리피지 {data.get('mean_slippage_bps', data.get('avg_slippage_bps', '—'))} bps",
        )
    if report_id == "leverage_stress":
        return _lines(
            f"시나리오 수 {len(data.get('scenarios') or data.get('results') or []) or '—'}",
            f"상태: {data.get('status', data.get('decision', '—'))}",
        )
    if report_id == "model_quality":
        metrics = data.get("metrics") or {}
        blockers = data.get("blockers") or []
        return _lines(
            f"판정: {data.get('decision', '—')}",
            f"AUC {metrics.get('challenger_avg_roc_auc', '—')} · "
            f"Brier {metrics.get('overall_avg_brier_score', '—')} · "
            f"fold std {metrics.get('roc_auc_std', '—')}",
            f"현재 전략 벤치 gap {metrics.get('current_strategy_gap_pct', '—')}pp · "
            f"rank label OOS gap {metrics.get('rank_label_oos_gap_pp', '—')}pp",
            f"차단 요인 {len(blockers)}개",
            *[f"· {item}" for item in blockers[:2]],
        )
    if report_id == "paper_validation":
        paths = data.get("audit_buy_paths") or {}
        rank = data.get("rank_gate_paper_tracker") or {}
        agree = data.get("llm_ai_agreement") or {}
        return _lines(
            f"LLM 캐시 일치 {agree.get('agreement_pct', '—')}% "
            f"(비교 {agree.get('comparable_with_ai_score', 0)}건)",
            f"SKIP: AI {paths.get('skip_ai_score_layer', 0)} · "
            f"LLM {paths.get('skip_llm_block_layer', 0)} · "
            f"rank {paths.get('skip_rank_gate_layer', 0)}",
            f"AI통과·LLM차단 {paths.get('ai_pass_llm_block', 0)} · 제출 {paths.get('buy_submitted', 0)}",
            f"Rank paper: {rank.get('calendar_days_with_rank_events', 0)}/"
            f"{rank.get('min_calendar_days_required', 14)}일 · "
            f"ready={rank.get('gate_ready', False)}",
        )
    # fallback
    keys = ", ".join(list(data.keys())[:8])
    return _lines(f"파일: {source_path}", f"주요 필드: {keys}")


def group_specs() -> dict[str, list[OpsReportSpec]]:
    groups: dict[str, list[OpsReportSpec]] = {
        "지금 쓰는 운영": [],
        "백테스트·가드": [],
        "모델 (가끔)": [],
    }
    for spec in OPS_REPORT_SPECS:
        if spec.report_id in {"paper_ops", "audit_daily", "slippage", "llm_cache", "execution_alignment"}:
            groups["지금 쓰는 운영"].append(spec)
        elif spec.report_id in {"fold_variance", "promotion", "model_quality", "paper_validation"}:
            groups["모델 (가끔)"].append(spec)
        else:
            groups["백테스트·가드"].append(spec)
    return groups
