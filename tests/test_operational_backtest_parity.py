import numpy as np
import pandas as pd
from dataclasses import replace
from types import SimpleNamespace

from src.portfolio_backtester import (
    _sort_tournament_alpha_candidates,
    run_portfolio_backtest,
)
from src.portfolio_sleeves import default_sleeves_config
from src.rank_ai_gate import RankAIGateScore
from src.settings import StrategySettings
from src.sleeved_portfolio_backtester import (
    _daily_profile_parameter_maps,
    run_sleeved_portfolio_backtest,
)


def _price_frame(
    start: float = 100.0,
    end: float = 160.0,
    rows: int = 300,
) -> pd.DataFrame:
    close = np.linspace(start, end, rows)
    return pd.DataFrame(
        {
            "date": pd.bdate_range("2025-01-02", periods=rows),
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "adj_close": close,
            "volume": np.full(rows, 1_000_000),
        }
    )


def _base_kwargs() -> dict:
    return {
        "initial_cash": 10_000.0,
        "max_positions": 1,
        "target_position_pct": 0.30,
        "transaction_cost_pct": 0.0,
        "ma_fast": 5,
        "ma_slow": 20,
        "rsi_buy_limit": 101.0,
    }


def test_tournament_alpha_order_matches_live_rank_ai_blend() -> None:
    candidates = pd.DataFrame(
        [
            {"ticker": "A", "rank_ai_percentile": 1.0, "ai_score": 0.0},
            {"ticker": "B", "rank_ai_percentile": 0.8, "ai_score": 1.0},
        ]
    )

    ranked = _sort_tournament_alpha_candidates(candidates)

    assert ranked["ticker"].tolist() == ["B", "A"]
    assert ranked.iloc[0]["tournament_alpha_score"] == 0.87


def test_tournament_alpha_can_use_rank_only_order() -> None:
    candidates = pd.DataFrame(
        [
            {"ticker": "A", "rank_ai_percentile": 1.0, "ai_score": 0.0},
            {"ticker": "B", "rank_ai_percentile": 0.8, "ai_score": 1.0},
        ]
    )

    ranked = _sort_tournament_alpha_candidates(candidates, rank_weight=1.0)

    assert ranked["ticker"].tolist() == ["A", "B"]


def test_rank_primary_selector_bypasses_conventional_entry_direction() -> None:
    prices = _price_frame(160.0, 100.0)
    score = RankAIGateScore(
        ticker="AAPL",
        score=0.9,
        percentile=1.0,
        allowed=True,
        reason="passed",
    )
    rank_history = {
        pd.Timestamp(date): {"AAPL": score}
        for date in prices["date"]
    }
    operational_settings = SimpleNamespace(
        rank_ai_buy_gate_enabled=True,
        rank_ai_buy_top_k_enabled=True,
        rank_ai_buy_gate_min_score_quantile=0.85,
        rank_ai_buy_gate_top_bucket_pct=0.15,
        max_orders_per_run=1,
        max_total_positions=1,
    )

    _, equity, _ = run_portfolio_backtest(
        ticker_data={"AAPL": prices},
        operational_settings=operational_settings,
        rank_ai_buy_gate_enabled=True,
        rank_ai_primary_selector_enabled=True,
        rank_ai_score_history=rank_history,
        **_base_kwargs(),
    )

    assert equity["positions_count"].max() == 1


def test_direct_product_route_uses_underlying_signal_and_product_price() -> None:
    source = _price_frame()
    product = _price_frame(20.0, 50.0)

    _, equity, trades = run_portfolio_backtest(
        ticker_data={"AAPL": source},
        leveraged_product_data={"AAPB": product},
        leveraged_product_routes={"AAPL": "AAPB"},
        prefer_leveraged_products=True,
        allow_leveraged_etfs=True,
        allow_single_name_leveraged_products=True,
        leveraged_etf_allowlist=["AAPB"],
        max_leveraged_etf_positions=1,
        max_holding_days=10,
        **_base_kwargs(),
    )

    assert equity["open_symbols"].str.contains("AAPB").any()
    assert not trades.empty
    assert set(trades["ticker"]) == {"AAPB"}
    assert set(trades["signal_ticker"]) == {"AAPL"}
    assert trades["leveraged"].all()


