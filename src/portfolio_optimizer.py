"""Mean-Variance Optimization and Black-Litterman portfolio weight computation."""

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def compute_mvo_weights(
    returns_df: pd.DataFrame,
    min_weight: float = 0.05,
    max_weight: float = 0.40,
) -> dict[str, float]:
    """Max-Sharpe MVO weights. Falls back to equal weight on failure."""
    tickers = returns_df.columns.tolist()
    n = len(tickers)

    if n == 1:
        return {tickers[0]: 1.0}

    clean = returns_df.dropna()
    if len(clean) < max(n + 2, 10):
        return {t: 1.0 / n for t in tickers}

    mu = clean.mean().values
    Sigma = clean.cov().values

    def neg_sharpe(w: np.ndarray) -> float:
        port_vol = float(np.sqrt(w @ Sigma @ w))
        if port_vol < 1e-10:
            return 0.0
        return -(w @ mu) / port_vol

    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]
    bounds = [(min_weight, max_weight)] * n
    w0 = np.full(n, 1.0 / n)

    res = minimize(neg_sharpe, w0, method="SLSQP", bounds=bounds, constraints=constraints,
                   options={"ftol": 1e-9, "maxiter": 500})

    weights = res.x if res.success else w0
    weights = np.maximum(weights, 0.0)
    total = weights.sum()
    weights = weights / total if total > 1e-12 else w0

    return {tickers[i]: float(weights[i]) for i in range(n)}


def compute_bl_weights(
    returns_df: pd.DataFrame,
    ai_scores: dict[str, float],
    tau: float = 0.05,
    risk_aversion: float = 1.5,
    min_weight: float = 0.05,
    max_weight: float = 0.40,
) -> dict[str, float]:
    """Black-Litterman weights using AI scores as absolute return views.

    AI score > 0.5 → positive view on that ticker's daily return.
    Views are combined with CAPM equilibrium returns via BL formula.
    """
    tickers = returns_df.columns.tolist()
    n = len(tickers)

    if n == 1:
        return {tickers[0]: 1.0}

    clean = returns_df.dropna()
    if len(clean) < max(n + 2, 10):
        return {t: 1.0 / n for t in tickers}

    Sigma = clean.cov().values
    w_eq = np.full(n, 1.0 / n)

    # CAPM equilibrium returns: pi = lambda * Sigma * w_eq
    pi = risk_aversion * Sigma @ w_eq

    # Build view matrix P, view vector Q, uncertainty Omega
    P_rows, Q_rows, omega_diags = [], [], []
    for i, ticker in enumerate(tickers):
        score = ai_scores.get(ticker, 0.5)
        deviation = score - 0.5
        if abs(deviation) > 0.05:
            row = np.zeros(n)
            row[i] = 1.0
            # Scale: 0.5 deviation in score → ~0.1% expected daily excess return
            expected_return = pi[i] + deviation * 0.002
            P_rows.append(row)
            Q_rows.append(expected_return)
            omega_diags.append(tau * float(row @ Sigma @ row))

    if P_rows:
        P = np.array(P_rows)
        Q = np.array(Q_rows)
        Omega = np.diag(omega_diags)
        try:
            tSigma_inv = np.linalg.inv(tau * Sigma)
            Omega_inv = np.linalg.inv(Omega)
            M_inv = np.linalg.inv(tSigma_inv + P.T @ Omega_inv @ P)
            mu_bl = M_inv @ (tSigma_inv @ pi + P.T @ Omega_inv @ Q)
        except np.linalg.LinAlgError:
            mu_bl = pi
    else:
        mu_bl = pi

    def neg_sharpe_bl(w: np.ndarray) -> float:
        port_vol = float(np.sqrt(w @ Sigma @ w))
        if port_vol < 1e-10:
            return 0.0
        return -(w @ mu_bl) / port_vol

    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]
    bounds = [(min_weight, max_weight)] * n
    w0 = np.full(n, 1.0 / n)

    res = minimize(neg_sharpe_bl, w0, method="SLSQP", bounds=bounds, constraints=constraints,
                   options={"ftol": 1e-9, "maxiter": 500})

    weights = res.x if res.success else w0
    weights = np.maximum(weights, 0.0)
    total = weights.sum()
    weights = weights / total if total > 1e-12 else w0

    return {tickers[i]: float(weights[i]) for i in range(n)}


