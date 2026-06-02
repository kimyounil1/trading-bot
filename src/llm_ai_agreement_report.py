"""Compare ensemble AI score pass/fail vs LLM consensus (llm_cache + execution_audit)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import EXECUTION_AUDIT_LOG_PATH
from src.daily_audit_summary import load_execution_audit
from src.settings import load_settings

DEFAULT_LLM_CACHE = Path("data/llm_cache.json")
DEFAULT_OUTPUT_DIR = Path("logs/llm_ai_comparison")
DEFAULT_CANDIDATE_BUY = Path("logs/candidate_cache/latest_buy.csv")

_VERDICT_RE = re.compile(r"^(ACCEPT|REJECT):\s*", re.IGNORECASE)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_llm_side(raw: str) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    match = _VERDICT_RE.match(text)
    return match.group(1).upper() if match else None


def _load_llm_cache(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _ai_scores_from_audit(audit_df: pd.DataFrame) -> pd.DataFrame:
    if audit_df.empty:
        return pd.DataFrame(columns=["ticker", "date", "ai_score"])
    df = audit_df.copy()
    df["ai_score"] = pd.to_numeric(df.get("ai_score"), errors="coerce")
    df = df[df["ai_score"].notna()]
    if df.empty:
        return pd.DataFrame(columns=["ticker", "date", "ai_score"])
    df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df["date"] = df["ts"].dt.strftime("%Y-%m-%d")
    df["ticker"] = df["ticker"].astype(str).str.upper()
    return (
        df.groupby(["ticker", "date"], as_index=False)["ai_score"]
        .max()
        .rename(columns={"ai_score": "ai_score"})
    )


def _cache_comparison_rows(
    cache: dict[str, Any],
    ai_by_ticker_date: pd.DataFrame,
    threshold: float,
) -> list[dict[str, Any]]:
    ai_lookup: dict[tuple[str, str], float] = {}
    for row in ai_by_ticker_date.itertuples(index=False):
        ai_lookup[(str(row.ticker).upper(), str(row.date))] = float(row.ai_score)

    rows: list[dict[str, Any]] = []
    for key, entry in cache.items():
        if "_" not in key:
            continue
        ticker, date = key.rsplit("_", 1)
        ticker = ticker.upper()
        llm_ok = bool(entry.get("is_approved"))
        ai_score = ai_lookup.get((ticker, date))
        ai_ok = None if ai_score is None else ai_score >= threshold
        agree = None if ai_ok is None else ai_ok == llm_ok
        rows.append(
            {
                "ticker": ticker,
                "date": date,
                "ai_score": ai_score,
                "ai_ok": ai_ok,
                "llm_ok": llm_ok,
                "agree": agree,
                "llm_category": str(entry.get("category") or "")[:200],
            }
        )
    return rows


def _confusion_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "both_pass": 0,
        "both_fail": 0,
        "ai_pass_llm_reject": 0,
        "ai_fail_llm_pass": 0,
    }
    for row in rows:
        if row.get("ai_ok") is None:
            continue
        ai_ok = bool(row["ai_ok"])
        llm_ok = bool(row["llm_ok"])
        if ai_ok and llm_ok:
            counts["both_pass"] += 1
        elif not ai_ok and not llm_ok:
            counts["both_fail"] += 1
        elif ai_ok and not llm_ok:
            counts["ai_pass_llm_reject"] += 1
        else:
            counts["ai_fail_llm_pass"] += 1
    return counts


def _candidate_buy_snapshot(
    buy_path: Path,
    cache: dict[str, Any],
    threshold: float,
    as_of_date: str,
) -> dict[str, Any]:
    if not buy_path.is_file():
        return {"path": str(buy_path), "rows": 0, "notes": ["latest_buy.csv missing"]}
    buy = pd.read_csv(buy_path)
    buy["ticker"] = buy["ticker"].astype(str).str.upper()
    buy["ai_score"] = pd.to_numeric(buy.get("ai_score"), errors="coerce")
    signals = buy[buy["signal"].astype(str) == "BUY"].copy()
    rows: list[dict[str, Any]] = []
    for _, r in signals.iterrows():
        ticker = str(r["ticker"]).upper()
        ai_score = r["ai_score"]
        ai_ok = bool(pd.notna(ai_score) and float(ai_score) >= threshold)
        ent = cache.get(f"{ticker}_{as_of_date}")
        if not ent:
            rows.append({"ticker": ticker, "ai_score": ai_score, "ai_ok": ai_ok, "in_llm_cache": False})
            continue
        llm_ok = bool(ent.get("is_approved"))
        rows.append(
            {
                "ticker": ticker,
                "ai_score": float(ai_score) if pd.notna(ai_score) else None,
                "ai_ok": ai_ok,
                "llm_ok": llm_ok,
                "agree": ai_ok == llm_ok,
                "in_llm_cache": True,
            }
        )
    comparable = [r for r in rows if r.get("in_llm_cache")]
    agree_n = sum(1 for r in comparable if r.get("agree"))
    return {
        "path": str(buy_path),
        "as_of_date": as_of_date,
        "buy_signal_rows": int(len(signals)),
        "in_llm_cache": int(len(comparable)),
        "agreement_rate": (agree_n / len(comparable)) if comparable else None,
        "confusion": _confusion_counts(comparable),
        "disagreements": [r for r in comparable if not r.get("agree")][:15],
    }


def build_llm_ai_agreement_report(
    llm_cache_path: str | Path = DEFAULT_LLM_CACHE,
    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
    candidate_buy_path: str | Path = DEFAULT_CANDIDATE_BUY,
    lookback_days: int = 90,
    ai_threshold: float | None = None,
) -> dict[str, Any]:
    settings = load_settings()
    threshold = (
        float(ai_threshold)
        if ai_threshold is not None
        else float(settings.ai_score_buy_threshold)
    )

    cache_path = Path(llm_cache_path)
    cache = _load_llm_cache(cache_path)
    audit_df = (
        load_execution_audit(Path(audit_path), lookback_days=lookback_days)
        if Path(audit_path).is_file()
        else pd.DataFrame()
    )
    ai_by_date = _ai_scores_from_audit(audit_df)
    cache_rows = _cache_comparison_rows(cache, ai_by_date, threshold)
    comparable = [r for r in cache_rows if r.get("ai_ok") is not None]
    agree_n = sum(1 for r in comparable if r.get("agree"))
    confusion = _confusion_counts(comparable)

    # LLM_ADVISORY rows are biased (logged when LLM would reject in advisory-only mode).
    advisory_note = (
        "LLM_ADVISORY event_type is not used for agreement rate — it only logs "
        "WOULD_REJECT when AI passed; use llm_cache comparison instead."
    )
    advisory_rows: list[dict[str, Any]] = []
    if not audit_df.empty and "event_type" in audit_df.columns:
        adv = audit_df[audit_df["event_type"].astype(str) == "LLM_ADVISORY"].copy()
        adv["ai_score"] = pd.to_numeric(adv.get("ai_score"), errors="coerce")
        adv["llm_side"] = adv.get("llm_verdict", pd.Series(dtype=str)).map(_parse_llm_side)
        for _, r in adv.iterrows():
            side = r.get("llm_side")
            if side not in ("ACCEPT", "REJECT") or pd.isna(r.get("ai_score")):
                continue
            ai_ok = float(r["ai_score"]) >= threshold
            llm_ok = side == "ACCEPT"
            advisory_rows.append(
                {
                    "ticker": str(r.get("ticker", "")).upper(),
                    "ai_score": float(r["ai_score"]),
                    "ai_ok": ai_ok,
                    "llm_ok": llm_ok,
                    "agree": ai_ok == llm_ok,
                }
            )

    as_of_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    disagreements = [r for r in comparable if not r.get("agree")]
    disagreements.sort(
        key=lambda r: (abs((r.get("ai_score") or 0) - threshold), r.get("ticker", "")),
        reverse=True,
    )

    scores = [float(r["ai_score"]) for r in comparable if r.get("ai_score") is not None]
    llm_binary = [1.0 if r["llm_ok"] else 0.0 for r in comparable]
    score_corr = None
    if len(scores) >= 3:
        score_corr = float(pd.Series(scores).corr(pd.Series(llm_binary)))

    return {
        "generated_at": _utc_now_iso(),
        "ai_score_buy_threshold": threshold,
        "llm_cache_path": str(cache_path),
        "llm_cache_entries": len(cache),
        "comparable_with_ai_score": len(comparable),
        "agreement_rate": (agree_n / len(comparable)) if comparable else None,
        "agreement_pct": round(100 * agree_n / len(comparable), 1) if comparable else None,
        "score_llm_corr": score_corr,
        "confusion": confusion,
        "disagreements_sample": disagreements[:20],
        "llm_advisory_audit_rows": len(advisory_rows),
        "llm_advisory_agreement_rate": (
            sum(1 for r in advisory_rows if r["agree"]) / len(advisory_rows)
            if advisory_rows
            else None
        ),
        "notes": [advisory_note],
        "candidate_buy": _candidate_buy_snapshot(
            Path(candidate_buy_path), cache, threshold, as_of_date
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM vs AI score agreement report")
    parser.add_argument("--llm-cache", default=str(DEFAULT_LLM_CACHE))
    parser.add_argument("--audit-path", default=EXECUTION_AUDIT_LOG_PATH)
    parser.add_argument("--candidate-buy", default=str(DEFAULT_CANDIDATE_BUY))
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--ai-threshold", type=float, default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    report = build_llm_ai_agreement_report(
        llm_cache_path=args.llm_cache,
        audit_path=args.audit_path,
        candidate_buy_path=args.candidate_buy,
        lookback_days=args.lookback_days,
        ai_threshold=args.ai_threshold,
    )
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "latest_summary.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== LLM vs AI score agreement ===")
    print(f"Threshold: {report['ai_score_buy_threshold']}")
    print(f"LLM cache comparable: {report['comparable_with_ai_score']}")
    print(f"Agreement: {report.get('agreement_pct')}%")
    c = report["confusion"]
    print(
        f"  both pass={c['both_pass']} both fail={c['both_fail']} "
        f"ai+ llm-={c['ai_pass_llm_reject']} ai- llm+={c['ai_fail_llm_pass']}"
    )
    if report.get("score_llm_corr") is not None:
        print(f"  ai_score vs llm_approve corr: {report['score_llm_corr']:.3f}")
    cb = report.get("candidate_buy", {})
    if cb.get("in_llm_cache"):
        print(
            f"Today's BUY candidates in cache: {cb['in_llm_cache']}, "
            f"agree {round(100 * (cb.get('agreement_rate') or 0), 1)}%"
        )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
