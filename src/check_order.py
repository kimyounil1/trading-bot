import sys

from src.broker_adapter import get_broker_adapter
from src.settings import load_settings


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m src.check_order <order_id>")
        raise SystemExit(1)

    order_id = sys.argv[1]
    settings = load_settings()
    broker = get_broker_adapter(settings.broker_provider)
    order = broker.get_order_status(order_id)

    print("Order summary")
    print("-" * 80)
    for key, value in order.items():
        print(f"{key}={value}")

    print()
    print("Current positions")
    print("-" * 80)
    positions = broker.get_positions()

    if not positions:
        print("No open positions.")
        return

    for position in positions:
        print(
            f"{position['symbol']}: "
            f"qty={position['qty']}, "
            f"market_value={position['market_value']:.2f}, "
            f"cost_basis={position['cost_basis']:.2f}, "
            f"unrealized_pl={position['unrealized_pl']:.2f}, "
            f"unrealized_plpc={position['unrealized_plpc']:.4f}"
        )


if __name__ == "__main__":
    main()
