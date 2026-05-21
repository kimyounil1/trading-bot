import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.compare_strategy_snapshots import compare_snapshot_metrics, format_comparison_report, load_snapshot
from src.qlib_ingest import build_dump_bin_command, resolve_dump_bin_script


class QlibWorkflowTest(unittest.TestCase):
    def test_resolve_dump_bin_script_from_repo_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_dir = Path(temp_dir) / "qlib"
            script_path = repo_dir / "scripts" / "dump_bin.py"
            script_path.parent.mkdir(parents=True, exist_ok=True)
            script_path.write_text("# stub\n", encoding="utf-8")

            resolved = resolve_dump_bin_script(qlib_repo_dir=repo_dir)
            self.assertEqual(resolved, script_path.resolve())

    def test_build_dump_bin_command_uses_expected_fields(self) -> None:
        command = build_dump_bin_command(
            dump_bin_script="/tmp/dump_bin.py",
            csv_dir="/tmp/csv",
            qlib_dir="/tmp/qlib_data",
            python_bin="/usr/bin/python3",
        )

        self.assertEqual(command[0], "/usr/bin/python3")
        self.assertIn("--include_fields", command)
        self.assertIn("open,high,low,close,volume,factor", command)
        self.assertIn("--symbol_field_name", command)
        self.assertIn("instrument", command)

    def test_compare_snapshot_metrics_returns_deltas(self) -> None:
        base_snapshot = {
            "result": {
                "final_equity": 10000.0,
                "total_return": 0.10,
                "benchmark_return": 0.08,
                "max_drawdown": -0.05,
                "trades": 10,
                "win_rate": 0.40,
            }
        }
        candidate_snapshot = {
            "result": {
                "final_equity": 11000.0,
                "total_return": 0.12,
                "benchmark_return": 0.09,
                "max_drawdown": -0.04,
                "trades": 12,
                "win_rate": 0.50,
            }
        }

        comparison = compare_snapshot_metrics(base_snapshot, candidate_snapshot)
        self.assertEqual(comparison["final_equity"]["absolute_delta"], 1000.0)
        self.assertAlmostEqual(comparison["win_rate"]["absolute_delta"], 0.10)

    def test_load_snapshot_and_report(self) -> None:
        payload = {
            "result": {
                "final_equity": 10000.0,
                "total_return": 0.10,
                "benchmark_return": 0.08,
                "max_drawdown": -0.05,
                "trades": 10,
                "win_rate": 0.40,
            }
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_path = Path(temp_dir) / "snapshot.json"
            snapshot_path.write_text(json.dumps(payload), encoding="utf-8")

            loaded = load_snapshot(snapshot_path)
            report = format_comparison_report(snapshot_path, snapshot_path, compare_snapshot_metrics(loaded, loaded))

        self.assertIn("base_snapshot=", report)
        self.assertIn("final_equity", report)


if __name__ == "__main__":
    unittest.main()
