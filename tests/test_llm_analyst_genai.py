import unittest
import hashlib
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

    @patch("src.llm_analyst._generate_runtime_llm_text")
    @patch("src.llm_analyst.llm_backend_available", return_value=True)
    @patch(
        "src.llm_analyst._headlines_before_date",
        return_value=[
            "[2026-07-23T10:00:00Z] benzinga: Headline\n"
            "Summary: Material filing detail"
        ],
    )
    def test_evaluate_parses_reject(
        self, _headlines, _backend_available, mock_generate
    ) -> None:
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
        _headlines.assert_called_once_with(
            "AAPL",
            unittest.mock.ANY,
            max_articles=8,
            include_details=True,
        )
        prompt = mock_generate.call_args.args[0]
        self.assertIn("Material filing detail", prompt)
        self.assertIn("Prefer article body/summary evidence", prompt)

    @patch("src.llm_analyst._save_cache")
    @patch("src.llm_analyst._load_cache")
    @patch("src.llm_analyst._generate_runtime_llm_text")
    @patch("src.llm_analyst.llm_backend_available", return_value=True)
    @patch(
        "src.llm_analyst._headlines_before_date",
        return_value=["[time] source: headline\nSummary: unchanged"],
    )
    def test_live_cache_reused_only_for_same_news_fingerprint(
        self,
        _headlines,
        _backend,
        mock_generate,
        mock_load,
        mock_save,
    ) -> None:
        news_item = "[time] source: headline\nSummary: unchanged"
        fingerprint = hashlib.sha256(news_item.encode("utf-8")).hexdigest()
        mock_load.return_value = {
            "AAPL_2026-07-23": {
                "is_approved": True,
                "reason": "cached",
                "category_reason": "cached",
                "news_fingerprint": fingerprint,
            }
        }
        with patch("src.llm_analyst.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2026-07-23"
            ok, reason = evaluate_ticker_consensus(
                "AAPL",
                settings=SimpleNamespace(llm_cache_enabled=True),
            )
        self.assertTrue(ok)
        self.assertEqual(reason, "cached")
        mock_generate.assert_not_called()
        mock_save.assert_not_called()

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

    def test_parse_llm_decision_accepts_agy_markdown_and_negative_alias(self) -> None:
        ok, category, reason = parse_llm_decision(
            "**DECISION:** Negative\n"
            "**CATEGORY:** Legal / Regulatory\n"
            "**REASON:** SEC 회계 사기 혐의가 제기됐습니다."
        )
        self.assertFalse(ok)
        self.assertEqual(category, "Legal / Regulatory")
        self.assertEqual(reason, "SEC 회계 사기 혐의가 제기됐습니다.")

    @patch("src.llm_analyst._generate_runtime_llm_text")
    @patch("src.llm_analyst.llm_backend_available", return_value=True)
    @patch("src.llm_analyst._headlines_before_date", return_value=["Headline"])
    def test_evaluate_rejects_when_cot_mentions_approve(
        self, _headlines, _backend_available, mock_generate
    ) -> None:
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
