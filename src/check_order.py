import sys

from src.alpaca_client import get_order_summary, get_positions_summary


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m src.check_order <order_id>")
        raise SystemExit(1)

    order_id = sys.argv[1]
    order = get_order_summary(order_id)

    print("Order summary")
    print("-" * 80)
    for key, value in order.items():
        print(f"{key}={value}")

    print()
    print("Current positions")
    print("-" * 80)
    positions = get_positions_summary()

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
