from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.strategy import add_indicators
from src.features import FEATURE_COLUMNS, build_features
from src.ml_model import load_ai_score_model


@dataclass
class PortfolioBacktestResult:
    initial_cash: float
    final_equity: float
    total_return: float
    max_drawdown: float
    trades: int
    win_rate: float
    benchmark_return: float


def _prepare_ticker_frame(
    ticker: str,
    df: pd.DataFrame,
    ma_fast: int = 20,
    ma_slow: int = 50,
    rsi_buy_limit: float = 70,
    use_ai_score: bool = False,
    ai_score_buy_threshold: float = 0.55,
) -> pd.DataFrame:
    raw_df = df.copy()
    df = add_indicators(df, ma_fast=ma_fast, ma_slow=ma_slow).copy()
    df = df.sort_values("date").reset_index(drop=True)

    df["ticker"] = ticker
    df["ai_score"] = None

    if use_ai_score:
        try:
            bundle = load_ai_score_model()
            model = bundle["model"]
            feature_columns = bundle["feature_columns"]

            feature_df = build_features(
                raw_df,
                prediction_horizon=bundle.get("prediction_horizon", 5),
                target_return_threshold=bundle.get("target_return_threshold", 0.0),
            )

            feature_df["ai_score"] = model.predict_proba(
                feature_df[feature_columns]
            )[:, 1]

            score_df = feature_df[["date", "ai_score"]].copy()
            score_df["date"] = pd.to_datetime(score_df["date"])

            df["date"] = pd.to_datetime(df["date"])
            df = df.merge(score_df, on="date", how="left", suffixes=("", "_model"))

            if "ai_score_model" in df.columns:
                df["ai_score"] = df["ai_score_model"]
                df = df.drop(columns=["ai_score_model"])

        except Exception:
            df["ai_score"] = None

    base_buy_signal = (df["ma_fast"] > df["ma_slow"]) & (df["rsi"] < rsi_buy_limit)

    if use_ai_score:
        df["buy_signal"] = base_buy_signal & (
            pd.to_numeric(df["ai_score"], errors="coerce") >= ai_score_buy_threshold
        )
    else:
        df["buy_signal"] = base_buy_signal

    df["sell_signal"] = df["ma_fast"] < df["ma_slow"]

    return df[
        [
            "date",
            "ticker",
            "close",
            "ma20",
            "ma50",
            "ma_fast",
            "ma_slow",
            "rsi",
            "ai_score",
            "buy_signal",
            "sell_signal",
        ]
    ]

