from src.alpaca_client import get_account_summary


def main() -> None:
    account = get_account_summary()

    print("Alpaca paper account connected.")
    print(f"status={account['status']}")
    print(f"currency={account['currency']}")
    print(f"cash={account['cash']:.2f}")
    print(f"portfolio_value={account['portfolio_value']:.2f}")
    print(f"buying_power={account['buying_power']:.2f}")
    print(f"positions_count={account['positions_count']}")


if __name__ == "__main__":
    main()
