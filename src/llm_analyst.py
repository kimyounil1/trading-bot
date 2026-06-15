"""LLM(Gemini) 기반 뉴스 및 정성적 분석 에이전트."""

from __future__ import annotations

import json
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple

from google import genai

from src.llm_vllm import (
    generate_vllm_text,
    should_fallback_to_vllm,
    vllm_fallback_enabled,
)
from src.news_sentiment import _headlines_before_date, _headlines_current

if TYPE_CHECKING:
    from google.genai import Client as GenaiClient

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
CACHE_PATH = Path("data/llm_cache.json")
DEFAULT_LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")

_genai_client: GenaiClient | None = None


def _resolve_api_key() -> str | None:
    if GEMINI_API_KEY:
        return GEMINI_API_KEY
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def llm_backend_available() -> bool:
    return bool(_resolve_api_key()) or vllm_fallback_enabled()


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip() or default)
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "").strip() or default)
    except (TypeError, ValueError):
        return default


# Bounded retry for transient Gemini errors (429/RESOURCE_EXHAUSTED/503) before
# falling back to vLLM / degraded mode. Conservative defaults bound live-path latency.
LLM_MAX_RETRIES = _env_int("LLM_MAX_RETRIES", 2)
LLM_RETRY_BASE_DELAY = _env_float("LLM_RETRY_BASE_DELAY", 2.0)
LLM_RETRY_MAX_DELAY = _env_float("LLM_RETRY_MAX_DELAY", 8.0)

_RETRYABLE_MARKERS = (
    "resource_exhausted",
    "rate limit",
    "rate_limit",
    "ratelimit",
    "too many requests",
    "429",
    "503",
    "unavailable",
    "quota",
)
_NON_RETRYABLE_AUTH_MARKERS = (
    "invalid api key",
    "api key not valid",
    "permission denied",
    "unauthenticated",
    "401",
    "403",
)
_RETRY_DELAY_RE = re.compile(r"retry_?delay\D+(\d+(?:\.\d+)?)", re.IGNORECASE)


def _is_retryable_gemini_error(exc: BaseException) -> bool:
    """True for transient Gemini errors (429/quota/503) worth an in-place retry.

    Auth/permission failures are never retried.
    """
    message = str(exc).lower()
    type_name = type(exc).__name__.lower()
    if any(marker in message for marker in _NON_RETRYABLE_AUTH_MARKERS):
        return False
    return any(marker in message or marker in type_name for marker in _RETRYABLE_MARKERS)


def _suggested_retry_delay(exc: BaseException) -> float | None:
    """Best-effort parse of a server-suggested retry delay (seconds) from the error."""
    match = _RETRY_DELAY_RE.search(str(exc))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _call_with_retry(
    fn: Callable[[], str],
    *,
    max_retries: int = LLM_MAX_RETRIES,
    base_delay: float = LLM_RETRY_BASE_DELAY,
    max_delay: float = LLM_RETRY_MAX_DELAY,
    is_retryable: Callable[[BaseException], bool] = _is_retryable_gemini_error,
    sleep: Callable[[float], None] | None = None,
    rng: Callable[[], float] | None = None,
) -> str:
    """Call fn(), retrying transient failures with capped exponential backoff + jitter.

    Honors a server-suggested retry delay when the error carries one. Non-retryable
    errors (and exhausted retries) propagate so the caller's vLLM/degraded fallback runs.
    """
    sleep = sleep or time.sleep
    rng = rng or random.random
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - re-raised when not retryable/exhausted
            if attempt >= max_retries or not is_retryable(exc):
                raise
            suggested = _suggested_retry_delay(exc)
            base = suggested if suggested is not None else base_delay * (2 ** attempt)
            delay = min(base, max_delay) + rng() * 0.5 * base_delay
            print(
                f"Gemini transient error (attempt {attempt + 1}/{max_retries + 1}), "
                f"retrying in {delay:.1f}s: {exc}"
            )
            sleep(delay)
            attempt += 1


