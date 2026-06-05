import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.live_readiness import build_live_readiness_report
from src.settings import StrategySettings


class LiveReadinessTest(unittest.TestCase):
    def test_paper_environment_reports_no_go_with_rank_gate(self) -> None:
        settings = StrategySettings(rank_ai_buy_gate_enabled=True)
        report = build_live_readiness_report(settings=settings, environment="paper")
        self.assertEqual(report["overall"], "NO_GO")
        self.assertFalse(report["safe_to_execute_live"])
        self.assertTrue(any("rank_gate_ready" in r for r in report["reasons"]))

    def test_live_profile_safe_when_reports_synthetic(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            pv = root / "paper_validation"
            pv.mkdir(parents=True)
            (pv / "latest_summary.json").write_text(
                json.dumps(
                    {
                        "rank_gate_paper_tracker": {
                            "gate_ready": True,
                            "calendar_days_with_rank_events": 14,
                            "min_calendar_days_required": 14,
                        }
                    }
                ),
                encoding="utf-8",
            )
            hist = pv / "history.jsonl"
            for i in range(14):
                hist.write_text(
                    (hist.read_text(encoding="utf-8") if hist.exists() else "")
                    + json.dumps({"date": f"2026-06-{i+1:02d}"})
                    + "\n",
                    encoding="utf-8",
                )
            llm = root / "llm_advisory"
            llm.mkdir()
            (llm / "precision.json").write_text(
                json.dumps(
                    {
                        "events_used": {"llm_reject": 3, "llm_accept": 3},
                        "forward_return": {
                            "llm_reject": {"n": 3},
                            "llm_accept": {"n": 3},
                        },
                    }
                ),
                encoding="utf-8",
            )
            mq = root / "model_quality"
            mq.mkdir()
            (mq / "latest_summary.json").write_text(
                json.dumps({"decision": "HOLD"}),
                encoding="utf-8",
            )

            settings = StrategySettings(
                trading_environment="live",
                broker_provider="paper",
                live_safety_enabled=True,
                live_safety_max_daily_loss_pct=0.03,
                rank_ai_buy_gate_enabled=False,
                llm_advisory_only=True,
            )

            import src.live_readiness as lr

            old_pv, old_llm, old_mq = lr.PAPER_VALIDATION_PATH, lr.LLM_PRECISION_PATH, lr.MODEL_QUALITY_PATH
            try:
                lr.PAPER_VALIDATION_PATH = pv / "latest_summary.json"
                lr.LLM_PRECISION_PATH = llm / "precision.json"
                lr.MODEL_QUALITY_PATH = mq / "latest_summary.json"
                report = build_live_readiness_report(settings=settings, environment="live")
            finally:
                lr.PAPER_VALIDATION_PATH = old_pv
                lr.LLM_PRECISION_PATH = old_llm
                lr.MODEL_QUALITY_PATH = old_mq

            self.assertFalse(report["safe_to_execute_live"])
            self.assertTrue(
                any("not live-capable" in r for r in report["reasons"])
                or any("live_safety" in r for r in report["reasons"])
                or report["overall"] == "NO_GO"
            )


if __name__ == "__main__":
    unittest.main()
