import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import os

from src import llm_analyst
from src.llm_analyst import (
    _generate_llm_text_with_provider,
    _response_text,
    evaluate_ticker_consensus,
    llm_cache_only_for_run,
    llm_skipped_for_run,
    parse_llm_decision,
    reset_genai_client,
)


class TestLlmAnalystGenai(unittest.TestCase):
    def tearDown(self) -> None:
        reset_genai_client()

    def test_llm_cache_only_for_run(self) -> None:
        with patch("src.llm_analyst.llm_skipped_for_run", return_value=False):
            self.assertFalse(llm_cache_only_for_run(execute_orders=False))
            self.assertFalse(llm_cache_only_for_run(execute_orders=True))
        with patch("src.llm_analyst.llm_skipped_for_run", return_value=False), patch.dict(
            os.environ, {"LLM_CACHE_ONLY_DRY_RUN": "1"}
        ):
            self.assertTrue(llm_cache_only_for_run(execute_orders=False))
        with patch("src.llm_analyst.llm_skipped_for_run", return_value=True):
            self.assertTrue(llm_cache_only_for_run(execute_orders=False))
            self.assertTrue(llm_skipped_for_run())

    def test_response_text_from_text_attr(self) -> None:
        response = SimpleNamespace(text="  hello  ")
        self.assertEqual(_response_text(response), "hello")

    def test_response_text_from_candidates(self) -> None:
        part = SimpleNamespace(text="from parts")
        content = SimpleNamespace(parts=[part])
        candidate = SimpleNamespace(content=content)
        response = SimpleNamespace(text=None, candidates=[candidate])
        self.assertEqual(_response_text(response), "from parts")

    @patch("src.llm_analyst._generate_gemini_text", return_value="DECISION: APPROVE")
    def test_generate_llm_text_calls_client(self, mock_gemini) -> None:
        with patch("src.llm_analyst._resolve_api_key", return_value="test-key"):
            text, provider = _generate_llm_text_with_provider(
                "prompt",
                model="gemini-2.0-flash",
            )
        self.assertEqual(text, "DECISION: APPROVE")
        self.assertEqual(provider, "gemini")
        mock_gemini.assert_called_once()

    @patch("src.llm_analyst._generate_llm_text_with_provider")
    @patch("src.llm_analyst._headlines_before_date", return_value=["Headline"])
    def test_evaluate_parses_reject(self, _headlines, mock_generate) -> None:
        mock_generate.return_value = (
            "DECISION: REJECT\nCATEGORY: Fraud\nREASON: 회계 이슈",
            "gemini",
        )
        with patch.object(llm_analyst, "GEMINI_API_KEY", "test-key"):
            ok, reason = evaluate_ticker_consensus(
                "AAPL",
                settings=SimpleNamespace(llm_cache_enabled=False),
            )
        self.assertFalse(ok)
        self.assertIn("Fraud", reason)

    def test_parse_llm_decision_simple_block(self) -> None:
        ok, category, reason = parse_llm_decision(
            "DECISION: REJECT\nCATEGORY: Fraud\nREASON: 회계 이슈"
        )
        self.assertFalse(ok)
        self.assertEqual(category, "Fraud")
        self.assertEqual(reason, "회계 이슈")

    def test_parse_llm_decision_takes_final_block_from_cot(self) -> None:
        # Thinking-mode output: echoes the template, muses over APPROVE, answers REJECT last.
        text = (
            "CATEGORY: [None, Lawsuit, Fraud, Guidance, Financials, Other]\n"
            "REASON: [One sentence explanation in Korean]\n"
            "If I APPROVE, I'm saying risks are not critical. DECISION: APPROVE seems "
            "technically accurate... but institutional selling matters.\n"
            "Let's go with REJECT.\n"
            "DECISION: REJECT\nCATEGORY: Financials\nREASON: 밸류에이션 의문과 기관 매도세가 확인됩니다."
        )
        ok, category, reason = parse_llm_decision(text)
        self.assertFalse(ok)
        self.assertEqual(category, "Financials")
        self.assertEqual(reason, "밸류에이션 의문과 기관 매도세가 확인됩니다.")

    def test_parse_llm_decision_clips_long_reason(self) -> None:
        text = "DECISION: APPROVE\nCATEGORY: None\nREASON: " + "가" * 1000
        ok, _category, reason = parse_llm_decision(text)
        self.assertTrue(ok)
        self.assertLessEqual(len(reason), llm_analyst.MAX_LLM_REASON_LEN + 1)

    def test_parse_llm_decision_missing_block(self) -> None:
        ok, category, reason = parse_llm_decision("no structured output here")
        self.assertIsNone(ok)
        self.assertEqual(category, "None")
        self.assertEqual(reason, "")

    @patch("src.llm_analyst._generate_llm_text_with_provider")
    @patch("src.llm_analyst._headlines_before_date", return_value=["Headline"])
    def test_evaluate_rejects_when_cot_mentions_approve(self, _headlines, mock_generate) -> None:
        mock_generate.return_value = (
            "Maybe DECISION: APPROVE is defensible... no.\n"
            "DECISION: REJECT\nCATEGORY: Guidance\nREASON: 가이던스 하향.",
            "gemini",
        )
        with patch.object(llm_analyst, "GEMINI_API_KEY", "test-key"):
            ok, reason = evaluate_ticker_consensus(
                "AAPL",
                settings=SimpleNamespace(llm_cache_enabled=False),
            )
        self.assertFalse(ok)
        self.assertIn("가이던스", reason)


if __name__ == "__main__":
    unittest.main()
