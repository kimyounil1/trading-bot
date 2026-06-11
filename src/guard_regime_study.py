"""Multi-regime guard relaxation study (bull vs bear windows).

Compares sector/crowding guard scenarios across predefined market regimes,
writes artifacts for Ops/LLM, and exports a compact policy JSON for future
adaptive guards or model features.

Artifacts:
  logs/guard_regime_study/latest_summary.json
  logs/guard_regime_study/regime_comparison.csv
  data/research/guard_regime_policy.json
"""

from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pandas as pd

from src.data_loader import load_price_data_batch
from src.macro_loader import load_macro_data
from src.portfolio_backtest_settings import portfolio_backtest_kwargs
from src.portfolio_backtester import run_portfolio_backtest
from src.settings import StrategySettings, load_settings

DEFAULT_OUTPUT_DIR = Path("logs/guard_regime_study")
POLICY_PATH = Path("data/research/guard_regime_policy.json")
AUDIT_PATH = Path("logs/execution_audit.csv")

CALENDAR_DAYS = 14
WARMUP_CALENDAR_DAYS = 90
INITIAL_CASH = 100_000.0

GUARD_REGIME_STUDY_KEYS = (
    "generated_at",
    "methodology",
    "regimes",
    "recommendations",
    "llm_context_ko",
    "policy_path",
)


@dataclass(frozen=True)
class RegimeWindow:
    regime_id: str
    label_ko: str
    report_start: str
    report_end: str
    description: str


# Fixed windows (SPY 10–14d returns validated from 2y history)
REGIME_WINDOWS: tuple[RegimeWindow, ...] = (
    RegimeWindow(
        regime_id="bull_recent",
        label_ko="강세 (2026-03-30~04-14)",
        report_start="2026-03-30",
        report_end="2026-04-14",
        description="SPY ~+10% rally; tests guard relaxation in strong tape",
    ),
    RegimeWindow(
        regime_id="bear_recent",
        label_ko="약세·횡보 (2026-05-27~06-09)",
        report_start="2026-05-27",
        report_end="2026-06-09",
        description="Current weak tape; SPY ~-1.8%",
    ),
    RegimeWindow(
        regime_id="bear_stress",
        label_ko="급락 스트레스 (2025-03-25~04-08)",
        report_start="2025-03-25",
        report_end="2025-04-08",
        description="Tariff shock; SPY ~-14% in 2w",
    ),
)

SCENARIOS: tuple[tuple[str, dict[str, Any]], ...] = (
    ("baseline", {}),
    ("sector_max_3", {"max_sector_positions": 3}),
    ("crowding_max_3", {"crowding_max_positions": 3}),
    ("sector3_crowding3", {"max_sector_positions": 3, "crowding_max_positions": 3}),
)


