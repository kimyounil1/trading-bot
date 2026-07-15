"""Budget-isolated core/tournament/cash sleeve portfolio backtest."""

from __future__ import annotations

from dataclasses import replace
import math
from typing import Any

import pandas as pd

from src.portfolio_backtest_settings import portfolio_backtest_kwargs
from src.portfolio_backtester import (
    PortfolioBacktestResult,
    build_ai_score_frames,
    run_portfolio_backtest,
)
from src.portfolio_sleeves import (
    CASH_SLEEVE_ID,
    CORE_SLEEVE_ID,
    TOURNAMENT_SLEEVE_ID,
    load_sleeve_definitions,
)
from src.market_regime import compute_daily_regime
from src.settings import (
    StrategySettings,
    apply_dynamic_profile,
    merge_settings_overlay,
)
from src.rank_ai_gate import build_rank_ai_gate_score_history
from src.trading_config_guard import load_named_profile_overlay


def _daily_profile_parameter_maps(
    settings: StrategySettings,
    *,
    ticker_data: dict[str, pd.DataFrame],
    vix_df: pd.DataFrame | None,
    sleeve_id: str,
    sleeve_target_weight: float,
    profile_overrides_by_regime: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[pd.Timestamp, dict[str, Any]], dict[pd.Timestamp, dict[str, Any]]]:
    spy_df = ticker_data.get("SPY")
    if spy_df is None or spy_df.empty or vix_df is None or vix_df.empty:
        return {}, {}
    regimes = compute_daily_regime(spy_df, vix_df)
    entry: dict[pd.Timestamp, dict[str, Any]] = {}
    exits: dict[pd.Timestamp, dict[str, Any]] = {}
    tournament_overlay = (
        load_named_profile_overlay("tournament_paper")
        if sleeve_id == TOURNAMENT_SLEEVE_ID
        else None
    )
    for date, regime in regimes.items():
        regime_name = str(regime).upper()
        dynamic, _ = apply_dynamic_profile(settings, regime_name)
        research_override = (profile_overrides_by_regime or {}).get(regime_name)
        if research_override:
            dynamic = merge_settings_overlay(dynamic, research_override)
        entry_settings = (
            merge_settings_overlay(dynamic, tournament_overlay)
            if tournament_overlay is not None
            else dynamic
        )
        normalized_date = pd.Timestamp(date).normalize()
        entry[normalized_date] = {
            "ma_fast": entry_settings.ma_fast,
            "ma_slow": entry_settings.ma_slow,
            "rsi_buy_limit": entry_settings.rsi_buy_limit,
            "ai_score_buy_threshold": entry_settings.ai_score_buy_threshold,
            "relative_strength_min_excess_return": (
                entry_settings.relative_strength_min_excess_return
            ),
            "max_positions": entry_settings.max_total_positions,
            "target_position_pct": min(
                1.0,
                entry_settings.max_position_pct / sleeve_target_weight,
            ),
            "allocation_method": entry_settings.allocation_method,
            "tournament_alpha_rank_weight": (
                entry_settings.tournament_alpha_rank_weight
            ),
        }
        # Live exits use the account-wide dynamic profile, not the tournament
        # buy overlay. Keep that behavior explicit in the replay.
        exits[normalized_date] = {
            "stop_loss_pct": dynamic.stop_loss_pct,
            "take_profit_pct": dynamic.take_profit_pct,
            "trailing_stop_pct": dynamic.trailing_stop_pct,
            "max_holding_days": dynamic.max_holding_days,
        }
    return entry, exits


def _sleeve_settings(
    settings: StrategySettings,
    *,
    sleeve_id: str,
    target_weight: float,
) -> StrategySettings:
    active = settings
    if sleeve_id == TOURNAMENT_SLEEVE_ID:
        active = merge_settings_overlay(
            settings,
            load_named_profile_overlay("tournament_paper"),
        )
    account_position_pct = float(active.max_position_pct)
    sleeve_position_pct = min(1.0, account_position_pct / target_weight)
    return replace(
        active,
        max_position_pct=sleeve_position_pct,
        portfolio_sleeves_enabled=False,
    )


