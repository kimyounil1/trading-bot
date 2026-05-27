import pandas as pd
from src.earnings import get_next_earnings_date, is_earnings_window

def test_earnings():
    ticker = "NVDA"
    print(f"Checking earnings for {ticker}...")
    
    date = get_next_earnings_date(ticker, cache_ttl_hours=0) # Force refresh
    if date:
        print(f"Next earnings date for {ticker}: {date}")
        
        # Test window logic
        now = pd.Timestamp.now().normalize()
        in_window, reason = is_earnings_window(ticker, now)
        print(f"Is {ticker} in earnings window today ({now.date()})? {in_window}")
        print(f"Reason: {reason}")
        
        # Test specific date (exactly on earnings)
        in_window_on, reason_on = is_earnings_window(ticker, date)
        print(f"Is {ticker} in earnings window on {date.date()}? {in_window_on}")
        print(f"Reason: {reason_on}")
        
    else:
        print(f"Could not fetch earnings for {ticker}")

if __name__ == "__main__":
    test_earnings()
