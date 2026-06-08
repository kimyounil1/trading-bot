from __future__ import annotations

import src.config  # noqa: F401  # load .env (GEMINI_API_KEY) before LLM

import argparse
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd
from src.settings import load_settings, apply_dynamic_profile
from src.data_loader import load_price_data_batch
from src.strategy import add_indicators, generate_signal, is_bullish_market_regime
from src.logger import log_execution_audit, log_signal, log_order, log_order_status
from src.risk_manager import (
    ExitDecision,
    apply_buy_safety_limits,
    apply_effective_leverage_exposure_limits,
    apply_portfolio_exposure_limits,
    check_additional_buy_allowed,
    check_buy_allowed,
    check_exit_allowed,
    get_recent_buy_symbols,
    get_today_buy_notional,
)
from src.alpaca_client import get_position_entry_date
from src.order_intent import AuditContext, build_audit_context, build_buy_intent
from src.broker_adapter import get_broker_adapter
from src.live_deploy_guard import assert_live_execution_allowed
from src.live_readiness import assert_live_readiness_for_execute
from src.risk.live_safety import LiveSafetyGuard
from src.trading_config_guard import (
    apply_environment_profile,
    resolve_trading_environment,
    validate_trading_config,
)
from src.market_clock import get_market_clock
from src.notifier import notify_order, notify_error, notify_run_summary, notify_info
from src.ml_model import load_ai_score_model, predict_ai_score_from_bundle
from src.instrument_meta import format_audit_reason
from src.margin_leverage_paper_gate import (
    apply_margin_leverage_paper_overrides,
    evaluate_margin_leverage_buy_block,
)
from src.market_regime import get_current_regime
from src.buy_guards import apply_sector_score_bonus, apply_shared_buy_guards
from src.llm_analyst import llm_cache_only_for_run
from src.macro_events import get_macro_event_risk
from src.candidate_cache import get_dynamic_universe
from src.sector_rotation import get_sector_leadership
from src.position_dust import (
    count_meaningful_positions,
    dust_position_min_usd,
    effective_position,
    is_dust_position,
    meaningful_gross_exposure,
    meaningful_open_symbols,
)
from src.position_sizing import (
    cap_single_order_amount,
    conviction_adjustments,
)
from src.portfolio_sleeves import (
    CORE_SLEEVE_ID,
    PortfolioSleeveAllocator,
    sleeve_fields_for_audit,
    sleeves_enabled,
    trim_candidates_to_sleeve_budget,
    validate_sleeve_open_order_budget,
)
from src.rank_ai_gate import apply_rank_ai_buy_gate, build_rank_ai_gate_scores

# 트레일링 스탑용 최고점 기록 경로
PEAKS_PATH = Path("data/trailing_peaks.json")

def _quarantine_corrupt_peaks_file(path: Path) -> None:
    corrupt_path = path.with_suffix(f"{path.suffix}.corrupt")
    try:
        if corrupt_path.exists():
            corrupt_path.unlink()
        path.replace(corrupt_path)
        print(f"Warning: moved corrupt peaks file to {corrupt_path}")
    except OSError as exc:
        print(f"Warning: failed to quarantine corrupt peaks file {path}: {exc}")

def _normalize_peaks(payload: object) -> dict[str, float]:
    if not isinstance(payload, dict):
        raise ValueError("peaks payload must be a JSON object")

    normalized: dict[str, float] = {}
    for ticker, value in payload.items():
        if ticker is None:
            continue
        try:
            normalized[str(ticker).strip().upper()] = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid peak value for {ticker!r}: {value!r}") from exc
    return normalized

