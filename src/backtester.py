from dataclasses import dataclass

import pandas as pd

from src.strategy import add_indicators


@dataclass
class BacktestResult:
    ticker: str
    total_return: float
    buy_hold_return: float
    max_drawdown: float
    trades: int
    win_rate: float
    final_equity: float


def run_backtest(
    ticker: str,
    df: pd.DataFrame,
    initial_cash: float = 10000.0,
) -> tuple[BacktestResult, pd.DataFrame, pd.DataFrame]:
    df = add_indicators(df).copy()
    df = df.sort_values("date").reset_index(drop=True)

    cash = initial_cash
    shares = 0.0
    in_position = False
    entry_price = 0.0

    trades: list[dict] = []
    equity_rows: list[dict] = []

    for _, row in df.iterrows():
        date = row["date"]
        close = float(row["close"])
        ma20 = float(row["ma20"])
        ma50 = float(row["ma50"])
        rsi = float(row["rsi"])

        buy_signal = ma20 > ma50 and rsi < 70
        sell_signal = ma20 < ma50

        action = "HOLD"

        if not in_position and buy_signal:
            shares = cash / close
            cash = 0.0
            in_position = True
            entry_price = close
            action = "BUY"

            trades.append(
                {
                    "ticker": ticker,
                    "entry_date": date,
                    "entry_price": close,
                    "exit_date": None,
                    "exit_price": None,
                    "return_pct": None,
                }
            )

        elif in_position and sell_signal:
            cash = shares * close
            shares = 0.0
            in_position = False
            action = "SELL"

            trade_return = (close / entry_price) - 1.0
            trades[-1]["exit_date"] = date
            trades[-1]["exit_price"] = close
            trades[-1]["return_pct"] = trade_return

        equity = cash + shares * close

        equity_rows.append(
            {
                "date": date,
                "ticker": ticker,
                "close": close,
                "ma20": ma20,
                "ma50": ma50,
                "rsi": rsi,
                "action": action,
                "cash": cash,
                "shares": shares,
                "equity": equity,
            }
        )

    equity_df = pd.DataFrame(equity_rows)
    trades_df = pd.DataFrame(trades)

    if equity_df.empty:
        raise ValueError(f"No equity rows for {ticker}")

    equity_df["strategy_return"] = equity_df["equity"].pct_change().fillna(0.0)
    equity_df["buy_hold_equity"] = (
        initial_cash * equity_df["close"] / equity_df["close"].iloc[0]
    )
    equity_df["running_max"] = equity_df["equity"].cummax()
    equity_df["drawdown"] = equity_df["equity"] / equity_df["running_max"] - 1.0

    final_equity = float(equity_df["equity"].iloc[-1])
    total_return = final_equity / initial_cash - 1.0
    buy_hold_return = (
        float(equity_df["buy_hold_equity"].iloc[-1]) / initial_cash - 1.0
    )
    max_drawdown = float(equity_df["drawdown"].min())

    closed_trades = trades_df.dropna(subset=["exit_date"]) if not trades_df.empty else trades_df
    trades_count = int(len(closed_trades))

    if trades_count > 0:
        win_rate = float((closed_trades["return_pct"] > 0).mean())
    else:
        win_rate = 0.0

    result = BacktestResult(
        ticker=ticker,
        total_return=total_return,
        buy_hold_return=buy_hold_return,
        max_drawdown=max_drawdown,
        trades=trades_count,
        win_rate=win_rate,
        final_equity=final_equity,
    )

    return result, equity_df, trades_df
