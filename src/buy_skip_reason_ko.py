"""Korean explanations for buy skip / block reasons shown in CMS."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

_INSTRUMENT_PREFIX_RE = re.compile(r"^instrument_kind=[^;]+;\s*", re.IGNORECASE)


@dataclass(frozen=True)
class BuySkipExplanation:
    category: str
    summary: str
    detail: str
    action_hint: str = ""


def _strip_instrument_prefix(reason: str) -> str:
    return _INSTRUMENT_PREFIX_RE.sub("", str(reason or "").strip())


def _num(pattern: str, text: str, group: int = 1) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return match.group(group)


def explain_buy_skip_reason(
    reason: str,
    *,
    row: Mapping[str, Any] | None = None,
) -> BuySkipExplanation:
    """Turn raw English audit/cache reason into Korean labels for CMS."""
    raw = str(reason or "").strip()
    text = _strip_instrument_prefix(raw)
    row = row or {}

    if not text:
        label = str(row.get("execution_label") or "").strip()
        if label == "WOULD_SUBMIT_IF_EXECUTED":
            return BuySkipExplanation(
                category="매수 가능",
                summary="모든 검사를 통과했습니다.",
                detail="execute 실행 시 주문 후보로 제출될 수 있습니다.",
            )
        if label == "SESSION_CLOSED":
            return BuySkipExplanation(
                category="세션 차단",
                summary="현재 거래 세션에서는 주문을 넣을 수 없습니다.",
                detail="정규장·프리·애프터·오버나잇 허용 설정과 시장 시간을 확인하세요.",
            )
        if label == "SKIP_MAX_ORDERS":
            return BuySkipExplanation(
                category="주문 한도",
                summary="이번 run에서 허용된 최대 주문 건수에 도달했습니다.",
                detail="설정 `max_orders_per_run` 때문에 뒤 순위 후보는 제출되지 않습니다.",
            )
        if label == "SKIP_RANK_TOP_K":
            return BuySkipExplanation(
                category="랭크 배분",
                summary="rank 상위 K 밖이라 매수에서 제외됐습니다.",
                detail="85% 컷을 통과했지만 같은 run에서 rank percentile 상위 K에 들지 못했습니다.",
                action_hint="`rank_ai_buy_top_k_enabled`와 `max_orders_per_run`을 확인하세요.",
            )
        if label == "SKIP_DAILY_LIMIT":
            return BuySkipExplanation(
                category="일일 한도",
                summary="오늘 일일 매수 금액 상한에 도달했습니다.",
                detail="`max_daily_order_amount` 한도 때문에 추가 매수가 차단됩니다.",
            )
        if label == "SKIP_COOLDOWN":
            return BuySkipExplanation(
                category="재매수 쿨다운",
                summary="최근 매수한 종목이라 쿨다운 기간 중입니다.",
                detail="`buy_cooldown_days` 설정 동안 같은 종목 재매수가 제한됩니다.",
            )
        if label == "NOT_ALLOWED":
            return BuySkipExplanation(
                category="매수 불가",
                summary="리스크·가드 검사에서 매수가 허용되지 않았습니다.",
                detail="아래 원본 사유(영문) 또는 상세 컬럼을 확인하세요.",
            )
        return BuySkipExplanation(
            category="기타",
            summary="사유 문자열이 비어 있습니다.",
            detail="audit/candidate cache에 reason이 기록되지 않았습니다.",
        )

    lower = text.lower()

    if "max total positions reached" in lower:
        return BuySkipExplanation(
            category="포지션 한도",
            summary="보유 종목 수가 설정한 최대치(12종)에 도달했습니다.",
            detail=(
                "신규 종목 매수는 슬롯이 비어야 가능합니다. "
                "기존 보유 종목에 대한 추가 매수(add)는 별도 규칙으로 허용될 수 있습니다."
            ),
            action_hint="청산·축소 후 슬롯을 비우거나 `max_total_positions`를 조정하세요.",
        )

    if lower.startswith("signal is sell"):
        return BuySkipExplanation(
            category="매매 시그널",
            summary="기술적 시그널이 매수(BUY)가 아니라 매도(SELL)입니다.",
            detail="단기 이동평균이 역배열이거나 RSI·추세 조건이 매수 구간을 벗어났습니다.",
        )

    if lower.startswith("signal is hold"):
        return BuySkipExplanation(
            category="매매 시그널",
            summary="시그널이 HOLD(관망)입니다.",
            detail="추세·RSI·거래량·변동성 필터 중 하나 이상이 매수 조건을 충족하지 못했습니다.",
        )

    pct_match = re.search(
        r"rank ai gate blocked \(pct=([\d.]+),\s*cutoff=([\d.]+)\)",
        text,
        re.IGNORECASE,
    )
    if pct_match:
        p, cutoff = pct_match.group(1), pct_match.group(2)
        return BuySkipExplanation(
            category="Rank AI 게이트",
            summary=f"Rank AI 상위 백분위 {float(p)*100:.1f}% — 커트오프 {float(cutoff)*100:.0f}% 미달",
            detail=(
                "유니버스 전체 Rank AI 점수 중 상위 약 15% + 최소 quantile 0.85를 통과해야 "
                "paper 매수 게이트가 열립니다. 현재는 상대 순위가 낮아 차단되었습니다."
            ),
            action_hint="2주 paper 관측 중이면 gate 완화는 보류. 관측 후 cutoff 조정 검토.",
        )

    if "rank ai gate missing score" in lower:
        return BuySkipExplanation(
            category="Rank AI 게이트",
            summary="Rank AI 점수를 계산하지 못했습니다.",
            detail="가격 데이터 부족·모델 추론 실패 등으로 rank score가 없어 fail-closed로 차단됩니다.",
        )

    if "rank ai gate passed" in lower:
        return BuySkipExplanation(
            category="Rank AI 통과",
            summary="Rank AI paper 게이트를 통과했습니다.",
            detail="이후 슬리브 예산·일일 한도·주문 건수 등 다른 가드만 남았을 수 있습니다.",
        )

    if "ai score filter blocked" in lower:
        score = _num(r"score=([^,\)]+)", text)
        threshold = _num(r"threshold=([^,\)]+)", text)
        return BuySkipExplanation(
            category="AI 점수",
            summary=f"Champion AI 점수 {score or '?'} < 임계값 {threshold or '?'}",
            detail="`use_ai_score`와 `ai_score_buy_threshold` 설정에 따라 AI 점수가 낮으면 매수하지 않습니다.",
        )

    if "llm reject" in lower:
        return BuySkipExplanation(
            category="LLM 차단",
            summary="LLM 뉴스·리스크 분석에서 매수 거부(REJECT) 판정입니다.",
            detail=(
                "Gemini가 부정적 뉴스·가이던스·소송 등을 감지했습니다. "
                "`llm_advisory_only=true`이면 paper에서는 참고만 하고 blocking은 하지 않을 수 있습니다."
            ),
            action_hint="429 quota 초과 시에도 advisory 모드면 매수는 계속 검토됩니다.",
        )

    if "momentum crowding limit reached" in lower:
        peers = _num(r"peers=(\d+)", text)
        max_p = _num(r"max=(\d+)", text)
        ret = _num(r"candidate_return=([-\d.]+%)", text)
        return BuySkipExplanation(
            category="Crowding (모멘텀)",
            summary=f"모멘텀 crowding — 유사 상승 종목 {peers or '?'}개 (한도 {max_p or '2'})",
            detail=(
                f"최근 수익률 {ret or ''} 등 모멘텀 조건을 만족하는데, "
                "포트폴리오에 이미 비슷한 모멘텀 종목이 많아 분산 규칙으로 차단했습니다."
            ),
        )

    if "trend crowding limit reached" in lower:
        peers = _num(r"peers=(\d+)", text)
        gap = _num(r"candidate_gap=([-\d.]+%)", text)
        return BuySkipExplanation(
            category="Crowding (추세)",
            summary=f"추세 crowding — 유사 추세 종목 {peers or '?'}개 초과",
            detail=f"이평 대비 추세 gap {gap or ''} — 동일 추세 노출이 많아 추가 매수를 막았습니다.",
        )

    if "sector concentration limit reached" in lower:
        sector = _num(r"sector=([^,\)]+)", text)
        current = _num(r"current=(\d+)", text)
        max_s = _num(r"max=(\d+)", text)
        return BuySkipExplanation(
            category="섹터 집중",
            summary=f"섹터 '{sector or '?'}' 보유 {current or '?'}종 — 한도 {max_s or '2'}종",
            detail="같은 섹터에 이미 최대치만큼 보유 중이라 신규 매수를 허용하지 않습니다.",
        )

    if "core sleeve budget exhausted" in lower or "sleeve budget exhausted" in lower:
        remaining = _num(r"\$([\d.]+)\s*remaining", text)
        return BuySkipExplanation(
            category="슬리브 예산",
            summary=f"core 슬리브 이번 run 매수 예산 부족 (잔여 ${remaining or '0'})",
            detail=(
                "슬리브 target weight 대비 order_budget·headroom을 초과했습니다. "
                "cash surplus deploy가 켜져 있어도 gate 통과 후보가 먼저 필요합니다."
            ),
        )

    if "cash is zero or negative" in lower:
        return BuySkipExplanation(
            category="현금 부족",
            summary="계좌 가용 현금이 0 이하로 잡혀 신규 매수가 불가합니다.",
            detail="Alpaca buying_power/cash 스냅샷 기준입니다. 미체결 매수·슬리브 cash reserve를 확인하세요.",
        )

    if "target amount is zero or negative" in lower:
        return BuySkipExplanation(
            category="주문 금액",
            summary="계산된 매수 금액이 0 이하입니다.",
            detail="포지션 비중·cash buffer·배포 가능 현금 때문에 실질 주문액이 0이 되었습니다.",
        )

    if "high pairwise correlation" in lower:
        corr = _num(r"correlation \(([\d.]+)\)", text)
        sym = _num(r"with (\w+)", text)
        return BuySkipExplanation(
            category="상관관계",
            summary=f"보유 종목 {sym or '?'}와 상관계수 {corr or '?'} — 임계값 초과",
            detail="포트폴리오 분산을 위해 높은 상관관계 종목 추가 매수를 막았습니다.",
        )

    if "buy cooldown active" in lower:
        days = _num(r"\((\d+)d\)", text)
        return BuySkipExplanation(
            category="재매수 쿨다운",
            summary=f"최근 매수 후 {days or '?'}일 쿨다운 중입니다.",
            detail="같은 종목을 너무 자주 매수하지 않도록 하는 규칙입니다.",
        )

    if "daily order amount limit reached" in lower or "daily order amount capped" in lower:
        return BuySkipExplanation(
            category="일일 한도",
            summary="오늘 일일 매수 금액 한도에 도달했거나 잔여 한도만큼만 허용됩니다.",
            detail="`max_daily_order_amount` 설정을 확인하세요.",
        )

    if "negative news sentiment" in lower:
        score = _num(r"score=([-\d.]+)", text)
        return BuySkipExplanation(
            category="뉴스 센티먼트",
            summary=f"뉴스 감성 점수 {score or '?'}가 임계값보다 낮습니다.",
            detail="외부 뉴스 감성 필터가 켜져 있을 때 적용됩니다.",
        )

    if "earnings filter" in lower:
        return BuySkipExplanation(
            category="실적 발표",
            summary="실적 발표 전후 윈도우(earnings window)에 해당합니다.",
            detail="변동성·서프라이즈 리스크를 피하기 위해 일시적으로 매수를 막습니다.",
        )

    if "macro event risk" in lower:
        return BuySkipExplanation(
            category="매크로 리스크",
            summary="매크로 이벤트 리스크 구간으로 신규 매수가 차단되었습니다.",
            detail=text,
        )

    if "price data not loaded" in lower or "insufficient data" in lower:
        return BuySkipExplanation(
            category="데이터 부족",
            summary="가격/지표 데이터가 부족해 신호·AI 점수를 계산하지 못했습니다.",
            detail="raw CSV freshness, NaN bar, 상장 초기 등으로 lookback이 부족할 수 있습니다.",
        )

    if "buy allowed" in lower and "rank ai gate passed" not in lower:
        return BuySkipExplanation(
            category="매수 허용",
            summary="기본 리스크 검사는 통과했습니다.",
            detail="이후 LLM·Rank·슬리브·노출 한도 등 추가 가드 결과를 확인하세요.",
        )

    if "buy allowed" in lower:
        return BuySkipExplanation(
            category="매수 허용",
            summary="매수 조건을 통과했습니다.",
            detail=text,
        )

    return BuySkipExplanation(
        category="기타",
        summary=text[:120] + ("…" if len(text) > 120 else ""),
        detail=f"원문: {raw}",
        action_hint="원본 reason(영문) 전체는 '원본사유' 컬럼을 참고하세요.",
    )


def explain_execution_label(label: str) -> str:
    mapping = {
        "WOULD_SUBMIT_IF_EXECUTED": "execute 시 주문 제출 가능",
        "NOT_ALLOWED": "가드 미통과 — 매수 불가",
        "SESSION_CLOSED": "거래 세션 닫힘 — 주문 불가",
        "SKIP_MAX_ORDERS": "run당 최대 주문 수 초과",
        "SKIP_RANK_TOP_K": "rank 상위 K 밖",
        "SKIP_DAILY_LIMIT": "일일 매수 금액 한도",
        "SKIP_COOLDOWN": "재매수 쿨다운",
    }
    key = str(label or "").strip()
    return mapping.get(key, key or "—")
