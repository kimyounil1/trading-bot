import pytest

from src.alpaca_client import safe_order_qty_or_none, _safe_order_qty


def test_safe_order_qty_or_none_dust():
    assert safe_order_qty_or_none(0.0000004) is None


def test_safe_order_qty_or_none_normal():
    assert safe_order_qty_or_none(1.23456789) == pytest.approx(1.234567)


def test_safe_order_qty_raises_on_dust():
    with pytest.raises(ValueError, match="positive after truncation"):
        _safe_order_qty(0.0000001)
