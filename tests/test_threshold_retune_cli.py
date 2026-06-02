import json
from pathlib import Path

from src import threshold_retune_cli as cli


def test_run_threshold_retune_writes_report(monkeypatch, tmp_path):
    fake_report = {
        "best_buy_threshold": 0.62,
        "best_exit_threshold": 0.38,
        "rows_evaluated": 12,
    }

    def fake_retune(**kwargs):
        return fake_report, None

    def fake_write(report, results_df):
        out = tmp_path / "threshold_retune_report.json"
        out.write_text(json.dumps(report), encoding="utf-8")

    monkeypatch.setattr(cli, "load_settings", lambda: type("S", (), {"tickers": ["SPY"]})())
    import pandas as pd

    rows = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=300), "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0})
    monkeypatch.setattr(cli, "load_price_data_batch", lambda *a, **k: {"AAPL": rows, "^VIX": rows, "SPY": rows})
    monkeypatch.setattr(cli, "_filter_usable_ticker_data", lambda data, settings: data)
    monkeypatch.setattr(cli, "load_macro_data", lambda **k: None)
    monkeypatch.setattr(cli, "_run_threshold_retune", fake_retune)
    monkeypatch.setattr(cli, "_write_threshold_retune_report", fake_write)

    report = cli.run_threshold_retune(period="5y")
    assert report["best_buy_threshold"] == 0.62
    assert (tmp_path / "threshold_retune_report.json").is_file()
