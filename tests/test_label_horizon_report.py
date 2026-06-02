from __future__ import annotations

import pandas as pd

from src.label_horizon_report import build_label_horizon_report


def _price_frame(rows: int = 340) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=rows, freq="B")
    close = pd.Series([100 + i * 0.1 for i in range(rows)], dtype=float)
    return pd.DataFrame(
        {
            "date": dates,
            "open": close * 0.99,
            "high": close * 1.01,
            "low": close * 0.98,
            "close": close,
            "volume": 1_000_000,
            "adj_close": close,
        }
    )


def test_label_horizon_report_scores_grid():
    report = build_label_horizon_report(
        {"AAA": _price_frame(), "BBB": _price_frame()},
        horizons=(5, 20),
        thresholds=(0.0, 0.02),
    )

    assert report["status"] == "ok"
    assert report["best_candidate"] is not None
    assert len(report["candidates"]) == 4
    assert "horizon" in report["best_candidate"]


def test_label_horizon_report_missing_data():
    report = build_label_horizon_report({}, horizons=(5,), thresholds=(0.0,))
    assert report["status"] == "missing_data"
    assert report["candidates"] == []
