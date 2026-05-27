from __future__ import annotations

import argparse
import json
from pathlib import Path


RESULT_KEYS = [
    "final_equity",
    "total_return",
    "benchmark_return",
    "max_drawdown",
    "trades",
    "win_rate",
]


def load_snapshot(path: str | Path) -> dict:
    snapshot_path = Path(path).expanduser().resolve()
    with snapshot_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def compare_snapshot_metrics(base_snapshot: dict, candidate_snapshot: dict) -> dict[str, dict[str, float]]:
    base_result = base_snapshot["result"]
    candidate_result = candidate_snapshot["result"]
    comparison: dict[str, dict[str, float]] = {}

    for key in RESULT_KEYS:
        base_value = float(base_result[key])
        candidate_value = float(candidate_result[key])
        comparison[key] = {
            "base": base_value,
            "candidate": candidate_value,
            "absolute_delta": candidate_value - base_value,
        }

    return comparison


def format_comparison_report(base_path: str | Path, candidate_path: str | Path, comparison: dict[str, dict[str, float]]) -> str:
    lines = [
        f"base_snapshot={Path(base_path).expanduser().resolve()}",
        f"candidate_snapshot={Path(candidate_path).expanduser().resolve()}",
        "",
    ]

    for key in RESULT_KEYS:
        row = comparison[key]
        lines.append(
            f"{key}: base={row['base']:.6f}, candidate={row['candidate']:.6f}, delta={row['absolute_delta']:.6f}"
        )

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two strategy snapshot JSON files."
    )
    parser.add_argument(
        "--base",
        default="logs/baselines/current_strategy/baseline_snapshot.json",
        help="Path to the baseline snapshot JSON.",
    )
    parser.add_argument(
        "--candidate",
        required=True,
        help="Path to the candidate snapshot JSON to compare.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the comparison as JSON instead of plain text.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_snapshot = load_snapshot(args.base)
    candidate_snapshot = load_snapshot(args.candidate)
    comparison = compare_snapshot_metrics(base_snapshot, candidate_snapshot)

    if args.json:
        print(json.dumps(comparison, indent=2))
        return

    print(format_comparison_report(args.base, args.candidate, comparison))


if __name__ == "__main__":
    main()