def test_direct_product_route_falls_back_when_product_history_is_missing() -> None:
    _, equity, _ = run_portfolio_backtest(
        ticker_data={"AAPL": _price_frame()},
        leveraged_product_routes={"AAPL": "AAPB"},
        prefer_leveraged_products=True,
        allow_leveraged_etfs=True,
        allow_single_name_leveraged_products=True,
        leveraged_etf_allowlist=["AAPB"],
        **_base_kwargs(),
    )

    assert equity["open_symbols"].str.contains("AAPL").any()
    assert not equity["open_symbols"].str.contains("AAPB").any()


def test_entry_risk_override_blocks_leveraged_route() -> None:
    source = _price_frame()
    product = _price_frame(20.0, 50.0)
    overrides = {
        date: {"AAPL": {"allow_leveraged": False}}
        for date in source["date"]
    }

    _, equity, trades = run_portfolio_backtest(
        ticker_data={"AAPL": source},
        leveraged_product_data={"AAPB": product},
        leveraged_product_routes={"AAPL": "AAPB"},
        prefer_leveraged_products=True,
        allow_leveraged_etfs=True,
        allow_single_name_leveraged_products=True,
        leveraged_etf_allowlist=["AAPB"],
        entry_risk_overrides_by_date=overrides,
        max_holding_days=10,
        **_base_kwargs(),
    )

    assert equity["open_symbols"].str.contains("AAPL").any()
    assert not trades.empty
    assert set(trades["ticker"]) == {"AAPL"}
    assert not trades["leveraged"].any()


def test_entry_risk_override_scales_entry_notional() -> None:
    prices = _price_frame()
    overrides = {
        date: {"AAPL": {"notional_multiplier": 0.5}}
        for date in prices["date"]
    }
    _, baseline, _ = run_portfolio_backtest(
        ticker_data={"AAPL": prices},
        **_base_kwargs(),
    )
    _, reduced, _ = run_portfolio_backtest(
        ticker_data={"AAPL": prices},
        entry_risk_overrides_by_date=overrides,
        **_base_kwargs(),
    )

    baseline_entry = baseline[baseline["positions_count"] > 0].iloc[0]
    reduced_entry = reduced[reduced["positions_count"] > 0].iloc[0]
    assert reduced_entry["positions_value"] == baseline_entry["positions_value"] * 0.5


def test_historical_universe_snapshot_blocks_symbols_not_active_that_day() -> None:
    prices = _price_frame()
    _, equity, _ = run_portfolio_backtest(
        ticker_data={"AAPL": prices},
        historical_universe_by_date={prices["date"].min(): ["MSFT"]},
        **_base_kwargs(),
    )

    assert equity["positions_count"].max() == 0


def test_historical_universe_uses_static_fallback_before_first_snapshot() -> None:
    prices = _price_frame()
    _, equity, _ = run_portfolio_backtest(
        ticker_data={"AAPL": prices, "NEW": prices},
        historical_universe_by_date={prices["date"].max(): ["AAPL", "NEW"]},
        base_universe={"AAPL"},
        max_positions=2,
        **{key: value for key, value in _base_kwargs().items() if key != "max_positions"},
    )

    before_snapshot = equity[equity["date"] < prices["date"].max()]
    assert not before_snapshot["open_symbols"].str.contains("NEW").any()


def test_benchmark_universe_excludes_dynamic_additions() -> None:
    flat = _price_frame(100.0, 100.0)
    dynamic = _price_frame(100.0, 300.0)
    result, _, _ = run_portfolio_backtest(
        ticker_data={"AAPL": flat, "NEW": dynamic},
        benchmark_universe={"AAPL"},
        rsi_buy_limit=0.0,
        **{key: value for key, value in _base_kwargs().items() if key != "rsi_buy_limit"},
    )

    assert abs(result.benchmark_return) < 1e-12


