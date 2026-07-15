"""Daily paper BUY_PLAN versus operational backtest entry parity report."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import EXECUTION_AUDIT_LOG_PATH
from src.execution_audit_io import read_execution_audit_csv
from src.notifier import notify_error

DEFAULT_CONFIG_PATH = Path("config/paper_backtest_parity_config.json")
DEFAULT_OUTPUT_DIR = Path("logs/paper_backtest_parity")
DEFAULT_BACKTEST_DIR = Path("logs/daily_paper_backtest/latest")

REPORT_KEYS = (
    "generated_at",
    "market_date",
    "status",
    "live_plan_count",
    "backtest_entry_count",
    "matched_count",
    "candidate_recall",
    "policy_parity_rate",
    "route_match_rate",
    "multiplier_match_rate",
    "leverage_permission_match_rate",
    "notional_pct_mean_abs_diff",
    "duplicate_live_plan_count",
    "operational_error_count",
    "operational_error_samples",
    "submitted_buy_count",
    "filled_buy_count",
    "buy_fill_rate",
    "avg_buy_slippage_bps",
    "max_adverse_buy_slippage_bps",
    "forward_observed_market_days",
    "forward_unique_plan_count",
    "forward_gate_ready",
    "anomalies",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_parity_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "min_candidate_recall": 0.5,
        "min_policy_parity": 0.95,
        "max_notional_pct_abs_diff": 0.10,
        "operational_error_lookback_hours": 24,
        "max_adverse_slippage_bps": 60.0,
        "forward_start_date": "2026-07-14",
        "forward_min_market_days": 20,
        "forward_min_unique_plans": 30,
        "notify_anomalies": True,
    }
    config_path = Path(path)
    if config_path.is_file():
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        defaults.update(raw)
    return defaults


def _read_csv(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.is_file() or csv_path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame()


def _as_bool(value: Any) -> bool | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _normalize_live_plans(audit: pd.DataFrame, market_date: str) -> pd.DataFrame:
    if audit.empty or "event_type" not in audit.columns:
        return pd.DataFrame()
    plans = audit[audit["event_type"].astype(str) == "BUY_PLAN"].copy()
    if plans.empty or "decision_market_date" not in plans.columns:
        return pd.DataFrame()
    plans["decision_market_date"] = pd.to_datetime(
        plans["decision_market_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    plans = plans[plans["decision_market_date"] == market_date].copy()
    if plans.empty:
        return plans
    plans["signal_ticker"] = plans["signal_ticker"].fillna(plans["ticker"])
    plans["execution_ticker"] = plans["execution_ticker"].fillna(
        plans["signal_ticker"]
    )
    plans["sleeve_id"] = plans["sleeve_id"].fillna("core")
    for column in ("signal_ticker", "execution_ticker", "sleeve_id"):
        plans[column] = plans[column].astype(str).str.strip().str.upper()
    plans["quality_notional_multiplier"] = pd.to_numeric(
        plans["quality_notional_multiplier"], errors="coerce"
    )
    plans["planned_notional_pct"] = pd.to_numeric(
        plans["planned_notional_pct"], errors="coerce"
    )
    plans["quality_allow_leveraged"] = plans[
        "quality_allow_leveraged"
    ].map(_as_bool)
    plans["route_leveraged"] = plans["route_leveraged"].map(_as_bool)
    return plans


def _normalize_backtest_entries(
    entries: pd.DataFrame,
    market_date: str,
) -> pd.DataFrame:
    if entries.empty or "market_date" not in entries.columns:
        return pd.DataFrame()
    expected = entries.copy()
    expected["market_date"] = pd.to_datetime(
        expected["market_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    expected = expected[expected["market_date"] == market_date].copy()
    if expected.empty:
        return expected
    if "sleeve_id" not in expected.columns:
        expected["sleeve_id"] = "core"
    expected["sleeve_id"] = expected["sleeve_id"].fillna("core")
    for column in ("signal_ticker", "execution_ticker", "sleeve_id"):
        expected[column] = expected[column].astype(str).str.strip().str.upper()
    expected["quality_notional_multiplier"] = pd.to_numeric(
        expected["quality_notional_multiplier"], errors="coerce"
    )
    expected["planned_notional_pct"] = pd.to_numeric(
        expected["planned_notional_pct"], errors="coerce"
    )
    expected["quality_allow_leveraged"] = expected[
        "quality_allow_leveraged"
    ].map(_as_bool)
    expected["leveraged"] = expected["leveraged"].map(_as_bool)
    return expected


def _latest_market_date(equity_path: str | Path) -> str:
    equity = _read_csv(equity_path)
    if equity.empty or "date" not in equity.columns:
        raise ValueError(f"backtest equity has no dates: {equity_path}")
    dates = pd.to_datetime(equity["date"], errors="coerce").dropna()
    if dates.empty:
        raise ValueError(f"backtest equity has no valid dates: {equity_path}")
    return dates.max().date().isoformat()


def _recent_operational_errors(
    audit: pd.DataFrame,
    *,
    lookback_hours: int,
) -> pd.DataFrame:
    if audit.empty or "event_type" not in audit.columns:
        return pd.DataFrame()
    event_type = audit["event_type"].astype(str).str.upper()
    status = audit.get("status", pd.Series("", index=audit.index)).astype(str).str.upper()
    errors = audit[event_type.str.endswith("ERROR") | status.eq("ERROR")].copy()
    if errors.empty or "timestamp" not in errors.columns:
        return errors
    parsed = pd.to_datetime(errors["timestamp"], errors="coerce")
    cutoff = pd.Timestamp.now().tz_localize(None) - pd.Timedelta(hours=lookback_hours)
    return errors[parsed >= cutoff]


def _buy_fill_metrics(
    audit: pd.DataFrame,
    live_plans: pd.DataFrame,
) -> dict[str, float | int]:
    empty = {
        "submitted_buy_count": 0,
        "filled_buy_count": 0,
        "buy_fill_rate": 1.0,
        "avg_buy_slippage_bps": 0.0,
        "max_adverse_buy_slippage_bps": 0.0,
    }
    if audit.empty or live_plans.empty or "run_id" not in audit.columns:
        return empty
    run_ids = {
        str(value)
        for value in live_plans["run_id"].dropna().tolist()
        if str(value).strip()
    }
    if not run_ids:
        return empty
    scoped = audit[audit["run_id"].astype(str).isin(run_ids)].copy()
    events = scoped["event_type"].astype(str).str.upper()
    submitted = scoped[events == "BUY_SUBMITTED"].copy()
    statuses = scoped[events == "BUY_STATUS"].copy()
    submitted_count = int(len(submitted))
    if statuses.empty:
        return {**empty, "submitted_buy_count": submitted_count}
    filled = statuses[
        statuses["status"].astype(str).str.upper().str.contains("FILLED")
        & ~statuses["status"].astype(str).str.upper().str.contains("PARTIALLY")
    ].copy()
    filled_count = int(len(filled))
    reference = pd.to_numeric(filled["reference_price"], errors="coerce")
    fill_price = pd.to_numeric(filled["filled_avg_price"], errors="coerce")
    valid = reference.notna() & fill_price.notna() & (reference > 0)
    slippage = ((fill_price[valid] / reference[valid]) - 1.0) * 10_000.0
    return {
        "submitted_buy_count": submitted_count,
        "filled_buy_count": filled_count,
        "buy_fill_rate": (
            filled_count / submitted_count if submitted_count else 1.0
        ),
        "avg_buy_slippage_bps": float(slippage.mean()) if not slippage.empty else 0.0,
        "max_adverse_buy_slippage_bps": (
            float(slippage.max()) if not slippage.empty else 0.0
        ),
    }


def _forward_progress(
    audit: pd.DataFrame,
    *,
    start_date: str,
    min_market_days: int,
    min_unique_plans: int,
) -> dict[str, int | bool]:
    empty = {
        "forward_observed_market_days": 0,
        "forward_unique_plan_count": 0,
        "forward_gate_ready": False,
    }
    if audit.empty or "event_type" not in audit.columns:
        return empty
    plans = audit[audit["event_type"].astype(str) == "BUY_PLAN"].copy()
    if plans.empty or "decision_market_date" not in plans.columns:
        return empty
    plans["_market_date"] = pd.to_datetime(
        plans["decision_market_date"], errors="coerce"
    ).dt.normalize()
    plans = plans[plans["_market_date"] >= pd.Timestamp(start_date).normalize()]
    if plans.empty:
        return empty
    plans["_sleeve"] = plans.get("sleeve_id", "core").fillna("core")
    plans["_signal"] = plans.get("signal_ticker", plans.get("ticker", ""))
    unique = plans.drop_duplicates(["_market_date", "_sleeve", "_signal"])
    market_days = int(unique["_market_date"].nunique())
    plan_count = int(len(unique))
    return {
        "forward_observed_market_days": market_days,
        "forward_unique_plan_count": plan_count,
        "forward_gate_ready": (
            market_days >= int(min_market_days)
            and plan_count >= int(min_unique_plans)
        ),
    }
def build_paper_backtest_parity_report(
    *,
    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
    backtest_entries_path: str | Path = DEFAULT_BACKTEST_DIR / "portfolio_entries.csv",
    backtest_equity_path: str | Path = DEFAULT_BACKTEST_DIR / "portfolio_equity.csv",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    market_date: str | None = None,
    config: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], pd.DataFrame]:
    cfg = load_parity_config() if config is None else dict(config)
    target_date = market_date or _latest_market_date(backtest_equity_path)
    audit = read_execution_audit_csv(audit_path)
    entries = _read_csv(backtest_entries_path)
    live_all = _normalize_live_plans(audit, target_date)
    expected_all = _normalize_backtest_entries(entries, target_date)

    key = ["sleeve_id", "signal_ticker"]
    live_columns = key + [
        "execution_ticker",
        "quality_notional_multiplier",
        "quality_allow_leveraged",
        "route_leveraged",
        "planned_notional_pct",
        "run_id",
    ]
    expected_columns = key + [
        "execution_ticker",
        "quality_notional_multiplier",
        "quality_allow_leveraged",
        "leveraged",
        "planned_notional_pct",
    ]
    if live_all.empty:
        duplicate_count = 0
        live = pd.DataFrame(columns=live_columns)
    else:
        duplicate_count = int(
            live_all.duplicated(key + ["run_id"], keep=False).sum()
        )
        live = live_all.sort_values("timestamp").drop_duplicates(key, keep="last")
    expected = (
        expected_all.drop_duplicates(key, keep="last")
        if not expected_all.empty
        else pd.DataFrame(columns=expected_columns)
    )
    comparison = expected.reindex(columns=expected_columns).merge(
        live.reindex(columns=live_columns),
        on=key,
        how="outer",
        suffixes=("_backtest", "_paper"),
        indicator=True,
    )
    matched = comparison[comparison["_merge"] == "both"].copy()
    if not matched.empty:
        matched["route_match"] = (
            matched["execution_ticker_backtest"]
            == matched["execution_ticker_paper"]
        )
        matched["multiplier_match"] = (
            matched["quality_notional_multiplier_backtest"]
            - matched["quality_notional_multiplier_paper"]
        ).abs() <= 1e-9
        matched["leverage_permission_match"] = (
            matched["quality_allow_leveraged_backtest"]
            == matched["quality_allow_leveraged_paper"]
        )
        matched["route_leverage_match"] = (
            matched["leveraged"] == matched["route_leveraged"]
        )
        matched["notional_pct_abs_diff"] = (
            matched["planned_notional_pct_backtest"]
            - matched["planned_notional_pct_paper"]
        ).abs()
        matched["policy_match"] = matched[
            [
                "route_match",
                "multiplier_match",
                "leverage_permission_match",
                "route_leverage_match",
            ]
        ].all(axis=1)
        comparison = comparison.merge(
            matched[
                key
                + [
                    "route_match",
                    "multiplier_match",
                    "leverage_permission_match",
                    "route_leverage_match",
                    "notional_pct_abs_diff",
                    "policy_match",
                ]
            ],
            on=key,
            how="left",
        )

    expected_count = int(len(expected))
    live_count = int(len(live))
    matched_count = int(len(matched))
    candidate_recall = matched_count / expected_count if expected_count else 1.0

    def _rate(column: str) -> float:
        if matched.empty:
            return 1.0
        return float(matched[column].fillna(False).mean())

    policy_rate = _rate("policy_match")
    route_rate = _rate("route_match")
    multiplier_rate = _rate("multiplier_match")
    leverage_rate = _rate("leverage_permission_match")
    notional_diff = (
        float(matched["notional_pct_abs_diff"].dropna().mean())
        if not matched.empty and matched["notional_pct_abs_diff"].notna().any()
        else 0.0
    )

    errors = _recent_operational_errors(
        audit,
        lookback_hours=int(cfg.get("operational_error_lookback_hours", 24)),
    )
    error_samples = (
        errors.reindex(columns=["timestamp", "event_type", "ticker", "reason"])
        .head(10)
        .fillna("")
        .to_dict(orient="records")
    )
    fill_metrics = _buy_fill_metrics(audit, live_all)
    forward_progress = _forward_progress(
        audit,
        start_date=str(cfg.get("forward_start_date", "2026-07-14")),
        min_market_days=int(cfg.get("forward_min_market_days", 20)),
        min_unique_plans=int(cfg.get("forward_min_unique_plans", 30)),
    )

    anomalies: list[str] = []
    if expected_count and not live_count:
        anomalies.append("backtest entries exist but no paper BUY_PLAN was logged")
    if expected_count and candidate_recall < float(cfg.get("min_candidate_recall", 0.5)):
        anomalies.append(
            f"candidate recall {candidate_recall:.1%} below "
            f"{float(cfg.get('min_candidate_recall', 0.5)):.1%}"
        )
    if matched_count and policy_rate < float(cfg.get("min_policy_parity", 0.95)):
        anomalies.append(
            f"policy parity {policy_rate:.1%} below "
            f"{float(cfg.get('min_policy_parity', 0.95)):.1%}"
        )
    if matched_count and notional_diff > float(
        cfg.get("max_notional_pct_abs_diff", 0.10)
    ):
        anomalies.append(
            f"mean planned notional difference {notional_diff:.1%} exceeds limit"
        )
    if duplicate_count:
        anomalies.append(f"duplicate BUY_PLAN rows in a run: {duplicate_count}")
    if not errors.empty:
        anomalies.append(f"operational errors in lookback: {len(errors)}")
    if float(fill_metrics["max_adverse_buy_slippage_bps"]) > float(
        cfg.get("max_adverse_slippage_bps", 60.0)
    ):
        anomalies.append(
            "adverse buy slippage "
            f"{float(fill_metrics['max_adverse_buy_slippage_bps']):.1f} bps "
            "exceeds limit"
        )

    report = {
        "generated_at": _utc_now_iso(),
        "market_date": target_date,
        "status": "anomaly" if anomalies else "ok",
        "live_plan_count": live_count,
        "backtest_entry_count": expected_count,
        "matched_count": matched_count,
        "candidate_recall": round(candidate_recall, 6),
        "policy_parity_rate": round(policy_rate, 6),
        "route_match_rate": round(route_rate, 6),
        "multiplier_match_rate": round(multiplier_rate, 6),
        "leverage_permission_match_rate": round(leverage_rate, 6),
        "notional_pct_mean_abs_diff": round(notional_diff, 6),
        "duplicate_live_plan_count": duplicate_count,
        "operational_error_count": int(len(errors)),
        "operational_error_samples": error_samples,
        "submitted_buy_count": int(fill_metrics["submitted_buy_count"]),
        "filled_buy_count": int(fill_metrics["filled_buy_count"]),
        "buy_fill_rate": round(float(fill_metrics["buy_fill_rate"]), 6),
        "avg_buy_slippage_bps": round(
            float(fill_metrics["avg_buy_slippage_bps"]), 4
        ),
        "max_adverse_buy_slippage_bps": round(
            float(fill_metrics["max_adverse_buy_slippage_bps"]), 4
        ),
        **forward_progress,
        "anomalies": anomalies,
    }
    validate_paper_backtest_parity_report(report)
    write_parity_artifacts(report, comparison, output_dir=output_dir)
    return report, comparison


def validate_paper_backtest_parity_report(report: dict[str, Any]) -> dict[str, Any]:
    for key in REPORT_KEYS:
        if key not in report:
            raise ValueError(f"Missing paper/backtest parity key: {key}")
    for key in ("candidate_recall", "policy_parity_rate"):
        if not 0.0 <= float(report[key]) <= 1.0:
            raise ValueError(f"{key} must be between 0 and 1")
    return report


def write_parity_artifacts(
    report: dict[str, Any],
    comparison: pd.DataFrame,
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    market_date = str(report["market_date"]).replace("-", "")
    report_path = target / f"parity_{market_date}.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (target / "latest_summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    comparison.to_csv(target / f"comparison_{market_date}.csv", index=False)
    comparison.to_csv(target / "latest_comparison.csv", index=False)
    return report_path


def format_parity_report(report: dict[str, Any]) -> str:
    lines = [
        "=== Paper vs backtest entry parity ===",
        f"Market date: {report['market_date']} | status={report['status']}",
        (
            f"Plans: paper={report['live_plan_count']} "
            f"backtest={report['backtest_entry_count']} "
            f"matched={report['matched_count']}"
        ),
        (
            f"Candidate recall={report['candidate_recall']:.1%} "
            f"policy parity={report['policy_parity_rate']:.1%} "
            f"route={report['route_match_rate']:.1%} "
            f"multiplier={report['multiplier_match_rate']:.1%}"
        ),
        (
            f"Leverage permission={report['leverage_permission_match_rate']:.1%} "
            f"notional mean abs diff={report['notional_pct_mean_abs_diff']:.1%}"
        ),
        (
            f"Duplicates={report['duplicate_live_plan_count']} "
            f"operational errors={report['operational_error_count']}"
        ),
        (
            f"Fills={report['filled_buy_count']}/{report['submitted_buy_count']} "
            f"rate={report['buy_fill_rate']:.1%} "
            f"avg_slippage={report['avg_buy_slippage_bps']:.1f}bps "
            f"max_adverse={report['max_adverse_buy_slippage_bps']:.1f}bps"
        ),
        (
            f"Forward gate: days={report['forward_observed_market_days']}/20 "
            f"plans={report['forward_unique_plan_count']}/30 "
            f"ready={report['forward_gate_ready']}"
        ),
    ]
    for anomaly in report.get("anomalies") or []:
        lines.append(f"ANOMALY: {anomaly}")
    return "\n".join(lines)


def maybe_notify_parity_anomalies(
    report: dict[str, Any],
    *,
    enabled: bool = True,
) -> bool:
    if not enabled or not report.get("anomalies"):
        return False
    return notify_error(
        "Paper/backtest parity anomaly",
        "\n".join(
            [
                f"market_date={report['market_date']}",
                *[f"- {item}" for item in report["anomalies"]],
                (
                    f"paper={report['live_plan_count']}, "
                    f"backtest={report['backtest_entry_count']}, "
                    f"matched={report['matched_count']}"
                ),
            ]
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-path", default=EXECUTION_AUDIT_LOG_PATH)
    parser.add_argument(
        "--backtest-entries",
        default=str(DEFAULT_BACKTEST_DIR / "portfolio_entries.csv"),
    )
    parser.add_argument(
        "--backtest-equity",
        default=str(DEFAULT_BACKTEST_DIR / "portfolio_equity.csv"),
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--market-date")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--notify-anomalies", action="store_true")
    args = parser.parse_args()

    config = load_parity_config(args.config)
    report, _ = build_paper_backtest_parity_report(
        audit_path=args.audit_path,
        backtest_entries_path=args.backtest_entries,
        backtest_equity_path=args.backtest_equity,
        output_dir=args.output_dir,
        market_date=args.market_date,
        config=config,
    )
    print(format_parity_report(report))
    maybe_notify_parity_anomalies(
        report,
        enabled=(
            args.notify_anomalies and bool(config.get("notify_anomalies", True))
        ),
    )


if __name__ == "__main__":
    main()
