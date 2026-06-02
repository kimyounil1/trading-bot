import pandas as pd

from src.rank_gate_forward_return import build_rank_gate_forward_return_report


def _mock_settings(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        "src.rank_gate_forward_return.load_settings",
        lambda: SimpleNamespace(
            rank_ai_buy_gate_enabled=True,
            rank_ai_buy_gate_min_score_quantile=0.85,
        ),
    )


def test_rank_gate_forward_return_basic(tmp_path, monkeypatch):
    _mock_settings(monkeypatch)
    audit_path = tmp_path / "execution_audit.csv"
    audit_path.write_text(
        "timestamp,event_type,ticker,action,status,reason,rank_ai_percentile\n"
        "2026-05-01T10:00:00Z,SKIP_BUY,AAA,BUY,SKIPPED,rank ai gate blocked (pct=0.70),0.70\n"
        "2026-05-01T10:05:00Z,BUY_SUBMITTED,BBB,BUY,accepted,rank ai gate passed (pct=0.90),0.90\n",
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
        "src.rank_gate_forward_return.load_price_data_batch",
        lambda tickers, period, force_refresh=False: {"AAA": aaa, "BBB": bbb},
    )

    report = build_rank_gate_forward_return_report(
        audit_path=audit_path,
        lookback_days=365,
        horizon_days=20,
        price_period="2y",
    )
    assert report["events_used"]["blocked"] == 1
    assert report["events_used"]["passed"] == 1
    assert report["forward_return"]["blocked"]["mean_return"] < 0
    assert report["forward_return"]["passed"]["mean_return"] > 0
    assert report["forward_return"]["delta_mean_passed_minus_blocked"] > 0


def test_rank_gate_forward_return_insufficient_forward_bars(tmp_path, monkeypatch):
    _mock_settings(monkeypatch)
    audit_path = tmp_path / "execution_audit.csv"
    audit_path.write_text(
        "timestamp,event_type,ticker,action,status,reason,rank_ai_percentile\n"
        "2026-05-01T10:00:00Z,SKIP_BUY,AAA,BUY,SKIPPED,rank ai gate blocked,0.70\n",
        encoding="utf-8",
    )
    short = pd.DataFrame(
        {
            "date": pd.date_range("2026-05-01", periods=5, freq="D"),
            "adj_close": [100, 101, 102, 103, 104],
        }
    )
    monkeypatch.setattr(
        "src.rank_gate_forward_return.load_price_data_batch",
        lambda tickers, period, force_refresh=False: {"AAA": short},
    )

    report = build_rank_gate_forward_return_report(
        audit_path=audit_path,
        lookback_days=365,
        horizon_days=20,
    )
    assert report["events_used"]["blocked"] == 0
    assert report["excluded_rows"]["insufficient_forward_bars"] == 1
