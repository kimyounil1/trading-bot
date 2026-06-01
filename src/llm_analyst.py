"""LLM(Gemini) 기반 뉴스 및 정성적 분석 에이전트."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from google import genai

from src.news_sentiment import _headlines_before_date, _headlines_current

if TYPE_CHECKING:
    from google.genai import Client as GenaiClient

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
CACHE_PATH = Path("data/llm_cache.json")
DEFAULT_LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")

_genai_client: GenaiClient | None = None


def _get_genai_client() -> GenaiClient:
    global _genai_client
    if _genai_client is None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required for LLM calls")
        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
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


def _generate_llm_text(prompt: str, *, model: str | None = None) -> str:
    client = _get_genai_client()
    response = client.models.generate_content(
        model=model or DEFAULT_LLM_MODEL,
        contents=prompt,
    )
    return _response_text(response)


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

    if not GEMINI_API_KEY:
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
Provide your decision in the following structured format:
DECISION: [APPROVE or REJECT]
CATEGORY: [None, Lawsuit, Fraud, Guidance, Financials, Other]
REASON: [One sentence explanation in Korean]
"""
        text = _generate_llm_text(prompt)
        upper_text = text.upper()

        is_approved = "DECISION: APPROVE" in upper_text or "DECISION: [APPROVE]" in upper_text

        category = "None"
        if "CATEGORY:" in upper_text:
            idx = upper_text.find("CATEGORY:")
            line = text[idx + 9 :].split("\n")[0].strip()
            category = line.strip("[]")

        reason = "LLM Approved"
        if "REASON:" in upper_text:
            idx = upper_text.find("REASON:")
            reason = text[idx + 7 :].strip()
        elif not is_approved:
            reason = "정성적 리스크 감지됨"

        category_reason = f"[{category}] {reason}" if category != "None" else reason

        if cache_enabled:
            cache[cache_key] = {
                "is_approved": is_approved,
                "category": category,
                "reason": reason,
                "category_reason": category_reason,
                "timestamp": datetime.now().isoformat(),
            }
            _save_cache(cache)

        return is_approved, category_reason

    except Exception as e:
        print(f"Error in LLM analysis for {ticker}: {e}")
        is_ok = degraded_mode == "PASS"
        status = "Auto-Approved" if is_ok else "Auto-Rejected"
        return is_ok, f"LLM Analysis failed: {e} ({status} per policy)"
