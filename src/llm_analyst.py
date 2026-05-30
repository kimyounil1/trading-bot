"""LLM(Gemini) 기반 뉴스 및 정성적 분석 에이전트."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

import google.generativeai as genai
import yfinance as yf
import pandas as pd

# Gemini API 설정 (환경 변수 필요)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

CACHE_PATH = Path("data/llm_cache.json")
DEFAULT_LLM_MODEL = os.getenv("LLM_MODEL", "gemma-4-26b-a4b-it")


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


def evaluate_ticker_consensus(ticker: str, settings: Optional[Any] = None) -> Tuple[bool, str]:
    """LLM을 사용하여 해당 종목의 최신 뉴스를 분석하고 매수 승인 여부를 결정한다.
    
    Returns:
        (is_approved, reason)
    """
    if not GEMINI_API_KEY:
        return True, "GEMINI_API_KEY not found, skipping qualitative analysis (Auto-Approved)"

    cache_enabled = getattr(settings, "llm_cache_enabled", True)
    degraded_mode = getattr(settings, "llm_degraded_mode", "PASS").upper()

    today = datetime.now().strftime("%Y-%m-%d")
    cache = _load_cache()
    
    # 캐시 확인 (동일 티커, 동일 날짜면 재사용)
    cache_key = f"{ticker}_{today}"
    if cache_enabled and cache_key in cache:
        cached = cache[cache_key]
        return cached["is_approved"], cached.get("category_reason") or cached["reason"]

    try:
        # 1. 최신 뉴스 가져오기 (yfinance)
        t = yf.Ticker(ticker)
        news = t.news
        if not news:
            return True, "No recent news found for qualitative analysis"

        # 최근 뉴스 5개 제목 추출
        headlines = [n.get("title") for n in news[:5]]
        news_context = "\n".join([f"- {h}" for h in headlines])

        # 2. LLM에게 분석 요청
        model = genai.GenerativeModel(DEFAULT_LLM_MODEL)
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
        response = model.generate_content(prompt)
        text = response.text.strip()
        upper_text = text.upper()

        is_approved = "DECISION: APPROVE" in upper_text or "DECISION: [APPROVE]" in upper_text
        
        category = "None"
        if "CATEGORY:" in upper_text:
            idx = upper_text.find("CATEGORY:")
            # Find next newline or end of string
            line = text[idx + 9:].split("\n")[0].strip()
            category = line.strip("[]")

        reason = "LLM Approved"
        if "REASON:" in upper_text:
            idx = upper_text.find("REASON:")
            reason = text[idx + 7:].strip()
        elif not is_approved:
            reason = "정성적 리스크 감지됨"

        category_reason = f"[{category}] {reason}" if category != "None" else reason

        # 캐시 저장
        if cache_enabled:
            cache[cache_key] = {
                "is_approved": is_approved,
                "category": category,
                "reason": reason,
                "category_reason": category_reason,
                "timestamp": datetime.now().isoformat()
            }
            _save_cache(cache)

        return is_approved, category_reason

    except Exception as e:
        print(f"Error in LLM analysis for {ticker}: {e}")
        # Default policy: Auto-approve on failure but log it
        is_ok = (degraded_mode == "PASS")
        status = "Auto-Approved" if is_ok else "Auto-Rejected"
        return is_ok, f"LLM Analysis failed: {e} ({status} per policy)"
