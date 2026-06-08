import unittest

from src.order_intent import build_buy_intent, sleeve_audit_fields


class OrderIntentSleevesTest(unittest.TestCase):
    def test_build_buy_intent_carries_sleeve_fields(self) -> None:
        intent = build_buy_intent(
            run_id="run1",
            ticker="nvda",
            notional=100.0,
            sleeve_id="core",
            sleeve_strategy="current_core",
            sleeve_target_weight=0.5,
            sleeve_budget_before=5000.0,
            sleeve_budget_after=4900.0,
            sleeve_risk_mode="normal",
        )
        self.assertEqual(intent.sleeve_id, "core")
        self.assertEqual(intent.sleeve_strategy, "current_core")
        self.assertEqual(intent.sleeve_target_weight, 0.5)
        self.assertEqual(intent.sleeve_budget_before, 5000.0)
        self.assertEqual(intent.sleeve_budget_after, 4900.0)
        self.assertEqual(intent.sleeve_risk_mode, "normal")

    def test_sleeve_audit_fields_from_intent(self) -> None:
        intent = build_buy_intent(
            run_id="run1",
            ticker="amd",
            notional=50.0,
            sleeve_id="tournament",
            sleeve_strategy="alpha_tournament",
            sleeve_risk_mode="paper_only",
        )
        fields = sleeve_audit_fields(intent=intent)
        self.assertEqual(fields["sleeve_id"], "tournament")
        self.assertEqual(fields["sleeve_risk_mode"], "paper_only")


if __name__ == "__main__":
    unittest.main()