def run_sleeved_portfolio_backtest(
    settings: StrategySettings,
    *,
    ticker_data: dict[str, pd.DataFrame],
    benchmark_df: pd.DataFrame | None = None,
    relative_strength_benchmark_df: pd.DataFrame | None = None,
    vix_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
    initial_cash: float = 10_000.0,
    transaction_cost_pct: float = 0.001,
    evaluation_start_date: Any | None = None,
    evaluation_end_date: Any | None = None,
    leveraged_product_data: dict[str, pd.DataFrame] | None = None,
    leveraged_product_routes: dict[str, str] | None = None,
    historical_universe_by_date: dict[Any, list[str]] | None = None,
    base_universe: set[str] | list[str] | None = None,
    benchmark_universe: set[str] | list[str] | None = None,
    ai_score_frames: dict[str, pd.DataFrame] | None = None,
    rank_ai_score_history: dict[Any, dict[str, Any]] | None = None,
    rank_ai_primary_selector_enabled: bool | None = None,
    entry_risk_overrides_by_date: dict[
        Any, dict[str, dict[str, Any]]
    ] | None = None,
    fractionable_symbols: set[str] | None = None,
    include_external_filters: bool = False,
    apply_dynamic_profiles: bool = True,
    dynamic_profile_overrides_by_regime: dict[str, dict[str, Any]] | None = None,
) -> tuple[PortfolioBacktestResult, pd.DataFrame, pd.DataFrame]:
    """Run configured sleeves independently and aggregate their daily ledgers.

    Sleeve budgets are isolated, matching their configured capital authority.
    Cross-sleeve duplicate-symbol and intraday order contention are deliberately
    left visible for attribution instead of being silently resolved.
    """
    definitions = load_sleeve_definitions(settings)
    shared_ai_scores = ai_score_frames
    if settings.use_ai_score and shared_ai_scores is None:
        shared_ai_scores = build_ai_score_frames(
            ticker_data,
            vix_df=vix_df,
            spy_df=ticker_data.get("SPY"),
            macro_df=macro_df,
        )
    shared_rank_history = rank_ai_score_history
    if settings.rank_ai_buy_gate_enabled and shared_rank_history is None:
        shared_rank_history = build_rank_ai_gate_score_history(
            ticker_data,
            settings,
            vix_df=vix_df,
            spy_df=ticker_data.get("SPY"),
            macro_df=macro_df,
            historical_universe_by_date=historical_universe_by_date,
            base_universe=base_universe,
        )
    active = {
        sleeve_id: definition
        for sleeve_id, definition in definitions.items()
        if definition.enabled and definition.target_weight > 0
    }
    if not active:
        kwargs = portfolio_backtest_kwargs(
            settings,
            ticker_data=ticker_data,
            benchmark_df=benchmark_df,
            relative_strength_benchmark_df=relative_strength_benchmark_df,
            vix_df=vix_df,
            macro_df=macro_df,
            ai_score_frames=shared_ai_scores,
            initial_cash=initial_cash,
            transaction_cost_pct=transaction_cost_pct,
            evaluation_start_date=evaluation_start_date,
            evaluation_end_date=evaluation_end_date,
            leveraged_product_data=leveraged_product_data,
            leveraged_product_routes=leveraged_product_routes,
            historical_universe_by_date=historical_universe_by_date,
            base_universe=base_universe,
            benchmark_universe=benchmark_universe,
            rank_ai_score_history=shared_rank_history,
            rank_ai_primary_selector_enabled=rank_ai_primary_selector_enabled,
            entry_risk_overrides_by_date=entry_risk_overrides_by_date,
            fractionable_symbols=fractionable_symbols,
            include_external_filters=include_external_filters,
        )
        return run_portfolio_backtest(**kwargs)

    component_equity: dict[str, pd.DataFrame] = {}
    component_results: dict[str, PortfolioBacktestResult] = {}
    trade_frames: list[pd.DataFrame] = []
    entry_frames: list[pd.DataFrame] = []
    for sleeve_id in (CORE_SLEEVE_ID, TOURNAMENT_SLEEVE_ID):
        definition = active.get(sleeve_id)
        if definition is None:
            continue
        sleeve_cash = initial_cash * float(definition.target_weight)
        active_settings = _sleeve_settings(
            settings,
            sleeve_id=sleeve_id,
            target_weight=float(definition.target_weight),
        )
        entry_overrides: dict[pd.Timestamp, dict[str, Any]] = {}
        exit_overrides: dict[pd.Timestamp, dict[str, Any]] = {}
        if apply_dynamic_profiles:
            entry_overrides, exit_overrides = _daily_profile_parameter_maps(
                settings,
                ticker_data=ticker_data,
                vix_df=vix_df,
                sleeve_id=sleeve_id,
                sleeve_target_weight=float(definition.target_weight),
                profile_overrides_by_regime=dynamic_profile_overrides_by_regime,
            )
        kwargs = portfolio_backtest_kwargs(
            active_settings,
            ticker_data=ticker_data,
            benchmark_df=benchmark_df,
            relative_strength_benchmark_df=relative_strength_benchmark_df,
            vix_df=vix_df,
            macro_df=macro_df,
            ai_score_frames=shared_ai_scores,
            initial_cash=sleeve_cash,
            transaction_cost_pct=transaction_cost_pct,
            evaluation_start_date=evaluation_start_date,
            evaluation_end_date=evaluation_end_date,
            leveraged_product_data=leveraged_product_data,
            leveraged_product_routes=leveraged_product_routes,
            historical_universe_by_date=historical_universe_by_date,
            base_universe=base_universe,
            benchmark_universe=benchmark_universe,
            rank_ai_score_history=shared_rank_history,
            rank_ai_primary_selector_enabled=rank_ai_primary_selector_enabled,
            entry_parameter_overrides_by_date=entry_overrides,
            entry_risk_overrides_by_date=entry_risk_overrides_by_date,
            exit_parameter_overrides_by_date=exit_overrides,
            tournament_alpha_enabled=(sleeve_id == TOURNAMENT_SLEEVE_ID),
            fractionable_symbols=fractionable_symbols,
            cash_reserve_pct=0.0,
            include_external_filters=include_external_filters,
        )
        result, equity, trades = run_portfolio_backtest(**kwargs)
        entries = equity.attrs.get("entry_events")
        if isinstance(entries, pd.DataFrame) and not entries.empty:
            tagged_entries = entries.copy()
            tagged_entries["sleeve_id"] = sleeve_id
            entry_frames.append(tagged_entries)
        component_results[sleeve_id] = result
        component_equity[sleeve_id] = equity.copy()
        if not trades.empty:
            tagged = trades.copy()
            tagged["sleeve_id"] = sleeve_id
            trade_frames.append(tagged)

    cash_weight = float(
        active.get(CASH_SLEEVE_ID).target_weight
        if active.get(CASH_SLEEVE_ID) is not None
        else 0.0
    )
    static_cash = initial_cash * cash_weight
    dates = sorted(
        {
            pd.Timestamp(date)
            for equity in component_equity.values()
            for date in pd.to_datetime(equity["date"])
        }
    )
    combined = pd.DataFrame({"date": dates}).set_index("date")
    for sleeve_id, equity in component_equity.items():
        frame = equity.copy()
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.set_index("date").reindex(combined.index).ffill()
        combined[f"{sleeve_id}_equity"] = frame["equity"]
        combined[f"{sleeve_id}_cash"] = frame["cash"]
        combined[f"{sleeve_id}_positions_value"] = frame["positions_value"]
        combined[f"{sleeve_id}_positions_count"] = frame["positions_count"]
        combined[f"{sleeve_id}_open_symbols"] = frame["open_symbols"].fillna("")

    equity_columns = [column for column in combined if column.endswith("_equity")]
    cash_columns = [column for column in combined if column.endswith("_cash")]
    position_value_columns = [
        column for column in combined if column.endswith("_positions_value")
    ]
    position_count_columns = [
        column for column in combined if column.endswith("_positions_count")
    ]
    combined["cash"] = combined[cash_columns].sum(axis=1) + static_cash
    combined["positions_value"] = combined[position_value_columns].sum(axis=1)
    combined["equity"] = combined[equity_columns].sum(axis=1) + static_cash
    combined["positions_count"] = combined[position_count_columns].sum(axis=1)
    combined["open_symbols"] = combined.apply(
        lambda row: "|".join(
            f"{sleeve_id}:{row.get(f'{sleeve_id}_open_symbols', '')}"
            for sleeve_id in (CORE_SLEEVE_ID, TOURNAMENT_SLEEVE_ID)
            if row.get(f"{sleeve_id}_open_symbols", "")
        ),
        axis=1,
    )
    combined["borrowed_cash"] = 0.0
    combined["gross_exposure_pct"] = combined["positions_value"] / combined["equity"]
    combined["cumulative_margin_interest"] = 0.0
    combined["daily_return"] = combined["equity"].pct_change().fillna(0.0)
    combined["running_max"] = combined["equity"].cummax()
    combined["drawdown"] = combined["equity"] / combined["running_max"] - 1.0

    benchmark_source = next(iter(component_equity.values()))
    benchmark_scale = initial_cash / float(
        next(iter(component_results.values())).initial_cash
    )
    combined["benchmark_equity"] = (
        pd.Series(
            benchmark_source["benchmark_equity"].to_numpy(),
            index=pd.to_datetime(benchmark_source["date"]),
        )
        .reindex(combined.index)
        .ffill()
        * benchmark_scale
    )
    combined = combined.reset_index()
    combined.attrs["entry_events"] = (
        pd.concat(entry_frames, ignore_index=True)
        if entry_frames
        else pd.DataFrame()
    )

    trades = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()
    final_equity = float(combined.iloc[-1]["equity"])
    total_return = final_equity / initial_cash - 1.0
    daily = combined["daily_return"]
    std = float(daily.std())
    result = PortfolioBacktestResult(
        initial_cash=initial_cash,
        final_equity=final_equity,
        total_return=total_return,
        max_drawdown=float(combined["drawdown"].min()),
        trades=int(len(trades)),
        win_rate=(
            float((trades["return_pct"] > 0).mean()) if not trades.empty else 0.0
        ),
        benchmark_return=float(combined.iloc[-1]["benchmark_equity"] / initial_cash - 1.0),
        sharpe_ratio=(float(daily.mean() / std * math.sqrt(252)) if std > 1e-10 else 0.0),
    )
    return result, combined, trades
