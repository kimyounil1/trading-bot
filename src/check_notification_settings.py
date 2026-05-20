from src.notification_settings import load_notification_config


def main() -> None:
    config = load_notification_config()

    print("Notification settings")
    print("-" * 80)

    for key, value in config.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
