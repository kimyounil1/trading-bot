import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src import llm_analyst
from src.llm_analyst import (
    _generate_llm_text,
    _response_text,
    evaluate_ticker_consensus,
    reset_genai_client,
)


class TestLlmAnalystGenai(unittest.TestCase):
    def tearDown(self) -> None:
        reset_genai_client()

    def test_response_text_from_text_attr(self) -> None:
        response = SimpleNamespace(text="  hello  ")
        self.assertEqual(_response_text(response), "hello")

    def test_response_text_from_candidates(self) -> None:
        part = SimpleNamespace(text="from parts")
        content = SimpleNamespace(parts=[part])
        candidate = SimpleNamespace(content=content)
        response = SimpleNamespace(text=None, candidates=[candidate])
        self.assertEqual(_response_text(response), "from parts")

    @patch("src.llm_analyst._get_genai_client")
    def test_generate_llm_text_calls_client(self, mock_get_client) -> None:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = SimpleNamespace(
            text="DECISION: APPROVE"
        )
        mock_get_client.return_value = mock_client

        text = _generate_llm_text("prompt", model="gemini-2.0-flash")
        self.assertEqual(text, "DECISION: APPROVE")
        mock_client.models.generate_content.assert_called_once_with(
            model="gemini-2.0-flash",
            contents="prompt",
        )

    @patch("src.llm_analyst._generate_llm_text")
    @patch("src.llm_analyst._headlines_before_date", return_value=["Headline"])
    def test_evaluate_parses_reject(self, _headlines, mock_generate) -> None:
        mock_generate.return_value = (
            "DECISION: REJECT\nCATEGORY: Fraud\nREASON: 회계 이슈"
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
