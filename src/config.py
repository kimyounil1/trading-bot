import os
from dotenv import load_dotenv

load_dotenv()

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_PAPER = os.getenv("ALPACA_PAPER", "True").lower() == "true"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "False").lower() == "true"

SIGNAL_LOG_PATH = os.getenv("SIGNAL_LOG_PATH", "logs/signals.csv")
LOG_PATH = SIGNAL_LOG_PATH
ORDER_LOG_PATH = os.getenv("ORDER_LOG_PATH", "logs/orders.csv")
EXECUTION_AUDIT_LOG_PATH = os.getenv("EXECUTION_AUDIT_LOG_PATH", "logs/execution_audit.csv")
