import unittest

import pandas as pd

from src.regime_stop_policy import (
    BEAR_ONLY_TIGHT_STOP_PROFILE,
    CONSERVATIVE_REGIME_STOP_PROFILE,
    classify_spy_regime,
    resolve_regime_stop_params,
    spy_return_lookback,
)


class RegimeStopPolicyTest(unittest.TestCase):
    def _spy_frame(self) -> pd.DataFrame:
        dates = pd.date_range("2026-01-01", periods=30, freq="B")
        closes = [100 + i * 0.5 for i in range(30)]
        return pd.DataFrame({"date": dates, "close": closes})

    def test_spy_return_lookback_positive(self) -> None:
        df = self._spy_frame()
        ret = spy_return_lookback(df, pd.Timestamp("2026-02-10"), 20)
        self.assertIsNotNone(ret)
        assert ret is not None
        self.assertGreater(ret, 0)

    def test_classify_bull(self) -> None:
        self.assertEqual(classify_spy_regime(0.05), "bull")

    def test_classify_stress(self) -> None:
        self.assertEqual(classify_spy_regime(-0.10), "stress")

    def test_resolve_regime_adaptive_bull(self) -> None:
        df = self._spy_frame()
        stop, trail, regime = resolve_regime_stop_params(
            df,
            pd.Timestamp("2026-02-10"),
            fallback_stop_loss_pct=0.05,
            fallback_trailing_stop_pct=0.20,
            enabled=True,
        )
        self.assertEqual(regime, "bull")
        self.assertAlmostEqual(stop, 0.07)
        self.assertAlmostEqual(trail, 0.18)

    def test_conservative_tighter_than_standard(self) -> None:
        stop_s, _, _ = resolve_regime_stop_params(
            self._spy_frame(),
            pd.Timestamp("2026-02-10"),
            fallback_stop_loss_pct=0.05,
            fallback_trailing_stop_pct=0.20,
            enabled=True,
            profile=CONSERVATIVE_REGIME_STOP_PROFILE,
        )
        stop_std, _, _ = resolve_regime_stop_params(
            self._spy_frame(),
            pd.Timestamp("2026-02-10"),
            fallback_stop_loss_pct=0.05,
            fallback_trailing_stop_pct=0.20,
            enabled=True,
        )
        self.assertLess(stop_s, stop_std)

    def test_bear_only_profile_negative_spy(self) -> None:
        stop, trail, regime = resolve_regime_stop_params(
            None,
            pd.Timestamp("2026-06-01"),
            fallback_stop_loss_pct=0.05,
            fallback_trailing_stop_pct=0.20,
            enabled=True,
            profile=BEAR_ONLY_TIGHT_STOP_PROFILE,
        )
        self.assertEqual(regime, "fixed")  # no spy df → fallback

    def test_bear_only_classify_at_zero(self) -> None:
        self.assertEqual(
            classify_spy_regime(0.0, bull_threshold=0.0, stress_threshold=-0.999),
            "bull",
        )
        self.assertEqual(
            classify_spy_regime(-0.01, bull_threshold=0.0, stress_threshold=-0.999),
            "bear",
        )


if __name__ == "__main__":
    unittest.main()
