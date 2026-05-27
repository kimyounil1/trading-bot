from __future__ import annotations

"""섹터 분류 및 포지션 집중도 체크."""

SECTOR_MAP: dict[str, str] = {
    # 빅테크
    "AAPL": "tech", "MSFT": "tech", "GOOGL": "tech", "AMZN": "tech", "META": "tech",
    # 반도체
    "NVDA": "semis", "AVGO": "semis", "AMD": "semis", "INTC": "semis", "QCOM": "semis",
    "TSM": "semis", "ASML": "semis", "ARM": "semis", "MU": "semis", "AMAT": "semis",
    "LRCX": "semis", "KLAC": "semis", "SNPS": "semis", "CDNS": "semis", "SMH": "semis",
    # 소프트웨어/클라우드
    "ANET": "software", "ORCL": "software", "CRM": "software", "ADBE": "software",
    "NOW": "software", "PLTR": "software", "PANW": "software", "CRWD": "software",
    "NET": "software", "DDOG": "software", "SNOW": "software", "MDB": "software",
    "XLK": "software",
    # 소비자 인터넷/플랫폼
    "NFLX": "consumer_tech", "SHOP": "consumer_tech", "UBER": "consumer_tech",
    "ABNB": "consumer_tech", "RBLX": "consumer_tech",
    # 미디어/통신
    "DIS": "media", "CMCSA": "media", "T": "telecom", "VZ": "telecom",
    # 금융
    "JPM": "financials", "BAC": "financials", "WFC": "financials", "C": "financials",
    "GS": "financials", "MS": "financials", "BLK": "financials", "SCHW": "financials",
    "AXP": "financials", "V": "financials", "MA": "financials", "PYPL": "financials",
    "COIN": "financials", "BRK-B": "financials", "XLF": "financials",
    # 헬스케어
    "UNH": "healthcare", "JNJ": "healthcare", "LLY": "healthcare", "MRK": "healthcare",
    "ABBV": "healthcare", "PFE": "healthcare", "TMO": "healthcare", "ISRG": "healthcare",
    "ABT": "healthcare", "MDT": "healthcare", "CVS": "healthcare", "XLV": "healthcare",
    # 소비재
    "COST": "consumer", "WMT": "consumer", "TGT": "consumer", "HD": "consumer",
    "LOW": "consumer", "MCD": "consumer", "SBUX": "consumer", "NKE": "consumer",
    "LULU": "consumer",
    # 자동차
    "TSLA": "auto", "F": "auto", "GM": "auto",
    # 산업재
    "CAT": "industrial", "DE": "industrial", "GE": "industrial", "HON": "industrial",
    # 방산/항공
    "BA": "defense", "LMT": "defense", "RTX": "defense",
    # 운송
    "UPS": "transport", "UNP": "transport",
    # 에너지
    "XOM": "energy", "CVX": "energy", "COP": "energy", "SLB": "energy", "XLE": "energy",
    # 소재
    "LIN": "materials", "FCX": "materials", "NEM": "materials", "APD": "materials",
    # 유틸리티
    "NEE": "utilities", "SO": "utilities", "DUK": "utilities",
    # 리츠
    "PLD": "realestate", "AMT": "realestate", "EQIX": "realestate",
    # 광의 ETF (분산된 것으로 간주)
    "SPY": "etf", "QQQ": "etf", "DIA": "etf", "IWM": "etf", "VTI": "etf",
}

DEFAULT_MAX_SECTOR_POSITIONS = 2


def get_sector(ticker: str) -> str:
    return SECTOR_MAP.get(ticker.upper(), "unknown")


def count_sector_positions(open_symbols: set[str], sector: str) -> int:
    """현재 보유 포지션 중 해당 섹터 종목 수를 반환한다."""
    return sum(
        1 for sym in open_symbols
        if get_sector(sym) == sector
    )


def is_sector_allowed(
    ticker: str,
    open_symbols: set[str],
    max_sector_positions: int = DEFAULT_MAX_SECTOR_POSITIONS,
) -> tuple[bool, str]:
    """매수 가능 여부와 이유를 반환한다.

    ETF는 섹터 제한에서 제외한다 (분산된 것으로 간주).
    'unknown' 섹터도 제한하지 않는다.
    """
    sector = get_sector(ticker)

    if sector in ("etf", "unknown"):
        return True, "sector check skipped"

    count = count_sector_positions(open_symbols, sector)
    if count >= max_sector_positions:
        return False, (
            f"sector concentration limit reached "
            f"(sector={sector}, current={count}, max={max_sector_positions})"
        )

    return True, f"sector={sector}, current={count}/{max_sector_positions}"