def compute_weights_from_ticker_data(
    candidate_tickers: list[str],
    ticker_data: dict,
    ai_scores: dict[str, float],
    allocation_method: str = "mvo",
    lookback_days: int = 60,
    min_weight: float = 0.05,
    max_weight: float = 0.40,
) -> dict[str, float]:
    """Compute MVO/BL weights from a ticker_data dict for use in live main.py."""
    n = len(candidate_tickers)
    equal = {t: 1.0 / n for t in candidate_tickers}

    if n <= 1 or allocation_method == "equal_weight":
        return equal

    returns_cols: dict[str, list[float]] = {}
    for ticker in candidate_tickers:
        df = ticker_data.get(ticker)
        if df is None or df.empty:
            continue
        closes = df.sort_values("date")["close"].values
        if len(closes) < 2:
            continue
        rets = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]
        returns_cols[ticker] = rets[-lookback_days:]

    if not returns_cols:
        return equal

    min_len = min(len(v) for v in returns_cols.values())
    if min_len < 10:
        return equal

    import pandas as pd

    returns_df = pd.DataFrame(
        {t: v[-min_len:] for t, v in returns_cols.items()}
    )

    if allocation_method == "mvo":
        weights = compute_mvo_weights(returns_df, min_weight=min_weight, max_weight=max_weight)
    elif allocation_method == "bl_mvo":
        weights = compute_bl_weights(
            returns_df, ai_scores=ai_scores, min_weight=min_weight, max_weight=max_weight
        )
    else:
        return equal

    for t in candidate_tickers:
        if t not in weights:
            weights[t] = min_weight
    total = sum(weights.values())
    return {t: weights[t] / total for t in candidate_tickers}


def compute_candidate_weights(
    market_df: pd.DataFrame,
    candidate_tickers: list[str],
    current_date: pd.Timestamp,
    ai_scores: dict[str, float],
    allocation_method: str = "mvo",
    lookback_days: int = 60,
    min_weight: float = 0.05,
    max_weight: float = 0.40,
) -> dict[str, float]:
    """Compute portfolio weights for a set of buy candidates.

    Uses historical returns from market_df up to current_date.
    Falls back to equal weight when data is insufficient.
    """
    n = len(candidate_tickers)
    equal = {t: 1.0 / n for t in candidate_tickers}

    if n <= 1 or allocation_method == "equal_weight":
        return equal

    # Pull lookback window (need 2x calendar days to get ~lookback trading days)
    lookback_start = current_date - pd.Timedelta(days=lookback_days * 2)
    hist = market_df[
        (market_df["date"] <= current_date)
        & (market_df["date"] >= lookback_start)
        & (market_df["ticker"].isin(candidate_tickers))
    ]

    if hist.empty:
        return equal

    prices = hist.pivot(index="date", columns="ticker", values="close").sort_index()
    returns_df = prices.pct_change().dropna(how="all").tail(lookback_days)

    # Drop tickers with too many NaN
    returns_df = returns_df.dropna(axis=1, thresh=len(returns_df) // 2)
    available = [t for t in candidate_tickers if t in returns_df.columns]
    if len(available) < 2:
        return equal

    returns_df = returns_df[available].dropna()

    if allocation_method == "mvo":
        weights = compute_mvo_weights(returns_df, min_weight=min_weight, max_weight=max_weight)
    elif allocation_method == "bl_mvo":
        weights = compute_bl_weights(
            returns_df, ai_scores=ai_scores, min_weight=min_weight, max_weight=max_weight
        )
    else:
        weights = equal

    # Fill missing tickers with min_weight, then renormalize
    for t in candidate_tickers:
        if t not in weights:
            weights[t] = min_weight
    total = sum(weights.values())
    return {t: weights[t] / total for t in candidate_tickers}
