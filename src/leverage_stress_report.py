"""Stress portfolio equity under gap-down and correlation-spike scenarios."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_OUTPUT_DIR = Path("logs/leverage_stress")
DEFAULT_EQUITY_PATH = Path("logs/portfolio_backtest/portfolio_equity.csv")
DEFAULT_CONFIG_PATH = Path("config/leverage_stress_config.json")

LEVERAGE_STRESS_ALERT_KEYS = (
    "passed",
    "failures",
    "thresholds",
)

LEVERAGE_STRESS_REPORT_KEYS = (
    "generated_at",
    "input",
    "scenarios",
)

STRESS_SCENARIOS = (
    {"name": "gap_down_5pct", "gap_down_pct": 0.05, "correlation_multiplier": 1.0},
    {"name": "gap_down_10pct", "gap_down_pct": 0.10, "correlation_multiplier": 1.0},
    {"name": "correlation_spike_1p5x", "gap_down_pct": 0.0, "correlation_multiplier": 1.5},
    {"name": "gap_down_10pct_corr_1p5x", "gap_down_pct": 0.10, "correlation_multiplier": 1.5},
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_equity_series(path: str | Path = DEFAULT_EQUITY_PATH) -> pd.Series:
    frame = pd.read_csv(path)
    if "equity" not in frame.columns:
        raise ValueError("equity CSV must contain an 'equity' column")
    date_col = "date" if "date" in frame.columns else frame.columns[0]
    series = pd.to_numeric(frame["equity"], errors="coerce").dropna()
    series.index = pd.to_datetime(frame[date_col], errors="coerce")
    return series.sort_index()


def stress_equity_series(
    equity: pd.Series,
    *,
    gap_down_pct: float,
    leverage: float,
    correlation_multiplier: float,
) -> pd.Series:
    if equity.empty:
        raise ValueError("equity series must not be empty")
    returns = equity.pct_change().fillna(0.0).astype(float)
    if gap_down_pct > 0:
        shock_idx = returns.idxmin() if len(returns) > 1 else returns.index[0]
        returns = returns.copy()
        returns.loc[shock_idx] = float(returns.loc[shock_idx]) - gap_down_pct * leverage
    if correlation_multiplier != 1.0:
        returns = returns.apply(
            lambda value: float(value) * correlation_multiplier if value < 0 else float(value)
        )
    stressed = (1.0 + returns).cumprod() * float(equity.iloc[0])
    stressed.name = "stressed_equity"
    return stressed


def max_drawdown_pct(equity: pd.Series) -> float:
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    return round(float(drawdown.min()) * 100.0, 4)


def build_leverage_stress_report(
    equity: pd.Series,
    *,
    leverage: float = 1.0,
    scenarios: tuple[dict[str, Any], ...] = STRESS_SCENARIOS,
) -> dict[str, Any]:
    if leverage <= 0:
        raise ValueError("leverage must be positive")

    baseline_final = float(equity.iloc[-1])
    baseline_dd = max_drawdown_pct(equity)
    scenario_rows: list[dict[str, Any]] = []

    for scenario in scenarios:
        stressed = stress_equity_series(
            equity,
            gap_down_pct=float(scenario["gap_down_pct"]),
            leverage=leverage,
            correlation_multiplier=float(scenario["correlation_multiplier"]),
        )
        final_equity = float(stressed.iloc[-1])
        scenario_rows.append(
            {
                "name": scenario["name"],
                "gap_down_pct": scenario["gap_down_pct"],
                "correlation_multiplier": scenario["correlation_multiplier"],
                "final_equity": round(final_equity, 2),
                "final_equity_delta_pct": round((final_equity / baseline_final - 1.0) * 100.0, 4),
                "max_drawdown_pct": max_drawdown_pct(stressed),
                "max_drawdown_delta_pct": round(max_drawdown_pct(stressed) - baseline_dd, 4),
            }
        )

    report = {
        "generated_at": _utc_now_iso(),
        "input": {
            "rows": int(len(equity)),
            "leverage": leverage,
            "baseline_final_equity": round(baseline_final, 2),
            "baseline_max_drawdown_pct": baseline_dd,
        },
        "scenarios": scenario_rows,
    }
    validate_leverage_stress_report(report)
    return report


def validate_leverage_stress_report(report: dict[str, Any]) -> dict[str, Any]:
    for key in LEVERAGE_STRESS_REPORT_KEYS:
        if key not in report:
            raise ValueError(f"Missing leverage stress report key: {key}")
    if not report["scenarios"]:
        raise ValueError("scenarios must not be empty")
    return report


def load_leverage_stress_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    if not path.is_file():
        return {
            "default_leverage": 2.0,
            "alert_if_stressed_drawdown_below_pct": -25.0,
            "alert_if_gap10_final_equity_loss_below_pct": -15.0,
            "notify_telegram": True,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_leverage_stress_alerts(
    report: dict[str, Any],
    *,
    leverage: float,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or load_leverage_stress_config()
    failures: list[str] = []
    dd_floor = float(config.get("alert_if_stressed_drawdown_below_pct", -25.0))
    gap10_floor = float(config.get("alert_if_gap10_final_equity_loss_below_pct", -15.0))

    for row in report.get("scenarios") or []:
        if float(row.get("max_drawdown_pct", 0.0)) < dd_floor:
            failures.append(
                f"{row['name']}: max_drawdown_pct={row['max_drawdown_pct']} < {dd_floor}"
            )
        if row["name"] == "gap_down_10pct":
            loss_pct = float(row.get("final_equity_delta_pct", 0.0))
            if loss_pct < gap10_floor:
                failures.append(
                    f"gap_down_10pct: final_equity_delta_pct={loss_pct} < {gap10_floor} "
                    f"(leverage={leverage})"
                )

    return {
        "passed": not failures,
        "failures": failures,
        "thresholds": {
            "alert_if_stressed_drawdown_below_pct": dd_floor,
            "alert_if_gap10_final_equity_loss_below_pct": gap10_floor,
            "leverage": leverage,
        },
    }


def maybe_notify_leverage_stress(
    report: dict[str, Any],
    alerts: dict[str, Any],
    *,
    notify: bool = True,
) -> None:
    if alerts.get("passed") or not notify:
        return
    from src.notifier import notify_info

    body = "\n".join(alerts.get("failures") or [])
    notify_info("⚠️ Leverage stress thresholds breached", body)


def write_leverage_stress_artifacts(
    report: dict[str, Any],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "latest_summary.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def run_leverage_stress_report(
    equity_path: str | Path = DEFAULT_EQUITY_PATH,
    *,
    leverage: float | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    notify_telegram: bool | None = None,
) -> dict[str, Any]:
    config = load_leverage_stress_config()
    leverage = float(leverage if leverage is not None else config.get("default_leverage", 1.0))
    equity = load_equity_series(equity_path)
    report = build_leverage_stress_report(equity, leverage=leverage)
    alerts = evaluate_leverage_stress_alerts(report, leverage=leverage, config=config)
    report["alerts"] = alerts
    write_leverage_stress_artifacts(report, output_dir)
    if notify_telegram is None:
        notify_telegram = bool(config.get("notify_telegram", True))
    maybe_notify_leverage_stress(report, alerts, notify=notify_telegram)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Leverage stress scenarios on portfolio equity")
    parser.add_argument("--equity-path", default=str(DEFAULT_EQUITY_PATH))
    parser.add_argument("--leverage", type=float, default=1.0)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = run_leverage_stress_report(
        args.equity_path,
        leverage=args.leverage,
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
