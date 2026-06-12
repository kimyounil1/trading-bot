import pandas as pd

from src.llm_block_precision_report import build_llm_block_precision_report


def test_llm_block_precision_accept_vs_reject(tmp_path, monkeypatch):
    audit_path = tmp_path / "execution_audit.csv"
    audit_path.write_text(
        "timestamp,event_type,ticker,action,status,reason,llm_verdict\n"
        "2026-05-01T10:00:00Z,BUY_SUBMITTED,AAA,BUY,accepted,ok,REJECT: risk\n"
        "2026-05-01T10:05:00Z,BUY_SUBMITTED,BBB,BUY,accepted,ok,ACCEPT: clear\n",
        encoding="utf-8",
    )
    aaa = pd.DataFrame(
        {
            "date": pd.date_range("2026-05-01", periods=40, freq="D"),
            "adj_close": [100 - i for i in range(40)],
        }
    )
    bbb = pd.DataFrame(
        {
            "date": pd.date_range("2026-05-01", periods=40, freq="D"),
            "adj_close": [100 + i for i in range(40)],
        }
    )
    monkeypatch.setattr(
        "src.llm_block_precision_report.load_price_data_batch",
        lambda tickers, period, force_refresh=False: {"AAA": aaa, "BBB": bbb},
    )

    report = build_llm_block_precision_report(
        audit_path=audit_path,
        lookback_days=365,
        horizon_days=20,
        price_period="2y",
    )
    assert report["events_used"]["llm_reject"] == 1
    assert report["events_used"]["llm_accept"] == 1
    assert report["forward_return"]["llm_reject"]["mean_return"] < 0
    assert report["forward_return"]["llm_accept"]["mean_return"] > 0
    assert report["forward_return"]["delta_mean_accept_minus_reject"] > 0


def test_llm_block_precision_no_parsed_verdicts(tmp_path):
    audit_path = tmp_path / "execution_audit.csv"
    audit_path.write_text(
        "timestamp,event_type,ticker,action,status,reason,llm_verdict\n"
        "2026-05-01T10:00:00Z,BUY_SUBMITTED,AAA,BUY,accepted,ok,\n",
        encoding="utf-8",
    )
    report = build_llm_block_precision_report(
        audit_path=audit_path,
        lookback_days=365,
        horizon_days=20,
    )
    assert report["events_used"]["llm_reject"] == 0
    assert report["events_used"]["llm_accept"] == 0
    assert "No LLM decision rows" in report["notes"][0]


def test_llm_block_precision_counts_blocking_mode_events(tmp_path, monkeypatch):
    """LLM REJECTs in blocking mode appear as LLM_ADVISORY / SKIP_BUY, never BUY_SUBMITTED."""
    audit_path = tmp_path / "execution_audit.csv"
    audit_path.write_text(
        "timestamp,event_type,ticker,action,status,reason,llm_verdict\n"
        "2026-05-01T10:00:00Z,LLM_ADVISORY,AAA,BUY,WOULD_REJECT,advisory,REJECT: risk\n"
        "2026-05-01T10:05:00Z,SKIP_BUY,CCC,BUY,skipped,LLM Reject,REJECT: fraud\n"
        # Same ticker+date+side as above: deduped to one event.
        "2026-05-01T15:45:00Z,SKIP_BUY,CCC,BUY,skipped,LLM Reject,REJECT: fraud\n"
        "2026-05-01T10:10:00Z,BUY_SUBMITTED,BBB,BUY,accepted,ok,ACCEPT: clear\n"
        # Accepted by LLM but skipped for non-LLM reasons: still an ACCEPT decision.
        "2026-05-01T10:15:00Z,SKIP_BUY,DDD,BUY,skipped,budget,ACCEPT: clear\n",
        encoding="utf-8",
    )
    prices = {
        ticker: pd.DataFrame(
            {
                "date": pd.date_range("2026-05-01", periods=40, freq="D"),
                "adj_close": [100 + sign * i for i in range(40)],
            }
        )
        for ticker, sign in [("AAA", -1), ("CCC", -1), ("BBB", 1), ("DDD", 1)]
    }
    monkeypatch.setattr(
        "src.llm_block_precision_report.load_price_data_batch",
        lambda tickers, period, force_refresh=False: prices,
    )

    report = build_llm_block_precision_report(
        audit_path=audit_path,
        lookback_days=365,
        horizon_days=20,
    )
    assert report["events_used"]["llm_reject"] == 2
    assert report["events_used"]["llm_accept"] == 2
    assert report["events_by_type"] == {
        "LLM_ADVISORY": 1,
        "SKIP_BUY": 2,
        "BUY_SUBMITTED": 1,
    }
    assert report["forward_return"]["llm_reject"]["mean_return"] < 0
    assert report["forward_return"]["delta_mean_accept_minus_reject"] > 0