def llm_skipped_for_run() -> bool:
    """Skip LLM buy guard during pytest/CI (TRADING_BOT_SKIP_LLM=1 or PYTEST_CURRENT_TEST)."""
    if _env_truthy("TRADING_BOT_SKIP_LLM"):
        return True
    return "PYTEST_CURRENT_TEST" in os.environ


def llm_cache_only_for_run(*, execute_orders: bool) -> bool:
    """Dry-run/paper: live LLM on cache miss by default; tests skip API calls."""
    if llm_skipped_for_run():
        return True
    if execute_orders:
        return False
    if _env_truthy("LLM_CACHE_ONLY_DRY_RUN"):
        return True
    live_env = os.getenv("LLM_LIVE_IN_DRY_RUN", "").strip().lower()
    if live_env in {"0", "false", "no"}:
        return True
    if live_env in {"1", "true", "yes"}:
        return False
    return False


def _get_genai_client() -> GenaiClient:
    global _genai_client
    api_key = _resolve_api_key()
    if _genai_client is None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required for LLM calls")
        _genai_client = genai.Client(api_key=api_key)
    return _genai_client


def reset_genai_client() -> None:
    """Clear cached client (tests)."""
    global _genai_client
    _genai_client = None


def _response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return str(text).strip()
    candidates = getattr(response, "candidates", None) or []
    if candidates:
        content = getattr(candidates[0], "content", None)
        parts = getattr(content, "parts", None) if content else None
        if parts:
            chunk = getattr(parts[0], "text", None)
            if chunk:
                return str(chunk).strip()
    raise ValueError("empty LLM response")


def _generate_gemini_text(prompt: str, *, model: str | None = None) -> str:
    client = _get_genai_client()

    def _call() -> str:
        response = client.models.generate_content(
            model=model or DEFAULT_LLM_MODEL,
            contents=prompt,
        )
        return _response_text(response)

    return _call_with_retry(_call)


def _generate_llm_text_with_provider(prompt: str, *, model: str | None = None) -> Tuple[str, str]:
    """Return (text, provider) where provider is 'gemini' or 'vllm'."""
    gemini_error: BaseException | None = None
    if _resolve_api_key():
        try:
            return _generate_gemini_text(prompt, model=model), "gemini"
        except Exception as exc:
            if not should_fallback_to_vllm(exc):
                raise
            gemini_error = exc
            print(f"Gemini LLM failed, trying local vLLM fallback: {exc}")

    if vllm_fallback_enabled():
        try:
            return generate_vllm_text(prompt), "vllm"
        except Exception as vllm_exc:
            if gemini_error is not None:
                raise RuntimeError(
                    f"Gemini failed ({gemini_error}); local vLLM failed ({vllm_exc})"
                ) from vllm_exc
            raise

    if gemini_error is not None:
        raise gemini_error
    raise ValueError(
        "No LLM backend available (set GEMINI_API_KEY or configure LLM_VLLM_BASE_URL)"
    )


def _generate_llm_text(prompt: str, *, model: str | None = None) -> str:
    text, _provider = _generate_llm_text_with_provider(prompt, model=model)
    return text


def _load_cache() -> Dict[str, dict]:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache: Dict[str, dict]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


_DECISION_RE = re.compile(r"DECISION:\s*\[?\s*(APPROVE|REJECT)\s*\]?", re.IGNORECASE)
_CATEGORY_RE = re.compile(r"CATEGORY:\s*\[?\s*([^\]\n]+?)\s*\]?\s*$", re.IGNORECASE | re.MULTILINE)
_REASON_RE = re.compile(r"REASON:\s*(.+)", re.IGNORECASE)

MAX_LLM_REASON_LEN = 300


