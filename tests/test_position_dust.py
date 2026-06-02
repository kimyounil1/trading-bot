from src.position_dust import (
    count_meaningful_positions,
    dust_position_min_usd,
    effective_position,
    is_dust_position,
)


def test_is_dust_position_below_threshold():
    pos = {"symbol": "GOOGL", "qty": 9.34e-7, "market_value": 0.000346}
    assert is_dust_position(pos, min_usd=5.0) is True


def test_is_dust_position_above_threshold():
    pos = {"symbol": "ABBV", "qty": 14.0, "market_value": 3045.0}
    assert is_dust_position(pos, min_usd=5.0) is False


def test_effective_position_returns_none_for_dust():
    pos = {"symbol": "NVDA", "qty": 4.56e-7, "market_value": 0.0001}
    assert effective_position(pos, min_usd=5.0) is None


def test_count_meaningful_positions_excludes_dust():
    positions = [
        {"symbol": "ABBV", "market_value": 3000.0},
        {"symbol": "GOOGL", "market_value": 0.0003},
        {"symbol": "MSFT", "market_value": 0.0003},
    ]
    assert count_meaningful_positions(positions, min_usd=5.0) == 1


def test_dust_position_min_usd_from_settings():
    class _Settings:
        dust_position_min_usd = 10.0

    assert dust_position_min_usd(_Settings()) == 10.0
