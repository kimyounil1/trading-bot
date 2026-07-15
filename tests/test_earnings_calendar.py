import pandas as pd

from src import earnings


def test_datetime_index_calendar_is_normalized(monkeypatch, tmp_path) -> None:
    class FakeTicker:
        calendar = {
            "Earnings Date": pd.DatetimeIndex(
                ["2026-08-01 16:00:00+00:00", "2026-08-02 16:00:00+00:00"]
            )
        }
        earnings_dates = pd.DataFrame()

    monkeypatch.setattr(earnings, "EARNINGS_CACHE_DIR", tmp_path)
    monkeypatch.setattr(earnings.yf, "Ticker", lambda _: FakeTicker())

    result = earnings.get_next_earnings_date("SKHYV", cache_ttl_hours=0)

    assert result == pd.Timestamp("2026-08-01 16:00:00")
    assert result.tzinfo is None
