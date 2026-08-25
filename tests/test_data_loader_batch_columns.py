import pandas as pd

from src.data_loader import _extract_ticker_from_batch, _normalize_price_frame


def test_extract_and_normalize_price_ticker_multiindex() -> None:
    index = pd.date_range("2026-01-02", periods=3, freq="D", name="Date")
    raw = pd.DataFrame(
        {
            ("Open", "AAA"): [10.0, 10.5, 11.0],
            ("High", "AAA"): [11.0, 11.5, 12.0],
            ("Low", "AAA"): [9.0, 10.0, 10.5],
            ("Close", "AAA"): [10.5, 11.0, 11.5],
            ("Volume", "AAA"): [1000.0, 1100.0, 1200.0],
        },
        index=index,
    )
    raw.columns = pd.MultiIndex.from_tuples(raw.columns)
    extracted = _extract_ticker_from_batch(raw, "AAA", 2)
    normalized = _normalize_price_frame("AAA", extracted)
    assert {"date", "open", "high", "low", "close", "volume"} <= set(normalized.columns)
    assert float(normalized["close"].iloc[-1]) == 11.5
    assert not normalized["close"].isna().any()


def test_extract_ticker_price_multiindex() -> None:
    index = pd.date_range("2026-01-02", periods=2, freq="D", name="Date")
    columns = pd.MultiIndex.from_product(
        [["AAA", "BBB"], ["Open", "High", "Low", "Close", "Volume"]]
    )
    downloaded = pd.DataFrame(
        [
            [1, 2, 0.5, 1.5, 10, 3, 4, 2, 3.5, 20],
            [1.5, 2.5, 1, 2, 11, 3.5, 4.5, 3, 4, 21],
        ],
        index=index,
        columns=columns,
    )
    extracted = _extract_ticker_from_batch(downloaded, "BBB", 2)
    normalized = _normalize_price_frame("BBB", extracted)
    assert float(normalized["close"].iloc[-1]) == 4.0
