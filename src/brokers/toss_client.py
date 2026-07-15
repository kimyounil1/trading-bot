"""Toss Securities Open API client — read-only phase.

Implements OAuth2 client-credentials auth + GET reads against
https://openapi.tossinvest.com (see docs/runbook.md "Toss").

Order mutation endpoints (POST /orders, cancel, modify) are intentionally NOT
implemented here yet: this module is read-only so a wiring mistake cannot place
a live order. See src/brokers/toss.py for the adapter surface.

Auth: POST /oauth2/token (grant_type=client_credentials) -> access_token (~1h).
Account/asset/order reads also require the X-Tossinvest-Account header.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Optional

import requests

DEFAULT_API_BASE = "https://openapi.tossinvest.com"
DEFAULT_TIMEOUT_SEC = 15.0
_TOKEN_REFRESH_MARGIN_SEC = 300.0  # refresh ~5 min before expiry
_MAX_RETRIES = 3

_token_lock = threading.Lock()
_cached_token: Optional[str] = None
_token_expiry_epoch: float = 0.0
_cached_account_seq: Optional[str] = None


class TossAPIError(RuntimeError):
    """Toss API returned an error envelope or unexpected response."""

    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(f"Toss API {status} {code}: {message}")


def api_base() -> str:
    return os.getenv("TOSS_API_BASE", DEFAULT_API_BASE).strip().rstrip("/") or DEFAULT_API_BASE


def _timeout() -> float:
    try:
        return float(os.getenv("TOSS_TIMEOUT", str(DEFAULT_TIMEOUT_SEC)))
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_SEC


def _client_id() -> str:
    return (os.getenv("TOSS_CLIENT_ID") or "").strip()


def _client_secret() -> str:
    return (os.getenv("TOSS_SECRET_KEY") or os.getenv("TOSS_CLIENT_SECRET") or "").strip()


def credentials_available() -> bool:
    return bool(_client_id() and _client_secret())


def reset_token_cache() -> None:
    """Clear cached token/account (tests, key rotation)."""
    global _cached_token, _token_expiry_epoch, _cached_account_seq
    with _token_lock:
        _cached_token = None
        _token_expiry_epoch = 0.0
        _cached_account_seq = None


def _raise_for_error(response: requests.Response) -> None:
    if response.status_code < 400:
        return
    code = "unknown"
    message = response.text[:300]
    try:
        payload = response.json()
        err = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(err, dict):
            code = str(err.get("code", code))
            message = str(err.get("message", message))
    except ValueError:
        pass
    raise TossAPIError(response.status_code, code, message)


def _get_token() -> str:
    global _cached_token, _token_expiry_epoch
    with _token_lock:
        now = time.time()
        if _cached_token and now < _token_expiry_epoch - _TOKEN_REFRESH_MARGIN_SEC:
            return _cached_token
        if not credentials_available():
            raise TossAPIError(
                0, "missing-credentials", "TOSS_CLIENT_ID / TOSS_SECRET_KEY not set"
            )
        response = requests.post(
            f"{api_base()}/oauth2/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": _client_id(),
                "client_secret": _client_secret(),
            },
            timeout=_timeout(),
        )
        _raise_for_error(response)
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise TossAPIError(response.status_code, "no-token", "token response missing access_token")
        expires_in = float(payload.get("expires_in", 3600) or 3600)
        _cached_token = str(token)
        _token_expiry_epoch = now + expires_in
        return _cached_token


def _request(
    method: str,
    path: str,
    *,
    account: bool = False,
    params: Optional[dict[str, Any]] = None,
) -> Any:
    """Authenticated request with bounded 429/5xx retry. Reads only."""
    url = f"{api_base()}{path}"
    last_exc: Optional[BaseException] = None
    for attempt in range(_MAX_RETRIES):
        headers = {"Authorization": f"Bearer {_get_token()}"}
        if account:
            seq = resolve_account_seq()
            if seq:
                headers["X-Tossinvest-Account"] = seq
        try:
            response = requests.request(
                method, url, headers=headers, params=params, timeout=_timeout()
            )
        except requests.RequestException as exc:
            last_exc = exc
            if attempt == _MAX_RETRIES - 1:
                raise TossAPIError(0, "network-error", str(exc)) from exc
            time.sleep(2.0**attempt)
            continue

        if response.status_code == 401 and attempt < _MAX_RETRIES - 1:
            reset_token_cache()
            continue
        if response.status_code == 429 and attempt < _MAX_RETRIES - 1:
            retry_after = response.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else 2.0**attempt
            except ValueError:
                delay = 2.0**attempt
            time.sleep(min(delay, 10.0))
            continue
        if response.status_code >= 500 and attempt < _MAX_RETRIES - 1:
            time.sleep(2.0**attempt)
            continue

        _raise_for_error(response)
        if not response.content:
            return None
        return response.json()

    if last_exc is not None:
        raise TossAPIError(0, "network-error", str(last_exc)) from last_exc
    raise TossAPIError(0, "unknown", "request failed without response")


_ENVELOPE_KEYS = ("result", "data")
_LIST_KEYS = ("items", "list", "elements", "content")
_OBJECT_KEYS = ("result", "data")


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _as_list(payload: Any, *keys: str) -> list[dict[str, Any]]:
    """Extract a list from a Toss response.

    Handles bare lists, {envelope: [...]}, and nested {envelope: {items: [...]}}.
    """
    if isinstance(payload, list):
        return _dicts(payload)
    if not isinstance(payload, dict):
        return []

    # Direct list under an envelope or caller-provided key (e.g. accounts -> result: [...]).
    for key in (*_ENVELOPE_KEYS, *_LIST_KEYS, *keys):
        if isinstance(payload.get(key), list):
            return _dicts(payload[key])

    # Nested list one level down (e.g. holdings -> result: {items: [...]}).
    for env in _ENVELOPE_KEYS:
        inner = payload.get(env)
        if isinstance(inner, dict):
            for key in (*_LIST_KEYS, *keys):
                if isinstance(inner.get(key), list):
                    return _dicts(inner[key])
    return []


def _as_object(payload: Any) -> dict[str, Any]:
    """Extract a dict body from a Toss response ({result|data: {...}} or {...})."""
    if isinstance(payload, dict):
        for key in _OBJECT_KEYS:
            value = payload.get(key)
            if isinstance(value, dict):
                return value
        return payload
    return {}


def get_accounts() -> list[dict[str, Any]]:
    """GET /api/v1/accounts — account list (no account header needed)."""
    payload = _request("GET", "/api/v1/accounts")
    return _as_list(payload, "accounts")


def resolve_account_seq() -> Optional[str]:
    """Env TOSS_ACCOUNT, else first account from GET /api/v1/accounts (cached)."""
    global _cached_account_seq
    env_seq = (os.getenv("TOSS_ACCOUNT") or "").strip()
    if env_seq:
        return env_seq
    if _cached_account_seq is not None:
        return _cached_account_seq or None
    accounts = get_accounts()
    seq = ""
    if accounts:
        first = accounts[0]
        for key in ("accountSeq", "accountNo", "account_seq", "seq", "id"):
            if first.get(key) not in (None, ""):
                seq = str(first[key])
                break
    _cached_account_seq = seq
    return seq or None


def get_holdings() -> list[dict[str, Any]]:
    """GET /api/v1/holdings — held stocks (needs account header)."""
    payload = _request("GET", "/api/v1/holdings", account=True)
    return _as_list(payload, "holdings")


def get_orders(status: str = "OPEN", *, limit: int = 100) -> list[dict[str, Any]]:
    """GET /api/v1/orders — order list (needs account header).

    status is required by Toss and must be 'OPEN' (working) or 'CLOSED' (done).
    """
    params: dict[str, Any] = {"status": status, "limit": limit}
    payload = _request("GET", "/api/v1/orders", account=True, params=params)
    return _as_list(payload, "orders")


def get_order(order_id: str) -> dict[str, Any]:
    """GET /api/v1/orders/{orderId} — order detail (needs account header)."""
    payload = _request("GET", f"/api/v1/orders/{order_id}", account=True)
    return _as_object(payload)


def get_buying_power(currency: str = "KRW") -> dict[str, Any]:
    """GET /api/v1/buying-power — cash buying power (needs account header).

    currency is required by Toss ('KRW' or 'USD').
    """
    payload = _request(
        "GET", "/api/v1/buying-power", account=True, params={"currency": currency}
    )
    return _as_object(payload)


def get_prices(symbols: list[str]) -> list[dict[str, Any]]:
    """GET /api/v1/prices — current prices (token only, no account header)."""
    joined = ",".join(str(s).strip().upper() for s in symbols if str(s).strip())
    payload = _request("GET", "/api/v1/prices", params={"symbols": joined})
    return _as_list(payload, "prices")


def get_stocks(symbols: list[str]) -> list[dict[str, Any]]:
    """GET /api/v1/stocks — stock/ETF metadata for up to 200 known symbols."""
    normalized = [
        str(symbol).strip().upper()
        for symbol in symbols
        if str(symbol).strip()
    ]
    normalized = list(dict.fromkeys(normalized))
    if not normalized:
        return []
    if len(normalized) > 200:
        raise ValueError("Toss stock metadata supports at most 200 symbols per request")
    payload = _request(
        "GET",
        "/api/v1/stocks",
        params={"symbols": ",".join(normalized)},
    )
    return _as_list(payload, "stocks")
