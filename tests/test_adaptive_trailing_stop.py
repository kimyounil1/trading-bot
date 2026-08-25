import unittest
import pandas as pd
import numpy as np
from types import SimpleNamespace
from src.strategy import add_indicators

class TestAdaptiveTrailingStop(unittest.TestCase):
    def test_atr_calculation(self):
        # Create a sample dataframe with high/low/close
        rows = 50
        df = pd.DataFrame({
            "open": np.linspace(100, 150, rows),
            "high": np.linspace(105, 155, rows),
            "low": np.linspace(95, 145, rows),
            "close": np.linspace(102, 152, rows),
            "adj_close": np.linspace(102, 152, rows),
            "volume": np.linspace(1000, 2000, rows)
        })
        
        df_with_indicators = add_indicators(df)
        self.assertIn("atr", df_with_indicators.columns)
        self.assertFalse(df_with_indicators["atr"].isna().all())

    def test_add_indicators_coerces_numeric_ohlc(self) -> None:
        rows = 40
        df = pd.DataFrame(
            {
                "open": [str(100 + i) for i in range(rows)],
                "high": [str(105 + i) for i in range(rows)],
                "low": [str(95 + i) for i in range(rows)],
                "close": [str(102 + i) for i in range(rows)],
                "volume": [str(1000 + i) for i in range(rows)],
            }
        )
        out = add_indicators(df)
        self.assertFalse(out.empty)
        self.assertIn("ma_slow", out.columns)
        
    def test_adaptive_logic_mock(self):
        # In main.py, the logic is:
        # trailing_pct = (atr_val * multiplier) / peak_price
        
        peak_price = 100.0
        atr_val = 2.0 # 2% volatility
        multiplier = 3.0
        
        # Expected trailing_pct = (2.0 * 3.0) / 100.0 = 0.06 (6%)
        trailing_pct = (atr_val * multiplier) / peak_price
        self.assertEqual(trailing_pct, 0.06)
        
        # Test bounds
        trailing_pct_low = max(0.02, min(0.20, (0.1 * 3.0) / 100.0)) # (0.3 / 100) = 0.003 -> 0.02
        self.assertEqual(trailing_pct_low, 0.02)
        
        trailing_pct_high = max(0.02, min(0.20, (10.0 * 3.0) / 100.0)) # (30 / 100) = 0.30 -> 0.20
        self.assertEqual(trailing_pct_high, 0.20)

if __name__ == "__main__":
    unittest.main()
