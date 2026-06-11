from __future__ import annotations

import src.config  # noqa: F401  # load .env (GEMINI_API_KEY) before LLM

from src.daily_bar_session import check_price_frame_freshness
from src.trading.bot_helpers import (
    PEAKS_PATH,
    apply_volume_volatility_filters,
    audit_log,
    execution_block_label,
    execution_reference_price,
    filled_notional,
    format_llm_verdict,
    get_signal_for_ticker,
    load_peaks,
    normalize_peaks,
    offline_account_summary,
    order_is_filled,
    parse_args,
    quarantine_corrupt_peaks_file,
    resolve_full_exit_reason,
    save_peaks,
    summarize_run_metrics,
)
from src.trading.buy_pipeline import run_buy_pipeline
from src.trading.exit_pipeline import run_exit_pipeline
from src.trading.sleeve_rebalance_pipeline import run_sleeve_rebalance_pipeline
from src.trading.run_context import (
    build_sleeve_rebalance_run_context,
    build_trading_run_context,
)
from src.trading.run_finalize import (
    compact_buy_summary,
    compact_exit_summary,
    finalize_trading_run,
)

# Backward-compatible aliases for tests and legacy imports
_load_peaks = load_peaks
_save_peaks = save_peaks
_normalize_peaks = normalize_peaks
_quarantine_corrupt_peaks_file = quarantine_corrupt_peaks_file
_format_llm_verdict = format_llm_verdict
_summarize_run_metrics = summarize_run_metrics
_resolve_full_exit_reason = resolve_full_exit_reason
_apply_volume_volatility_filters = apply_volume_volatility_filters
_offline_account_summary = offline_account_summary
_execution_reference_price = execution_reference_price
_execution_block_label = execution_block_label
_order_is_filled = order_is_filled
_audit_log = audit_log
_filled_notional = filled_notional
_check_price_frame_freshness = check_price_frame_freshness


def main() -> None:
    args = parse_args()
    if getattr(args, "sleeve_rebalance_only", False):
        ctx = build_sleeve_rebalance_run_context(execute_orders=args.execute)
        run_sleeve_rebalance_pipeline(ctx)
        finalize_trading_run(ctx)
        return

    ctx = build_trading_run_context(execute_orders=args.execute)
    run_exit_pipeline(ctx)
    run_sleeve_rebalance_pipeline(ctx)
    ctx.sleeve_ctx.refresh_snapshot()
    ctx.sleeve_ctx.apply_cash_surplus_deploy()
    run_buy_pipeline(ctx)
    finalize_trading_run(ctx)


if __name__ == "__main__":
    main()
