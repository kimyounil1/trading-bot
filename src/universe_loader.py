"""Scan-universe profiles: smoke (CI), paper (strategy_config), research (master CSV)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

MASTER_PATH = Path("config/universe_master.csv")
SMOKE_PATH = Path("config/universe_smoke.json")
VALID_PROFILES = frozenset({"smoke", "paper", "research"})


def normalize_tickers(tickers: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in tickers:
        ticker = str(raw).strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        out.append(ticker)
    return out


def get_universe_profile() -> str:
    profile = os.environ.get("UNIVERSE_PROFILE", "paper").strip().lower()
    if profile not in VALID_PROFILES:
        raise ValueError(
            f"Invalid UNIVERSE_PROFILE={profile!r}; expected one of {sorted(VALID_PROFILES)}"
        )
    return profile


def load_master_tickers(path: Path = MASTER_PATH) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"Master universe file missing: {path}")
    frame = pd.read_csv(path)
    column = "ticker" if "ticker" in frame.columns else frame.columns[0]
    return normalize_tickers(frame[column].astype(str).tolist())


def load_smoke_tickers(path: Path = SMOKE_PATH) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"Smoke universe file missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    tickers = payload.get("tickers")
    if not isinstance(tickers, list) or not tickers:
        raise ValueError(f"{path}: 'tickers' must be a non-empty list")
    return normalize_tickers([str(t) for t in tickers])


def resolve_scan_tickers(
    config_tickers: list[str],
    *,
    profile: str | None = None,
) -> list[str]:
    """Return the daily scan list for the active universe profile."""
    active = (profile or get_universe_profile()).strip().lower()
    if active == "paper":
        return normalize_tickers(config_tickers)
    if active == "smoke":
        return load_smoke_tickers()
    if active == "research":
        return load_master_tickers()
    raise ValueError(f"Unknown universe profile: {active}")
