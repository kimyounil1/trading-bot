"""Daily market-regime snapshot: current regime + evidence indicators + breadth.

Records what the bot's own regime classifier (src.market_regime) sees each day so
regime transitions are visible in history — the BULL->NEUTRAL/BEAR flip is the
trigger to re-evaluate the no-guard tournament sleeve. Sends a Telegram note when
the regime changes from the previous snapshot.

Outputs logs/market_regime/latest_snapshot.json and appends history.jsonl.

Usage:
  .venv/bin/python -m src.market_regime_snapshot
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.data_loader import load_price_data_batch
from src.market_regime import get_current_regime
from src.settings import load_settings

DEFAULT_OUTPUT_DIR = Path("logs/market_regime")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _close_series(df: pd.DataFrame | None) -> pd.Series | None:
    if df is None or df.empty or "date" not in df.columns:
        return None
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date", "close"]).sort_values("date")
    if out.empty:
        return None
    return out.set_index("date")["close"]


def _pct(numer: float, denom: float) -> float | None:
    if not denom or pd.isna(denom):
        return None
    return round((numer / denom - 1.0) * 100.0, 2)


def _spy_indicators(spy: pd.Series) -> dict:
    last = float(spy.iloc[-1])
    ma50 = spy.rolling(50).mean().iloc[-1]
    ma200 = spy.rolling(200).mean().iloc[-1]
    out = {
        "spy_close": round(last, 2),
        "spy_vs_ma50_pct": _pct(last, float(ma50)) if pd.notna(ma50) else None,
        "spy_vs_ma200_pct": _pct(last, float(ma200)) if pd.notna(ma200) else None,
        "spy_vs_52w_high_pct": _pct(last, float(spy.tail(252).max())),
    }
    for label, days in (("1m", 21), ("3m", 63), ("6m", 126)):
        out[f"spy_return_{label}_pct"] = (
            _pct(last, float(spy.iloc[-days - 1])) if len(spy) > days else None
        )
    return out


def _breadth(ticker_data: dict[str, pd.DataFrame]) -> dict:
    above50 = above200 = pos1m = total = 0
    for df in ticker_data.values():
        closes = _close_series(df)
        if closes is None or len(closes) < 210:
            continue
        total += 1
        last = float(closes.iloc[-1])
        if last > closes.rolling(50).mean().iloc[-1]:
            above50 += 1
        if last > closes.rolling(200).mean().iloc[-1]:
            above200 += 1
        if last > float(closes.iloc[-22]):
            pos1m += 1
    if total == 0:
        return {"breadth_names": 0}
    return {
        "breadth_names": total,
        "breadth_above_ma50_pct": round(above50 / total * 100.0, 1),
        "breadth_above_ma200_pct": round(above200 / total * 100.0, 1),
        "breadth_1m_positive_pct": round(pos1m / total * 100.0, 1),
    }


def _previous_regime(history_path: Path) -> str | None:
    if not history_path.is_file():
        return None
    lines = [ln for ln in history_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1]).get("regime")
    except json.JSONDecodeError:
        return None


def build_regime_snapshot() -> dict:
    settings = load_settings()
    tickers = [str(t).strip().upper() for t in settings.tickers]
    loaded = load_price_data_batch(
        list(dict.fromkeys(tickers + ["SPY", "^VIX"])),
        period="1y",
        cache_max_age_minutes=120,
    )
    spy_df = loaded.get("SPY")
    vix_df = loaded.get("^VIX")
    spy = _close_series(spy_df)
    vix = _close_series(vix_df)
    if spy is None or vix is None:
        raise ValueError("SPY/VIX price data unavailable for regime snapshot")

    snapshot = {
        "generated_at": _utc_now_iso(),
        "as_of": str(spy.index.max().date()),
        "regime": get_current_regime(spy_df, vix_df),
        **_spy_indicators(spy),
        "vix": round(float(vix.iloc[-1]), 2),
        "vix_20d_avg": round(float(vix.tail(20).mean()), 2),
        **_breadth({t: loaded[t] for t in tickers if t in loaded}),
    }
    return snapshot


def write_regime_snapshot(output_dir: Path = DEFAULT_OUTPUT_DIR, *, notify: bool = True) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    history_path = output_dir / "history.jsonl"
    previous = _previous_regime(history_path)

    snapshot = build_regime_snapshot()
    snapshot["previous_regime"] = previous
    snapshot["regime_changed"] = previous is not None and snapshot["regime"] != previous

    latest = output_dir / "latest_snapshot.json"
    latest.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False) + "\n")

    if snapshot["regime_changed"] and notify:
        try:
            from src.notifier import notify_info

            notify_info(
                f"Market regime changed: {previous} → {snapshot['regime']}",
                (
                    f"SPY {snapshot['spy_close']} (50MA {snapshot['spy_vs_ma50_pct']}%, "
                    f"200MA {snapshot['spy_vs_ma200_pct']}%), VIX {snapshot['vix']}. "
                    "Re-evaluate the no-guard tournament sleeve if leaving BULL."
                ),
            )
        except Exception:
            pass
    return latest


def main() -> None:
    parser = argparse.ArgumentParser(description="Write daily market regime snapshot")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--no-notify", action="store_true")
    args = parser.parse_args()
    path = write_regime_snapshot(Path(args.output_dir), notify=not args.no_notify)
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    print(
        f"regime={snapshot['regime']} (prev={snapshot['previous_regime']}, "
        f"changed={snapshot['regime_changed']}) as_of={snapshot['as_of']}"
    )
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
