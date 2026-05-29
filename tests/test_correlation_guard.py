import unittest
import pandas as pd
import numpy as np
from src.correlation_guard import is_correlation_allowed


class TestCorrelationGuard(unittest.TestCase):
    def setUp(self):
        # Set random seed for deterministic test data
        np.random.seed(42)
        # Create mock ticker data
        self.dates = pd.date_range(start="2024-01-01", periods=100)
        
        # Ticker A: Baseline
        self.ticker_a = "A"
        self.data_a = pd.DataFrame({
            "close": np.linspace(100, 110, 100) + np.random.normal(0, 0.5, 100)
        }, index=self.dates)
        
        # Ticker B: Highly correlated with A
        self.ticker_b = "B"
        self.data_b = pd.DataFrame({
            "close": self.data_a["close"] * 1.05 + np.random.normal(0, 0.1, 100)
        }, index=self.dates)
        
        # Ticker C: Uncorrelated / Low correlation with A
        self.ticker_c = "C"
        self.data_c = pd.DataFrame({
            "close": np.random.normal(100, 5, 100)
        }, index=self.dates)
        
        self.ticker_data = {
            "A": self.data_a,
            "B": self.data_b,
            "C": self.data_c
        }

    def test_no_open_positions(self):
        allowed, reason = is_correlation_allowed("B", set(), self.ticker_data)
        self.assertTrue(allowed)
        self.assertEqual(reason, "no open positions to compare")

    def test_high_correlation(self):
        # A is held, trying to buy B (highly correlated)
        open_symbols = {"A"}
        allowed, reason = is_correlation_allowed("B", open_symbols, self.ticker_data, max_corr=0.8)
        self.assertFalse(allowed)
        self.assertIn("high pairwise correlation", reason)

    def test_high_portfolio_avg_correlation(self):
        # A and C are held, trying to buy B
        # A vs B: 0.98, C vs B: low, but average might be high
        open_symbols = {"A", "C"}
        # Assume C vs B correlation is around 0.3. Avg (0.98 + 0.3) / 2 = 0.64
        # If threshold is 0.6, it should be blocked.
        allowed, reason = is_correlation_allowed(
            "B", open_symbols, self.ticker_data, 
            max_corr=0.99, # Pairwise passes
            max_portfolio_avg_corr=0.45 # Avg fails
        )
        self.assertFalse(allowed)
        self.assertIn("high portfolio average correlation", reason)

    def test_low_correlation(self):
        # A is held, trying to buy C (uncorrelated)
        open_symbols = {"A"}
        allowed, reason = is_correlation_allowed("C", open_symbols, self.ticker_data, max_corr=0.8)
        self.assertTrue(allowed)
        self.assertEqual(reason, "correlation check passed")

    def test_insufficient_data(self):
        # New ticker with only 10 days of data
        ticker_short = "SHORT"
        data_short = pd.DataFrame({
            "close": np.random.normal(100, 1, 10)
        }, index=self.dates[-10:])
        self.ticker_data["SHORT"] = data_short
        
        open_symbols = {"A"}
        allowed, reason = is_correlation_allowed("SHORT", open_symbols, self.ticker_data, lookback_days=60)
        self.assertTrue(allowed)
        self.assertIn("insufficient data", reason)


if __name__ == "__main__":
    unittest.main()
