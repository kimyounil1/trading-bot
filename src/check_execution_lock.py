from src.execution_lock import load_execution_lock


def main() -> None:
    lock = load_execution_lock()

    print("Execution lock")
    print("-" * 80)
    for key, value in lock.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
