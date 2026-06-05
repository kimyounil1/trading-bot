from src.brokers import broker_account_snapshot
from src.settings import load_settings


def main() -> None:
    settings = load_settings()
    account, _ = broker_account_snapshot(settings.broker_provider)

    print(f"Broker ({settings.broker_provider}) account connected.")
    print(f"status={account['status']}")
    print(f"currency={account['currency']}")
    print(f"cash={account['cash']:.2f}")
    print(f"portfolio_value={account['portfolio_value']:.2f}")
    print(f"buying_power={account['buying_power']:.2f}")
    print(f"positions_count={account['positions_count']}")


if __name__ == "__main__":
    main()
