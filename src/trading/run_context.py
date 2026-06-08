"""Trading run context — account, market data, guards, mutable run state."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import json

from src.broker_adapter import get_broker_adapter
from src.buy_guards import apply_sector_score_bonus  # noqa: F401
from src.candidate_cache import get_dynamic_universe
from src.data_loader import load_price_data_batch
from src.live_deploy_guard import assert_live_execution_allowed
from src.live_readiness import assert_live_readiness_for_execute
from src.logger import log_execution_audit
from src.market_clock import get_market_clock
from src.market_regime import get_current_regime
from src.ml_model import load_ai_score_model
from src.macro_loader import load_macro_data
from src.margin_leverage_paper_gate import (
    apply_margin_leverage_paper_overrides,
    evaluate_margin_leverage_buy_block,
)
from src.notifier import notify_info
from src.llm_analyst import llm_cache_only_for_run
from src.order_intent import AuditContext, build_audit_context
from src.position_dust import (
    count_meaningful_positions,
    dust_position_min_usd,
    meaningful_gross_exposure,
    meaningful_open_symbols,
)
from src.rank_ai_gate import build_rank_ai_gate_scores
from src.risk.live_safety import LiveSafetyGuard
from src.risk_manager import get_recent_buy_symbols, get_today_buy_notional
from src.sector_rotation import get_sector_leadership
from src.settings import apply_dynamic_profile, load_settings
from src.sleeve_runtime import SleeveRunContext, init_sleeve_run_context
from src.strategy import is_bullish_market_regime
from src.trading.bot_helpers import load_peaks, offline_account_summary
from src.trading_config_guard import (
    apply_environment_profile,
    resolve_trading_environment,
    validate_trading_config,
)
from src.daily_bar_session import check_price_frame_freshness


@dataclass
class TradingRunContext:
    execute_orders: bool
    run_id: str
    settings: Any
    profile_name: str
    trading_env: str
    broker_adapter: Any
    audit_ctx: AuditContext
    sleeve_ctx: SleeveRunContext
    account: dict[str, Any]
    positions: list[dict[str, Any]]
    positions_by_symbol: dict[str, dict[str, Any]]
    open_symbols: set[str]
    ticker_data: dict[str, Any]
    spy_df: Any
    vix_df: Any
    macro_df: Any
    market_clock: Any
    live_safety_guard: LiveSafetyGuard
    extended_slippage: float
    current_regime: str
    can_submit_orders: bool
    circuit_breaker_active: bool
    dust_min_usd: float
    meaningful_positions_count: int
    guard_open_symbols: set[str]
    current_gross_exposure: float
    peaks: dict[str, float]
    price_data_freshness: dict[str, tuple[bool, str]]
    market_regime_bullish: bool
    rank_ai_gate_scores: dict[str, Any]
    ai_model_bundle: Any
    top_sectors: list[str]
    margin_leverage_block_active: bool
    margin_leverage_block_reason: str
    cash: float
    orders_submitted: int = 0
    submitted_notional_today: float = 0.0
    recent_buy_symbols: set[str] = field(default_factory=set)
    exit_summary_rows: list[str] = field(default_factory=list)
    buy_summary_rows: list[str] = field(default_factory=list)
    skipped_reasons: Counter = field(default_factory=Counter)
    data_error_count: int = 0
    api_error_count: int = 0
    live_order_count: int = 0
    positions_count: int = 0


def build_trading_run_context(*, execute_orders: bool) -> TradingRunContext:
    execute_orders = execute_orders
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
        account = offline_account_summary()
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
    sleeve_ctx = init_sleeve_run_context(
        settings,
        broker_adapter=broker_adapter,
        account=account,
        positions=positions,
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
    peaks = load_peaks()
    price_data_freshness = {
        ticker: check_price_frame_freshness(raw_df, market_clock)
        for ticker, raw_df in ticker_data.items()
    }

    # 섹터 순환매 분석 (Phase 15-A)
    top_sectors = []
    if getattr(settings, "sector_rotation_enabled", False):
        top_sectors = get_sector_leadership()

    print("-" * 80)

    return TradingRunContext(
        execute_orders=execute_orders,
        run_id=run_id,
        settings=settings,
        profile_name=profile_name,
        trading_env=trading_env,
        broker_adapter=broker_adapter,
        audit_ctx=audit_ctx,
        sleeve_ctx=sleeve_ctx,
        account=account,
        positions=positions,
        positions_by_symbol=positions_by_symbol,
        open_symbols=open_symbols,
        ticker_data=ticker_data,
        spy_df=spy_df,
        vix_df=vix_df,
        macro_df=macro_df,
        market_clock=market_clock,
        live_safety_guard=live_safety_guard,
        extended_slippage=extended_slippage,
        current_regime=current_regime,
        can_submit_orders=can_submit_orders,
        circuit_breaker_active=circuit_breaker_active,
        dust_min_usd=dust_min_usd,
        meaningful_positions_count=meaningful_positions_count,
        guard_open_symbols=guard_open_symbols,
        current_gross_exposure=current_gross_exposure,
        peaks=peaks,
        price_data_freshness=price_data_freshness,
        market_regime_bullish=market_regime_bullish,
        rank_ai_gate_scores=rank_ai_gate_scores,
        ai_model_bundle=ai_model_bundle,
        top_sectors=top_sectors,
        margin_leverage_block_active=margin_leverage_block_active,
        margin_leverage_block_reason=margin_leverage_block_reason,
        cash=cash,
        orders_submitted=orders_submitted,
        submitted_notional_today=submitted_notional_today,
        recent_buy_symbols=recent_buy_symbols,
        exit_summary_rows=exit_summary_rows,
        buy_summary_rows=buy_summary_rows,
        skipped_reasons=skipped_reasons,
        data_error_count=data_error_count,
        api_error_count=api_error_count,
        live_order_count=live_order_count,
        positions_count=positions_count,
    )