def run_portfolio_backtest(
    ticker_data: dict[str, pd.DataFrame],
    initial_cash: float = 10000.0,
    max_positions: int = 3,
    target_position_pct: float = 0.30,
    transaction_cost_pct: float = 0.001,
    ma_fast: int = 20,
    ma_slow: int = 50,
    rsi_buy_limit: float = 70,
    use_ai_score: bool = False,
    ai_score_buy_threshold: float = 0.55,
) -> tuple[PortfolioBacktestResult, pd.DataFrame, pd.DataFrame]:
    prepared_frames = [
        _prepare_ticker_frame(
            ticker,
            df,
            ma_fast=ma_fast,
            ma_slow=ma_slow,
            rsi_buy_limit=rsi_buy_limit,
            use_ai_score=use_ai_score,
            ai_score_buy_threshold=ai_score_buy_threshold,
        )
        for ticker, df in ticker_data.items()
    ]

    market_df = pd.concat(prepared_frames, ignore_index=True)
    market_df["date"] = pd.to_datetime(market_df["date"])
    market_df = market_df.sort_values(["date", "ticker"]).reset_index(drop=True)

    all_dates = sorted(market_df["date"].unique())

    cash = initial_cash
    positions: dict[str, dict] = {}

    trades: list[dict] = []
    equity_rows: list[dict] = []

    for current_date in all_dates:
        day_df = market_df[market_df["date"] == current_date].copy()
        day_prices = {
            row["ticker"]: float(row["close"])
            for _, row in day_df.iterrows()
        }

        for ticker in list(positions.keys()):
            ticker_row = day_df[day_df["ticker"] == ticker]

            if ticker_row.empty:
                continue

            row = ticker_row.iloc[0]
            close = float(row["close"])

            if bool(row["sell_signal"]):
                position = positions.pop(ticker)
                qty = position["qty"]
                entry_price = position["entry_price"]
                entry_date = position["entry_date"]

                gross_value = qty * close
                cost = gross_value * transaction_cost_pct
                net_value = gross_value - cost
                cash += net_value

                return_pct = (net_value / position["cost_basis"]) - 1.0

                trades.append(
                    {
                        "ticker": ticker,
                        "entry_date": entry_date,
                        "exit_date": current_date,
                        "entry_price": entry_price,
                        "exit_price": close,
                        "qty": qty,
                        "cost_basis": position["cost_basis"],
                        "exit_value": net_value,
                        "return_pct": return_pct,
                        "exit_reason": "SELL_SIGNAL",
                    }
                )

        positions_value = sum(
            pos["qty"] * day_prices.get(ticker, pos["last_price"])
            for ticker, pos in positions.items()
        )
        equity = cash + positions_value

        slots_left = max_positions - len(positions)

        if slots_left > 0:
            buy_candidates = day_df[
                (day_df["buy_signal"]) &
                (~day_df["ticker"].isin(positions.keys()))
            ].copy()

            buy_candidates["trend_strength"] = (
                buy_candidates["ma_fast"] / buy_candidates["ma_slow"]
            )

            buy_candidates = buy_candidates.sort_values(
                ["trend_strength", "rsi"],
                ascending=[False, True],
            )

            for _, row in buy_candidates.head(slots_left).iterrows():
                ticker = row["ticker"]
                close = float(row["close"])

                if close <= 0:
                    continue

                target_value = equity * target_position_pct
                available_value = min(cash, target_value)

                if available_value <= 0:
                    continue

                cost = available_value * transaction_cost_pct
                net_investment = available_value - cost

                if net_investment <= 0:
                    continue

                qty = net_investment / close
                cash -= available_value

                positions[ticker] = {
                    "qty": qty,
                    "entry_price": close,
                    "entry_date": current_date,
                    "cost_basis": available_value,
                    "last_price": close,
                }

        for ticker, pos in positions.items():
            if ticker in day_prices:
                pos["last_price"] = day_prices[ticker]

        positions_value = sum(
            pos["qty"] * pos["last_price"]
            for pos in positions.values()
        )
        equity = cash + positions_value

        equity_rows.append(
            {
                "date": current_date,
                "cash": cash,
                "positions_value": positions_value,
                "equity": equity,
                "positions_count": len(positions),
                "open_symbols": ",".join(sorted(positions.keys())),
            }
        )

    equity_df = pd.DataFrame(equity_rows)

    if equity_df.empty:
        raise ValueError("No equity rows generated")

    equity_df["daily_return"] = equity_df["equity"].pct_change().fillna(0.0)
    equity_df["running_max"] = equity_df["equity"].cummax()
    equity_df["drawdown"] = equity_df["equity"] / equity_df["running_max"] - 1.0

    trades_df = pd.DataFrame(trades)

    final_equity = float(equity_df["equity"].iloc[-1])
    total_return = final_equity / initial_cash - 1.0
    max_drawdown = float(equity_df["drawdown"].min())

    trades_count = int(len(trades_df))

    if trades_count > 0:
        win_rate = float((trades_df["return_pct"] > 0).mean())
    else:
        win_rate = 0.0

    benchmark_values = []
    shares = {}

    first_date = equity_df["date"].iloc[0]
    first_day = market_df[market_df["date"] == first_date]

    equal_cash = initial_cash / len(ticker_data)

    for _, row in first_day.iterrows():
        ticker = row["ticker"]
        close = float(row["close"])
        shares[ticker] = equal_cash / close

    for current_date in equity_df["date"]:
        day_df = market_df[market_df["date"] == current_date]
        prices = {
            row["ticker"]: float(row["close"])
            for _, row in day_df.iterrows()
        }

        value = 0.0
        for ticker, qty in shares.items():
            price = prices.get(ticker)
            if price is not None:
                value += qty * price

        benchmark_values.append(value)

    equity_df["benchmark_equity"] = benchmark_values
    benchmark_return = (
        float(equity_df["benchmark_equity"].iloc[-1]) / initial_cash - 1.0
    )

    result = PortfolioBacktestResult(
        initial_cash=initial_cash,
        final_equity=final_equity,
        total_return=total_return,
        max_drawdown=max_drawdown,
        trades=trades_count,
        win_rate=win_rate,
        benchmark_return=benchmark_return,
    )

    return result, equity_df, trades_df


def save_portfolio_backtest_outputs(
    output_dir: str | Path,
    result: PortfolioBacktestResult,
    equity_df: pd.DataFrame,
    trades_df: pd.DataFrame,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_df = pd.DataFrame(
        [
            {
                "initial_cash": result.initial_cash,
                "final_equity": result.final_equity,
                "total_return": result.total_return,
                "benchmark_return": result.benchmark_return,
                "max_drawdown": result.max_drawdown,
                "trades": result.trades,
                "win_rate": result.win_rate,
            }
        ]
    )

    summary_df.to_csv(output_dir / "portfolio_summary.csv", index=False)
    equity_df.to_csv(output_dir / "portfolio_equity.csv", index=False)
    trades_df.to_csv(output_dir / "portfolio_trades.csv", index=False)