def parse_llm_decision(text: str) -> tuple[bool | None, str, str]:
    """Extract the final DECISION/CATEGORY/REASON block from LLM output.

    Thinking-mode responses repeat DECISION/CATEGORY/REASON while reasoning
    (and echo the prompt template), so only the last occurrence of each field
    is the model's answer. Reason is clipped to one line for audit logging.
    """
    decisions = _DECISION_RE.findall(text)
    decision = decisions[-1].upper() if decisions else None

    categories = [c.strip() for c in _CATEGORY_RE.findall(text) if "," not in c]
    category = categories[-1] if categories else "None"

    reasons = [r.strip() for r in _REASON_RE.findall(text)]
    reason = reasons[-1] if reasons else ""
    if reason.startswith("[") and reason.endswith("]"):
        reason = reason[1:-1].strip()
    if len(reason) > MAX_LLM_REASON_LEN:
        reason = reason[: MAX_LLM_REASON_LEN].rstrip() + "…"

    is_approved = None if decision is None else decision == "APPROVE"
    return is_approved, category, reason


def evaluate_ticker_consensus(
    ticker: str,
    settings: Optional[Any] = None,
    as_of_date: Optional[str] = None,
    *,
    cache_only: bool = False,
    fallback_current_headlines: bool = False,
) -> Tuple[bool, str]:
    """LLM을 사용하여 해당 종목의 최신 뉴스를 분석하고 매수 승인 여부를 결정한다.

    as_of_date: cache key date (YYYY-MM-DD). Backtest replay should pass entry_date.
    cache_only: if True, never call the API on cache miss (use llm_degraded_mode).

    Returns:
        (is_approved, reason)
    """
    cache_enabled = getattr(settings, "llm_cache_enabled", True)
    degraded_mode = getattr(settings, "llm_degraded_mode", "PASS").upper()
    date_key = as_of_date or datetime.now().strftime("%Y-%m-%d")
    cache = _load_cache()
    cache_key = f"{ticker}_{date_key}"

    if cache_enabled and cache_key in cache:
        cached = cache[cache_key]
        return cached["is_approved"], cached.get("category_reason") or cached["reason"]

    if cache_only:
        is_ok = degraded_mode == "PASS"
        status = "Auto-Approved" if is_ok else "Auto-Rejected"
        return is_ok, f"LLM cache miss ({status} per policy)"

    if not llm_backend_available():
        return True, "GEMINI_API_KEY not found, skipping qualitative analysis (Auto-Approved)"

    try:
        headlines = _headlines_before_date(ticker, date_key, max_articles=5)
        if not headlines and fallback_current_headlines:
            headlines = _headlines_current(ticker, max_articles=5)
        if not headlines:
            return True, "No recent news found for qualitative analysis"

        news_context = "\n".join([f"- {h}" for h in headlines])
        prompt = f"""
Analyze the following recent news headlines for the stock ticker '{ticker}'.
Your goal is to identify critical fundamental risks that a purely quantitative model might miss (e.g., fraud, major lawsuits, catastrophic product failure, or terrible forward guidance).

News Headlines:
{news_context}

Based on these headlines, should we proceed with buying this stock?
Provide your decision in the following structured format only (no extra commentary):
DECISION: [APPROVE or REJECT]
CATEGORY: [None, Lawsuit, Fraud, Guidance, Financials, Other]
REASON: [One sentence explanation in Korean]
"""
        text, provider = _generate_llm_text_with_provider(prompt)

        parsed_approved, category, reason = parse_llm_decision(text)
        is_approved = bool(parsed_approved)
        if not reason:
            reason = "LLM Approved" if is_approved else "정성적 리스크 감지됨"

        category_reason = f"[{category}] {reason}" if category != "None" else reason
        if provider == "vllm":
            category_reason = f"[local-vLLM] {category_reason}"

        if cache_enabled:
            cache[cache_key] = {
                "is_approved": is_approved,
                "category": category,
                "reason": reason,
                "category_reason": category_reason,
                "llm_provider": provider,
                "timestamp": datetime.now().isoformat(),
            }
            _save_cache(cache)

        return is_approved, category_reason

    except Exception as e:
        print(f"Error in LLM analysis for {ticker}: {e}")
        is_ok = degraded_mode == "PASS"
        status = "Auto-Approved" if is_ok else "Auto-Rejected"
        return is_ok, f"LLM Analysis failed: {e} ({status} per policy)"
