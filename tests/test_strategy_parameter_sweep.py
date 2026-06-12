from src.strategy_parameter_sweep import _passes_oos_gate


def test_passes_oos_gate_requires_baseline_plus_half_pp():
    metrics = {
        "gap_pp": 2.0,
        "sharpe_ratio": 1.2,
        "max_drawdown_pct": -12.0,
    }
    assert _passes_oos_gate(metrics, baseline_gap_pp=1.0) is True
    assert _passes_oos_gate(metrics, baseline_gap_pp=1.8) is False


def test_passes_oos_gate_requires_min_sharpe():
    metrics = {
        "gap_pp": 5.0,
        "sharpe_ratio": 0.8,
        "max_drawdown_pct": -10.0,
    }
    assert _passes_oos_gate(metrics, baseline_gap_pp=0.0) is False
