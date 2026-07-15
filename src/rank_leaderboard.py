"""Rank AI cross-sectional leaderboard for CMS and dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.rank_ai_gate import RankAIGateScore, build_rank_ai_gate_scores, rank_ai_gate_effective_cutoff

LATEST_RANK_PATH = Path("logs/candidate_cache/latest_rank.csv")


def build_rank_leaderboard_frame(
    scores: dict[str, RankAIGateScore],
    *,
    open_symbols: set[str] | None = None,
    buy_df: pd.DataFrame | None = None,
    settings: Any | None = None,
) -> pd.DataFrame:
    """Full-universe rank table sorted by cross-sectional percentile."""
    held = {str(symbol).upper() for symbol in (open_symbols or set())}
    buy_lookup: dict[str, dict[str, Any]] = {}
    if buy_df is not None and not buy_df.empty and "ticker" in buy_df.columns:
        for _, row in buy_df.iterrows():
            buy_lookup[str(row["ticker"]).upper()] = row.to_dict()

    rows: list[dict[str, Any]] = []
    for ticker, gate_score in scores.items():
        symbol = str(ticker).upper()
        buy = buy_lookup.get(symbol, {})
        rows.append(
            {
                "ticker": symbol,
                "rank_ai_score": round(float(gate_score.score), 4),
                "rank_ai_percentile": round(float(gate_score.percentile), 4),
                "rank_gate_pass": bool(gate_score.allowed),
                "is_held": symbol in held,
                "signal": buy.get("signal"),
                "risk_allowed": buy.get("risk_allowed"),
                "would_submit_if_execute": buy.get("would_submit_if_execute"),
                "execution_label": buy.get("execution_label"),
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "rank",
                "ticker",
                "rank_ai_score",
                "rank_ai_percentile",
                "rank_gate_pass",
                "is_held",
            ]
        )

    frame = pd.DataFrame(rows)
    frame = frame.sort_values(
        ["rank_ai_percentile", "rank_ai_score", "ticker"],
        ascending=[False, False, True],
    )
    frame.insert(0, "rank", range(1, len(frame) + 1))
    if settings is not None:
        frame["rank_cutoff"] = rank_ai_gate_effective_cutoff(settings)
    return frame.reset_index(drop=True)


def format_rank_leaderboard_for_display(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()

    def _status(row: pd.Series) -> str:
        if bool(row.get("is_held")):
            return "보유"
        if bool(row.get("would_submit_if_execute")):
            return "매수후보"
        if bool(row.get("rank_gate_pass")):
            signal = str(row.get("signal") or "").upper()
            if signal == "BUY" and row.get("risk_allowed") is False:
                return "차단"
            if signal == "BUY":
                return "PASS"
            return "PASS·시그널없음"
        return "cutoff미달"

    out["상태"] = out.apply(_status, axis=1)
    rename = {
        "rank": "순위",
        "ticker": "종목",
        "rank_ai_score": "Rank점수",
        "rank_ai_percentile": "Rank백분위",
        "rank_gate_pass": "Gate통과",
        "is_held": "보유중",
        "signal": "시그널",
        "ai_score": "AI점수",
    }
    out = out.rename(columns={k: v for k, v in rename.items() if k in out.columns})
    display_cols = [
        c
        for c in [
            "순위",
            "종목",
            "Rank백분위",
            "Rank점수",
            "상태",
            "시그널",
            "AI점수",
            "보유중",
            "Gate통과",
        ]
        if c in out.columns
    ]
    return out[display_cols]


def build_rank_leaderboard_live(settings: Any, positions: list[dict[str, Any]] | None = None) -> pd.DataFrame:
    """Score the configured universe without running the full candidate-cache pipeline."""
    from src.candidate_cache import _load_cache_ticker_data
    from src.macro_loader import load_macro_data

    open_symbols = {
        str(position.get("symbol", "")).upper()
        for position in (positions or [])
        if position.get("symbol")
    }
    tickers = list(settings.tickers)
    ticker_data = _load_cache_ticker_data(tickers, settings)
    vix_df = ticker_data.get("^VIX")
    if vix_df is None or vix_df.empty:
        vix_df = ticker_data.get("VIX")
    spy_df = ticker_data.get("SPY")
    macro_df = (
        load_macro_data(period="2y") if getattr(settings, "use_ai_score", False) else None
    )
    scores = build_rank_ai_gate_scores(
        ticker_data,
        settings,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    return build_rank_leaderboard_frame(
        scores,
        open_symbols=open_symbols,
        settings=settings,
    )


def load_latest_rank_leaderboard() -> tuple[dict[str, Any], pd.DataFrame]:
    from src.candidate_cache import LATEST_META_PATH, _read_csv_or_empty, load_latest_candidate_cache

    meta, _, _ = load_latest_candidate_cache()
    rank_df = _read_csv_or_empty(LATEST_RANK_PATH)
    if rank_df.empty and LATEST_META_PATH.exists():
        raise FileNotFoundError(
            "Rank leaderboard cache missing. Run python -m src.generate_candidate_cache"
        )
    return meta, rank_df
