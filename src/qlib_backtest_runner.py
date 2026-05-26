import argparse
import json
from pathlib import Path

import pandas as pd

from src.generate_qlib_snapshot import main as generate_qlib_snapshot_main
from src.ml_model import load_ai_score_model
from src.settings import DEFAULT_SETTINGS, StrategySettings, validate_settings
from src.strategy import add_indicators


def load_signal_frame(signal_csv: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(Path(signal_csv).expanduser().resolve())
    required = {"datetime", "instrument", "score"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Signal CSV missing required columns: {sorted(missing)}")

    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    frame["score"] = pd.to_numeric(frame["score"], errors="coerce")
    frame = frame.dropna(subset=["datetime", "instrument", "score"])
    frame = frame.sort_values(["datetime", "instrument"]).reset_index(drop=True)
    if frame.empty:
        raise ValueError("Signal CSV contains no valid rows")

    return frame.set_index(["datetime", "instrument"])[["score"]]


def build_momentum_signal_from_qlib_ready(
    csv_dir: str | Path,
    momentum_window: int = 20,
) -> pd.DataFrame:
    if momentum_window <= 0:
        raise ValueError("momentum_window must be positive")

    rows: list[pd.DataFrame] = []
    for path in sorted(Path(csv_dir).expanduser().resolve().glob("*.csv")):
        frame = pd.read_csv(path)
        required = {"instrument", "datetime", "close"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{path} missing required columns: {sorted(missing)}")

        frame["datetime"] = pd.to_datetime(frame["datetime"])
        frame["instrument"] = frame["instrument"].astype(str).str.upper()
        frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
        frame = frame.dropna(subset=["datetime", "instrument", "close"])
        frame = frame.sort_values("datetime").reset_index(drop=True)
        frame["score"] = frame["close"].pct_change(momentum_window)
        rows.append(frame[["datetime", "instrument", "score"]])

    if not rows:
        raise ValueError(f"No qlib-ready CSV files found in {csv_dir}")

    signal = pd.concat(rows, ignore_index=True)
    signal = signal.dropna(subset=["score"]).sort_values(["datetime", "instrument"]).reset_index(drop=True)
    if signal.empty:
        raise ValueError("Momentum signal is empty after applying lookback window")

    return signal.set_index(["datetime", "instrument"])[["score"]]


def load_qlib_ready_price_frame(csv_dir: str | Path) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for path in sorted(Path(csv_dir).expanduser().resolve().glob("*.csv")):
        frame = pd.read_csv(path)
        required = {"instrument", "datetime", "close"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{path} missing required columns: {sorted(missing)}")

        frame["instrument"] = frame["instrument"].astype(str).str.upper()
        frame["datetime"] = pd.to_datetime(frame["datetime"])
        frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
        rows.append(frame[["datetime", "instrument", "close"]])

    if not rows:
        raise ValueError(f"No qlib-ready CSV files found in {csv_dir}")

    prices = pd.concat(rows, ignore_index=True)
    prices = prices.dropna(subset=["datetime", "instrument", "close"])
    return prices.sort_values(["datetime", "instrument"]).reset_index(drop=True)


def load_strategy_settings_from_json(path: str | Path) -> StrategySettings:
    settings_path = Path(path).expanduser().resolve()
    merged = DEFAULT_SETTINGS.__dict__.copy()
    if settings_path.exists():
        merged.update(json.loads(settings_path.read_text(encoding="utf-8")))
    return validate_settings(StrategySettings(**merged))


def build_strategy_signal_from_price_data(
    ticker_data: dict[str, pd.DataFrame],
    settings: StrategySettings,
    ai_model_bundle=None,
    trend_weight: float = 1.0,
    rsi_weight: float = 1.0,
    ai_weight: float = 1.0,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []

    for ticker, raw_df in ticker_data.items():
        frame = raw_df.copy()
        if "datetime" in frame.columns and "date" not in frame.columns:
            frame = frame.rename(columns={"datetime": "date"})
        if "date" not in frame.columns:
            raise ValueError(f"{ticker} price data must contain a date or datetime column")

        indicator_df = add_indicators(frame, settings).copy()
        if indicator_df.empty:
            continue

        indicator_df["date"] = pd.to_datetime(indicator_df["date"])
        indicator_df["trend_strength"] = indicator_df["ma_fast"] / indicator_df["ma_slow"] - 1.0
        indicator_df["rsi_buffer"] = (settings.rsi_buy_limit - indicator_df["rsi"]) / 100.0
        indicator_df["eligible"] = (
            (indicator_df["ma_fast"] > indicator_df["ma_slow"])
            & (indicator_df["rsi"] < settings.rsi_buy_limit)
        )
        indicator_df["score"] = (
            trend_weight * indicator_df["trend_strength"]
            + rsi_weight * indicator_df["rsi_buffer"]
        )

        if settings.use_ai_score and ai_model_bundle is not None:
            try:
                ai_series = ai_model_bundle.predict_proba(frame)
                ai_dates = pd.to_datetime(frame["date"]).iloc[ai_series.index].reset_index(drop=True)
                ai_score_df = pd.DataFrame(
                    {
                        "date": ai_dates,
                        "ai_score": ai_series.values,
                    }
                )
                indicator_df = indicator_df.merge(ai_score_df, on="date", how="left")
                indicator_df["eligible"] = indicator_df["eligible"] & (
                    indicator_df["ai_score"] >= settings.ai_score_buy_threshold
                )
                indicator_df["score"] = indicator_df["score"] + ai_weight * indicator_df["ai_score"].fillna(0.0)
            except Exception:
                indicator_df["ai_score"] = None

        signal_rows = indicator_df.loc[indicator_df["eligible"], ["date", "score"]].copy()
        if signal_rows.empty:
            continue

        signal_rows["instrument"] = ticker.upper()
        signal_rows = signal_rows.rename(columns={"date": "datetime"})
        rows.append(signal_rows[["datetime", "instrument", "score"]])

    if not rows:
        raise ValueError("Strategy signal is empty for the provided ticker data")

    signal = pd.concat(rows, ignore_index=True)
    signal = signal.sort_values(["datetime", "instrument"]).reset_index(drop=True)
    return signal.set_index(["datetime", "instrument"])[["score"]]


def apply_signal_execution_constraints(
    signal_frame: pd.DataFrame,
    *,
    max_active_signals: int,
    max_new_signals_per_day: int,
    cooldown_days: int,
) -> pd.DataFrame:
    if max_active_signals <= 0:
        raise ValueError("max_active_signals must be positive")
    if max_new_signals_per_day <= 0:
        raise ValueError("max_new_signals_per_day must be positive")
    if cooldown_days < 0:
        raise ValueError("cooldown_days must be non-negative")

    frame = signal_frame.reset_index().copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    frame["score"] = pd.to_numeric(frame["score"], errors="coerce")
    frame = frame.dropna(subset=["datetime", "instrument", "score"])
    frame = frame.sort_values(["datetime", "score", "instrument"], ascending=[True, False, True])
    if frame.empty:
        raise ValueError("Signal frame contains no valid rows")

    active_symbols: set[str] = set()
    last_entry_dates: dict[str, pd.Timestamp] = {}
    constrained_rows: list[dict] = []

    for current_date, day_df in frame.groupby("datetime", sort=True):
        day_df = day_df.sort_values(["score", "instrument"], ascending=[False, True]).reset_index(drop=True)
        today_symbols = set(day_df["instrument"])

        keep_rows: list[dict] = []
        next_active_symbols: set[str] = set()
        for _, row in day_df.iterrows():
            instrument = row["instrument"]
            if instrument not in active_symbols:
                continue
            if len(keep_rows) >= max_active_signals:
                break
            keep_rows.append(row.to_dict())
            next_active_symbols.add(instrument)

        available_slots = max_active_signals - len(keep_rows)
        new_slots = min(max_new_signals_per_day, available_slots)
        new_rows: list[dict] = []
        if new_slots > 0:
            for _, row in day_df.iterrows():
                instrument = row["instrument"]
                if instrument in next_active_symbols:
                    continue

                last_entry_date = last_entry_dates.get(instrument)
                if last_entry_date is not None:
                    days_since_entry = (pd.Timestamp(current_date) - last_entry_date).days
                    if days_since_entry <= cooldown_days:
                        continue

                new_rows.append(row.to_dict())
                next_active_symbols.add(instrument)
                last_entry_dates[instrument] = pd.Timestamp(current_date)
                if len(new_rows) >= new_slots:
                    break

        constrained_rows.extend(keep_rows)
        constrained_rows.extend(new_rows)
        active_symbols = next_active_symbols & today_symbols

    constrained = pd.DataFrame(constrained_rows)
    if constrained.empty:
        raise ValueError("Signal frame is empty after applying execution constraints")

    constrained = constrained.sort_values(["datetime", "instrument"]).reset_index(drop=True)
    return constrained.set_index(["datetime", "instrument"])[["score"]]


def infer_backtest_window(signal_frame: pd.DataFrame) -> tuple[str, str]:
    unique_dates = sorted(signal_frame.index.get_level_values("datetime").unique())
    if len(unique_dates) < 2:
        raise ValueError("Signal frame must contain at least two trading dates")

    # Qlib daily backtests reference the next trading step during execution,
    # so using the last available signal date can overflow the trade calendar.
    return (
        unique_dates[0].strftime("%Y-%m-%d"),
        unique_dates[-2].strftime("%Y-%m-%d"),
    )


def compute_report_metrics(report_df: pd.DataFrame, initial_cash: float) -> dict[str, float]:
    if report_df.empty:
        raise ValueError("Qlib backtest report is empty")
    if "return" not in report_df.columns or "bench" not in report_df.columns:
        raise ValueError("Qlib backtest report must contain 'return' and 'bench' columns")

    net_returns = pd.to_numeric(report_df["return"], errors="coerce").fillna(0.0)
    if "cost" in report_df.columns:
        net_returns = net_returns - pd.to_numeric(report_df["cost"], errors="coerce").fillna(0.0)

    benchmark_returns = pd.to_numeric(report_df["bench"], errors="coerce").fillna(0.0)
    equity_curve = initial_cash * (1.0 + net_returns).cumprod()
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1.0

    estimated_trades = 0
    if "turnover" in report_df.columns:
        turnover = pd.to_numeric(report_df["turnover"], errors="coerce").fillna(0.0)
        estimated_trades = int((turnover > 0).sum())

    return {
        "initial_cash": float(initial_cash),
        "final_equity": float(equity_curve.iloc[-1]),
        "total_return": float(equity_curve.iloc[-1] / initial_cash - 1.0),
        "max_drawdown": float(drawdown.min()),
        "trades": estimated_trades,
        "win_rate": 0.0,
        "benchmark_return": float((1.0 + benchmark_returns).cumprod().iloc[-1] - 1.0),
    }


def build_close_price_lookup(price_frame: pd.DataFrame) -> dict[tuple[pd.Timestamp, str], float]:
    lookup: dict[tuple[pd.Timestamp, str], float] = {}
    for _, row in price_frame.iterrows():
        lookup[(pd.Timestamp(row["datetime"]), str(row["instrument"]).upper())] = float(row["close"])
    return lookup


def extract_trades_from_positions(
    positions: dict,
    close_price_lookup: dict[tuple[pd.Timestamp, str], float],
) -> pd.DataFrame:
    open_positions: dict[str, dict] = {}
    rows: list[dict] = []
    dates = sorted(positions.keys())

    for current_date in dates:
        snapshot = positions[current_date].position
        holdings = {
            ticker.upper(): info
            for ticker, info in snapshot.items()
            if ticker not in {"cash", "now_account_value"}
        }

        for ticker, tracked in list(open_positions.items()):
            current_info = holdings.get(ticker)
            current_amount = float(current_info["amount"]) if current_info is not None else 0.0

            if current_info is not None and current_amount == tracked["amount"]:
                continue

            exit_price = close_price_lookup.get((pd.Timestamp(current_date), ticker))
            if exit_price is None:
                exit_price = tracked["entry_price"]

            if tracked["amount"] > 0:
                return_pct = exit_price / tracked["entry_price"] - 1.0
                rows.append(
                    {
                        "ticker": ticker,
                        "entry_date": tracked["entry_date"],
                        "exit_date": pd.Timestamp(current_date),
                        "entry_price": tracked["entry_price"],
                        "exit_price": exit_price,
                        "qty": tracked["amount"],
                        "return_pct": return_pct,
                    }
                )

            open_positions.pop(ticker, None)

            if current_info is not None and current_amount > 0:
                open_positions[ticker] = {
                    "entry_date": pd.Timestamp(current_date),
                    "entry_price": float(current_info["price"]),
                    "amount": current_amount,
                }

        for ticker, info in holdings.items():
            if ticker in open_positions:
                continue
            amount = float(info["amount"])
            if amount <= 0:
                continue
            open_positions[ticker] = {
                "entry_date": pd.Timestamp(current_date),
                "entry_price": float(info["price"]),
                "amount": amount,
            }

    if not rows:
        return pd.DataFrame(
            columns=["ticker", "entry_date", "exit_date", "entry_price", "exit_price", "qty", "return_pct"]
        )

    trades_df = pd.DataFrame(rows).sort_values(["exit_date", "ticker"]).reset_index(drop=True)
    return trades_df


def save_signal_csv(signal_frame: pd.DataFrame, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    signal_frame.reset_index().to_csv(path, index=False)
    return path


def save_trades_csv(trades_df: pd.DataFrame, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    trades_df.to_csv(path, index=False)
    return path


def run_custom_signal_backtest(
    *,
    signal_frame: pd.DataFrame,
    price_frame: pd.DataFrame,
    settings: StrategySettings,
    initial_cash: float,
    open_cost: float,
    close_cost: float,
    start_time: str,
    end_time: str,
    n_drop: int = 1,
) -> tuple[dict[str, float], pd.DataFrame, pd.DataFrame]:
    filtered_prices = price_frame.copy()
    filtered_prices["datetime"] = pd.to_datetime(filtered_prices["datetime"])
    filtered_prices["instrument"] = filtered_prices["instrument"].astype(str).str.upper()
    filtered_prices["close"] = pd.to_numeric(filtered_prices["close"], errors="coerce")
    filtered_prices = filtered_prices.dropna(subset=["datetime", "instrument", "close"])
    filtered_prices = filtered_prices[
        (filtered_prices["datetime"] >= pd.Timestamp(start_time))
        & (filtered_prices["datetime"] <= pd.Timestamp(end_time))
    ].copy()
    if filtered_prices.empty:
        raise ValueError("No price rows available for the requested custom backtest window")

    filtered_signals = signal_frame.reset_index().copy()
    filtered_signals["datetime"] = pd.to_datetime(filtered_signals["datetime"])
    filtered_signals["instrument"] = filtered_signals["instrument"].astype(str).str.upper()
    filtered_signals["score"] = pd.to_numeric(filtered_signals["score"], errors="coerce")
    filtered_signals = filtered_signals.dropna(subset=["datetime", "instrument", "score"])
    filtered_signals = filtered_signals[
        (filtered_signals["datetime"] >= pd.Timestamp(start_time))
        & (filtered_signals["datetime"] <= pd.Timestamp(end_time))
    ].copy()
    if filtered_signals.empty:
        raise ValueError("No signal rows available for the requested custom backtest window")

    filtered_signals = filtered_signals.sort_values(
        ["datetime", "score", "instrument"],
        ascending=[True, False, True],
    ).reset_index(drop=True)

    signals_by_date = {
        current_date: day_df.reset_index(drop=True)
        for current_date, day_df in filtered_signals.groupby("datetime", sort=True)
    }
    prices_by_date = {
        current_date: day_df.reset_index(drop=True)
        for current_date, day_df in filtered_prices.groupby("datetime", sort=True)
    }

    all_dates = sorted(prices_by_date.keys())
    cash = float(initial_cash)
    positions: dict[str, dict] = {}
    recent_buy_dates: dict[str, pd.Timestamp] = {}
    trades: list[dict] = []
    equity_rows: list[dict] = []

    max_positions = max(1, int(settings.max_total_positions))
    max_orders_per_run = max(1, int(settings.max_orders_per_run))
    max_daily_order_amount = float(settings.max_daily_order_amount)
    max_position_pct = float(settings.max_position_pct)

    for current_date in all_dates:
        day_prices_df = prices_by_date[current_date]
        day_prices = {
            str(row["instrument"]).upper(): float(row["close"])
            for _, row in day_prices_df.iterrows()
        }
        day_signal_df = signals_by_date.get(current_date, pd.DataFrame(columns=["datetime", "instrument", "score"]))
        day_signal_df = day_signal_df.sort_values(["score", "instrument"], ascending=[False, True]).reset_index(drop=True)
        signal_symbols = set(day_signal_df["instrument"].astype(str).str.upper())

        for ticker in list(positions.keys()):
            if ticker in signal_symbols:
                continue
            close = day_prices.get(ticker)
            if close is None:
                continue

            position = positions.pop(ticker)
            gross_value = position["qty"] * close
            cost = gross_value * close_cost
            net_value = gross_value - cost
            cash += net_value
            trades.append(
                {
                    "ticker": ticker,
                    "entry_date": position["entry_date"],
                    "exit_date": current_date,
                    "entry_price": position["entry_price"],
                    "exit_price": close,
                    "qty": position["qty"],
                    "cost_basis": position["cost_basis"],
                    "exit_value": net_value,
                    "return_pct": net_value / position["cost_basis"] - 1.0,
                    "exit_reason": "SIGNAL_REMOVED",
                }
            )

        for ticker, position in positions.items():
            if ticker in day_prices:
                position["last_price"] = day_prices[ticker]

        daily_buy_budget = min(max_daily_order_amount, cash)
        orders_placed = 0
        if current_date == all_dates[-1]:
            day_signal_df = day_signal_df.iloc[0:0]
        for _, signal in day_signal_df.iterrows():
            ticker = str(signal["instrument"]).upper()
            if ticker in positions or ticker not in day_prices:
                continue
            if len(positions) >= max_positions or orders_placed >= max_orders_per_run:
                break

            last_buy_date = recent_buy_dates.get(ticker)
            if last_buy_date is not None:
                days_since_buy = (pd.Timestamp(current_date) - last_buy_date).days
                if days_since_buy <= int(settings.buy_cooldown_days):
                    continue

            close = day_prices[ticker]
            equity_before_buy = cash + sum(
                position["qty"] * position["last_price"] for position in positions.values()
            )
            target_value = min(
                equity_before_buy * max_position_pct,
                float(settings.max_test_order_amount),
                daily_buy_budget,
                cash,
            )
            if target_value <= 0:
                continue

            fee = target_value * open_cost
            gross_value = target_value - fee
            if gross_value <= 0:
                continue

            qty = gross_value / close
            cash -= target_value
            daily_buy_budget -= target_value
            positions[ticker] = {
                "entry_date": pd.Timestamp(current_date),
                "entry_price": close,
                "qty": qty,
                "cost_basis": target_value,
                "last_price": close,
            }
            recent_buy_dates[ticker] = pd.Timestamp(current_date)
            orders_placed += 1

        positions_value = sum(position["qty"] * position["last_price"] for position in positions.values())
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

    last_date = all_dates[-1]
    last_prices_df = prices_by_date[last_date]
    last_prices = {
        str(row["instrument"]).upper(): float(row["close"])
        for _, row in last_prices_df.iterrows()
    }
    for ticker, position in list(positions.items()):
        close = last_prices.get(ticker, position["last_price"])
        gross_value = position["qty"] * close
        cost = gross_value * close_cost
        net_value = gross_value - cost
        cash += net_value
        trades.append(
            {
                "ticker": ticker,
                "entry_date": position["entry_date"],
                "exit_date": last_date,
                "entry_price": position["entry_price"],
                "exit_price": close,
                "qty": position["qty"],
                "cost_basis": position["cost_basis"],
                "exit_value": net_value,
                "return_pct": net_value / position["cost_basis"] - 1.0,
                "exit_reason": "END_OF_BACKTEST",
            }
        )
        positions.pop(ticker, None)

    if equity_rows:
        positions_value = 0.0
        equity_rows[-1]["cash"] = cash
        equity_rows[-1]["positions_value"] = positions_value
        equity_rows[-1]["equity"] = cash + positions_value
        equity_rows[-1]["positions_count"] = 0
        equity_rows[-1]["open_symbols"] = ""

    equity_df = pd.DataFrame(equity_rows)
    if equity_df.empty:
        raise ValueError("No equity rows generated during custom backtest")

    equity_df["daily_return"] = equity_df["equity"].pct_change().fillna(0.0)
    equity_df["running_max"] = equity_df["equity"].cummax()
    equity_df["drawdown"] = equity_df["equity"] / equity_df["running_max"] - 1.0

    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        trades_df = pd.DataFrame(
            columns=[
                "ticker",
                "entry_date",
                "exit_date",
                "entry_price",
                "exit_price",
                "qty",
                "cost_basis",
                "exit_value",
                "return_pct",
                "exit_reason",
            ]
        )
    else:
        trades_df = trades_df.sort_values(["exit_date", "ticker"]).reset_index(drop=True)

    benchmark_values: list[float] = []
    first_prices = prices_by_date[all_dates[0]]
    tracked_instruments = []
    for ticker in settings.tickers:
        match = first_prices[first_prices["instrument"] == ticker.upper()]
        if match.empty:
            continue
        tracked_instruments.append(ticker.upper())

    shares: dict[str, float] = {}
    if tracked_instruments:
        equal_cash = initial_cash / len(tracked_instruments)
        for ticker in tracked_instruments:
            close = float(first_prices[first_prices["instrument"] == ticker]["close"].iloc[0])
            shares[ticker] = equal_cash / close

    for current_date in equity_df["date"]:
        day_prices_df = prices_by_date[pd.Timestamp(current_date)]
        day_prices = {
            str(row["instrument"]).upper(): float(row["close"])
            for _, row in day_prices_df.iterrows()
        }
        benchmark_value = 0.0
        for ticker, qty in shares.items():
            price = day_prices.get(ticker)
            if price is not None:
                benchmark_value += qty * price
        benchmark_values.append(benchmark_value)

    equity_df["benchmark_equity"] = benchmark_values
    final_equity = float(equity_df["equity"].iloc[-1])
    result = {
        "initial_cash": float(initial_cash),
        "final_equity": final_equity,
        "total_return": final_equity / initial_cash - 1.0,
        "max_drawdown": float(equity_df["drawdown"].min()),
        "trades": int(len(trades_df)),
        "win_rate": float((trades_df["return_pct"] > 0).mean()) if not trades_df.empty else 0.0,
        "benchmark_return": (
            float(equity_df["benchmark_equity"].iloc[-1]) / initial_cash - 1.0
            if benchmark_values
            else 0.0
        ),
    }
    return result, equity_df, trades_df


def run_qlib_backtest(
    *,
    provider_uri: str | Path,
    region: str,
    signal_frame: pd.DataFrame,
    benchmark: str,
    initial_cash: float,
    topk: int,
    n_drop: int,
    deal_price: str,
    open_cost: float,
    close_cost: float,
    min_cost: float,
    start_time: str,
    end_time: str,
) -> tuple[pd.DataFrame, object]:
    try:
        import qlib
        from qlib.config import REG_CN, REG_US
        from qlib.contrib.evaluate import backtest_daily
        from qlib.contrib.strategy import TopkDropoutStrategy
    except ImportError as exc:
        raise ImportError("qlib is not installed in the current environment") from exc

    region_value = region.lower()
    if region_value == "us":
        qlib_region = REG_US
        limit_threshold = None
    elif region_value == "cn":
        qlib_region = REG_CN
        limit_threshold = 0.095
    else:
        raise ValueError("region must be 'us' or 'cn'")

    qlib.init(provider_uri=str(Path(provider_uri).expanduser().resolve()), region=qlib_region)

    strategy = TopkDropoutStrategy(
        topk=topk,
        n_drop=n_drop,
        signal=signal_frame,
    )
    report_df, positions = backtest_daily(
        start_time=start_time,
        end_time=end_time,
        strategy=strategy,
        account=initial_cash,
        benchmark=benchmark,
        exchange_kwargs={
            "deal_price": deal_price,
            "open_cost": open_cost,
            "close_cost": close_cost,
            "min_cost": min_cost,
            "limit_threshold": limit_threshold,
        },
    )
    return report_df, positions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a Qlib daily backtest from a signal CSV or generated momentum signal."
    )
    parser.add_argument("--provider-uri", required=True, help="Path to the Qlib binary dataset.")
    parser.add_argument("--output-dir", required=True, help="Directory for report and snapshot outputs.")
    parser.add_argument(
        "--execution-engine",
        choices=["qlib", "custom"],
        default="qlib",
        help="Backtest execution engine.",
    )
    parser.add_argument("--region", default="us", help="Qlib region: us or cn.")
    parser.add_argument("--benchmark", default="SPY", help="Benchmark instrument code.")
    parser.add_argument("--signal-csv", default=None, help="Optional signal CSV with datetime,instrument,score.")
    parser.add_argument(
        "--qlib-ready-dir",
        default="logs/baselines/current_strategy/qlib_ready",
        help="Directory used to build fallback momentum signals.",
    )
    parser.add_argument(
        "--signal-mode",
        choices=["momentum", "strategy"],
        default="momentum",
        help="Signal generation mode when --signal-csv is not provided.",
    )
    parser.add_argument("--momentum-window", type=int, default=20)
    parser.add_argument("--initial-cash", type=float, default=10000.0)
    parser.add_argument("--topk", type=int, default=None)
    parser.add_argument("--n-drop", type=int, default=None)
    parser.add_argument("--deal-price", default="close")
    parser.add_argument("--open-cost", type=float, default=0.0005)
    parser.add_argument("--close-cost", type=float, default=0.0015)
    parser.add_argument("--min-cost", type=float, default=5.0)
    parser.add_argument("--start-time", default=None)
    parser.add_argument("--end-time", default=None)
    parser.add_argument("--settings-json", default="config/strategy_config.json")
    parser.add_argument("--tickers-file", default=None)
    parser.add_argument("--price-period", default="2y")
    parser.add_argument("--trend-weight", type=float, default=1.0)
    parser.add_argument("--rsi-weight", type=float, default=1.0)
    parser.add_argument("--ai-weight", type=float, default=1.0)
    return parser.parse_args()


def _build_signal_frame(args: argparse.Namespace, settings: StrategySettings) -> pd.DataFrame:
    if args.signal_csv:
        return load_signal_frame(args.signal_csv)

    if args.signal_mode == "strategy":
        from src.data_loader import load_cached_price_data_batch

        ai_model_bundle = None
        if settings.use_ai_score:
            try:
                ai_model_bundle = load_ai_score_model()
            except Exception:
                ai_model_bundle = None

        ticker_data = load_cached_price_data_batch(settings.tickers, period=args.price_period)
        return build_strategy_signal_from_price_data(
            ticker_data,
            settings,
            ai_model_bundle=ai_model_bundle,
            trend_weight=args.trend_weight,
            rsi_weight=args.rsi_weight,
            ai_weight=args.ai_weight,
        )

    return build_momentum_signal_from_qlib_ready(
        args.qlib_ready_dir,
        momentum_window=args.momentum_window,
    )


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    settings = load_strategy_settings_from_json(args.settings_json)
    price_frame = load_qlib_ready_price_frame(args.qlib_ready_dir)
    signal_frame = _build_signal_frame(args, settings)

    inferred_start, inferred_end = infer_backtest_window(signal_frame)
    start_time = args.start_time or inferred_start
    end_time = args.end_time or inferred_end
    topk = args.topk if args.topk is not None else (
        settings.max_total_positions if args.signal_mode == "strategy" else 10
    )
    n_drop = args.n_drop if args.n_drop is not None else (
        1 if args.signal_mode == "strategy" else 2
    )

    if topk <= 0:
        raise ValueError("topk must be positive")
    if n_drop < 0:
        raise ValueError("n_drop must be non-negative")

    if args.signal_mode == "strategy" and args.execution_engine == "qlib":
        signal_frame = apply_signal_execution_constraints(
            signal_frame,
            max_active_signals=topk,
            max_new_signals_per_day=settings.max_orders_per_run,
            cooldown_days=settings.buy_cooldown_days,
        )

    signal_csv_path = save_signal_csv(signal_frame, output_dir / "signal.csv")
    positions_path = output_dir / "qlib_positions_summary.json"

    if args.execution_engine == "custom":
        metrics, equity_df, trades_df = run_custom_signal_backtest(
            signal_frame=signal_frame,
            price_frame=price_frame,
            settings=settings,
            initial_cash=args.initial_cash,
            open_cost=args.open_cost,
            close_cost=args.close_cost,
            start_time=start_time,
            end_time=end_time,
            n_drop=n_drop,
        )
        report_path = output_dir / "backtest_equity.csv"
        equity_df.to_csv(report_path, index=False)
        positions_path.write_text(json.dumps({"position_count": 0, "engine": "custom"}), encoding="utf-8")
        trades_path = save_trades_csv(trades_df, output_dir / "qlib_trades.csv")
    else:
        report_df, positions = run_qlib_backtest(
            provider_uri=args.provider_uri,
            region=args.region,
            signal_frame=signal_frame,
            benchmark=args.benchmark,
            initial_cash=args.initial_cash,
            topk=topk,
            n_drop=n_drop,
            deal_price=args.deal_price,
            open_cost=args.open_cost,
            close_cost=args.close_cost,
            min_cost=args.min_cost,
            start_time=start_time,
            end_time=end_time,
        )
        report_path = output_dir / "qlib_report.csv"
        report_df.to_csv(report_path, index=True)
        positions_path.write_text(json.dumps({"position_count": len(positions), "engine": "qlib"}), encoding="utf-8")
        trades_df = extract_trades_from_positions(
            positions,
            build_close_price_lookup(price_frame),
        )
        trades_path = save_trades_csv(trades_df, output_dir / "qlib_trades.csv")
        metrics = compute_report_metrics(report_df, initial_cash=args.initial_cash)
        if not trades_df.empty:
            metrics["trades"] = int(len(trades_df))
            metrics["win_rate"] = float((trades_df["return_pct"] > 0).mean())

    snapshot_args = [
        "generate_qlib_snapshot",
        "--output",
        str(output_dir / "snapshot.json"),
        "--period",
        f"{start_time}:{end_time}",
        "--settings-json",
        args.settings_json,
        "--equity-csv",
        str(report_path),
        "--trades-csv",
        str(trades_path),
        "--provider-uri",
        str(Path(args.provider_uri).expanduser().resolve()),
        "--qlib-region",
        args.region.lower(),
        "--initial-cash",
        str(metrics["initial_cash"]),
        "--final-equity",
        str(metrics["final_equity"]),
        "--total-return",
        str(metrics["total_return"]),
        "--benchmark-return",
        str(metrics["benchmark_return"]),
        "--max-drawdown",
        str(metrics["max_drawdown"]),
        "--trades",
        str(metrics["trades"]),
        "--win-rate",
        str(metrics["win_rate"]),
    ]
    if args.tickers_file:
        snapshot_args.extend(["--tickers-file", args.tickers_file])

    import sys

    original_argv = sys.argv
    try:
        sys.argv = snapshot_args
        generate_qlib_snapshot_main()
    finally:
        sys.argv = original_argv

    print(f"Saved Qlib signal to {signal_csv_path}")
    print(f"Saved Qlib report to {report_path}")
    print(f"Saved Qlib trades to {trades_path}")
    print(f"Saved Qlib positions summary to {positions_path}")
    print(f"Saved Qlib snapshot to {output_dir / 'snapshot.json'}")


if __name__ == "__main__":
    main()
