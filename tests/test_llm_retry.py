import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src import llm_analyst
from src.llm_analyst import (
    _call_with_retry,
    _generate_gemini_text,
    _is_retryable_gemini_error,
    _suggested_retry_delay,
)


class TestLlmRetry(unittest.TestCase):
    def test_is_retryable_for_transient_errors(self) -> None:
        for msg in (
            "429 RESOURCE_EXHAUSTED: quota exceeded",
            "Too Many Requests",
            "503 Service Unavailable",
            "rate limit reached",
        ):
            self.assertTrue(_is_retryable_gemini_error(RuntimeError(msg)), msg)

    def test_not_retryable_for_auth_or_generic(self) -> None:
        self.assertFalse(_is_retryable_gemini_error(RuntimeError("API key not valid")))
        self.assertFalse(_is_retryable_gemini_error(RuntimeError("403 permission denied")))
        self.assertFalse(_is_retryable_gemini_error(ValueError("empty LLM response")))

    def test_suggested_retry_delay_parsed(self) -> None:
        exc = RuntimeError("429 RESOURCE_EXHAUSTED ... retry_delay { seconds: 7 }")
        self.assertEqual(_suggested_retry_delay(exc), 7.0)
        self.assertIsNone(_suggested_retry_delay(RuntimeError("429 no delay hint")))

    def test_succeeds_after_transient_error(self) -> None:
        calls = {"n": 0}
        slept: list[float] = []

        def fn() -> str:
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("429 RESOURCE_EXHAUSTED")
            return "ok"

        result = _call_with_retry(
            fn, max_retries=2, base_delay=1.0, max_delay=8.0,
            sleep=slept.append, rng=lambda: 0.0,
        )
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 2)
        self.assertEqual(slept, [1.0])  # base_delay * 2**0, no jitter (rng=0)

    def test_exhausts_retries_then_raises(self) -> None:
        calls = {"n": 0}
        slept: list[float] = []

        def fn() -> str:
            calls["n"] += 1
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

        with self.assertRaises(RuntimeError):
            _call_with_retry(
                fn, max_retries=2, base_delay=1.0, max_delay=8.0,
                sleep=slept.append, rng=lambda: 0.0,
            )
        self.assertEqual(calls["n"], 3)  # initial + 2 retries
        self.assertEqual(slept, [1.0, 2.0])  # exponential backoff

    def test_no_retry_on_auth_error(self) -> None:
        calls = {"n": 0}
        slept: list[float] = []

        def fn() -> str:
            calls["n"] += 1
            raise RuntimeError("API key not valid")

        with self.assertRaises(RuntimeError):
            _call_with_retry(fn, max_retries=3, sleep=slept.append, rng=lambda: 0.0)
        self.assertEqual(calls["n"], 1)  # raised immediately, no retry
        self.assertEqual(slept, [])

    def test_honors_server_suggested_delay(self) -> None:
        calls = {"n": 0}
        slept: list[float] = []

        def fn() -> str:
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("429 ... retry_delay { seconds: 3 }")
            return "ok"

        result = _call_with_retry(
            fn, max_retries=2, base_delay=1.0, max_delay=8.0,
            sleep=slept.append, rng=lambda: 0.0,
        )
        self.assertEqual(result, "ok")
        self.assertEqual(slept, [3.0])  # suggested delay honored over backoff

    def test_delay_capped_at_max(self) -> None:
        slept: list[float] = []

        def fn() -> str:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

        with self.assertRaises(RuntimeError):
            _call_with_retry(
                fn, max_retries=4, base_delay=5.0, max_delay=8.0,
                sleep=slept.append, rng=lambda: 0.0,
            )
        # base 5*2**n -> 5,10,20,40 capped to 8 (plus 0 jitter)
        self.assertEqual(slept, [5.0, 8.0, 8.0, 8.0])


class TestGenerateGeminiTextRetry(unittest.TestCase):
    def test_generate_gemini_text_retries_then_succeeds(self) -> None:
        calls = {"n": 0}

        def generate_content(*, model, contents):  # noqa: ANN001 - test stub
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("429 RESOURCE_EXHAUSTED: quota")
            return SimpleNamespace(text="DECISION: APPROVE")

        fake_client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        with patch.object(llm_analyst, "_get_genai_client", return_value=fake_client), patch.object(
            llm_analyst.time, "sleep", lambda _seconds: None
        ):
            text = _generate_gemini_text("prompt")
        self.assertEqual(text, "DECISION: APPROVE")
        self.assertEqual(calls["n"], 2)


if __name__ == "__main__":
    unittest.main()
