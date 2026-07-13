from __future__ import annotations

import numpy as np
import pandas as pd

from src.conditional_margin_leverage import resolve_conditional_margin_leverage
from src.margin_leverage_paper_gate import apply_margin_leverage_paper_overrides
from src.settings import StrategySettings


def _settings() -> StrategySettings:
    return StrategySettings(
        conditional_margin_leverage_enabled=True,
        conditional_margin_leverage_bull_factor=2.0,
        conditional_margin_leverage_defensive_factor=1.0,
        conditional_margin_leverage_vix_max=22.0,
        market_regime_ma_fast=50,
        market_regime_ma_slow=200,
        max_position_pct=0.15,
    )


def _frame(values: np.ndarray | list[float]) -> pd.DataFrame:
    return pd.DataFrame({"adj_close": values})


def test_conditional_margin_uses_2x_only_in_bull_low_vix() -> None:
    decision = resolve_conditional_margin_leverage(
        _settings(),
        spy_df=_frame(np.linspace(100.0, 220.0, 220)),
        vix_df=_frame([18.0] * 220),
    )

    assert decision.active is True
    assert decision.leverage_factor == 2.0


def test_conditional_margin_falls_back_to_1x_on_high_vix_or_missing_data() -> None:
    settings = _settings()
    high_vix = resolve_conditional_margin_leverage(
        settings,
        spy_df=_frame(np.linspace(100.0, 220.0, 220)),
        vix_df=_frame([23.0] * 220),
    )
    missing = resolve_conditional_margin_leverage(
        settings,
        spy_df=_frame([100.0] * 50),
        vix_df=None,
    )

    assert high_vix.leverage_factor == 1.0
    assert high_vix.active is False
    assert missing.leverage_factor == 1.0
    assert "fail-closed" in missing.reason


def test_paper_overrides_scale_position_and_gross_caps_with_effective_factor() -> None:
    settings = _settings()
    bull = apply_margin_leverage_paper_overrides(
        settings,
        effective_leverage_factor=2.0,
    )
    defensive = apply_margin_leverage_paper_overrides(
        settings,
        effective_leverage_factor=1.0,
    )

    assert bull.max_position_pct == 0.30
    assert bull.max_gross_exposure_pct == 2.0
    assert bull.max_effective_leverage_exposure_pct == 2.0
    assert defensive.max_position_pct == 0.15
    assert defensive.max_gross_exposure_pct == 1.0
