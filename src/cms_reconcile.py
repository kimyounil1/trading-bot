"""CMS paper execute vs Alpaca order reconciliation (no Streamlit dependency)."""

from __future__ import annotations

import pandas as pd


def reconcile_cms_execute_with_alpaca(
    execute_rows: list[dict] | pd.DataFrame,
    open_orders: list[dict],
    closed_orders: list[dict] | None = None,
) -> list[dict[str, str]]:
    """Detect CMS submit vs Alpaca OPEN mismatches after paper execute."""
    if isinstance(execute_rows, pd.DataFrame):
        rows = execute_rows.to_dict(orient="records")
    else:
        rows = list(execute_rows)

    closed_orders = closed_orders or []
    closed_by_id = {str(order.get("id", "")): order for order in closed_orders}
    open_by_id = {str(order.get("id", "")): order for order in open_orders}

    alerts: list[dict[str, str]] = []

    for row in rows:
        order_id = str(row.get("order_id") or "").strip()
        if not order_id or str(row.get("status", "")).upper() in {"ERROR", "SKIPPED"}:
            continue
        if order_id in open_by_id:
            continue
        if closed_by_id.get(order_id) is not None:
            continue
        alerts.append(
            {
                "kind": "cms_missing_on_alpaca",
                "severity": "warning",
                "message": (
                    f"CMS submitted {row.get('action')} {row.get('ticker')} "
                    f"(order_id={order_id}) but order is not OPEN or in recent closed list."
                ),
            }
        )

    cms_ids = {
        str(row.get("order_id"))
        for row in rows
        if row.get("order_id") and str(row.get("status", "")).upper() not in {"ERROR", "SKIPPED"}
    }
    for order in open_orders:
        client_id = str(order.get("client_order_id") or "")
        order_id = str(order.get("id") or "")
        if not client_id.startswith("cms_"):
            continue
        if order_id in cms_ids:
            continue
        alerts.append(
            {
                "kind": "alpaca_open_without_cms_log",
                "severity": "warning",
                "message": (
                    f"Alpaca OPEN {order.get('symbol')} {order.get('side')} "
                    f"(id={order_id}, client_order_id={client_id}) not in latest CMS execute batch."
                ),
            }
        )

    return alerts
