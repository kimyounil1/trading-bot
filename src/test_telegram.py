from src.notifier import notify_info, telegram_is_configured


def main() -> None:
    print(f"telegram_is_configured={telegram_is_configured()}")

    ok = notify_info(
        title="Telegram Test",
        body="Trading bot Telegram notification is working.",
    )

    print(f"sent={ok}")


if __name__ == "__main__":
    main()
