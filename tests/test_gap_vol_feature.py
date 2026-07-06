"""gap_vol_20d feature column (research-only, not in production FEATURE_COLUMNS)."""

import numpy as np
import pandas as pd

from src.features import FEATURE_COLUMNS, FEATURE_COLUMNS_WITH_GAP_VOL, RANK_GAP_VOL_FEATURE, build_features


def _price_frame(rows: int = 280) -> pd.DataFrame:
    values = np.arange(rows, dtype=float)
    return pd.DataFrame(
        {
            "date": pd.date_range("2023-01-01", periods=rows),
            "open": values + 1.0,
            "high": values + 2.0,
            "low": values + 0.5,
            "close": values + 1.5,
            "volume": values + 100.0,
        }
    )


def test_gap_vol_feature_computed_and_not_in_production_columns():
    df = build_features(_price_frame(), prediction_horizon=5)
    assert RANK_GAP_VOL_FEATURE in df.columns
    assert RANK_GAP_VOL_FEATURE not in FEATURE_COLUMNS
    assert FEATURE_COLUMNS_WITH_GAP_VOL[-1] == RANK_GAP_VOL_FEATURE
    assert df[RANK_GAP_VOL_FEATURE].notna().any()
