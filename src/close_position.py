import sys

from src.broker_adapter import get_broker_adapter
from src.market_clock import get_market_clock
from src.settings import load_settings


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m src.close_position <ticker>")
        raise SystemExit(1)

    ticker = sys.argv[1].upper()
    settings = load_settings()
    broker = get_broker_adapter(settings.broker_provider)
    positions = broker.get_positions()
    position = next(
        (p for p in positions if str(p["symbol"]).upper() == ticker),
        None,
    )
    if position is None:
        print(f"No open position for {ticker}.")
        return

    clock = get_market_clock(settings)
    submission = broker.submit_sell_qty(
        ticker,
        float(position["qty"]),
        limit_price=float(position.get("current_price") or 0.0),
        market_clock=clock,
        slippage_pct=float(getattr(settings, "extended_hours_limit_slippage_pct", 0.005)),
        client_order_id=f"cli_close_{ticker}",
    )

    print(f"Close order submitted for {ticker}.")
    print(f"order_id={submission.order_id}")
    print(f"side={submission.side}")
    print(f"type={submission.order_type}")
    print(f"status={submission.status}")


if __name__ == "__main__":
    main()