@contextmanager
def _settings_patch(settings: StrategySettings):
    with patch("src.risk_manager.load_settings", return_value=settings):
        yield


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _valid_close(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").dropna()


def spy_return_pct(
    spy_df: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> float | None:
    spy = spy_df.copy()
    spy["date"] = pd.to_datetime(spy["date"]).dt.normalize()
    col = "adj_close" if "adj_close" in spy.columns else "close"
    window = spy[(spy["date"] >= start.normalize()) & (spy["date"] <= end.normalize())]
    prices = _valid_close(window[col])
    if len(prices) < 2:
        return None
    return float(prices.iloc[-1] / prices.iloc[0] - 1.0)


def warmup_start_for_report(
    spy_df: pd.DataFrame,
    report_start: pd.Timestamp,
) -> pd.Timestamp:
    dates = pd.to_datetime(spy_df["date"]).sort_values()
    warmup = report_start - pd.Timedelta(days=WARMUP_CALENDAR_DAYS)
    valid = dates[dates >= warmup]
    if valid.empty:
        raise ValueError(f"No warmup dates before {report_start.date()}")
    return pd.Timestamp(valid.iloc[0])


def _window_metrics(
    equity_df: pd.DataFrame,
    report_start: pd.Timestamp,
    report_end: pd.Timestamp,
) -> dict[str, float]:
    eq = equity_df.copy()
    eq["date"] = pd.to_datetime(eq["date"])
    window = eq[(eq["date"] >= report_start) & (eq["date"] <= report_end)].copy()
    if window.empty or len(window) < 2:
        return {
            "return_pct": 0.0,
            "mdd_pct": 0.0,
            "sharpe": 0.0,
            "avg_invested_pct": 0.0,
            "trading_days": float(len(window)),
        }
    start_eq = float(window.iloc[0]["equity"])
    end_eq = float(window.iloc[-1]["equity"])
    ret = end_eq / start_eq - 1.0 if start_eq > 0 else 0.0
    window["daily_return"] = window["equity"].pct_change().fillna(0.0)
    window["running_max"] = window["equity"].cummax()
    window["drawdown"] = window["equity"] / window["running_max"] - 1.0
    mdd = float(window["drawdown"].min())
    std = float(window["daily_return"].std())
    sharpe = float(window["daily_return"].mean() / std * (252**0.5)) if std > 1e-10 else 0.0
    avg_inv = float((window["positions_value"] / window["equity"]).mean())
    return {
        "return_pct": round(ret * 100, 3),
        "mdd_pct": round(mdd * 100, 3),
        "sharpe": round(sharpe, 3),
        "avg_invested_pct": round(avg_inv * 100, 1),
        "trading_days": float(len(window)),
    }


def _run_scenario(
    scenario_id: str,
    *,
    base_settings: StrategySettings,
    kwargs: dict[str, Any],
    report_start: pd.Timestamp,
    report_end: pd.Timestamp,
    settings_overrides: dict[str, Any],
) -> dict[str, Any]:
    settings = copy.deepcopy(base_settings)
    for key, value in settings_overrides.items():
        setattr(settings, key, value)

    run_kw = copy.copy(kwargs)
    run_kw["crowding_guard_enabled"] = bool(getattr(settings, "crowding_guard_enabled", False))
    run_kw["max_sector_positions"] = int(getattr(settings, "max_sector_positions", 2))

    with _settings_patch(settings):
        result, equity_df, trades_df = run_portfolio_backtest(**run_kw)

    wm = _window_metrics(equity_df, report_start, report_end)
    spy_df = kwargs["ticker_data"]["SPY"]
    spy_ret = spy_return_pct(spy_df, report_start, report_end)

    trades_n = 0
    win_rate = 0.0
    if not trades_df.empty:
        tdf = trades_df.copy()
        tdf["exit_date"] = pd.to_datetime(tdf["exit_date"])
        window_trades = tdf[
            (tdf["exit_date"] >= report_start) & (tdf["exit_date"] <= report_end)
        ]
        trades_n = int(len(window_trades))
        if trades_n:
            win_rate = float((window_trades["return_pct"] > 0).mean())

    alpha = None
    if spy_ret is not None:
        alpha = round((wm["return_pct"] / 100 - spy_ret) * 100, 3)

    return {
        "scenario_id": scenario_id,
        "return_pct": wm["return_pct"],
        "spy_return_pct": round(spy_ret * 100, 3) if spy_ret is not None else None,
        "alpha_vs_spy_pp": alpha,
        "mdd_pct": wm["mdd_pct"],
        "sharpe": wm["sharpe"],
        "trades_in_window": trades_n,
        "win_rate_pct": round(win_rate * 100, 1),
        "avg_invested_pct": wm["avg_invested_pct"],
        "max_sector_positions": int(getattr(settings, "max_sector_positions", 2)),
        "crowding_max_positions": int(getattr(settings, "crowding_max_positions", 2)),
    }


def _forward_return(price_df: pd.DataFrame, event_date: pd.Timestamp, hold_days: int) -> float | None:
    df = price_df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    event_date = pd.Timestamp(event_date).normalize()
    idx = df.index[df["date"] == event_date]
    if idx.empty:
        past = df[df["date"] <= event_date]
        if past.empty:
            return None
        start_i = int(past.index[-1])
    else:
        start_i = int(idx[0])
    end_i = start_i + hold_days
    if end_i >= len(df):
        return None
    col = "adj_close" if "adj_close" in df.columns else "close"
    p0 = float(df.iloc[start_i][col])
    p1 = float(df.iloc[end_i][col])
    if p0 <= 0:
        return None
    return p1 / p0 - 1.0


def audit_counterfactual_summary(
    report_start: pd.Timestamp,
    report_end: pd.Timestamp,
    ticker_data: dict[str, pd.DataFrame],
    *,
    audit_path: Path = AUDIT_PATH,
    hold_days: int = 5,
) -> list[dict[str, Any]]:
    if not audit_path.is_file():
        return []

    audit = pd.read_csv(audit_path)
    audit["timestamp"] = pd.to_datetime(audit["timestamp"], errors="coerce")
    audit = audit[
        (audit["timestamp"] >= report_start)
        & (audit["timestamp"] <= report_end + pd.Timedelta(days=1))
        & audit["event_type"].astype(str).str.contains("SKIP", na=False)
    ].copy()
    if audit.empty:
        return []

    def _block_type(reason: str) -> str:
        r = str(reason).lower()
        if "sector concentration" in r:
            return "sector"
        if "crowding" in r:
            return "crowding"
        if "rank ai gate blocked" in r:
            return "rank_gate"
        if r.startswith("signal is"):
            return "signal"
        return "other"

    audit["block_type"] = audit["reason"].map(_block_type)
    audit["event_date"] = audit["timestamp"].dt.normalize()
    audit["ticker"] = audit["ticker"].astype(str).str.upper()
    deduped = audit.drop_duplicates(subset=["event_date", "ticker", "block_type"])

    rows: list[float] = []
    by_type: dict[str, list[float]] = {}
    for _, row in deduped.iterrows():
        ticker = row["ticker"]
        if ticker not in ticker_data:
            continue
        fwd = _forward_return(ticker_data[ticker], row["event_date"], hold_days)
        if fwd is None:
            continue
        bt = row["block_type"]
        by_type.setdefault(bt, []).append(fwd)

    out: list[dict[str, Any]] = []
    for bt, rets in sorted(by_type.items()):
        series = pd.Series(rets)
        out.append(
            {
                "block_type": bt,
                "hold_days": hold_days,
                "events": int(len(series)),
                "mean_forward_return_pct": round(float(series.mean()) * 100, 3),
                "median_forward_return_pct": round(float(series.median()) * 100, 3),
            }
        )
    return out


def _best_scenario(scenarios: list[dict[str, Any]]) -> str:
    if not scenarios:
        return "baseline"
    ranked = sorted(
        scenarios,
        key=lambda r: (r.get("return_pct", 0.0), r.get("sharpe", 0.0)),
        reverse=True,
    )
    return str(ranked[0]["scenario_id"])


def _limits_from_scenario(scenario_id: str, default_sector: int = 2, default_crowd: int = 2) -> dict[str, int]:
    sector = 3 if "sector" in scenario_id and scenario_id != "baseline" else default_sector
    crowd = 3 if "crowding" in scenario_id else default_crowd
    if scenario_id == "baseline":
        return {"max_sector_positions": 2, "crowding_max_positions": 2}
    return {"max_sector_positions": sector, "crowding_max_positions": crowd}


def derive_recommendations(regimes: dict[str, Any]) -> dict[str, Any]:
    bull = regimes.get("bull_recent") or {}
    bear_recent = regimes.get("bear_recent") or {}
    bear_stress = regimes.get("bear_stress") or {}

    bull_best = bull.get("best_scenario", "baseline")
    bear_best = bear_recent.get("best_scenario", "baseline")
    stress_best = bear_stress.get("best_scenario", "baseline")

    bull_cf = {r["block_type"]: r for r in (bull.get("audit_counterfactual") or [])}
    bear_cf = {r["block_type"]: r for r in (bear_recent.get("audit_counterfactual") or [])}

    sector_bull = bull_cf.get("sector", {}).get("mean_forward_return_pct")
    sector_bear = bear_cf.get("sector", {}).get("mean_forward_return_pct")
    crowd_bull = bull_cf.get("crowding", {}).get("mean_forward_return_pct")
    crowd_bear = bear_cf.get("crowding", {}).get("mean_forward_return_pct")

    policy = {
        "bull_market": {
            "preferred_scenario": bull_best,
            **_limits_from_scenario(bull_best),
            "rationale_ko": (
                f"강세 구간 백테스트 최적: {bull_best}. "
                f"섹터 차단 종목 5d forward 평균 {sector_bull}% "
                f"(있을 경우 완화 검토)."
            ),
        },
        "bear_market": {
            "preferred_scenario": bear_best,
            **_limits_from_scenario(bear_best),
            "rationale_ko": (
                f"약세 구간 백테스트 최적: {bear_best}. "
                f"섹터 차단 forward {sector_bear}%, crowding {crowd_bear}% — "
                "완화 시 손실 종목 유입 가능성."
            ),
        },
        "bear_stress": {
            "preferred_scenario": stress_best,
            **_limits_from_scenario(stress_best),
            "rationale_ko": f"급락 구간 최적: {stress_best}. 가드 유지 권장.",
        },
    }

    spy_bear = bear_recent.get("spy_return_pct")
    current_regime = "bear" if spy_bear is not None and spy_bear < 0 else "bull"

    return {
        "current_regime_hint": current_regime,
        "bull_market": policy["bull_market"],
        "bear_market": policy["bear_market"],
        "bear_stress": policy["bear_stress"],
        "do_not_relax_guards_when": [
            "audit sector/crowding blocked names show negative 5d forward returns",
            "rank_ai_buy_gate paper observation still active (Phase 32)",
        ],
        "adaptive_policy_suggestion": {
            "description": "Future: map SPY 20d return to max_sector/crowding limits",
            "bear_threshold_spy_20d_pct": -3.0,
            "bull_threshold_spy_20d_pct": 3.0,
            "bear_limits": {"max_sector_positions": 2, "crowding_max_positions": 2},
            "bull_limits": {"max_sector_positions": 3, "crowding_max_positions": 3},
        },
    }


def format_llm_context_ko(report: dict[str, Any]) -> str:
    rec = report.get("recommendations") or {}
    lines = [
        "[가드·레짐 연구 요약 — guard_regime_study]",
        f"생성: {report.get('generated_at', '—')}",
        "",
    ]
    for regime_id, block in (report.get("regimes") or {}).items():
        lines.append(
            f"• {block.get('label_ko', regime_id)}: SPY {block.get('spy_return_pct')}% | "
            f"최적 시나리오={block.get('best_scenario')} | "
            f"baseline { _scenario_return(block, 'baseline')}%"
        )
    lines.extend(
        [
            "",
            f"현재 레짐 힌트: {rec.get('current_regime_hint', '—')}",
            f"강세 권장: { (rec.get('bull_market') or {}).get('preferred_scenario') }",
            f"약세 권장: { (rec.get('bear_market') or {}).get('preferred_scenario') }",
            "Rank gate/LLM 차단은 본 연구 미포함.",
        ]
    )
    return "\n".join(lines)


def _scenario_return(block: dict[str, Any], scenario_id: str) -> str:
    for row in block.get("scenarios") or []:
        if row.get("scenario_id") == scenario_id:
            return str(row.get("return_pct", "—"))
    return "—"


def load_guard_regime_study_summary(
    path: Path | None = None,
) -> dict[str, Any] | None:
    summary_path = path or (DEFAULT_OUTPUT_DIR / "latest_summary.json")
    if not summary_path.is_file():
        return None
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def load_guard_regime_llm_context(max_chars: int = 2000) -> str:
    """Short Korean block for LLM prompts or ops dashboards."""
    report = load_guard_regime_study_summary()
    if not report:
        return ""
    text = str(report.get("llm_context_ko") or format_llm_context_ko(report))
    return text[:max_chars]


def load_guard_regime_policy(path: Path = POLICY_PATH) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def validate_guard_regime_study_report(report: dict[str, Any]) -> dict[str, Any]:
    for key in GUARD_REGIME_STUDY_KEYS:
        if key not in report:
            raise ValueError(f"Missing guard regime study key: {key}")
    return report


def build_guard_regime_study_report(
    *,
    base_settings: StrategySettings | None = None,
    regime_windows: tuple[RegimeWindow, ...] = REGIME_WINDOWS,
    scenarios: tuple[tuple[str, dict[str, Any]], ...] = SCENARIOS,
    audit_path: Path = AUDIT_PATH,
) -> dict[str, Any]:
    settings = base_settings or load_settings()
    static = [str(t).upper() for t in settings.tickers]
    tickers_to_load = list(dict.fromkeys([*static, "SPY", "^VIX"]))
    loaded = load_price_data_batch(tickers_to_load, period="2y")
    ticker_data = {t: loaded[t] for t in static if t in loaded}
    ticker_data["SPY"] = loaded["SPY"]

    vix_df = loaded.get("^VIX")
    macro_df = load_macro_data(period="2y") if settings.use_ai_score else None
    rs_bench = loaded.get(settings.relative_strength_benchmark_ticker)

    regimes_out: dict[str, Any] = {}
    flat_rows: list[dict[str, Any]] = []

    for window in regime_windows:
        report_start = pd.Timestamp(window.report_start)
        report_end = pd.Timestamp(window.report_end)
        warmup_start = warmup_start_for_report(loaded["SPY"], report_start)
        spy_ret = spy_return_pct(loaded["SPY"], report_start, report_end)

        base_kw = portfolio_backtest_kwargs(
            settings,
            ticker_data=ticker_data,
            benchmark_df=loaded.get("SPY"),
            relative_strength_benchmark_df=rs_bench,
            vix_df=vix_df,
            macro_df=macro_df,
            initial_cash=INITIAL_CASH,
        )
        base_kw["evaluation_start_date"] = warmup_start
        base_kw["evaluation_end_date"] = report_end

        scenario_rows: list[dict[str, Any]] = []
        for scenario_id, overrides in scenarios:
            row = _run_scenario(
                scenario_id,
                base_settings=settings,
                kwargs=base_kw,
                report_start=report_start,
                report_end=report_end,
                settings_overrides=overrides,
            )
            scenario_rows.append(row)
            flat_rows.append(
                {
                    "regime_id": window.regime_id,
                    "regime_label": window.label_ko,
                    **row,
                }
            )

        cf = audit_counterfactual_summary(
            report_start,
            report_end,
            ticker_data,
            audit_path=audit_path,
        )
        best = _best_scenario(scenario_rows)
        regimes_out[window.regime_id] = {
            "label_ko": window.label_ko,
            "description": window.description,
            "report_start": window.report_start,
            "report_end": window.report_end,
            "spy_return_pct": round(spy_ret * 100, 3) if spy_ret is not None else None,
            "best_scenario": best,
            "scenarios": scenario_rows,
            "audit_counterfactual": cf,
        }

    recommendations = derive_recommendations(regimes_out)
    report = {
        "generated_at": _utc_now_iso(),
        "methodology": {
            "report_calendar_days": CALENDAR_DAYS,
            "warmup_calendar_days": WARMUP_CALENDAR_DAYS,
            "initial_cash": INITIAL_CASH,
            "scenarios": [s[0] for s in scenarios],
            "limitations": [
                "Daily-bar portfolio backtest; not identical to live execute path.",
                "Rank AI percentile gate and LLM blocking not replayed.",
                "Audit counterfactual only for bear_recent window with live audit data.",
            ],
            "consumers": [
                "logs/paper_ops/latest_summary.json (guard_regime_study block)",
                "CMS Ops dashboard via ops_report_presenter",
                "load_guard_regime_llm_context() for LLM prompt appendix",
                "data/research/guard_regime_policy.json for future adaptive guards",
            ],
        },
        "regimes": regimes_out,
        "recommendations": recommendations,
        "policy_path": str(POLICY_PATH),
    }
    report["llm_context_ko"] = format_llm_context_ko(report)
    return validate_guard_regime_study_report(report)


def write_guard_regime_study_artifacts(
    report: dict[str, Any],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    policy_path: Path = POLICY_PATH,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "latest_summary.json"
    summary_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    regimes = report.get("regimes") or {}
    rows: list[dict[str, Any]] = []
    for regime_id, block in regimes.items():
        for scenario in block.get("scenarios") or []:
            rows.append(
                {
                    "regime_id": regime_id,
                    "regime_label": block.get("label_ko"),
                    "spy_return_pct": block.get("spy_return_pct"),
                    **scenario,
                }
            )
    pd.DataFrame(rows).to_csv(output_dir / "regime_comparison.csv", index=False)

    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy = {
        "version": 1,
        "generated_at": report.get("generated_at"),
        "source": str(summary_path),
        "recommendations": report.get("recommendations"),
        "regime_winners": {
            rid: block.get("best_scenario") for rid, block in regimes.items()
        },
    }
    policy_path.write_text(
        json.dumps(policy, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary_path


def run_guard_regime_study() -> dict[str, Any]:
    report = build_guard_regime_study_report()
    write_guard_regime_study_artifacts(report)
    return report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Multi-regime guard relaxation study")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = run_guard_regime_study()
    write_guard_regime_study_artifacts(report, Path(args.output_dir))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
