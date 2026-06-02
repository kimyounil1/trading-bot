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
    assert "No BUY_SUBMITTED rows with parsed LLM ACCEPT/REJECT verdicts." in report["notes"][0]
