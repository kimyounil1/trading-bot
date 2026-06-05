import unittest

from src.order_intent import build_audit_context, build_buy_intent, config_hash
from src.settings import StrategySettings


class OrderIntentTest(unittest.TestCase):
    def test_build_buy_intent_has_id(self) -> None:
        intent = build_buy_intent(run_id="run1", ticker="AAPL", notional=100.0)
        self.assertTrue(intent.intent_id.startswith("intent_"))
        self.assertEqual(intent.side, "BUY")

    def test_config_hash_stable(self) -> None:
        settings = StrategySettings()
        h1 = config_hash(settings)
        h2 = config_hash(settings)
        self.assertEqual(h1, h2)

    def test_audit_context_fields(self) -> None:
        ctx = build_audit_context(
            run_id="run1",
            settings=StrategySettings(),
            environment="paper",
        )
        fields = ctx.as_audit_fields()
        self.assertEqual(fields["run_id"], "run1")
        self.assertEqual(fields["environment"], "paper")


if __name__ == "__main__":
    unittest.main()
