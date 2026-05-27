"""LLM(Gemini) 기반 뉴스 및 정성적 분석 에이전트."""

import os
import google.generativeai as genai
import yfinance as yf
from typing import Tuple, Optional
import pandas as pd

# Gemini API 설정 (환경 변수 필요)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def evaluate_ticker_consensus(ticker: str) -> Tuple[bool, str]:
    """LLM을 사용하여 해당 종목의 최신 뉴스를 분석하고 매수 승인 여부를 결정한다.
    
    Returns:
        (is_approved, reason)
    """
    if not GEMINI_API_KEY:
        return True, "GEMINI_API_KEY not found, skipping qualitative analysis (Auto-Approved)"

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
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
Analyze the following recent news headlines for the stock ticker '{ticker}'.
Your goal is to identify critical fundamental risks that a purely quantitative model might miss (e.g., fraud, major lawsuits, catastrophic product failure, or terrible forward guidance).

News Headlines:
{news_context}

Based on these headlines, should we proceed with buying this stock?
Provide your decision in the following format:
DECISION: [APPROVE or REJECT]
REASON: [One sentence explanation in Korean]
"""
        response = model.generate_content(prompt)
        text = response.text.upper()

        if "REJECT" in text:
            reason = "정성적 리스크 감지됨"
            # 추출 시도
            if "REASON:" in text:
                reason = response.text.split("REASON:")[1].strip()
            return False, reason

        return True, "LLM Approved"

    except Exception as e:
        print(f"Error in LLM analysis for {ticker}: {e}")
        return True, f"LLM Analysis failed: {e} (Auto-Approved for safety)"
