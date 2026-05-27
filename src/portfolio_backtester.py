from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.strategy import add_indicators, build_market_regime_frame
from src.features import FEATURE_COLUMNS, build_features
from src.ml_model import load_ai_score_model
from src.portfolio_optimizer import compute_candidate_weights


@dataclass
class PortfolioBacktestResult:
    initial_cash: float
    final_equity: float
    total_return: float
    max_drawdown: float
    trades: int
    win_rate: float
    benchmark_return: float
    sharpe_ratio: float = 0.0


def _prepare_ticker_frame(
    ticker: str,
    df: pd.DataFrame,
    ma_fast: int = 20,
    ma_slow: int = 50,
    rsi_buy_limit: float = 70,
    use_ai_score: bool = False,
    ai_score_buy_threshold: float = 0.55,
    ai_model_bundle=None,
    ai_score_frame: pd.DataFrame | None = None,
    relative_strength_lookback_days: int = 20,
    volume_filter_enabled: bool = False,
    volume_lookback_days: int = 20,
    min_volume_ratio: float = 1.0,
    volatility_filter_enabled: bool = False,
    volatility_lookback_days: int = 20,
    max_volatility: float = 0.04,
) -> pd.DataFrame:
    raw_df = df.copy()
    df = add_indicators(df, ma_fast=ma_fast, ma_slow=ma_slow).copy()
    df = df.sort_values("date").reset_index(drop=True)

    df["ticker"] = ticker
    df["ai_score"] = None
    df["relative_return"] = df["close"].pct_change(relative_strength_lookback_days)
    df["volume_ratio"] = df["volume"] / df["volume"].rolling(volume_lookback_days).mean()
    df["volatility"] = df["close"].pct_change().rolling(volatility_lookback_days).std()
    df["volatility_20d"] = df["volatility"]

    if use_ai_score and ai_score_frame is not None:
        score_df = ai_score_frame[["date", "ai_score"]].copy()
        score_df["date"] = pd.to_datetime(score_df["date"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.merge(score_df, on="date", how="left", suffixes=("", "_model"))
        if "ai_score_model" in df.columns:
            df["ai_score"] = df["ai_score_model"]
            df = df.drop(columns=["ai_score_model"])
    elif use_ai_score:
        try:
            if ai_model_bundle is None:
                raise ValueError("AI score model was not loaded")
            score_df = build_ai_score_frame(raw_df, ai_model_bundle, vix_df=None, spy_df=None)
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

    if volume_filter_enabled:
        df["buy_signal"] = df["buy_signal"] & (
            pd.to_numeric(df["volume_ratio"], errors="coerce") >= min_volume_ratio
        )

    if volatility_filter_enabled:
        df["buy_signal"] = df["buy_signal"] & (
            pd.to_numeric(df["volatility"], errors="coerce") <= max_volatility
        )

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
            "relative_return",
            "volume_ratio",
            "volatility",
            "volatility_20d",
            "buy_signal",
            "sell_signal",
        ]
    ]


