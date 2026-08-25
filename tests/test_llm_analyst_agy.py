import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import llm_analyst
from src.llm_analyst import (
    DEFAULT_AGY_FALLBACK_MODEL,
    DEFAULT_AGY_MODEL,
    _agy_model_chain,
    _generate_agy_text,
    _generate_llm_text_with_provider,
    _generate_runtime_llm_text,
    llm_backend_available,
)


class TestLlmAnalystAgy(unittest.TestCase):
    @patch("src.llm_analyst.subprocess.run")
    @patch("src.llm_analyst._resolve_agy_cli", return_value="/opt/agy")
    def test_generate_agy_uses_safe_headless_command(self, _resolve, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="DECISION: APPROVE\n", stderr=""
        )
        with tempfile.TemporaryDirectory() as workdir, patch.dict(
            os.environ,
            {
                "AGY_WORKDIR": workdir,
                "ALPACA_API_KEY": "must-not-leak",
                "TELEGRAM_BOT_TOKEN": "must-not-leak",
            },
        ):
            text = _generate_agy_text("headline-only prompt")

        self.assertIn("APPROVE", text)
        command = mock_run.call_args.args[0]
        kwargs = mock_run.call_args.kwargs
        self.assertEqual(command[0], "/opt/agy")
        self.assertEqual(command[command.index("--model") + 1], DEFAULT_AGY_MODEL)
        self.assertIn("--sandbox", command)
        self.assertEqual(command[command.index("--mode") + 1], "plan")
        self.assertEqual(command[-1], "headline-only prompt")
        self.assertNotIn("ALPACA_API_KEY", kwargs["env"])
        self.assertNotIn("TELEGRAM_BOT_TOKEN", kwargs["env"])
        self.assertEqual(kwargs["env"]["AGY_CLI_HIDE_ACCOUNT_INFO"], "1")
        self.assertEqual(kwargs["cwd"], Path(workdir))
        self.assertFalse(kwargs["check"])

    @patch("src.llm_analyst.subprocess.run")
    @patch("src.llm_analyst._resolve_agy_cli", return_value="/opt/agy")
    def test_generate_agy_surfaces_nonzero_exit(self, _resolve, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=7, stdout="", stderr="quota exhausted"
        )
        with tempfile.TemporaryDirectory() as workdir, patch.dict(
            os.environ, {"AGY_WORKDIR": workdir}
        ):
            with self.assertRaisesRegex(RuntimeError, "quota exhausted"):
                _generate_agy_text("prompt")

    @patch("src.llm_analyst._generate_agy_text", return_value="DECISION: APPROVE")
    def test_force_agy_provider(self, mock_agy) -> None:
        text, provider = _generate_llm_text_with_provider(
            "prompt", force_provider="agy"
        )
        self.assertEqual(provider, "agy")
        self.assertIn("APPROVE", text)
        mock_agy.assert_called_once_with("prompt", model=None)

    @patch("src.llm_analyst._generate_agy_text")
    @patch("src.llm_analyst.vllm_fallback_enabled", return_value=False)
    @patch("src.llm_analyst._runtime_llm_provider", return_value="agy")
    def test_opus_quota_failure_uses_gemini_agy_quota(
        self, _provider, _vllm_disabled, mock_agy
    ) -> None:
        mock_agy.side_effect = [
            RuntimeError("Opus quota exhausted"),
            "DECISION: APPROVE",
        ]

        text, provider = _generate_runtime_llm_text("prompt")

        self.assertEqual(provider, f"agy:{DEFAULT_AGY_FALLBACK_MODEL}")
        self.assertIn("APPROVE", text)
        self.assertEqual(
            [call.kwargs["model"] for call in mock_agy.call_args_list],
            [DEFAULT_AGY_MODEL, DEFAULT_AGY_FALLBACK_MODEL],
        )

    @patch("src.llm_analyst.generate_vllm_text")
    @patch("src.llm_analyst._generate_agy_text")
    @patch("src.llm_analyst.vllm_fallback_enabled", return_value=True)
    @patch("src.llm_analyst._runtime_llm_provider", return_value="agy")
    def test_both_agy_models_failure_uses_opted_in_vllm(
        self, _provider, _vllm_enabled, mock_agy, mock_vllm
    ) -> None:
        mock_agy.side_effect = RuntimeError("model quota exhausted")
        mock_vllm.return_value = "DECISION: APPROVE"

        text, provider = _generate_runtime_llm_text("prompt")

        self.assertEqual(provider, "vllm")
        self.assertIn("APPROVE", text)
        self.assertEqual(mock_agy.call_count, 2)
        mock_vllm.assert_called_once_with("prompt")

    @patch("src.llm_analyst._resolve_agy_cli", return_value="/opt/agy")
    def test_agy_backend_availability(self, _resolve) -> None:
        self.assertTrue(llm_backend_available("agy"))
        self.assertFalse(llm_backend_available("unsupported"))

    def test_runtime_defaults_to_agy(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LLM_PROVIDER", None)
            self.assertEqual(llm_analyst._runtime_llm_provider(), "agy")

    def test_default_agy_model_chain(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGY_LLM_MODEL", None)
            os.environ.pop("AGY_LLM_FALLBACK_MODEL", None)
            self.assertEqual(
                _agy_model_chain(),
                (DEFAULT_AGY_MODEL, DEFAULT_AGY_FALLBACK_MODEL),
            )


if __name__ == "__main__":
    unittest.main()
