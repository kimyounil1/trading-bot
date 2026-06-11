import unittest

import pandas as pd

from src.buy_skip_reason_ko import explain_buy_skip_reason, explain_execution_label
from src.cms_helpers import format_audit_skips_for_display, format_buy_candidates_for_display


class BuySkipReasonKoTest(unittest.TestCase):
    def test_max_positions_korean(self) -> None:
        exp = explain_buy_skip_reason("max total positions reached (12)")
        self.assertEqual(exp.category, "포지션 한도")
        self.assertIn("12종", exp.summary)

    def test_signal_sell_korean(self) -> None:
        exp = explain_buy_skip_reason("signal is SELL")
        self.assertEqual(exp.category, "매매 시그널")
        self.assertIn("SELL", exp.summary)

    def test_rank_gate_korean(self) -> None:
        exp = explain_buy_skip_reason(
            "rank ai gate blocked (pct=0.72, cutoff=0.85)"
        )
        self.assertEqual(exp.category, "Rank AI 게이트")
        self.assertIn("72.0%", exp.summary)

    def test_crowding_korean(self) -> None:
        exp = explain_buy_skip_reason(
            "momentum crowding limit reached (peers=3, max=2, candidate_return=12.3%)"
        )
        self.assertEqual(exp.category, "Crowding (모멘텀)")

    def test_execution_label_empty_reason(self) -> None:
        exp = explain_buy_skip_reason(
            "",
            row={"execution_label": "WOULD_SUBMIT_IF_EXECUTED"},
        )
        self.assertEqual(exp.category, "매수 가능")

    def test_explain_execution_label(self) -> None:
        self.assertIn("제출", explain_execution_label("WOULD_SUBMIT_IF_EXECUTED"))

    def test_format_buy_candidates_adds_korean_columns(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "ticker": "PLTR",
                    "signal": "BUY",
                    "reason": "core sleeve budget exhausted ($0.00 remaining)",
                    "execution_label": "NOT_ALLOWED",
                    "ai_score": 0.9,
                }
            ]
        )
        out = format_buy_candidates_for_display(df)
        self.assertIn("스킵분류", out.columns)
        self.assertIn("한글요약", out.columns)
        self.assertIn("상세설명", out.columns)
        self.assertEqual(out.iloc[0]["종목"], "PLTR")
        self.assertEqual(out.iloc[0]["스킵분류"], "슬리브 예산")

    def test_format_audit_skips_adds_action_hint(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "timestamp": "2026-06-09T22:35:00Z",
                    "ticker": "AAPL",
                    "event_type": "SKIP_BUY",
                    "reason": "sector concentration limit reached (sector=Technology, current=2, max=2)",
                }
            ]
        )
        out = format_audit_skips_for_display(df)
        self.assertIn("조치힌트", out.columns)
        self.assertEqual(out.iloc[0]["스킵분류"], "섹터 집중")


if __name__ == "__main__":
    unittest.main()
