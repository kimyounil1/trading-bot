import sys

from src.alpaca_client import close_position_by_symbol, get_positions_summary


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m src.close_position <ticker>")
        raise SystemExit(1)

    ticker = sys.argv[1].upper()

    positions = get_positions_summary()
    open_symbols = {position["symbol"] for position in positions}

    if ticker not in open_symbols:
        print(f"No open position for {ticker}.")
        return

    order = close_position_by_symbol(ticker)

    print(f"Close order submitted for {ticker}.")
    print(f"order_id={order.id}")
    print(f"symbol={order.symbol}")
    print(f"side={order.side}")
    print(f"type={order.type}")
    print(f"status={order.status}")


if __name__ == "__main__":
    main()
