"""Order intent records — shared decision path for dry-run and live."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class OrderIntent:
    intent_id: str
    run_id: str
    ticker: str
    side: str
    notional: Optional[float] = None
    qty: Optional[float] = None
    signal: str = ""
    ai_score: Optional[float] = None
    rank_ai_score: Optional[float] = None
    rank_ai_percentile: Optional[float] = None
    llm_verdict: str = ""
    risk_reason: str = ""
    client_order_id: str = ""
    sleeve_id: str = "core"
    sleeve_strategy: str = ""
    sleeve_target_weight: Optional[float] = None
    sleeve_budget_before: Optional[float] = None
    sleeve_budget_after: Optional[float] = None
    sleeve_risk_mode: str = ""


@dataclass
class ExecutionResult:
    intent_id: str
    broker_order_id: str
    status: str
    side: str
    order_type: str
    filled_qty: Optional[float] = None
    filled_avg_price: Optional[float] = None
    error: str = ""


def new_intent_id() -> str:
    return f"intent_{uuid.uuid4().hex[:12]}"


def build_buy_intent(
    *,
    run_id: str,
    ticker: str,
    notional: float,
    signal: str = "",
    ai_score: Optional[float] = None,
    rank_ai_score: Optional[float] = None,
    rank_ai_percentile: Optional[float] = None,
    llm_verdict: str = "",
    risk_reason: str = "",
    client_order_id: str = "",
    sleeve_id: str = "core",
    sleeve_strategy: str = "",
    sleeve_target_weight: Optional[float] = None,
    sleeve_budget_before: Optional[float] = None,
    sleeve_budget_after: Optional[float] = None,
    sleeve_risk_mode: str = "",
) -> OrderIntent:
    return OrderIntent(
        intent_id=new_intent_id(),
        run_id=run_id,
        ticker=str(ticker).upper(),
        side="BUY",
        notional=round(float(notional), 2),
        signal=signal,
        ai_score=ai_score,
        rank_ai_score=rank_ai_score,
        rank_ai_percentile=rank_ai_percentile,
        llm_verdict=llm_verdict,
        risk_reason=risk_reason,
        client_order_id=client_order_id or f"buy_{run_id}_{ticker}",
        sleeve_id=str(sleeve_id or "core").lower(),
        sleeve_strategy=sleeve_strategy,
        sleeve_target_weight=sleeve_target_weight,
        sleeve_budget_before=sleeve_budget_before,
        sleeve_budget_after=sleeve_budget_after,
        sleeve_risk_mode=sleeve_risk_mode,
    )


def config_hash(settings: Any) -> str:
    payload = {
        "broker_provider": getattr(settings, "broker_provider", ""),
        "rank_ai_buy_gate_enabled": getattr(settings, "rank_ai_buy_gate_enabled", False),
        "llm_advisory_only": getattr(settings, "llm_advisory_only", True),
        "use_ai_score": getattr(settings, "use_ai_score", False),
        "ai_score_buy_threshold": getattr(settings, "ai_score_buy_threshold", None),
        "live_safety_enabled": getattr(settings, "live_safety_enabled", False),
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return digest[:16]


def model_version_label(ai_model_bundle: Any | None) -> str:
    if ai_model_bundle is None:
        return ""
    meta = getattr(ai_model_bundle, "metadata", None) or {}
    if isinstance(meta, dict):
        return str(meta.get("trained_at") or meta.get("version") or "")[:64]
    path = Path("models/ai_score_model_metadata.json")
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return str(data.get("trained_at") or data.get("version") or "")[:64]
        except (OSError, json.JSONDecodeError):
            return ""
    return ""


def rank_model_version_label(settings: Any) -> str:
    if not getattr(settings, "rank_ai_buy_gate_enabled", False):
        return ""
    return str(getattr(settings, "rank_ai_buy_gate_model_path", ""))[-80:]


@dataclass
class AuditContext:
    run_id: str
    broker: str
    environment: str
    config_hash: str
    model_version: str
    rank_model_version: str
    decision_id: str = field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:10]}")

    def as_audit_fields(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "broker": self.broker,
            "environment": self.environment,
            "config_hash": self.config_hash,
            "model_version": self.model_version,
            "rank_model_version": self.rank_model_version,
            "decision_id": self.decision_id,
        }


def build_audit_context(
    *,
    run_id: str,
    settings: Any,
    environment: str,
    ai_model_bundle: Any | None = None,
) -> AuditContext:
    return AuditContext(
        run_id=run_id,
        broker=str(getattr(settings, "broker_provider", "alpaca")),
        environment=environment,
        config_hash=config_hash(settings),
        model_version=model_version_label(ai_model_bundle),
        rank_model_version=rank_model_version_label(settings),
    )


def sleeve_audit_fields(
    *,
    sleeve_id: str = "core",
    sleeve_strategy: str = "",
    sleeve_target_weight: Optional[float] = None,
    sleeve_budget_before: Optional[float] = None,
    sleeve_budget_after: Optional[float] = None,
    sleeve_risk_mode: str = "",
    intent: Optional[OrderIntent] = None,
) -> dict[str, Any]:
    if intent is not None:
        return {
            "sleeve_id": intent.sleeve_id,
            "sleeve_strategy": intent.sleeve_strategy,
            "sleeve_target_weight": intent.sleeve_target_weight,
            "sleeve_budget_before": intent.sleeve_budget_before,
            "sleeve_budget_after": intent.sleeve_budget_after,
            "sleeve_risk_mode": intent.sleeve_risk_mode,
        }
    return {
        "sleeve_id": str(sleeve_id or "core").lower(),
        "sleeve_strategy": sleeve_strategy,
        "sleeve_target_weight": sleeve_target_weight,
        "sleeve_budget_before": sleeve_budget_before,
        "sleeve_budget_after": sleeve_budget_after,
        "sleeve_risk_mode": sleeve_risk_mode,
    }
