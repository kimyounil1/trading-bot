import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.llm_analyst import (
    _generate_llm_text_with_provider,
    evaluate_ticker_consensus,
    reset_genai_client,
)
from src.llm_vllm import should_fallback_to_vllm, vllm_fallback_enabled


class TestLlmVllmFallback(unittest.TestCase):
    def tearDown(self) -> None:
        reset_genai_client()

    def test_vllm_disabled_by_default(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("LLM_VLLM_ENABLED", None)
            os.environ.pop("LLM_VLLM_BASE_URL", None)
            self.assertFalse(vllm_fallback_enabled())

    def test_should_fallback_on_quota_error(self) -> None:
        exc = RuntimeError("429 RESOURCE_EXHAUSTED quota exceeded")
        with patch("src.llm_vllm.vllm_fallback_enabled", return_value=True):
            self.assertTrue(should_fallback_to_vllm(exc))

    @patch("src.llm_analyst.generate_vllm_text")
    @patch("src.llm_analyst._generate_gemini_text")
    def test_gemini_failure_uses_vllm(self, mock_gemini, mock_vllm) -> None:
        mock_gemini.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED")
        mock_vllm.return_value = "DECISION: APPROVE\nCATEGORY: None\nREASON: local ok"

        with patch("src.llm_analyst._resolve_api_key", return_value="test-key"), patch(
            "src.llm_analyst.vllm_fallback_enabled", return_value=True
        ), patch("src.llm_analyst.should_fallback_to_vllm", return_value=True):
            text, provider = _generate_llm_text_with_provider("prompt")
        self.assertEqual(provider, "vllm")
        self.assertIn("APPROVE", text)
        mock_vllm.assert_called_once()

    @patch("src.llm_analyst._generate_runtime_llm_text")
    @patch("src.llm_analyst.llm_backend_available", return_value=True)
    @patch("src.llm_analyst._headlines_before_date", return_value=["Headline"])
    def test_evaluate_tags_local_provider(
        self, mock_headlines, _backend_available, mock_llm
    ) -> None:
        mock_llm.return_value = (
            "DECISION: REJECT\nCATEGORY: Guidance\nREASON: 리스크",
            "vllm",
        )
        with patch("src.llm_analyst.GEMINI_API_KEY", "test-key"):
            ok, reason = evaluate_ticker_consensus(
                "AAPL",
                settings=SimpleNamespace(llm_cache_enabled=False),
            )
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("[local-vLLM]"))


if __name__ == "__main__":
    unittest.main()