def build_ai_score_frame(
    df: pd.DataFrame,
    ai_model_bundle,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    feature_df = build_features(
        df,
        prediction_horizon=ai_model_bundle.prediction_horizon,
        target_return_threshold=ai_model_bundle.target_return_threshold,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    score_df = feature_df[["date"]].copy()
    score_df["ai_score"] = ai_model_bundle.predict_proba(
        df, vix_df=vix_df, spy_df=spy_df, macro_df=macro_df
    ).values
    return score_df[["date", "ai_score"]]


def build_ai_score_frames(
    ticker_data: dict[str, pd.DataFrame],
    ai_model_bundle=None,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    if ai_model_bundle is None:
        ai_model_bundle = load_ai_score_model()

    score_frames = {}
    for ticker, df in ticker_data.items():
        score_frames[ticker] = build_ai_score_frame(
            df, ai_model_bundle, vix_df=vix_df, spy_df=spy_df, macro_df=macro_df
        )
    return score_frames


def _apply_market_regime_filter(
    market_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    market_regime_ma_fast: int,
    market_regime_ma_slow: int,
) -> pd.DataFrame:
    regime_df = build_market_regime_frame(
        benchmark_df,
        ma_fast=market_regime_ma_fast,
        ma_slow=market_regime_ma_slow,
    )
    filtered_df = market_df.merge(regime_df, on="date", how="left")
    filtered_df["market_regime_bullish"] = filtered_df["market_regime_bullish"] == True
    filtered_df["buy_signal"] = filtered_df["buy_signal"] & filtered_df["market_regime_bullish"]
    return filtered_df


def _build_benchmark_relative_return_frame(
    benchmark_df: pd.DataFrame,
    lookback_days: int,
) -> pd.DataFrame:
    if benchmark_df.empty:
        raise ValueError("No benchmark price data available for relative strength filter")
    if "date" not in benchmark_df.columns or "close" not in benchmark_df.columns:
        raise ValueError("Benchmark data must contain date and close columns")

    frame = benchmark_df[["date", "close"]].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values("date").reset_index(drop=True)
    frame["benchmark_relative_return"] = frame["close"].pct_change(lookback_days)
    return frame[["date", "benchmark_relative_return"]]


def _apply_relative_strength_filter(
    market_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    lookback_days: int,
    min_excess_return: float,
) -> pd.DataFrame:
    benchmark_returns = _build_benchmark_relative_return_frame(
        benchmark_df,
        lookback_days=lookback_days,
    )
    filtered_df = market_df.merge(benchmark_returns, on="date", how="left")
    filtered_df["relative_strength_excess_return"] = (
        pd.to_numeric(filtered_df["relative_return"], errors="coerce")
        - pd.to_numeric(filtered_df["benchmark_relative_return"], errors="coerce")
    )
    filtered_df["relative_strength_pass"] = (
        filtered_df["relative_strength_excess_return"] >= min_excess_return
    )
    filtered_df["buy_signal"] = filtered_df["buy_signal"] & filtered_df["relative_strength_pass"]
    return filtered_df


def run_portfolio_backtest(
    ticker_data: dict[str, pd.DataFrame],
    benchmark_df: pd.DataFrame | None = None,
    relative_strength_benchmark_df: pd.DataFrame | None = None,
    initial_cash: float = 10000.0,
    max_positions: int = 3,
    target_position_pct: float = 0.30,
    transaction_cost_pct: float = 0.001,
    ma_fast: int = 20,
    ma_slow: int = 50,
    rsi_buy_limit: float = 70,
    use_ai_score: bool = False,
    ai_score_buy_threshold: float = 0.55,
    market_regime_filter_enabled: bool = False,
    market_regime_ma_fast: int = 50,
    market_regime_ma_slow: int = 200,
    stop_loss_pct: float = 0.0,
    take_profit_pct: float = 0.0,
    trailing_stop_pct: float = 0.0,
    rank_trend_weight: float = 1.0,
    rank_ai_weight: float = 0.0,
    rank_momentum_weight: float = 0.0,
    rank_volatility_weight: float = 0.0,
    relative_strength_filter_enabled: bool = False,
    relative_strength_lookback_days: int = 20,
    relative_strength_min_excess_return: float = 0.0,
    volume_filter_enabled: bool = False,
    volume_lookback_days: int = 20,
    min_volume_ratio: float = 1.0,
    volatility_filter_enabled: bool = False,
    volatility_lookback_days: int = 20,
    max_volatility: float = 0.04,
    ai_score_frames: dict[str, pd.DataFrame] | None = None,
    allocation_method: str = "equal_weight",
    mvo_lookback_days: int = 60,
    mvo_min_weight: float = 0.05,
    mvo_max_weight: float = 0.40,
    ai_exit_enabled: bool = False,
    ai_exit_threshold: float = 0.30,
    ai_exit_dynamic_enabled: bool = False,
    ai_exit_vix_low: float = 15.0,
    ai_exit_vix_high: float = 25.0,
    ai_exit_threshold_bull: float = 0.55,
    ai_exit_threshold_bear: float = 0.28,
    vix_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
    evaluation_start_date: str | pd.Timestamp | None = None,
    evaluation_end_date: str | pd.Timestamp | None = None,
) -> tuple[PortfolioBacktestResult, pd.DataFrame, pd.DataFrame]:
    if relative_strength_lookback_days <= 0:
        raise ValueError("relative_strength_lookback_days must be positive")
    if volume_lookback_days <= 0:
        raise ValueError("volume_lookback_days must be positive")
    if min_volume_ratio < 0:
        raise ValueError("min_volume_ratio must be non-negative")
    if volatility_lookback_days <= 0:
        raise ValueError("volatility_lookback_days must be positive")
    if max_volatility < 0:
        raise ValueError("max_volatility must be non-negative")
    if not 0 <= stop_loss_pct < 1:
        raise ValueError("stop_loss_pct must be between 0 and 1")
    if take_profit_pct < 0:
        raise ValueError("take_profit_pct must be non-negative")
    if not 0 <= trailing_stop_pct < 1:
        raise ValueError("trailing_stop_pct must be between 0 and 1")

    ai_model_bundle = None
    if use_ai_score:
        try:
            ai_model_bundle = load_ai_score_model()
        except Exception:
            ai_model_bundle = None

    # SPY data for relative return feature
    spy_df = ticker_data.get("SPY")

    # Pre-compute AI score frames with full context (VIX + macro)
    _ai_score_frames = ai_score_frames
    if use_ai_score and ai_model_bundle is not None and _ai_score_frames is None:
        _ai_score_frames = build_ai_score_frames(
            ticker_data,
            ai_model_bundle=ai_model_bundle,
            vix_df=vix_df,
            spy_df=spy_df,
            macro_df=macro_df,
        )

    prepared_frames = [
        _prepare_ticker_frame(
            ticker,
            df,
            ma_fast=ma_fast,
            ma_slow=ma_slow,
            rsi_buy_limit=rsi_buy_limit,
            use_ai_score=use_ai_score,
            ai_score_buy_threshold=ai_score_buy_threshold,
            ai_model_bundle=ai_model_bundle,
            ai_score_frame=_ai_score_frames.get(ticker) if _ai_score_frames else None,
            relative_strength_lookback_days=relative_strength_lookback_days,
            volume_filter_enabled=volume_filter_enabled,
            volume_lookback_days=volume_lookback_days,
            min_volume_ratio=min_volume_ratio,
            volatility_filter_enabled=volatility_filter_enabled,
            volatility_lookback_days=volatility_lookback_days,
            max_volatility=max_volatility,
        )
        for ticker, df in ticker_data.items()
    ]

    market_df = pd.concat(prepared_frames, ignore_index=True)
    market_df["date"] = pd.to_datetime(market_df["date"])
    market_df = market_df.sort_values(["date", "ticker"]).reset_index(drop=True)
    if market_regime_filter_enabled:
        if benchmark_df is None:
            raise ValueError("benchmark_df is required when market_regime_filter_enabled=True")
        market_df = _apply_market_regime_filter(
            market_df,
            benchmark_df,
            market_regime_ma_fast=market_regime_ma_fast,
            market_regime_ma_slow=market_regime_ma_slow,
        )
    if relative_strength_filter_enabled:
        benchmark_for_relative_strength = relative_strength_benchmark_df
        if benchmark_for_relative_strength is None:
            benchmark_for_relative_strength = benchmark_df
        if benchmark_for_relative_strength is None:
            raise ValueError(
                "relative_strength_benchmark_df is required when "
                "relative_strength_filter_enabled=True"
            )
        market_df = _apply_relative_strength_filter(
            market_df,
            benchmark_for_relative_strength,
            lookback_days=relative_strength_lookback_days,
            min_excess_return=relative_strength_min_excess_return,
        )

    all_dates = sorted(market_df["date"].unique())
    trading_dates = all_dates
    if evaluation_start_date is not None:
        start_ts = pd.Timestamp(evaluation_start_date)
        trading_dates = [date for date in trading_dates if pd.Timestamp(date) >= start_ts]
    if evaluation_end_date is not None:
        end_ts = pd.Timestamp(evaluation_end_date)
        trading_dates = [date for date in trading_dates if pd.Timestamp(date) <= end_ts]
    if not trading_dates:
        raise ValueError("No dates available inside the requested evaluation window")

    # VIX lookup index for dynamic AI exit threshold
    _vix_by_date: dict = {}
    if ai_exit_dynamic_enabled and vix_df is not None and not vix_df.empty:
        _vix_tmp = vix_df.copy()
        _vix_tmp["date"] = pd.to_datetime(_vix_tmp["date"])
        _vix_tmp = _vix_tmp.sort_values("date")
        close_col = "adj_close" if "adj_close" in _vix_tmp.columns else "close"
        _vix_by_date = dict(zip(_vix_tmp["date"], _vix_tmp[close_col]))

    cash = initial_cash
    positions: dict[str, dict] = {}

    trades: list[dict] = []
    equity_rows: list[dict] = []

    for current_date in trading_dates:
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
            position = positions[ticker]
            position["highest_price"] = max(
                float(position.get("highest_price", position["entry_price"])),
                close,
            )

            exit_reason = None
            gross_return_pct = (close / float(position["entry_price"])) - 1.0
            drawdown_from_high = (close / float(position["highest_price"])) - 1.0

            ai_exit_triggered = False
            if ai_exit_enabled:
                ai_score_val = pd.to_numeric(row.get("ai_score"), errors="coerce")
                if not pd.isna(ai_score_val):
                    effective_threshold = ai_exit_threshold
                    if ai_exit_dynamic_enabled and _vix_by_date:
                        ts = pd.Timestamp(current_date)
                        vix_val = _vix_by_date.get(ts)
                        if vix_val is None:
                            past = {k: v for k, v in _vix_by_date.items() if k <= ts}
                            vix_val = past[max(past)] if past else None
                        if vix_val is not None:
                            if float(vix_val) < ai_exit_vix_low:
                                effective_threshold = ai_exit_threshold_bull
                            elif float(vix_val) > ai_exit_vix_high:
                                effective_threshold = ai_exit_threshold_bear
                    ai_exit_triggered = float(ai_score_val) < effective_threshold

            if stop_loss_pct > 0 and gross_return_pct <= -stop_loss_pct:
                exit_reason = "STOP_LOSS"
            elif trailing_stop_pct > 0 and drawdown_from_high <= -trailing_stop_pct:
                exit_reason = "TRAILING_STOP"
            elif ai_exit_triggered:
                exit_reason = "AI_EXIT"
            elif bool(row["sell_signal"]):
                exit_reason = "SELL_SIGNAL"
            elif take_profit_pct > 0 and gross_return_pct >= take_profit_pct:
                exit_reason = "TAKE_PROFIT"

            if exit_reason is not None:
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
                        "exit_reason": exit_reason,
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
            buy_candidates["rank_ai_score"] = pd.to_numeric(
                buy_candidates["ai_score"],
                errors="coerce",
            ).fillna(0.0)
            buy_candidates["rank_momentum"] = pd.to_numeric(
                buy_candidates["relative_return"],
                errors="coerce",
            ).fillna(0.0)
            buy_candidates["rank_volatility"] = pd.to_numeric(
                buy_candidates["volatility"],
                errors="coerce",
            ).fillna(0.0)
            buy_candidates["rank_score"] = (
                rank_trend_weight * (buy_candidates["trend_strength"] - 1.0)
                + rank_ai_weight * buy_candidates["rank_ai_score"]
                + rank_momentum_weight * buy_candidates["rank_momentum"]
                - rank_volatility_weight * buy_candidates["rank_volatility"]
            )

            buy_candidates = buy_candidates.sort_values(
                ["rank_score", "trend_strength", "rsi"],
                ascending=[False, False, True],
            )

            selected = buy_candidates.head(slots_left)
            candidate_tickers = selected["ticker"].tolist()

            # Compute dynamic weights when using MVO/BL
            if allocation_method != "equal_weight" and len(candidate_tickers) > 1:
                candidate_ai_scores = {
                    row["ticker"]: float(
                        pd.to_numeric(row["ai_score"], errors="coerce") or 0.5
                    )
                    for _, row in selected.iterrows()
                }
                alloc_weights = compute_candidate_weights(
                    market_df=market_df,
                    candidate_tickers=candidate_tickers,
                    current_date=current_date,
                    ai_scores=candidate_ai_scores,
                    allocation_method=allocation_method,
                    lookback_days=mvo_lookback_days,
                    min_weight=mvo_min_weight,
                    max_weight=mvo_max_weight,
                )
                # Total capital same as equal-weight baseline: N * target_position_pct * equity
                total_to_deploy = len(candidate_tickers) * target_position_pct * equity
            else:
                alloc_weights = {t: 1.0 / max(len(candidate_tickers), 1) for t in candidate_tickers}
                total_to_deploy = None  # use original target_position_pct per ticker

            for _, row in selected.iterrows():
                ticker = row["ticker"]
                close = float(row["close"])

                if close <= 0:
                    continue

                if total_to_deploy is not None:
                    target_value = total_to_deploy * alloc_weights.get(
                        ticker, 1.0 / len(candidate_tickers)
                    )
                else:
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
                    "highest_price": close,
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

    # Annualized Sharpe (252 trading days, risk-free=0)
    daily_returns = equity_df["daily_return"]
    std = float(daily_returns.std())
    sharpe_ratio = float(daily_returns.mean() / std * (252 ** 0.5)) if std > 1e-10 else 0.0

    result = PortfolioBacktestResult(
        initial_cash=initial_cash,
        final_equity=final_equity,
        total_return=total_return,
        max_drawdown=max_drawdown,
        trades=trades_count,
        win_rate=win_rate,
        benchmark_return=benchmark_return,
        sharpe_ratio=sharpe_ratio,
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
                "sharpe_ratio": result.sharpe_ratio,
                "trades": result.trades,
                "win_rate": result.win_rate,
            }
        ]
    )

    summary_df.to_csv(output_dir / "portfolio_summary.csv", index=False)
    equity_df.to_csv(output_dir / "portfolio_equity.csv", index=False)
    trades_df.to_csv(output_dir / "portfolio_trades.csv", index=False)
