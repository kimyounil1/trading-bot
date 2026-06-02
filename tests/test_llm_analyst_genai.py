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


if __name__ == "__main__":
    unittest.main()
