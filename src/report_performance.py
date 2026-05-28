"""실제 거래 내역과 백테스트 결과를 비교 분석하는 스크립트."""

import pandas as pd
from datetime import datetime, timedelta
from src.alpaca_client import get_account_summary, get_positions_summary
from src.config import SIGNAL_LOG_PATH, ORDER_LOG_PATH


def analyze_slippage(signals_path=None, orders_path=None):
    """signals log와 orders log를 결합하여 슬리피지를 분석한다."""
    
    # 인자가 제공되지 않으면 기본 경로 사용
    if signals_path is None:
        signals_path = SIGNAL_LOG_PATH
    if orders_path is None:
        orders_path = ORDER_LOG_PATH
        
    try:
        signals_df = pd.read_csv(signals_path)
        orders_df = pd.read_csv(orders_path)
    except FileNotFoundError:
        print("Log files not found.")
        return

    # 주문 체결 내역만 필터링 (기존 로그의 컬럼 밀림 현상 대응)
    # 1. 'event' 컬럼에서 확인
    filled_orders = orders_df[orders_df.get("event") == "STATUS_CHECK"].copy()
    
    # 2. 만약 비어있다면, 다른 컬럼에 밀려있는지 확인 (예: filled_avg_price 컬럼에 STATUS_CHECK이 있는 경우)
    if filled_orders.empty:
        # 마지막 컬럼들 중 'STATUS_CHECK'이 포함된 행 찾기
        mask = orders_df.apply(lambda row: "STATUS_CHECK" in row.values, axis=1)
        filled_orders = orders_df[mask].copy()
        
        # 컬럼 재매핑 (데이터 위치에 맞게)
        # 필터링된 행들에 대해 'STATUS_CHECK'이 위치한 인덱스를 기준으로 재배치
        def remap_row(row):
            vals = list(row)
            if "STATUS_CHECK" in vals:
                idx = vals.index("STATUS_CHECK")
                # STATUS_CHECK이 마지막(10번 인덱스)에 있다고 가정하고 밀린 경우 대응
                # timestamp, ticker, notional, order_id, status, side, order_type, filled_qty, filled_avg_price, reason, event
                if idx == 10:
                    return pd.Series([vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], vals[7], vals[8], vals[9], vals[10]],
                                   index=["timestamp", "ticker", "notional", "order_id", "status", "side", "order_type", "filled_qty", "filled_avg_price", "reason", "event"])
            return row

        if not filled_orders.empty:
            filled_orders = filled_orders.apply(remap_row, axis=1)

    if filled_orders.empty:
        print("No filled orders found in log.")
        return

    # 숫자형 변환
    filled_orders["filled_avg_price"] = pd.to_numeric(filled_orders["filled_avg_price"], errors="coerce")
    filled_orders = filled_orders.dropna(subset=["filled_avg_price"])


    # Timestamp 변환 (초 단위 절삭하여 매칭 확률 높임)
    signals_df["ts_short"] = pd.to_datetime(signals_df["timestamp"]).dt.floor("min")
    filled_orders["ts_short"] = pd.to_datetime(filled_orders["timestamp"]).dt.floor("min")

    # Ticker와 유사 시간대로 Join
    merged = pd.merge(
        filled_orders,
        signals_df,
        on=["ticker", "ts_short"],
        how="inner",
        suffixes=("_order", "_signal")
    )

    if merged.empty:
        print("Could not match orders with signals for slippage analysis.")
        # 시간을 좀 더 넓게 잡아보자 (5분 내외)
        return

    merged["slippage_pct"] = (merged["filled_avg_price"] - merged["close"]) / merged["close"] * 100

    # 슬리피지 USD 비용 계산
    merged["filled_qty"] = pd.to_numeric(merged["filled_qty"], errors="coerce")
    merged["slippage_usd"] = (merged["filled_avg_price"] - merged["close"]) * merged["filled_qty"]
    
    # BUY는 높은 가격에 체결되면 슬리피지 발생 (+), SELL은 낮은 가격에 체결되면 발생 (-)
    # 편의상 절대값이나 방향성을 고려해 출력
    print("\n=== Slippage Analysis (Actual vs Signal Price) ===")
    summary = merged.groupby("ticker").agg(
        avg_slippage_pct=("slippage_pct", "mean"),
        total_slippage_usd=("slippage_usd", "sum"),
        trades=("ticker", "count")
    )
    print(summary.to_string())
    print(f"\nOverall Average Slippage: {merged['slippage_pct'].mean():.4f}%")
    print(f"Total Slippage Cost: ${merged['slippage_usd'].sum():.2f}")


def report_account_performance():
    """Alpaca 계좌의 현재 실적 요약."""
    account = get_account_summary()
    positions = get_positions_summary()
    
    print("\n=== Account Performance Summary ===")
    print(f"Portfolio Value: ${account['portfolio_value']:.2f}")
    print(f"Cash: ${account['cash']:.2f}")
    
    if positions:
        print("\n--- Open Positions ---")
        pos_df = pd.DataFrame(positions)
        print(pos_df[["symbol", "qty", "market_value", "unrealized_plpc"]].to_string(index=False))
    else:
        print("\nNo open positions.")


def main():
    print(f"Performance Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_account_performance()
    analyze_slippage()


if __name__ == "__main__":
    main()