def _load_peaks() -> dict[str, float]:
    if not PEAKS_PATH.exists():
        return {}

    try:
        payload = json.loads(PEAKS_PATH.read_text(encoding="utf-8"))
        return _normalize_peaks(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Warning: failed to load peaks from {PEAKS_PATH}: {exc}")
        _quarantine_corrupt_peaks_file(PEAKS_PATH)
        return {}

def _save_peaks(peaks: dict[str, float]) -> None:
    PEAKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_peaks(peaks)
    temp_path = PEAKS_PATH.with_suffix(f"{PEAKS_PATH.suffix}.tmp")
    serialized = json.dumps(normalized, indent=2, sort_keys=True)
    temp_path.write_text(serialized, encoding="utf-8")
    with temp_path.open("r+", encoding="utf-8") as handle:
        handle.flush()
        os.fsync(handle.fileno())
    temp_path.replace(PEAKS_PATH)

from src.daily_bar_session import check_price_frame_freshness as _check_price_frame_freshness
from src.daily_bar_session import drop_incomplete_session_bar


def _format_llm_verdict(is_ok: bool | None, reason: str = "") -> str:
    if is_ok is None:
        return ""
    verdict = "ACCEPT" if is_ok else "REJECT"
    return f"{verdict}: {reason}" if reason else verdict


def _summarize_run_metrics(
    live_order_count: int,
    skipped_reasons: Counter,
    data_error_count: int,
    api_error_count: int,
) -> str:
    skip_summary = ", ".join(
        f"{reason}={count}" for reason, count in skipped_reasons.most_common()
    ) or "none"
    return (
        f"orders_submitted={live_order_count}, "
        f"skips={skip_summary}, "
        f"data_errors={data_error_count}, "
        f"api_errors={api_error_count}"
    )


def _resolve_full_exit_reason(
    *,
    unrealized_plpc: float,
    stop_loss_pct: float,
    take_profit_pct: float,
    trailing_drawdown: float | None,
    trailing_stop_pct: float,
    signal: str,
    ai_exit_triggered: bool,
    holding_days: int = 0,
    max_holding_days: int = 30,
) -> str | None:
    if stop_loss_pct > 0 and unrealized_plpc <= -stop_loss_pct:
        return "stop loss triggered"
    if max_holding_days > 0 and holding_days >= max_holding_days:
        return f"max holding period reached ({holding_days} days)"
    if (
        trailing_drawdown is not None
        and trailing_stop_pct > 0
        and trailing_drawdown >= trailing_stop_pct
    ):
        return "trailing stop triggered"
    if ai_exit_triggered:
        return "ai exit triggered"
    if signal == "SELL":
        return "strategy sell signal"
    if take_profit_pct > 0 and unrealized_plpc >= take_profit_pct:
        return "take profit triggered"
    return None
from src.macro_loader import load_macro_data


def _apply_volume_volatility_filters(signal: str, indicator_df, settings) -> str:
    if signal != "BUY":
        return signal

    latest = indicator_df.iloc[-1]

    if getattr(settings, "volume_filter_enabled", False):
        lookback = int(getattr(settings, "volume_lookback_days", 20))
        if lookback <= 0:
            raise ValueError("volume_lookback_days must be positive")
        volume_ma = indicator_df["volume"].rolling(lookback).mean().iloc[-1]
        if (
            pd.isna(volume_ma)
            or volume_ma <= 0
            or latest["volume"] / volume_ma < float(settings.min_volume_ratio)
        ):
            return "HOLD"

    if getattr(settings, "volatility_filter_enabled", False):
        lookback = int(getattr(settings, "volatility_lookback_days", 20))
        if lookback <= 0:
            raise ValueError("volatility_lookback_days must be positive")
        volatility = indicator_df["close"].pct_change().rolling(lookback).std().iloc[-1]
        if pd.isna(volatility) or volatility > float(settings.max_volatility):
            return "HOLD"

    return signal


def _offline_account_summary() -> dict:
    return {
        "status": "UNKNOWN",
        "currency": "USD",
        "cash": 0.0,
        "portfolio_value": 0.0,
        "buying_power": 0.0,
        "positions_count": 0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI trading bot MVP. Default mode is dry-run."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Submit real paper orders to Alpaca. Without this flag, dry-run only.",
    )
    return parser.parse_args()


def get_signal_for_ticker(
    ticker: str,
    raw_df,
    settings,
    ai_model_bundle=None,
    market_regime_bullish: bool = True,
    vix_df=None,
    spy_df=None,
    macro_df=None,
    market_clock=None,
) -> tuple[str, object, float | None]:
    if raw_df.empty:
        raise ValueError(f"No price data available for {ticker}")

    signal_df = (
        drop_incomplete_session_bar(raw_df, market_clock)
        if market_clock is not None
        else raw_df
    )
    if signal_df.empty:
        raise ValueError(f"No completed daily bars available for {ticker}")

    df = add_indicators(
        signal_df,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
    )
    if df.empty:
        raise ValueError(
            f"Not enough price history to generate signal for {ticker} "
            f"(rows={len(raw_df)}, ma_slow={settings.ma_slow})"
        )
    signal = generate_signal(df, rsi_buy_limit=settings.rsi_buy_limit)
    if (
        signal == "BUY"
        and getattr(settings, "market_regime_filter_enabled", False)
        and not market_regime_bullish
    ):
        signal = "HOLD"
    signal = _apply_volume_volatility_filters(signal, df, settings)
    latest = df.iloc[-1]

    ai_score = None
    if getattr(settings, "use_ai_score", False):
        try:
            if ai_model_bundle is None:
                raise ValueError("AI score model was not loaded")
            ai_score = predict_ai_score_from_bundle(
                signal_df,
                ai_model_bundle,
                vix_df=vix_df,
                spy_df=spy_df,
                macro_df=macro_df,
            )
        except Exception:
            ai_score = None

    return signal, latest, ai_score


def _execution_reference_price(
    indicators: dict | None,
    *,
    fallback: float | None = None,
) -> float:
    if indicators:
        for key in ("close", "adj_close"):
            value = indicators.get(key)
            if value is not None and float(value) > 0:
                return float(value)
    if fallback is not None and float(fallback) > 0:
        return float(fallback)
    raise ValueError("missing reference price for extended-hours limit order")


def _execution_block_label(execute_orders: bool, market_clock) -> str:
    if not execute_orders:
        return "DRY_RUN_ONLY"
    if market_clock.session.value == "closed":
        return "TRADING_SESSION_CLOSED"
    if not market_clock.orders_allowed:
        return "TRADING_SESSION_DISABLED"
    return "EXECUTION_BLOCKED"


def _order_is_filled(status: str) -> bool:
    normalized = str(status).upper()
    return "FILLED" in normalized and "PARTIALLY" not in normalized


def _audit_log(audit_ctx: AuditContext, **kwargs) -> None:
    log_execution_audit(**kwargs, **audit_ctx.as_audit_fields())


def _filled_notional(checked_order: dict, fallback: float) -> float:
    filled_qty = checked_order.get("filled_qty")
    filled_avg_price = checked_order.get("filled_avg_price")
    if (
        filled_qty in (None, "", "0", "0.0", "None")
        or filled_avg_price in (None, "", "None")
        or str(filled_qty).lower() == "none"
        or str(filled_avg_price).lower() == "none"
    ):
        return 0.0
    try:
        return float(filled_qty) * float(filled_avg_price)
    except (TypeError, ValueError):
        return 0.0


def main() -> None:
    args = parse_args()
    execute_orders = args.execute
    run_id = datetime.now().strftime("%Y%m%dT%H%M%S")
    settings = load_settings()
    broker_adapter = get_broker_adapter(settings.broker_provider)
    trading_env = resolve_trading_environment(settings)
    settings = apply_environment_profile(settings, trading_env)
    validate_trading_config(settings, trading_env, broker_adapter)
    if execute_orders:
        assert_live_execution_allowed(
            execute=True,
            trading_environment=trading_env,
        )
        assert_live_readiness_for_execute(
            settings=settings,
            environment=trading_env,
        )
    ai_model_bundle = None
    if getattr(settings, "use_ai_score", False):
        try:
            ai_model_bundle = load_ai_score_model()
        except Exception:
            ai_model_bundle = None
    audit_ctx = build_audit_context(
        run_id=run_id,
        settings=settings,
        environment=trading_env,
        ai_model_bundle=ai_model_bundle,
    )

    try:
        account = broker_adapter.get_account()
        positions = broker_adapter.get_positions()
        open_symbols = broker_adapter.get_open_symbols()
    except ConnectionError as exc:
        if execute_orders:
            raise
        print(f"Alpaca unavailable, using offline dry-run defaults: {exc}")
        account = _offline_account_summary()
        open_symbols = set()
        positions = []
    open_symbols = {str(symbol).upper() for symbol in open_symbols}
    positions_by_symbol = {
        str(position["symbol"]).upper(): position for position in positions
    }
    open_orders_for_sleeves: list[dict] = []
    try:
        open_orders_for_sleeves = broker_adapter.get_open_orders()
    except Exception as exc:
        print(f"Warning: open orders unavailable for sleeve allocator: {exc}")
        open_orders_for_sleeves = []
    sleeve_allocator = PortfolioSleeveAllocator(
        settings,
        account=account,
        positions=positions,
        open_orders=open_orders_for_sleeves,
    )
    sleeve_snapshot = sleeve_allocator.build_snapshot()
    sleeve_recon_ok = True
    sleeve_recon_reason = ""
    if sleeves_enabled(settings):
        sleeve_recon_ok, sleeve_recon_reason = validate_sleeve_open_order_budget(
            sleeve_snapshot,
            open_orders_for_sleeves,
        )
        sleeve_budgets = {
            sleeve_id: round(budget.order_budget, 2)
            for sleeve_id, budget in sleeve_snapshot.sleeves.items()
        }
        print(f"Portfolio sleeves enabled: order_budgets={sleeve_budgets}")
        if not sleeve_recon_ok:
            print(f"SLEEVE_RECONCILIATION_NO_GO: {sleeve_recon_reason}")

    core_sleeve_budget_remaining = (
        sleeve_allocator.order_budget_for(CORE_SLEEVE_ID)
        if sleeves_enabled(settings)
        else None
    )

    def _buy_sleeve_audit(
        *,
        budget_before: float | None = None,
        budget_after: float | None = None,
    ) -> dict:
        if not sleeves_enabled(settings):
            return {}
        return sleeve_fields_for_audit(
            sleeve_snapshot,
            sleeve_id=CORE_SLEEVE_ID,
            budget_before=budget_before,
            budget_after=budget_after,
        )
    # 다이내믹 유니버스 적용 (Phase 13)
    original_tickers = list(settings.tickers)
    if getattr(settings, "dynamic_universe_enabled", False):
        settings.tickers = get_dynamic_universe(
            original_tickers, 
            limit=int(getattr(settings, "dynamic_count", 50))
        )
    
    tickers_to_load = list(dict.fromkeys([*settings.tickers, *open_symbols]))
    # Always include SPY and ^VIX for live market regime calculation
    if "SPY" not in tickers_to_load:
        tickers_to_load.append("SPY")
    if "^VIX" not in tickers_to_load:
        tickers_to_load.append("^VIX")
    if getattr(settings, "market_regime_filter_enabled", False):
        regime_ticker = getattr(settings, "market_regime_ticker", "SPY")
        if regime_ticker not in tickers_to_load:
            tickers_to_load.append(regime_ticker)
    tickers_to_load = list(dict.fromkeys(tickers_to_load))
    try:
        ticker_data = load_price_data_batch(tickers_to_load, period="2y")
    except Exception as e:
        print(f"Warning: Failed to load batch price data: {e}. Retrying tickers individually to isolate failures...")
        ticker_data = {}
        for ticker in tickers_to_load:
            try:
                single_data = load_price_data_batch([ticker], period="2y")
                ticker_data.update(single_data)
            except Exception as single_err:
                print(f"Warning: Failed to load data for {ticker}: {single_err}")
    
    # SPY와 ^VIX 데이터를 로드한다. (실패 시에도 전체 봇 실행이 중단되지 않도록 별도 예외 처리)
    # 레짐 연산은 항상 SPY와 ^VIX를 기준으로 수행한다.
    spy_df = ticker_data.get("SPY")
    vix_df = ticker_data.get("^VIX")
    
    if spy_df is None or spy_df.empty or vix_df is None or vix_df.empty:
        try:
            missing_tickers = []
            if spy_df is None or spy_df.empty:
                missing_tickers.append("SPY")
            if vix_df is None or vix_df.empty:
                missing_tickers.append("^VIX")
            print(f"Fetching context tickers separately (None or empty in batch): {missing_tickers}")
            context_data = load_price_data_batch(missing_tickers, period="2y")
            if spy_df is None or spy_df.empty:
                spy_df = context_data.get("SPY")
                if spy_df is not None and not spy_df.empty:
                    ticker_data["SPY"] = spy_df
            if vix_df is None or vix_df.empty:
                vix_df = context_data.get("^VIX")
                if vix_df is not None and not vix_df.empty:
                    ticker_data["^VIX"] = vix_df
        except Exception as e:
            print(f"Warning: Failed to load market-context data (SPY/^VIX): {e}")

    # 시장 레짐 결정 (실시간 데이터로 항상 우선 계산, 실패 시 캐시 파일 안전 폴백)
    current_regime = None
    state_path = Path("data/market_regime_state.json")
    
    # 1. 실시간 데이터 기반 계산 시도
    if spy_df is not None and not spy_df.empty and vix_df is not None and not vix_df.empty:
        try:
            current_regime = get_current_regime(spy_df, vix_df)
            print(f"Calculated Market Regime (Live): {current_regime}")
        except Exception as e:
            print(f"Warning: Failed to calculate live market regime: {e}")

    # 2. 실시간 계산 실패 시 캐시에서 최근 유효한 레짐 폴백 로드
    if not current_regime:
        if state_path.exists():
            try:
                state_data = json.loads(state_path.read_text(encoding="utf-8"))
                # 역사적 시뮬레이션 데이터 차단 및 최근 24시간 이내의 캐시만 유효한 것으로 판단
                updated_at = datetime.fromisoformat(state_data.get("updated_at", ""))
                is_historical = state_data.get("is_historical", False)
                market_date_str = state_data.get("market_date")
                
                is_stale_market_date = False
                if market_date_str:
                    try:
                        # 캐시 생성일(updated_at) 대비 market_date가 5일을 초과해 오래되었는지 검사 (주말/공휴일 허용)
                        market_date = datetime.fromisoformat(market_date_str.split("T")[0]).date()
                        if (updated_at.date() - market_date).days > 5:
                            is_stale_market_date = True
                            print(f"Warning: Stale market date in cached regime (relative to write time): {market_date_str}")
                    except Exception as parse_err:
                        print(f"Warning: Failed to parse market_date from cache: {parse_err}")
                
                # 96시간(4일) 이내의 캐시까지 유효한 것으로 판단 (주말/휴일 고려)
                if not is_historical and not is_stale_market_date and (datetime.now() - updated_at).total_seconds() < 345600:
                    current_regime = state_data.get("regime")
                    print(f"Loaded Market Regime from state file (Fallback): {current_regime}")
            except Exception as e:
                print(f"Warning: Failed to load fallback market regime from state file: {e}")

    # 3. 모든 시도 실패 시 기본값 지정
    if not current_regime:
        current_regime = "NEUTRAL"
        print(f"Warning: All regime calculations failed. Falling back to default: {current_regime}")

    # 다이내믹 프로필 적용
    settings, profile_name = apply_dynamic_profile(settings, current_regime)

    if getattr(settings, "margin_leverage_paper_enabled", False):
        try:
            settings = apply_margin_leverage_paper_overrides(settings)
            print("Margin leverage paper proposal overrides applied.")
        except FileNotFoundError as exc:
            print(f"Warning: margin leverage paper proposal not applied: {exc}")

    margin_leverage_block_active, margin_leverage_block_reason = evaluate_margin_leverage_buy_block(
        float(getattr(settings, "leverage_factor", 1.0)),
        margin_leverage_paper_enabled=bool(
            getattr(settings, "margin_leverage_paper_enabled", False)
        ),
        margin_leverage_stress_gate_required=bool(
            getattr(settings, "margin_leverage_stress_gate_required", True)
        ),
    )
    if margin_leverage_block_active:
        print(f"MARGIN_LEVERAGE_GATE_BLOCK: {margin_leverage_block_reason}")

    print(f"Applied Strategy Profile: {profile_name}")
    print(f"  - Max Positions: {settings.max_total_positions}")
    print(f"  - Position Pct: {settings.max_position_pct:.1%}")
    print(f"  - Buy Threshold: {settings.ai_score_buy_threshold:.2f}")

    market_clock = get_market_clock(settings)
    live_safety_guard = LiveSafetyGuard.from_settings(
        settings,
        account=account,
        positions=positions,
    )
    if live_safety_guard.kill_switch_active():
        print(f"LIVE_SAFETY: manual kill switch active ({live_safety_guard.config.kill_switch_path})")
    extended_slippage = float(
        getattr(settings, "extended_hours_limit_slippage_pct", 0.005)
    )

    # VIX Panic Mode 알림
    if vix_df is not None and not vix_df.empty:
        close_col = "adj_close" if "adj_close" in vix_df.columns else "close"
        latest_vix = float(vix_df[close_col].iloc[-1])
        if latest_vix > 30.0:
            notify_info(
                "🔥 VIX Panic Mode Detected",
                f"VIX level: {latest_vix:.2f}\n"
                f"Market volatility is high. Defensive AI exit logic (threshold=0.45) is active."
            )

    macro_df = load_macro_data(period="2y") if getattr(settings, "use_ai_score", False) else None
    try:
        rank_ai_gate_scores = build_rank_ai_gate_scores(
            ticker_data,
            settings,
            vix_df=vix_df,
            spy_df=spy_df,
            macro_df=macro_df,
        )
        if rank_ai_gate_scores:
            print(
                "Rank AI buy/add gate enabled: "
                f"scored {len(rank_ai_gate_scores)} symbols"
            )
    except Exception as exc:
        if bool(getattr(settings, "rank_ai_buy_gate_fail_closed", True)):
            raise
        print(f"Warning: rank AI buy/add gate disabled for this run: {exc}")
        rank_ai_gate_scores = {}
    market_regime_bullish = True
    if getattr(settings, "market_regime_filter_enabled", False):
        regime_df = ticker_data.get(settings.market_regime_ticker)
        if regime_df is not None and not regime_df.empty:
            try:
                market_regime_bullish = is_bullish_market_regime(
                    regime_df,
                    ma_fast=settings.market_regime_ma_fast,
                    ma_slow=settings.market_regime_ma_slow,
                )
            except Exception as e:
                print(f"Warning: Failed to calculate bullish market regime trend: {e}. Failing closed.")
                market_regime_bullish = False
        else:
            print("Warning: Missing or empty regime benchmark data. Failing closed.")
            market_regime_bullish = False

    cash = account["cash"]
    # 레버리지 적용 (Phase 13)
    leverage = float(getattr(settings, "leverage_factor", 1.0))
    portfolio_value = account["portfolio_value"] * leverage
    
    last_equity = account.get("last_equity", account["portfolio_value"])
    
    # Drawdown Circuit Breaker: 전일 대비 -15% 이상 하락 시 신규 매수 중단
    # (주의: 레버리지 사용 시 실질 낙폭이 더 클 수 있으므로 실제 portfolio_value 기준 체크)
    daily_drawdown = (account["portfolio_value"] - last_equity) / last_equity if last_equity > 0 else 0
    max_drawdown_allowed = -float(getattr(settings, "max_portfolio_drawdown_pct", 0.15))
    
    circuit_breaker_active = daily_drawdown <= max_drawdown_allowed
    if circuit_breaker_active:
        print(f"CIRCUIT_BREAKER_ACTIVE: Daily drawdown ({daily_drawdown*100:.2f}%) "
              f"exceeded threshold ({max_drawdown_allowed*100:.2f}%). "
              f"New buys will be blocked.")

    positions_count = account["positions_count"]
    dust_min_usd = dust_position_min_usd(settings)
    meaningful_positions_count = count_meaningful_positions(
        positions, min_usd=dust_min_usd
    )
    guard_open_symbols = meaningful_open_symbols(positions, min_usd=dust_min_usd)
    current_gross_exposure = meaningful_gross_exposure(
        positions, min_usd=dust_min_usd
    )
    orders_submitted = 0
    submitted_notional_today = get_today_buy_notional()
    recent_buy_symbols = get_recent_buy_symbols(
        int(getattr(settings, "buy_cooldown_days", 0))
    )
    exit_summary_rows = []
    buy_summary_rows = []
    skipped_reasons: Counter[str] = Counter()
    data_error_count = 0
    api_error_count = 0
    live_order_count = 0

    print("Account loaded from Alpaca paper.")
    print(f"cash={cash:.2f}, positions_count={positions_count}")
    print(f"execute_orders={execute_orders}")
    print(f"llm_cache_only={llm_cache_only_for_run(execute_orders=execute_orders)}")
    if getattr(settings, "market_regime_filter_enabled", False):
        print(
            f"market_regime_ticker={settings.market_regime_ticker}, "
            f"market_regime_bullish={market_regime_bullish}"
        )
    print(
        f"broker_provider={market_clock.broker_provider}, "
        f"trading_session={market_clock.session.value}, "
        f"market_is_open={market_clock.is_open}, "
        f"orders_allowed={market_clock.orders_allowed}, "
        f"market_time={market_clock.timestamp}"
    )
    if not market_clock.orders_allowed:
        print(f"next_open={market_clock.next_open}")

    if execute_orders and not market_clock.orders_allowed:
        print(
            "EXECUTION_BLOCKED: current trading session is not enabled. "
            "Dry-run checks will continue."
        )

    can_submit_orders = (
        execute_orders and market_clock.orders_allowed and not circuit_breaker_active
    )

    # 트레일링 스탑용 최고가 정보 로드
    peaks = _load_peaks()
    price_data_freshness = {
        ticker: _check_price_frame_freshness(raw_df, market_clock)
        for ticker, raw_df in ticker_data.items()
    }

    # 섹터 순환매 분석 (Phase 15-A)
    top_sectors = []
    if getattr(settings, "sector_rotation_enabled", False):
        top_sectors = get_sector_leadership()

    print("-" * 80)

    # 1) 기존 보유 포지션 청산 조건 먼저 확인
    if positions:
        print("-" * 80)
        print("Checking open positions for exit conditions...")

        for position in positions:
            ticker = str(position["symbol"]).upper()
            try:
                if is_dust_position(position, min_usd=dust_min_usd):
                    dust_reason = (
                        f"dust position cleanup (<${dust_min_usd:g} market value)"
                    )
                    dust_mv = float(position["market_value"])
                    print(
                        f"{ticker}: DUST position qty={position['qty']}, "
                        f"market_value={dust_mv:.6f} — scheduling close"
                    )
                    exit_summary_rows.append(
                        f"{ticker}: DUST exit, market_value=${dust_mv:.6f}"
                    )
                    _audit_log(
                        audit_ctx,
                        event_type="DUST_EXIT",
                        ticker=ticker,
                        action="CLOSE",
                        status="SUBMITTED" if can_submit_orders else "DRY_RUN",
                        reason=dust_reason,
                        profile_name=profile_name,
                        regime=current_regime,
                    )
                    if can_submit_orders:
                        try:
                            dust_qty = float(position["qty"])
                            dust_submission = broker_adapter.submit_sell_qty(
                                ticker,
                                dust_qty,
                                limit_price=float(position.get("current_price") or 0.0),
                                market_clock=market_clock,
                                slippage_pct=extended_slippage,
                                client_order_id=f"dust_{run_id}_{ticker}",
                            )
                            live_order_count += 1
                            log_order(
                                ticker=ticker,
                                notional=0.0,
                                order_id=dust_submission.order_id,
                                status=dust_submission.status,
                                side=dust_submission.side,
                                order_type=dust_submission.order_type,
                                reason=dust_reason,
                            )
                            print(
                                f"  PAPER_DUST_CLOSE: {ticker}, "
                                f"order_id={dust_submission.order_id}, "
                                f"status={dust_submission.status}"
                            )
                            notify_info(
                                "🧹 Dust position closed",
                                f"{ticker}: closed negligible position (${dust_mv:.4f})",
                            )
                        except Exception as e:
                            print(f"  Dust close error for {ticker}: {e}")
                            api_error_count += 1
                            if isinstance(e, ConnectionError) and execute_orders:
                                notify_error(
                                    f"CRITICAL: Network error during dust close for {ticker}",
                                    e,
                                )
                    else:
                        print(f"  DRY_RUN: would close dust position {ticker}")
                    positions_by_symbol.pop(ticker, None)
                    open_symbols.discard(ticker)
                    guard_open_symbols.discard(ticker)
                    meaningful_positions_count = max(
                        0, meaningful_positions_count - 1
                    )
                    continue

                data_fresh, data_reason = price_data_freshness.get(
                    ticker,
                    (False, "price data not loaded"),
                )
                if not data_fresh:
                    print(f"{ticker}: SKIP_EXIT - {data_reason}")
                    exit_summary_rows.append(f"{ticker}: SKIP_EXIT {data_reason}")
                    skipped_reasons[f"exit:{data_reason}"] += 1
                    data_error_count += 1
                    _audit_log(
                        audit_ctx,
                        event_type="SKIP_EXIT",
                        ticker=ticker,
                        action="CLOSE",
                        status="SKIPPED",
                        reason=data_reason,
                        profile_name=profile_name,
                        regime=current_regime,
                    )
                    continue

                # 최고가 갱신 (트레일링 스탑용)
                current_price = float(position["current_price"])
                old_peak = peaks.get(ticker, 0.0)
                if current_price > old_peak:
                    peaks[ticker] = current_price

                signal, latest, ai_score = get_signal_for_ticker(
                    ticker,
                    ticker_data[ticker],
                    settings,
                    ai_model_bundle=ai_model_bundle,
                    market_regime_bullish=market_regime_bullish,
                    vix_df=vix_df,
                    spy_df=spy_df,
                    macro_df=macro_df,
                    market_clock=market_clock,
                )
                unrealized_plpc = float(position["unrealized_plpc"])

                ai_exit_triggered = False
                exit_thr = None

                # 보유 기간 계산 (Phase 18-C)
                holding_days = 0
                entry_date = get_position_entry_date(ticker)
                if entry_date:
                    holding_days = (datetime.now(entry_date.tzinfo) - entry_date).days
                    # print(f"  {ticker} held for {holding_days} days (entered {entry_date.date()})")

                # AI exit candidate
                if (
                    getattr(settings, "ai_exit_enabled", False)
                    and signal != "SELL"
                    and ai_score is not None
                ):
                    exit_thr = float(getattr(settings, "ai_exit_threshold", 0.35))
                    if getattr(settings, "ai_exit_dynamic_enabled", False) and vix_df is not None and not vix_df.empty:
                        close_col = "adj_close" if "adj_close" in vix_df.columns else "close"
                        latest_vix = float(vix_df[close_col].iloc[-1])
                        vix_low = float(getattr(settings, "ai_exit_vix_low", 15.0))
                        vix_high = float(getattr(settings, "ai_exit_vix_high", 25.0))
                        if latest_vix < vix_low:
                            exit_thr = float(getattr(settings, "ai_exit_threshold_bull", 0.55))
                        elif latest_vix > vix_high:
                            exit_thr = float(getattr(settings, "ai_exit_threshold_bear", 0.28))
                    if ai_score < exit_thr:
                        ai_exit_triggered = True

                # Trailing Stop (Phase 14-A / Phase 18-C Adaptive)
                peak_price = peaks.get(ticker, 0.0)
                trailing_pct = float(getattr(settings, "trailing_stop_pct", 0.05))

                if getattr(settings, "adaptive_trailing_stop_enabled", False) and "atr" in latest:
                    atr_val = float(latest["atr"])
                    if atr_val > 0 and peak_price > 0:
                        multiplier = float(getattr(settings, "atr_multiplier", 3.0))
                        # ATR 기반의 변동성을 백분율로 변환 (ATR * Multiplier 만큼 하락 시 스탑)
                        trailing_pct = (atr_val * multiplier) / peak_price
                        # 합리적 범위 내에서 제한 (예: 최소 2% ~ 최대 20%)
                        trailing_pct = max(0.02, min(0.20, trailing_pct))

                trailing_drawdown = None
                if peak_price > 0 and current_price < peak_price:
                    trailing_drawdown = (peak_price - current_price) / peak_price

                full_exit_reason = _resolve_full_exit_reason(
                    unrealized_plpc=unrealized_plpc,
                    stop_loss_pct=float(getattr(settings, "stop_loss_pct", 0.0)),
                    take_profit_pct=float(getattr(settings, "take_profit_pct", 0.0)),
                    trailing_drawdown=trailing_drawdown,
                    trailing_stop_pct=trailing_pct,
                    signal=signal,
                    ai_exit_triggered=ai_exit_triggered,
                    holding_days=holding_days,
                    max_holding_days=int(getattr(settings, "max_holding_days", 30)),
                )
                exit_decision = ExitDecision(
                    should_exit=full_exit_reason is not None,
                    reason="",
                )
                if full_exit_reason == "trailing stop triggered" and trailing_drawdown is not None:
                    exit_decision.reason = (
                        f"trailing stop triggered ({trailing_drawdown*100:.1f}% drop from peak ${peak_price:.2f})"
                    )
                elif full_exit_reason is not None:
                    exit_decision.reason = full_exit_reason

                print(
                    f"{ticker}: position_qty={position['qty']}, "
                    f"unrealized_plpc={unrealized_plpc * 100:.2f}%, "
                    f"signal={signal}, "
                    f"exit={exit_decision.should_exit}, "
                    f"reason='{exit_decision.reason}'"
                )

                exit_summary_rows.append(
                    f"{ticker}: pnl={unrealized_plpc * 100:.2f}%, "
                    f"signal={signal}, exit={exit_decision.should_exit}, "
                    f"reason={exit_decision.reason}"
                )

                # Partial Profit Taking (Phase 11-A)
                # 수익률이 take_profit_partial_pct 이상이면 비중의 절반을 매도 (분할 익절)
                partial_tp_thr = float(getattr(settings, "take_profit_partial_pct", 0.0))
                if not exit_decision.should_exit and partial_tp_thr > 0 and unrealized_plpc >= partial_tp_thr:
                    current_qty = float(position["qty"])
                    if current_qty > 0.1: 
                        sell_qty = round(current_qty * float(getattr(settings, "partial_exit_ratio", 0.5)), 4)
                        print(f"  PARTIAL_EXIT_TRIGGERED: {ticker} pnl={unrealized_plpc*100:.2f}% >= {partial_tp_thr*100:.2f}%. Selling {sell_qty}")
                        if can_submit_orders:
                            try:
                                partial_submission = broker_adapter.submit_sell_qty(
                                    ticker,
                                    sell_qty,
                                    limit_price=_execution_reference_price(
                                        None,
                                        fallback=current_price,
                                    ),
                                    market_clock=market_clock,
                                    slippage_pct=extended_slippage,
                                    client_order_id=f"part_{run_id}_{ticker}",
                                )
                                live_order_count += 1
                                _audit_log(
                                    audit_ctx,
                                    event_type="PARTIAL_EXIT",
                                    ticker=ticker,
                                    action="SELL",
                                    status=partial_submission.status,
                                    reason=f"partial take profit ({unrealized_plpc*100:.2f}%)",
                                    profile_name=profile_name,
                                    regime=current_regime,
                                    signal=signal,
                                    ai_score=ai_score,
                                    order_id=partial_submission.order_id,
                                    order_type=partial_submission.order_type,
                                    side=partial_submission.side,
                                    quantity=sell_qty,
                                )
                                notify_info("💰 Partial Profit Taken", f"{ticker}: Sold {sell_qty} shares at +{unrealized_plpc*100:.2f}% profit.")
                            except Exception as e:
                                print(f"  Partial exit error for {ticker}: {e}")
                                if isinstance(e, ConnectionError) and execute_orders:
                                    notify_error(f"CRITICAL: Network error during partial exit for {ticker}", e)
                                    raise
                                api_error_count += 1
                                _audit_log(
                                    audit_ctx,
                                    event_type="PARTIAL_EXIT",
                                    ticker=ticker,
                                    action="SELL",
                                    status="ERROR",
                                    reason=str(e),
                                    profile_name=profile_name,
                                    regime=current_regime,
                                    signal=signal,
                                    ai_score=ai_score,
                                    quantity=sell_qty,
                                )

                # Position Trimming / Rebalancing (Phase 14-B)
                # 현재 비중이 목표치보다 너무 크면 일부 매도 (20% 초과 시)
                rebalance_thr = float(getattr(settings, "rebalance_threshold_pct", 0.20))
                portfolio_val = float(account["portfolio_value"])
                target_weight = float(settings.max_position_pct)
                current_weight = float(position["market_value"]) / portfolio_val if portfolio_val > 0 else 0

                if not exit_decision.should_exit and current_weight > target_weight * (1 + rebalance_thr):
                    excess_value = float(position["market_value"]) - (portfolio_val * target_weight)
                    if excess_value > 50: # 최소 50달러 이상일 때만 리밸런싱
                        trim_qty = round(excess_value / current_price, 4)
                        print(f"  REBALANCE_TRIM: {ticker} weight {current_weight*100:.1f}% > target {target_weight*100:.1f}%. Trimming {trim_qty}")
                        if can_submit_orders:
                            try:
                                trim_submission = broker_adapter.submit_sell_qty(
                                    ticker,
                                    trim_qty,
                                    limit_price=_execution_reference_price(
                                        None,
                                        fallback=current_price,
                                    ),
                                    market_clock=market_clock,
                                    slippage_pct=extended_slippage,
                                    client_order_id=f"trim_{run_id}_{ticker}",
                                )
                                live_order_count += 1
                                _audit_log(
                                    audit_ctx,
                                    event_type="REBALANCE_TRIM",
                                    ticker=ticker,
                                    action="SELL",
                                    status=trim_submission.status,
                                    reason=f"rebalance trim (weight={current_weight:.4f})",
                                    profile_name=profile_name,
                                    regime=current_regime,
                                    signal=signal,
                                    ai_score=ai_score,
                                    order_id=trim_submission.order_id,
                                    order_type=trim_submission.order_type,
                                    side=trim_submission.side,
                                    quantity=trim_qty,
                                )
                            except Exception as e:
                                print(f"  Trim error for {ticker}: {e}")
                                if isinstance(e, ConnectionError) and execute_orders:
                                    notify_error(f"CRITICAL: Network error during rebalance trim for {ticker}", e)
                                    raise
                                api_error_count += 1
                                _audit_log(
                                    audit_ctx,
                                    event_type="REBALANCE_TRIM",
                                    ticker=ticker,
                                    action="SELL",
                                    status="ERROR",
                                    reason=str(e),
                                    profile_name=profile_name,
                                    regime=current_regime,
                                    signal=signal,
                                    ai_score=ai_score,
                                    quantity=trim_qty,
                                )

                if not exit_decision.should_exit:
                    continue

                if not can_submit_orders:
                    label = _execution_block_label(execute_orders, market_clock)
                    print(
                        f"  {label}: would CLOSE {ticker} "
                        f"reason='{exit_decision.reason}'"
                    )
                    skipped_reasons[f"exit:{label.lower()}"] += 1
                    _audit_log(
                        audit_ctx,
                        event_type="SKIP_EXIT",
                        ticker=ticker,
                        action="CLOSE",
                        status="SKIPPED",
                        reason=f"{label}: {exit_decision.reason}",
                        profile_name=profile_name,
                        regime=current_regime,
                        signal=signal,
                        ai_score=ai_score,
                    )
                    continue

                exit_qty = float(position["qty"])
                exit_submission = broker_adapter.submit_sell_qty(
                    ticker,
                    exit_qty,
                    limit_price=_execution_reference_price(
                        None,
                        fallback=current_price,
                    ),
                    market_clock=market_clock,
                    slippage_pct=extended_slippage,
                    client_order_id=f"exit_{run_id}_{ticker}",
                )
                live_order_count += 1

                log_order(
                    ticker=ticker,
                    notional=0.0,
                    order_id=exit_submission.order_id,
                    status=exit_submission.status,
                    side=exit_submission.side,
                    order_type=exit_submission.order_type,
                    reason=exit_decision.reason,
                )

                print(
                    f"  PAPER_CLOSE_SUBMITTED: {ticker}, "
                    f"order_id={exit_submission.order_id}, status={exit_submission.status}"
                )
                _audit_log(
                    audit_ctx,
                    event_type="FULL_EXIT",
                    ticker=ticker,
                    action="SELL",
                    status=exit_submission.status,
                    reason=exit_decision.reason,
                    profile_name=profile_name,
                    regime=current_regime,
                    signal=signal,
                    ai_score=ai_score,
                    order_id=exit_submission.order_id,
                    order_type=exit_submission.order_type,
                    side=exit_submission.side,
                )

                checked_order = broker_adapter.wait_for_order_status(exit_submission.order_id)
                log_order_status(
                    ticker=ticker,
                    order_id=checked_order["id"],
                    status=checked_order["status"],
                    side=checked_order["side"],
                    order_type=checked_order["type"],
                    filled_qty=checked_order["filled_qty"],
                    filled_avg_price=checked_order["filled_avg_price"],
                    reason=exit_decision.reason,
                )
                print(
                    f"  CLOSE_STATUS_CHECK: status={checked_order['status']}, "
                    f"filled_qty={checked_order['filled_qty']}, "
                    f"filled_avg_price={checked_order['filled_avg_price']}"
                )
                _audit_log(
                    audit_ctx,
                    event_type="FULL_EXIT_STATUS",
                    ticker=ticker,
                    action="SELL",
                    status=str(checked_order["status"]),
                    reason=exit_decision.reason,
                    profile_name=profile_name,
                    regime=current_regime,
                    signal=signal,
                    ai_score=ai_score,
                    order_id=str(checked_order["id"]),
                    order_type=str(checked_order["type"]),
                    side=str(checked_order["side"]),
                    filled_qty=checked_order["filled_qty"],
                    filled_avg_price=checked_order["filled_avg_price"],
                )

                notify_order(
                    action="CLOSE",
                    ticker=ticker,
                    status=checked_order["status"],
                    order_id=checked_order["id"],
                    reason=exit_decision.reason,
                    filled_qty=checked_order["filled_qty"],
                    filled_avg_price=checked_order["filled_avg_price"],
                )

                if ticker in open_symbols:
                    open_symbols.remove(ticker)
                    positions_by_symbol.pop(ticker, None)
                    positions_count -= 1

            except Exception as exc:
                if isinstance(exc, ConnectionError) and execute_orders:
                    notify_error("CRITICAL: Network error during exit loop", exc)
                    raise
                print(f"{ticker}: EXIT_CHECK_ERROR - {exc}")
                exit_summary_rows.append(f"{ticker}: EXIT_CHECK_ERROR - {exc}")
                api_error_count += 1
                _audit_log(
                    audit_ctx,
                    event_type="EXIT_ERROR",
                    ticker=ticker,
                    action="CLOSE",
                    status="ERROR",
                    reason=str(exc),
                    profile_name=profile_name,
                    regime=current_regime,
                )
                notify_error(f"{ticker} exit check error", exc)

        print("-" * 80)
    # 2) 신규 매수 후보 수집 (Pass 1: 신호 생성 + 리스크 검사, 주문 미제출)
    approved_buys: list[dict] = []

    # 매크로 이벤트 리스크 체크 (Phase 18-B)
    macro_risk_active = False
    macro_risk_reason = ""
    if getattr(settings, "macro_event_risk_enabled", False):
        macro_risk_active, macro_risk_reason = get_macro_event_risk(
            lookforward_days=int(getattr(settings, "macro_event_lookahead_days", 2)),
            lookback_days=int(getattr(settings, "macro_event_lookback_days", 1))
        )
        if macro_risk_active:
            print(f"MACRO_EVENT_RISK_ACTIVE: {macro_risk_reason}. New buys will be restricted.")

    if margin_leverage_block_active:
        print("New buys blocked until margin leverage stress gate passes (see runbook).")

    for ticker in settings.tickers:
        try:
            data_fresh, data_reason = price_data_freshness.get(
                ticker,
                (False, "price data not loaded"),
            )
            if not data_fresh:
                print(f"{ticker}: SKIP_BUY - {data_reason}")
                buy_summary_rows.append(f"{ticker}: SKIP_BUY {data_reason}")
                skipped_reasons[f"buy:{data_reason}"] += 1
                data_error_count += 1
                _audit_log(
                    audit_ctx,
                    event_type="SKIP_BUY",
                    ticker=ticker,
                    action="BUY",
                    status="SKIPPED",
                    reason=data_reason,
                    profile_name=profile_name,
                    regime=current_regime,
                )
                continue

            signal, latest, ai_score = get_signal_for_ticker(
                ticker,
                ticker_data[ticker],
                settings,
                ai_model_bundle=ai_model_bundle,
                market_regime_bullish=market_regime_bullish,
                vix_df=vix_df,
                spy_df=spy_df,
                macro_df=macro_df,
                market_clock=market_clock,
            )

            ai_score = apply_sector_score_bonus(ticker, ai_score, top_sectors)
            conviction = conviction_adjustments(settings, ai_score)
            if conviction.label != "neutral":
                print(f"{ticker}: sizing {conviction.label}")

            llm_is_ok = None
            llm_reason = ""

            held_position = effective_position(
                positions_by_symbol.get(ticker), min_usd=dust_min_usd
            )
            if held_position is not None:
                # 13-A: 이미 보유 중인 종목이라도 목표 비중에 미달하면 추가 매수 (Averaging up/down)
                risk = check_additional_buy_allowed(
                    signal=signal,
                    cash=cash,
                    portfolio_value=float(account["portfolio_value"]),
                    current_position_value=float(held_position["market_value"]),
                    position_mult=conviction.position_mult,
                    cash_buffer_mult=conviction.cash_buffer_mult,
                )
                risk_allowed = risk.allowed
                risk_reason = risk.reason
                target_amount = risk.target_amount
                
                # 추가 매수 시에도 최소 금액(예: 10달러) 이상일 때만 진행
                if risk_allowed and target_amount < 10.0:
                    risk_allowed = False
                    risk_reason = f"additional buy amount too small (${target_amount:.2f})"
                    target_amount = 0.0
            else:
                risk = check_buy_allowed(
                    signal=signal,
                    cash=cash,
                    current_positions_count=meaningful_positions_count,
                    portfolio_value=float(account["portfolio_value"]),
                    ticker=ticker,
                    position_mult=conviction.position_mult,
                    cash_buffer_mult=conviction.cash_buffer_mult,
                )
                risk_allowed = risk.allowed
                risk_reason = risk.reason
                target_amount = risk.target_amount

            if (
                risk_allowed
                and getattr(settings, "use_ai_score", False)
                and (
                    ai_score is None
                    or ai_score < float(settings.ai_score_buy_threshold)
                )
            ):
                risk_allowed = False
                risk_reason = (
                    f"ai score filter blocked "
                    f"(score={ai_score}, threshold={settings.ai_score_buy_threshold})"
                )
                target_amount = 0.0

            guard = apply_shared_buy_guards(
                ticker=ticker,
                position=held_position,
                settings=settings,
                risk_allowed=risk_allowed,
                risk_reason=risk_reason,
                target_amount=target_amount,
                ai_score=ai_score,
                open_symbols=guard_open_symbols,
                ticker_data=ticker_data,
                vix_df=vix_df,
                macro_risk_active=macro_risk_active,
                macro_risk_reason=macro_risk_reason,
                margin_leverage_block_active=margin_leverage_block_active,
                margin_leverage_block_reason=margin_leverage_block_reason,
                llm_cache_only=llm_cache_only_for_run(execute_orders=execute_orders),
            )
            risk_allowed = guard.risk_allowed
            risk_reason = guard.risk_reason
            target_amount = guard.target_amount
            llm_is_ok = guard.llm_is_ok
            llm_reason = guard.llm_reason

            rank_gate = apply_rank_ai_buy_gate(
                ticker=ticker,
                settings=settings,
                risk_allowed=risk_allowed,
                risk_reason=risk_reason,
                target_amount=target_amount,
                scores=rank_ai_gate_scores,
            )
            risk_allowed = rank_gate.risk_allowed
            risk_reason = rank_gate.risk_reason
            target_amount = rank_gate.target_amount

            if risk_allowed and held_position is None and llm_is_ok is False:
                llm_advisory_only = bool(getattr(settings, "llm_advisory_only", True))
                if llm_advisory_only:
                    _audit_log(
                        audit_ctx,
                        event_type="LLM_ADVISORY",
                        ticker=ticker,
                        action="BUY",
                        status="WOULD_REJECT",
                        reason=format_audit_reason(llm_reason, ticker),
                        profile_name=profile_name,
                        regime=current_regime,
                        signal=signal,
                        ai_score=ai_score,
                        llm_verdict=_format_llm_verdict(llm_is_ok, llm_reason),
                        notional=target_amount,
                    )

            order_amount = cap_single_order_amount(
                target_amount,
                float(account["portfolio_value"]),
                settings,
            )

            if risk_allowed:
                safety = apply_buy_safety_limits(
                    ticker=ticker,
                    order_amount=order_amount,
                    submitted_notional_today=submitted_notional_today,
                    recent_buy_symbols=recent_buy_symbols,
                    portfolio_value=float(account["portfolio_value"]),
                )
                risk_allowed = safety.allowed
                risk_reason = safety.reason if not safety.allowed else risk_reason
                order_amount = safety.target_amount

            if risk_allowed:
                exposure = apply_portfolio_exposure_limits(
                    ticker=ticker,
                    order_amount=order_amount,
                    cash=float(cash),
                    portfolio_value=float(account["portfolio_value"]) * float(getattr(settings, "leverage_factor", 1.0)),
                    buying_power=float(account.get("buying_power", 0.0)),
                    current_gross_exposure=current_gross_exposure,
                    current_position_value=float(held_position["market_value"]) if held_position is not None else 0.0,
                    cash_buffer_mult=conviction.cash_buffer_mult,
                )
                risk_allowed = exposure.allowed
                risk_reason = exposure.reason if not exposure.allowed else risk_reason
                order_amount = exposure.target_amount

            if risk_allowed:
                leverage_cap = apply_effective_leverage_exposure_limits(
                    ticker=ticker,
                    order_amount=order_amount,
                    portfolio_value=float(account["portfolio_value"]),
                    positions_by_symbol=positions_by_symbol,
                )
                risk_allowed = leverage_cap.allowed
                risk_reason = leverage_cap.reason if not leverage_cap.allowed else risk_reason
                order_amount = leverage_cap.target_amount

            if sleeves_enabled(settings):
                if not sleeve_recon_ok:
                    risk_allowed = False
                    risk_reason = sleeve_recon_reason
                    target_amount = 0.0
                    order_amount = 0.0
                elif core_sleeve_budget_remaining is not None and core_sleeve_budget_remaining <= 0:
                    risk_allowed = False
                    risk_reason = "core sleeve budget exhausted for this run"
                    order_amount = 0.0

            log_signal(
                ticker=ticker,
                signal=signal,
                close=latest["close"],
                ma20=latest["ma20"],
                ma50=latest["ma50"],
                rsi=latest["rsi"],
                ai_score=ai_score,
            )

            print(
                f"{ticker}: signal={signal}, "
                f"risk_allowed={risk_allowed}, "
                f"reason='{risk_reason}', "
                f"target_amount={target_amount:.2f}, "
                f"order_amount={order_amount:.2f}, "
                f"ai_score={ai_score}, "
                f"close={latest['close']:.2f}, "
                f"rsi={latest['rsi']:.2f}"
            )

            buy_summary_rows.append(
                f"{ticker}: signal={signal}, allowed={risk_allowed}, "
                f"reason={risk_reason}, order=${order_amount:.2f}, "
                f"ai_score={ai_score}"
            )
            if not risk_allowed:
                skipped_reasons[f"buy:{risk_reason}"] += 1
                _audit_log(
                    audit_ctx,
                    event_type="SKIP_BUY",
                    ticker=ticker,
                    action="BUY",
                    status="SKIPPED",
                    reason=format_audit_reason(risk_reason, ticker),
                    profile_name=profile_name,
                    regime=current_regime,
                    signal=signal,
                    ai_score=ai_score,
                    rank_ai_score=rank_gate.score,
                    rank_ai_percentile=rank_gate.percentile,
                    llm_verdict=_format_llm_verdict(llm_is_ok, llm_reason),
                    notional=order_amount,
                    **_buy_sleeve_audit(budget_after=0.0 if not risk_allowed else order_amount),
                )

            if risk_allowed:
                approved_buys.append({
                    "ticker": ticker,
                    "order_amount": order_amount,
                    "ai_score": ai_score,
                    "rank_ai_score": rank_gate.score,
                    "rank_ai_percentile": rank_gate.percentile,
                    "risk_reason": risk_reason,
                    "signal": signal,
                    "llm_verdict": _format_llm_verdict(llm_is_ok, llm_reason),
                    "limit_price": float(latest["close"]),
                })

        except Exception as exc:
            print(f"{ticker}: ERROR - {exc}")
            buy_summary_rows.append(f"{ticker}: ERROR - {exc}")
            api_error_count += 1
            _audit_log(
                audit_ctx,
                event_type="BUY_ERROR",
                ticker=ticker,
                action="BUY",
                status="ERROR",
                reason=str(exc),
                profile_name=profile_name,
                regime=current_regime,
            )
            notify_error(f"{ticker} bot error", exc)

    # 3) MVO 가중치 적용 (Pass 2: allocation_method에 따라 주문 금액 조정)
    allocation_method = getattr(settings, "allocation_method", "equal_weight")
    if allocation_method != "equal_weight" and len(approved_buys) > 1:
        candidate_tickers = [c["ticker"] for c in approved_buys]
        candidate_ai_scores = {
            c["ticker"]: float(c["ai_score"]) if c["ai_score"] is not None else 0.5
            for c in approved_buys
        }
        mvo_weights = compute_weights_from_ticker_data(
            candidate_tickers=candidate_tickers,
            ticker_data=ticker_data,
            ai_scores=candidate_ai_scores,
            allocation_method=allocation_method,
        )
        portfolio_value = float(account["portfolio_value"])
        for candidate in approved_buys:
            t = candidate["ticker"]
            mvo_amount = portfolio_value * mvo_weights.get(t, 1.0 / len(approved_buys))
            # Respect individual order cap
            candidate["order_amount"] = cap_single_order_amount(
                mvo_amount, portfolio_value, settings
            )
        print(
            f"MVO weights: "
            + ", ".join(
                f"{c['ticker']}={mvo_weights.get(c['ticker'], 0):.3f}"
                for c in approved_buys
            )
        )

    if sleeves_enabled(settings) and approved_buys:
        initial_core_budget = sleeve_allocator.order_budget_for(CORE_SLEEVE_ID)
        before_count = len(approved_buys)
        approved_buys, core_sleeve_budget_remaining = trim_candidates_to_sleeve_budget(
            approved_buys,
            initial_core_budget,
            min_amount=10.0,
        )
        if len(approved_buys) != before_count:
            print(
                "Portfolio sleeves: trimmed "
                f"{before_count - len(approved_buys)} buy candidate(s) to fit "
                f"core budget (${initial_core_budget:.2f})"
            )

    # 4) 주문 제출 (Pass 3)
    for candidate in approved_buys:
        ticker = candidate["ticker"]
        order_amount = candidate["order_amount"]
        risk_reason = candidate["risk_reason"]
        ai_score = candidate["ai_score"]
        signal = candidate["signal"]
        llm_verdict = candidate["llm_verdict"]

        if orders_submitted >= settings.max_orders_per_run:
            print("  SKIP_ORDER: max orders per run reached")
            buy_summary_rows.append(
                f"{ticker}: SKIP_ORDER max orders per run reached, "
                f"ai_score={ai_score}"
            )
            skipped_reasons["buy:max orders per run reached"] += 1
            _audit_log(
                audit_ctx,
                event_type="SKIP_BUY",
                ticker=ticker,
                action="BUY",
                status="SKIPPED",
                reason="max orders per run reached",
                profile_name=profile_name,
                regime=current_regime,
                signal=signal,
                ai_score=ai_score,
                llm_verdict=llm_verdict,
                notional=order_amount,
            )
            continue

        if not can_submit_orders:
            label = _execution_block_label(execute_orders, market_clock)
            print(
                f"  {label}: would BUY {ticker} "
                f"notional=${order_amount:.2f}"
            )
            buy_summary_rows.append(
                f"{ticker}: {label} would BUY ${order_amount:.2f}, "
                f"ai_score={ai_score}"
            )
            skipped_reasons[f"buy:{label.lower()}"] += 1
            _audit_log(
                audit_ctx,
                event_type="SKIP_BUY",
                ticker=ticker,
                action="BUY",
                status="SKIPPED",
                reason=label,
                profile_name=profile_name,
                regime=current_regime,
                signal=signal,
                ai_score=ai_score,
                llm_verdict=llm_verdict,
                notional=order_amount,
            )
            orders_submitted += 1
            submitted_notional_today += order_amount
            continue

        safety_check = live_safety_guard.check_new_buy(
            notional=order_amount,
            open_positions_count=meaningful_positions_count,
        )
        if not safety_check.allowed:
            print(f"  LIVE_SAFETY_BLOCK: would BUY {ticker} — {safety_check.reason}")
            buy_summary_rows.append(
                f"{ticker}: LIVE_SAFETY_BLOCK {safety_check.reason}, ai_score={ai_score}"
            )
            skipped_reasons["buy:live_safety"] += 1
            buy_intent = build_buy_intent(
                run_id=run_id,
                ticker=ticker,
                notional=order_amount,
                signal=signal,
                ai_score=ai_score,
                rank_ai_score=candidate.get("rank_ai_score"),
                rank_ai_percentile=candidate.get("rank_ai_percentile"),
                llm_verdict=llm_verdict,
                risk_reason=risk_reason,
            )
            _audit_log(
                audit_ctx,
                event_type="SKIP_BUY",
                ticker=ticker,
                action="BUY",
                status="SKIPPED",
                reason=f"live safety: {safety_check.reason}",
                profile_name=profile_name,
                regime=current_regime,
                signal=signal,
                ai_score=ai_score,
                llm_verdict=llm_verdict,
                notional=order_amount,
                risk_block_reason=safety_check.reason,
                order_intent_id=buy_intent.intent_id,
            )
            continue

        if (
            sleeves_enabled(settings)
            and core_sleeve_budget_remaining is not None
            and order_amount > core_sleeve_budget_remaining + 1e-6
        ):
            skipped_reasons["buy:core sleeve budget exhausted"] += 1
            _audit_log(
                audit_ctx,
                event_type="SKIP_BUY",
                ticker=ticker,
                action="BUY",
                status="SKIPPED",
                reason=(
                    f"core sleeve budget exhausted "
                    f"(${core_sleeve_budget_remaining:.2f} remaining)"
                ),
                profile_name=profile_name,
                regime=current_regime,
                signal=signal,
                ai_score=ai_score,
                llm_verdict=llm_verdict,
                notional=order_amount,
                **_buy_sleeve_audit(budget_before=core_sleeve_budget_remaining),
            )
            continue

        sleeve_budget_before_submit = core_sleeve_budget_remaining
        buy_intent = build_buy_intent(
            run_id=run_id,
            ticker=ticker,
            notional=order_amount,
            signal=signal,
            ai_score=ai_score,
            rank_ai_score=candidate.get("rank_ai_score"),
            rank_ai_percentile=candidate.get("rank_ai_percentile"),
            llm_verdict=llm_verdict,
            risk_reason=risk_reason,
            client_order_id=f"buy_{run_id}_{ticker}",
            sleeve_id=CORE_SLEEVE_ID,
            sleeve_strategy=(
                sleeve_snapshot.sleeves[CORE_SLEEVE_ID].strategy
                if sleeves_enabled(settings) and CORE_SLEEVE_ID in sleeve_snapshot.sleeves
                else "current_core"
            ),
            sleeve_target_weight=(
                sleeve_snapshot.sleeves[CORE_SLEEVE_ID].target_weight
                if sleeves_enabled(settings) and CORE_SLEEVE_ID in sleeve_snapshot.sleeves
                else None
            ),
            sleeve_budget_before=(
                sleeve_budget_before_submit
                if sleeves_enabled(settings)
                else None
            ),
            sleeve_budget_after=(
                max(0.0, float(sleeve_budget_before_submit or 0.0) - order_amount)
                if sleeves_enabled(settings)
                else None
            ),
            sleeve_risk_mode=(
                sleeve_snapshot.sleeves[CORE_SLEEVE_ID].risk_mode
                if sleeves_enabled(settings) and CORE_SLEEVE_ID in sleeve_snapshot.sleeves
                else ""
            ),
        )
        try:
            buy_submission = broker_adapter.submit_buy_notional(
                ticker=ticker,
                notional=order_amount,
                limit_price=float(candidate["limit_price"]),
                market_clock=market_clock,
                slippage_pct=extended_slippage,
                client_order_id=buy_intent.client_order_id,
            )
            live_safety_guard.record_order_success()
            live_order_count += 1
            orders_submitted += 1
            submitted_notional_today += order_amount
            if core_sleeve_budget_remaining is not None:
                core_sleeve_budget_remaining = max(
                    0.0, core_sleeve_budget_remaining - order_amount
                )

            log_order(
                ticker=ticker,
                notional=order_amount,
                order_id=buy_submission.order_id,
                status=buy_submission.status,
                side=buy_submission.side,
                order_type=buy_submission.order_type,
                reason=risk_reason,
            )

            print(
                f"  PAPER_ORDER_SUBMITTED: BUY {ticker} "
                f"notional=${order_amount:.2f}, "
                f"session={market_clock.session.value}, "
                f"order_id={buy_submission.order_id}, status={buy_submission.status}"
            )
            _audit_log(
                audit_ctx,
                event_type="BUY_SUBMITTED",
                ticker=ticker,
                action="BUY",
                status=buy_submission.status,
                reason=risk_reason,
                profile_name=profile_name,
                regime=current_regime,
                signal=signal,
                ai_score=ai_score,
                rank_ai_score=candidate.get("rank_ai_score"),
                rank_ai_percentile=candidate.get("rank_ai_percentile"),
                llm_verdict=llm_verdict,
                order_id=buy_submission.order_id,
                order_type=buy_submission.order_type,
                side=buy_submission.side,
                notional=order_amount,
                order_intent_id=buy_intent.intent_id,
                broker_order_id=buy_submission.order_id,
                **_buy_sleeve_audit(
                    budget_before=buy_intent.sleeve_budget_before,
                    budget_after=buy_intent.sleeve_budget_after,
                ),
            )

            checked_order = broker_adapter.wait_for_order_status(buy_submission.order_id)
            log_order_status(
                ticker=ticker,
                order_id=checked_order["id"],
                status=checked_order["status"],
                side=checked_order["side"],
                order_type=checked_order["type"],
                filled_qty=checked_order["filled_qty"],
                filled_avg_price=checked_order["filled_avg_price"],
                reason=risk_reason,
            )
            print(
                f"  BUY_STATUS_CHECK: status={checked_order['status']}, "
                f"filled_qty={checked_order['filled_qty']}, "
                f"filled_avg_price={checked_order['filled_avg_price']}"
            )
            _audit_log(
                audit_ctx,
                event_type="BUY_STATUS",
                ticker=ticker,
                action="BUY",
                status=str(checked_order["status"]),
                reason=risk_reason,
                profile_name=profile_name,
                regime=current_regime,
                signal=signal,
                ai_score=ai_score,
                llm_verdict=llm_verdict,
                order_id=str(checked_order["id"]),
                order_type=str(checked_order["type"]),
                side=str(checked_order["side"]),
                notional=order_amount,
                filled_qty=checked_order["filled_qty"],
                filled_avg_price=checked_order["filled_avg_price"],
            )

            if _order_is_filled(checked_order["status"]):
                notify_order(
                    action="BUY",
                    ticker=ticker,
                    status=checked_order["status"],
                    order_id=checked_order["id"],
                    reason=risk_reason,
                    filled_qty=checked_order["filled_qty"],
                    filled_avg_price=checked_order["filled_avg_price"],
                )
            else:
                print(
                    f"  BUY_PENDING: {ticker} limit order remains "
                    f"{checked_order['status']} (overnight/extended hours)"
                )

            buy_summary_rows.append(
                f"{ticker}: BUY_SUBMITTED status={checked_order['status']}, "
                f"filled_qty={checked_order['filled_qty']}, "
                f"filled_avg_price={checked_order['filled_avg_price']}, "
                f"ai_score={ai_score}"
            )

            filled_notional = _filled_notional(checked_order, order_amount)
            if filled_notional > 0:
                if ticker not in guard_open_symbols:
                    guard_open_symbols.add(ticker)
                    open_symbols.add(ticker)
                    positions_count += 1
                cash -= filled_notional
                current_gross_exposure += filled_notional
        except Exception as exc:
            live_safety_guard.record_order_failure()
            if isinstance(exc, ConnectionError) and execute_orders:
                notify_error(f"CRITICAL: Network error during buy execution for {ticker}", exc)
                raise
            print(f"  Buy order error for {ticker}: {exc}")
            api_error_count += 1
            _audit_log(
                audit_ctx,
                event_type="BUY_ERROR",
                ticker=ticker,
                action="BUY",
                status="ERROR",
                reason=str(exc),
                profile_name=profile_name,
                regime=current_regime,
                signal=signal,
                ai_score=ai_score,
                notional=order_amount,
            )

    # 6) 결과 저장 및 피크 정보 갱신
    _save_peaks(peaks)

    metrics_summary = _summarize_run_metrics(
        live_order_count=live_order_count,
        skipped_reasons=skipped_reasons,
        data_error_count=data_error_count,
        api_error_count=api_error_count,
    )
    exit_summary = f"{metrics_summary}\n{compact_exit_summary(exit_summary_rows, limit=20)}"
    buy_summary = f"{metrics_summary}\n{compact_buy_summary(buy_summary_rows, limit=10)}"

    try:
        notify_run_summary(
            market_is_open=market_clock.orders_allowed,
            execute_orders=execute_orders,
            cash=account["cash"],
            portfolio_value=account["portfolio_value"],
            positions_count=account["positions_count"],
            exit_summary=exit_summary,
            buy_summary=buy_summary,
        )
    except Exception as exc:
        print(f"TELEGRAM_SUMMARY_ERROR - {exc}")



def compact_buy_summary(rows: list[str], limit: int = 10) -> str:
    if not rows:
        return "No buy checks."

    priority_rows = []
    blocked_count = 0
    skipped_count = 0
    not_allowed_count = 0
    error_rows = []

    for row in rows:
        lower = row.lower()

        if "error" in lower:
            error_rows.append(row)
        elif "allowed=true" in lower:
            priority_rows.append(row)
        elif "skip_order" in lower or "max orders" in lower:
            skipped_count += 1
        elif "allowed=false" in lower:
            not_allowed_count += 1
        else:
            blocked_count += 1

    selected = []

    if error_rows:
        selected.extend(error_rows[:limit])

    remaining = max(0, limit - len(selected))
    selected.extend(priority_rows[:remaining])

    summary_lines = selected[:limit]

    hidden_allowed = max(0, len(priority_rows) - max(0, limit - len(error_rows)))
    hidden_total = hidden_allowed + blocked_count + skipped_count + not_allowed_count

    summary_lines.append("")
    summary_lines.append(
        f"Summary: allowed_candidates={len(priority_rows)}, "
        f"errors={len(error_rows)}, "
        f"not_allowed={not_allowed_count}, "
        f"skipped_or_blocked={skipped_count + blocked_count}, "
        f"hidden={hidden_total}"
    )

    return "\n".join(summary_lines)


def compact_exit_summary(rows: list[str], limit: int = 20) -> str:
    if not rows:
        return "No open positions."

    if len(rows) <= limit:
        return "\n".join(rows)

    shown = rows[:limit]
    shown.append(f"... hidden_exit_rows={len(rows) - limit}")
    return "\n".join(shown)



if __name__ == "__main__":
    main()
