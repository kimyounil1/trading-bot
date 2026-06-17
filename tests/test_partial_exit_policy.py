import unittest
from types import SimpleNamespace

from src.partial_exit_policy import (
    compute_partial_exit_thresholds,
    evaluate_partial_exit,
    load_partial_exit_state,
    normalize_partial_exit_state,
    save_partial_exit_state,
    sync_partial_exit_state,
)
from src.partial_exit_policy import PARTIAL_EXIT_STATE_PATH


class PartialExitPolicyTest(unittest.TestCase):
    def _settings(self, **overrides):
        base = {
            "max_position_pct": 0.15,
            "partial_exit_ratio": 0.5,
        }
        base.update(overrides)
        return SimpleNamespace(**base)

    def test_thresholds_scale_with_portfolio_and_max_position_pct(self) -> None:
        small = compute_partial_exit_thresholds(
            portfolio_value=10_000.0,
            settings=self._settings(max_position_pct=0.15),
            dust_min_usd=5.0,
        )
        large = compute_partial_exit_thresholds(
            portfolio_value=100_000.0,
            settings=self._settings(max_position_pct=0.15),
            dust_min_usd=5.0,
        )

        self.assertAlmostEqual(small.target_slot_notional, 1_500.0)
        self.assertAlmostEqual(large.target_slot_notional, 15_000.0)
        self.assertGreater(large.min_position_market_value, small.min_position_market_value)
        self.assertGreater(large.min_sell_notional, small.min_sell_notional)

    def test_small_asml_like_position_is_skipped(self) -> None:
        thresholds = compute_partial_exit_thresholds(
            portfolio_value=98_700.0,
            settings=self._settings(max_position_pct=0.15, partial_exit_ratio=0.5),
            dust_min_usd=5.0,
        )
        allowed, reason = evaluate_partial_exit(
            position_market_value=460.0,
            sell_notional=230.0,
            thresholds=thresholds,
            already_taken=False,
        )
        self.assertFalse(allowed)
        self.assertIn("too small", reason)

    def test_full_slot_position_allows_partial_once(self) -> None:
        thresholds = compute_partial_exit_thresholds(
            portfolio_value=100_000.0,
            settings=self._settings(max_position_pct=0.15, partial_exit_ratio=0.5),
            dust_min_usd=5.0,
        )
        position_mv = 15_000.0
        sell_notional = 7_500.0

        allowed, reason = evaluate_partial_exit(
            position_market_value=position_mv,
            sell_notional=sell_notional,
            thresholds=thresholds,
            already_taken=False,
        )
        self.assertTrue(allowed)
        self.assertEqual(reason, "")

        allowed_again, reason_again = evaluate_partial_exit(
            position_market_value=position_mv * 0.5,
            sell_notional=sell_notional * 0.5,
            thresholds=thresholds,
            already_taken=True,
        )
        self.assertFalse(allowed_again)
        self.assertIn("already taken", reason_again)

    def test_sync_clears_flags_for_closed_symbols(self) -> None:
        synced = sync_partial_exit_state(
            {"ASML": True, "AAPL": True},
            {"AAPL"},
        )
        self.assertEqual(synced, {"AAPL": True})

    def test_save_and_load_round_trip(self) -> None:
        with self.subTest("round trip"):
            original = PARTIAL_EXIT_STATE_PATH
            temp = original.with_suffix(".json.testtmp")
            try:
                import src.partial_exit_policy as module

                module.PARTIAL_EXIT_STATE_PATH = temp
                save_partial_exit_state({"asml": True, "gm": False})
                loaded = load_partial_exit_state(open_symbols={"ASML", "GM"})
                self.assertEqual(loaded, {"ASML": True})
            finally:
                module.PARTIAL_EXIT_STATE_PATH = original
                if temp.exists():
                    temp.unlink()

    def test_normalize_rejects_invalid_payload(self) -> None:
        with self.assertRaises(ValueError):
            normalize_partial_exit_state({"AAPL": "yes"})


if __name__ == "__main__":
    unittest.main()