def test_cash_reserve_and_nonfractionable_execution_are_enforced() -> None:
    kwargs = _base_kwargs()
    kwargs["target_position_pct"] = 1.0
    _, equity, _ = run_portfolio_backtest(
        ticker_data={"AAPL": _price_frame(100.0, 101.0)},
        cash_reserve_pct=0.20,
        fractionable_symbols=set(),
        **kwargs,
    )

    first = equity[equity["positions_count"] > 0].iloc[0]
    assert first["positions_value"] <= 8_000.01
    assert first["cash"] >= 1_999.99


def test_partial_take_profit_is_recorded_once_per_holding() -> None:
    _, _, trades = run_portfolio_backtest(
        ticker_data={"AAPL": _price_frame(100.0, 180.0)},
        take_profit_partial_pct=0.03,
        partial_exit_ratio=0.5,
        max_holding_days=0,
        **_base_kwargs(),
    )

    partials = trades[trades["exit_reason"] == "PARTIAL_TAKE_PROFIT"]
    assert len(partials) == 1
    assert partials.iloc[0]["qty"] > 0


def test_sleeved_backtest_keeps_cash_budget_and_tags_component_trades(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "src.sleeved_portfolio_backtester.load_named_profile_overlay",
        lambda _: {
            "max_total_positions": 12,
            "max_position_pct": 0.35,
            "max_holding_days": 14,
            "use_ai_score": False,
            "rank_ai_buy_gate_enabled": False,
            "portfolio_sleeves_enabled": False,
        },
    )
    settings = StrategySettings(
        tickers=["AAPL"],
        ma_fast=5,
        ma_slow=20,
        rsi_buy_limit=101.0,
        max_position_pct=0.15,
        max_total_positions=12,
        max_orders_per_run=6,
        portfolio_sleeves_enabled=True,
        sleeves=default_sleeves_config(),
    )

    result, equity, trades = run_sleeved_portfolio_backtest(
        settings,
        ticker_data={"AAPL": _price_frame()},
        initial_cash=10_000.0,
        transaction_cost_pct=0.0,
        apply_dynamic_profiles=False,
    )

    assert result.final_equity > 10_000.0
    assert {"core_equity", "tournament_equity"}.issubset(equity.columns)
    assert equity.iloc[0]["cash"] >= 2_000.0
    assert not trades.empty
    assert set(trades["sleeve_id"]) == {"core", "tournament"}


def test_daily_profile_maps_scale_account_position_cap_to_sleeve(
    monkeypatch,
) -> None:
    settings = StrategySettings(
        tickers=["SPY"],
        ma_fast=30,
        ma_slow=200,
        rsi_buy_limit=100.0,
        max_position_pct=0.15,
        max_total_positions=12,
    )
    profile = replace(
        settings,
        ai_score_buy_threshold=0.3,
        tournament_alpha_rank_weight=1.0,
        stop_loss_pct=0.12,
        take_profit_pct=0.30,
    )
    date = pd.Timestamp("2026-07-13")
    monkeypatch.setattr(
        "src.sleeved_portfolio_backtester.compute_daily_regime",
        lambda *_: pd.Series(["BULL"], index=[date]),
    )
    monkeypatch.setattr(
        "src.sleeved_portfolio_backtester.apply_dynamic_profile",
        lambda *_: (profile, "AGGRESSIVE"),
    )

    entry, exits = _daily_profile_parameter_maps(
        settings,
        ticker_data={"SPY": _price_frame()},
        vix_df=_price_frame(),
        sleeve_id="core",
        sleeve_target_weight=0.5,
    )

    assert entry[date]["target_position_pct"] == 0.30
    assert entry[date]["ai_score_buy_threshold"] == 0.3
    assert entry[date]["tournament_alpha_rank_weight"] == 1.0
    assert exits[date]["stop_loss_pct"] == 0.12
    assert exits[date]["take_profit_pct"] == 0.30
