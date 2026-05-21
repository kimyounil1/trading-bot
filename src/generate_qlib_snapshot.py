import argparse
import json
from pathlib import Path

import pandas as pd

from src.snapshot_utils import build_snapshot_payload, save_snapshot_payload


def _load_json(path: str | Path | None) -> dict:
    if path is None:
        return {}
    with Path(path).expanduser().resolve().open("r", encoding="utf-8") as file:
        return json.load(file)


def _load_tickers(path: str | Path | None) -> list[str]:
    if path is None:
        return []

    tickers_path = Path(path).expanduser().resolve()
    if tickers_path.suffix.lower() == ".json":
        data = json.loads(tickers_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("Ticker JSON must be a list")
        return [str(item).upper() for item in data]

    return [
        line.strip().upper()
        for line in tickers_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _count_rows(path: str | Path | None) -> int:
    if path is None:
        return 0
    frame = pd.read_csv(Path(path).expanduser().resolve())
    return int(len(frame))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a baseline-compatible snapshot JSON from Qlib backtest metrics."
    )
    parser.add_argument("--output", required=True, help="Snapshot JSON output path.")
    parser.add_argument("--period", default="2y", help="Backtest period label.")
    parser.add_argument("--settings-json", default=None, help="Optional settings JSON path.")
    parser.add_argument("--tickers-file", default=None, help="Optional ticker file path.")
    parser.add_argument("--equity-csv", default=None, help="Optional equity CSV path.")
    parser.add_argument("--trades-csv", default=None, help="Optional trades CSV path.")
    parser.add_argument("--provider-uri", default=None, help="Optional qlib provider URI.")
    parser.add_argument("--qlib-region", default="us", help="Optional qlib region label.")
    parser.add_argument("--initial-cash", type=float, required=True)
    parser.add_argument("--final-equity", type=float, required=True)
    parser.add_argument("--total-return", type=float, required=True)
    parser.add_argument("--benchmark-return", type=float, required=True)
    parser.add_argument("--max-drawdown", type=float, required=True)
    parser.add_argument("--trades", type=int, required=True)
    parser.add_argument("--win-rate", type=float, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = _load_json(args.settings_json)
    tickers = _load_tickers(args.tickers_file)
    if not tickers and isinstance(settings, dict):
        raw_tickers = settings.get("tickers", [])
        if isinstance(raw_tickers, list):
            tickers = [str(item).upper() for item in raw_tickers]
    result = {
        "initial_cash": args.initial_cash,
        "final_equity": args.final_equity,
        "total_return": args.total_return,
        "max_drawdown": args.max_drawdown,
        "trades": args.trades,
        "win_rate": args.win_rate,
        "benchmark_return": args.benchmark_return,
    }

    payload = build_snapshot_payload(
        period=args.period,
        tickers=tickers,
        settings=settings,
        result=result,
        equity_rows=_count_rows(args.equity_csv),
        trade_rows=_count_rows(args.trades_csv),
        extra_fields={
            "provider_uri": args.provider_uri,
            "qlib_region": args.qlib_region,
            "equity_csv": str(Path(args.equity_csv).expanduser().resolve()) if args.equity_csv else None,
            "trades_csv": str(Path(args.trades_csv).expanduser().resolve()) if args.trades_csv else None,
        },
    )

    output_path = save_snapshot_payload(payload, args.output)
    print(f"Saved Qlib snapshot to {output_path}")


if __name__ == "__main__":
    main()
