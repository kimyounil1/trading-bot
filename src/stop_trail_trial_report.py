"""stop5_trail10 paper trial tracker: return / MDD / exit mix over the observation window.

Trial: trailing_stop_pct 0.20 -> 0.10 (stop_loss_pct 0.05 unchanged, regime adaptive off).
Backtest follow-up expectation (logs/regime_stop_backtest/followup_latest_summary.json):
return -0.2pp vs baseline, MDD -9.4% -> -6.3%.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from src.config import EXECUTION_AUDIT_LOG_PATH
from src.daily_audit_summary import load_execution_audit

DEFAULT_STATE_PATH = Path("logs/stop_trail_trial/trial_state.json")
DEFAULT_OUTPUT = Path("logs/stop_trail_trial/latest_summary.json")
DEFAULT_OBSERVATION_DAYS = 14
BASELINE_TRAILING_STOP_PCT = 0.20


def _utc_now() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc)).tz_localize(None)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def start_trial(
    state_path: str | Path = DEFAULT_STATE_PATH,
    *,
    settings: Any | None = None,
    observation_days: int = DEFAULT_OBSERVATION_DAYS,
) -> dict[str, Any]:
    """Record trial start state. Refuses to overwrite a running trial."""
    path = Path(state_path)
    existing = _read_json(path)
    if existing.get("started_at"):
        return existing

    if settings is None:
        from src.settings import load_settings

        settings = load_settings()

    state = {
        "trial": "stop5_trail10",
        "started_at": _utc_now().strftime("%Y-%m-%d"),
        "observation_days": observation_days,
        "config": {
            "stop_loss_pct": float(getattr(settings, "stop_loss_pct", 0.05)),
            "trailing_stop_pct": float(getattr(settings, "trailing_stop_pct", 0.10)),
        },
        "baseline": {
            "stop_loss_pct": 0.05,
            "trailing_stop_pct": BASELINE_TRAILING_STOP_PCT,
        },
        "backtest_expectation": {
            "return_delta_pp": -0.2,
            "mdd_baseline_pct": -9.4,
            "mdd_trial_pct": -6.3,
            "source": "logs/regime_stop_backtest/followup_latest_summary.json",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    return state


def _max_drawdown_pct(equity: pd.Series) -> float | None:
    values = pd.to_numeric(equity, errors="coerce").dropna()
    values = values[values > 0]
    if len(values) < 2:
        return None
    running_peak = values.cummax()
    drawdown = values / running_peak - 1.0
    return round(float(drawdown.min()) * 100.0, 2)


def _window_return_pct(equity: pd.Series) -> float | None:
    values = pd.to_numeric(equity, errors="coerce").dropna()
    values = values[values > 0]
    if len(values) < 2:
        return None
    return round((float(values.iloc[-1]) / float(values.iloc[0]) - 1.0) * 100.0, 2)


def _fetch_equity_frame() -> pd.DataFrame:
    from src.portfolio_pnl_report import fetch_alpaca_portfolio_histories

    _h1w, h1m, hall = fetch_alpaca_portfolio_histories()
    frame = hall if not hall.empty else h1m
    return frame


def _spy_return_pct(start: pd.Timestamp, end: pd.Timestamp) -> float | None:
    from src.data_loader import load_price_data_batch

    try:
        spy = load_price_data_batch(["SPY"], period="3mo").get("SPY")
    except Exception:
        return None
    if spy is None or spy.empty:
        return None
    df = spy.copy()
    df["date"] = pd.to_datetime(df.get("date"), errors="coerce").dt.normalize()
    col = "adj_close" if "adj_close" in df.columns else "close"
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["date", col]).sort_values("date")
    window = df[(df["date"] >= start.normalize()) & (df["date"] <= end.normalize())]
    return _window_return_pct(window[col])


def _exit_mix_since(audit_path: Path, start: pd.Timestamp) -> dict[str, int]:
    df = (
        load_execution_audit(audit_path, lookback_days=90)
        if audit_path.is_file()
        else pd.DataFrame()
    )
    mix = {"trailing_stop": 0, "stop_loss": 0, "max_holding": 0, "other": 0, "total": 0}
    if df.empty:
        return mix
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df.get("timestamp"), errors="coerce", utc=True)
    df = df[
        (df.get("event_type", "").astype(str) == "FULL_EXIT")
        & df["timestamp"].notna()
        & (df["timestamp"].dt.tz_localize(None) >= start)
    ]
    for reason in df.get("reason", "").astype(str):
        lowered = reason.lower()
        mix["total"] += 1
        if "trailing stop" in lowered:
            mix["trailing_stop"] += 1
        elif "stop loss" in lowered:
            mix["stop_loss"] += 1
        elif "max holding" in lowered:
            mix["max_holding"] += 1
        else:
            mix["other"] += 1
    return mix


def build_stop_trail_trial_report(
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
    equity_frame: pd.DataFrame | None = None,
    spy_return_fn: Callable[[pd.Timestamp, pd.Timestamp], float | None] | None = None,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    state = _read_json(Path(state_path))
    if not state.get("started_at"):
        return {
            "generated_at": _utc_now_iso(),
            "status": "NOT_STARTED",
            "notes": [
                "Run scripts/run_stop_trail_trial_report.sh --start after setting trailing_stop_pct=0.10."
            ],
        }

    now_ts = now if now is not None else _utc_now()
    if now_ts.tzinfo is not None:
        now_ts = now_ts.tz_localize(None)
    start = pd.Timestamp(state["started_at"])
    observation_days = int(state.get("observation_days") or DEFAULT_OBSERVATION_DAYS)
    days_elapsed = max(0, (now_ts.normalize() - start.normalize()).days)

    if equity_frame is None:
        try:
            equity_frame = _fetch_equity_frame()
        except Exception as exc:
            equity_frame = pd.DataFrame(columns=["date", "equity"])
            broker_error = str(exc)
        else:
            broker_error = None
    else:
        broker_error = None

    eq = equity_frame.copy()
    if not eq.empty:
        eq["date"] = pd.to_datetime(eq.get("date"), errors="coerce")
        if hasattr(eq["date"].dt, "tz_localize") and eq["date"].dt.tz is not None:
            eq["date"] = eq["date"].dt.tz_localize(None)
        eq = eq.dropna(subset=["date"]).sort_values("date")
        eq = eq[eq["date"] >= start]
    return_pct = _window_return_pct(eq["equity"]) if not eq.empty else None
    mdd_pct = _max_drawdown_pct(eq["equity"]) if not eq.empty else None

    spy_fn = spy_return_fn or _spy_return_pct
    spy_pct = spy_fn(start, now_ts)

    exit_mix = _exit_mix_since(Path(audit_path), start)

    status = "OBSERVING" if days_elapsed < observation_days else "READY_TO_EVALUATE"
    notes: list[str] = [
        "Evaluate after the window: keep 0.10 if MDD improves without return drag "
        "beyond backtest expectation (-0.2pp); otherwise revert trailing_stop_pct to 0.20."
    ]
    if broker_error:
        notes.append(f"equity history unavailable: {broker_error}")

    report = {
        "generated_at": _utc_now_iso(),
        "trial": state.get("trial", "stop5_trail10"),
        "status": status,
        "started_at": state["started_at"],
        "days_elapsed": days_elapsed,
        "observation_days": observation_days,
        "config": state.get("config"),
        "baseline": state.get("baseline"),
        "backtest_expectation": state.get("backtest_expectation"),
        "window_metrics": {
            "return_pct": return_pct,
            "max_drawdown_pct": mdd_pct,
            "spy_return_pct": spy_pct,
            "equity_points": int(len(eq)),
        },
        "exit_mix_since_start": exit_mix,
        "notes": notes,
    }
    return report


def write_stop_trail_trial_report(
    output_path: str | Path = DEFAULT_OUTPUT,
    **kwargs: Any,
) -> Path:
    report = build_stop_trail_trial_report(**kwargs)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="stop5_trail10 paper trial tracker")
    parser.add_argument("--start", action="store_true", help="Record trial start state")
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    if args.start:
        state = start_trial(args.state_path)
        print(json.dumps(state, indent=2, ensure_ascii=False))

    path = write_stop_trail_trial_report(args.output, state_path=args.state_path)
    print(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
