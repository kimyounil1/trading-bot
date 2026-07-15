import pytest

from src.alpaca_client import (
    _safe_order_qty,
    safe_full_close_qty_or_none,
    safe_order_qty_or_none,
)


def test_safe_order_qty_or_none_dust():
    assert safe_order_qty_or_none(0.0000004) is None


def test_safe_order_qty_or_none_normal():
    assert safe_order_qty_or_none(1.23456789) == pytest.approx(1.234567)


def test_safe_order_qty_raises_on_dust():
    with pytest.raises(ValueError, match="positive after truncation"):
        _safe_order_qty(0.0000001)


def test_full_close_qty_preserves_nine_decimal_position_precision():
    assert safe_full_close_qty_or_none(0.000000497) == pytest.approx(0.000000497)
    assert safe_full_close_qty_or_none(15.8465388) == pytest.approx(15.8465388)
