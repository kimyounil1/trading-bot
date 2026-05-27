from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import pandas as pd
import numpy as np
from src.strategy import add_indicators, generate_signal, is_bullish_market_regime
from src.settings import StrategyProfile, PortfolioConfig, AllocationType

@dataclass
class BacktestResult:
    ticker: str
    total_return: float
    buy_hold_return: float
    max_drawdown: float
    trades: int
    win_rate: float
    final_equity: float

class MultiStrategyBacktester:
    """
    Multi-Strategy Portfolio Backtester
    Handles multiple strategies, asset allocation, and portfolio-level risk management.
    """
    def __init__(
        self,
        config: PortfolioConfig,
        initial_cash: float = 10000.0,
        benchmark_df: pd.DataFrame = None,
        model: Any = None
    ):
        self.config = config
        self.initial_cash = initial_cash
        self.benchmark_df = benchmark_df
        self.model = model

    def run(self, all_data: Dict[str, pd.DataFrame]) -> tuple[BacktestResult, pd.DataFrame]:
        all_dates = sorted(pd.concat([df['date'] for df in all_data.values()]).unique())
        master_df = pd.DataFrame({'date': all_dates})
        
        strategy_signals = {}
        for profile in self.config.strategies:
            strategy_signals[profile.name] = self._generate_strategy_signals(profile, all_data)

        return self._simulate_portfolio(master_df, strategy_signals, all_data)

    def _generate_strategy_signals(self, profile: StrategyProfile, all_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        all_profile_dates = []
        for t in profile.tickers:
            if t in all_data:
                all_profile_dates.extend(all_data[t]['date'].tolist())
        
        unique_dates = sorted(list(set(all_profile_dates)))
        signal_matrix = pd.DataFrame(0.0, index=unique_dates, columns=profile.tickers)

        for ticker in profile.tickers:
            if ticker not in all_data:
                continue
            
            df = all_data[ticker].copy().sort_values('date').set_index('date')
            df = add_indicators(df, profile)
            
            regime_ok = True
            if profile.market_regime_filter_enabled and self.benchmark_df is not None:
                regime_ok = is_bullish_market_regime(self.benchmark_df, profile.market_regime_ma_fast, profile.market_regime_ma_slow)

            for date, row in df.iterrows():
                if not regime_ok:
                    signal_matrix.loc[date, ticker] = 0.0
                    continue
                
                sig = generate_signal(row, profile, model=self.model, benchmark_df=self.benchmark_df)
                if sig == "BUY":
                    signal_matrix.loc[date, ticker] = 1.0
                elif sig == "SELL":
                    signal_matrix.loc[date, ticker] = -1.0
                else:
                    signal_matrix.loc[date, ticker] = 0.0
                    
        return signal_matrix

    def _simulate_portfolio(self, master_df: pd.DataFrame, strategy_signals: Dict[str, pd.DataFrame], all_data: Dict[str, pd.DataFrame]) -> tuple[BacktestResult, pd.DataFrame]:
        cash = self.initial_cash
        positions: Dict[str, float] = {}  # ticker -> quantity
        entry_prices: Dict[str, float] = {} 
        peak_prices: Dict[str, float] = {}  
        equity_history = []
        trades = []
        
        all_tickers = list(set(t for p in self.config.strategies for t in p.tickers))
        target_exposure = pd.DataFrame(0.0, index=master_df['date'], columns=all_tickers)

        # 1. Calculate Target Weights
        for profile in self.config.strategies:
            if self.config.allocation.allocation_type == AllocationType.EQUAL_WEIGHT:
                strat_weight = 1.0 / len(self.config.strategies)
            elif self.config.allocation.allocation_type == AllocationType.FIXED_WEIGHT:
                strat_weight = self.config.allocation.weights.get(profile.name, 0.0)
            elif self.config.allocation.allocation_type == AllocationType.RISK_PARITY:
                # Simplified Risk Parity: Weight inversely proportional to volatility
                # We'll handle this in the loop by adjusting target_weights
                strat_weight = 1.0 
            else:
                strat_weight = 1.0 / len(self.config.strategies)
            
            sigs = strategy_signals[profile.name].replace(-1.0, 0.0)
            for ticker in profile.tickers:
                if ticker in target_exposure.columns:
                    target_exposure.loc[target_exposure.index, ticker] += sigs[ticker] * strat_weight

        # 2. Simulation Loop
        for date in master_df['date']:
            current_prices = {}
            for ticker in all_tickers:
                if ticker in all_data:
                    d = all_data[ticker]
                    row_match = d[d['date'] <= date]
                    if not row_match.empty:
                        current_prices[ticker] = float(row_match.iloc[-1]['close'])

            current_equity = cash
            for t, qty in positions.items():
                if t in current_prices:
                    current_equity += qty * current_prices[t]
            
            equity_history.append({'date': date, 'equity': current_equity})

            # --- Risk Management: SL/TP/Trailing ---
            for ticker in list(positions.keys()):
                if ticker in current_prices:
                    price = current_prices[ticker]
                    entry = entry_prices.get(ticker, price)
                    peak = peak_prices.get(ticker, price)
                    
                    ts_triggered = self.config.trailing_stop_pct and price < peak * (1 - self.config.trailing_stop_pct)
                    sl_triggered = self.config.stop_loss_pct and price < entry * (1 - self.config.stop_loss_pct)
                    tp_triggered = self.config.take_profit_pct and price > entry * (1 + self.config.take_profit_pct)

                    if ts_triggered or sl_triggered or tp_triggered:
                        qty = positions[ticker]
                        cash += qty * price
                        trades.append({"date": date, "ticker": ticker, "type": "EXIT_RISK", "price": price, "qty": qty})
                        del positions[ticker]
                        del entry_prices[ticker]
                        del peak_prices[ticker]

            # --- Rebalancing ---
            target_weights = target_exposure.loc[date].copy()
            
            # [Step 2-1] Risk-Parity implementation (Inverse Volatility)
            if self.config.allocation.allocation_type == AllocationType.RISK_PARITY:
                vols = []
                active_indices = []
                for t in target_weights.index:
                    if target_weights[t] > 0 and t in all_data:
                        df = all_data[t].sort_values('date')
                        vol = df['close'].pct_change().rolling(20).std().iloc[-1]
                        if pd.notna(vol) and vol > 0:
                            vols.append(1.0/vol)
                            active_indices.append(t)
                
                if active_indices:
                    sum_inv_vol = sum(vols)
                    for i, t in enumerate(active_indices):
                        target_weights[t] = vols[i] / sum_inv_vol
                    # Zero out other weights
                    for t in target_weights.index:
                        if t not in active_indices:
                            target_weights[t] = 0.0
                else:
                    target_weights[:] = 0.0

            # Constraint: max_total_positions
            active_tickers = [t for t, w in target_weights.items() if w > 0]
            if len(active_tickers) > self.config.max_total_positions:
                scale_factor = self.config.max_total_positions / len(active_tickers)
                target_weights = target_weights * scale_factor

            for ticker in all_tickers:
                if ticker not in current_prices: continue
                target_w = target_weights[ticker]
                price = current_prices[ticker]
                current_qty = positions.get(ticker, 0.0)
                target_val = current_equity * target_w
                current_val = current_qty * price
                diff_val = target_val - current_val
                
                if abs(diff_val) > current_equity * 0.005:
                    if diff_val > 0: 
                        if cash >= diff_val:
                            buy_qty = diff_val / price
                            positions[ticker] = current_qty + buy_qty
                            cash -= diff_val
                            entry_prices[ticker] = price
                            peak_prices[ticker] = price
                            trades.append({"date": date, "ticker": ticker, "type": "BUY", "price": price, "qty": buy_qty})
                    elif diff_val < 0: 
                        sell_qty = abs(diff_val) / price
                        actual_sell = min(sell_qty, current_qty)
                        if actual_sell > 0:
                            positions[ticker] = current_qty - actual_sell
                            cash += actual_sell * price
                            trades.append({"date": date, "ticker": ticker, "type": "SELL", "price": price, "qty": actual_sell})
                            if positions[ticker] <= 1e-6:
                                del positions[ticker]
                                del entry_prices[ticker]
                                del peak_prices[ticker]
                if ticker in positions:
                    peak_prices[ticker] = max(peak_prices.get(ticker, price), price)

        # 3. Finalize
        equity_df = pd.DataFrame(equity_history).set_index('date')
        if not equity_df.empty:
            equity_df['returns'] = equity_df['equity'].pct_change().fillna(0.0)
            equity_df['drawdown'] = (equity_df['equity'] / equity_df['equity'].cummax()) - 1.0
        else:
            equity_df = pd.DataFrame()

        final_equity = float(equity_df['equity'].iloc[-1]) if not equity_df.empty else self.initial_cash
        total_return = (final_equity / self.initial_cash) - 1.0
        max_drawdown = float(equity_df['drawdown'].min()) if not equity_df.empty else 0.0
        trades_df = pd.DataFrame(trades)
        trades_count = len(trades)
        win_rate = 0.0 
        
        return BacktestResult("PORTFOLIO", total_return, 0.0, max_drawdown, trades_count, win_rate, final_equity), equity_df

def run_portfolio_backtest(config: PortfolioConfig, all_data: Dict[str, pd.DataFrame], **kwargs) -> tuple[BacktestResult, pd.DataFrame]:
    backtester = MultiStrategyBacktester(config, **kwargs)
    return backtester.run(all_data)
