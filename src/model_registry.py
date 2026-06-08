"""Strategy-sleeve model registry — separate from champion promotion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ModelRegistration:
    model_id: str
    model_type: str
    trained_at: str
    feature_set: str
    allowed_sleeves: tuple[str, ...]
    allowed_environments: tuple[str, ...]
    promotion_status: str
    paper_only: bool


DEFAULT_MODELS: tuple[ModelRegistration, ...] = (
    ModelRegistration(
        model_id="core_ai_score_model",
        model_type="ai_score",
        trained_at="",
        feature_set="champion_features_v1",
        allowed_sleeves=("core",),
        allowed_environments=("paper", "live", "research"),
        promotion_status="champion",
        paper_only=False,
    ),
    ModelRegistration(
        model_id="rank_ai_gate_model",
        model_type="rank_cross_section",
        trained_at="",
        feature_set="rank_label_h20_top15",
        allowed_sleeves=("core", "tournament"),
        allowed_environments=("paper", "research"),
        promotion_status="paper_experiment",
        paper_only=True,
    ),
    ModelRegistration(
        model_id="tournament_alpha_model",
        model_type="alpha_tournament",
        trained_at="",
        feature_set="rank_ai_overlay_v1",
        allowed_sleeves=("tournament",),
        allowed_environments=("paper", "research"),
        promotion_status="experimental",
        paper_only=True,
    ),
    ModelRegistration(
        model_id="crypto_or_competition_model",
        model_type="competition_adapter",
        trained_at="",
        feature_set="external_competition_stub",
        allowed_sleeves=("tournament",),
        allowed_environments=("research",),
        promotion_status="blocked",
        paper_only=True,
    ),
)


def list_models() -> list[ModelRegistration]:
    return list(DEFAULT_MODELS)


def get_model(model_id: str) -> ModelRegistration:
    normalized = str(model_id).strip().lower()
    for model in DEFAULT_MODELS:
        if model.model_id == normalized:
            return model
    raise KeyError(f"unknown model_id: {model_id}")


def models_for_sleeve(sleeve_id: str) -> list[ModelRegistration]:
    target = str(sleeve_id).strip().lower()
    return [model for model in DEFAULT_MODELS if target in model.allowed_sleeves]


def assert_model_environment_allowed(model_id: str, environment: str) -> None:
    model = get_model(model_id)
    env = str(environment).strip().lower()
    if env not in model.allowed_environments:
        raise RuntimeError(
            f"model {model_id} is not allowed in environment {environment!r}"
        )
    if env == "live" and model.paper_only:
        raise RuntimeError(f"model {model_id} is paper_only and cannot run live")


def assert_sleeve_model_allowed(model_id: str, sleeve_id: str) -> None:
    model = get_model(model_id)
    target = str(sleeve_id).strip().lower()
    if target not in model.allowed_sleeves:
        raise RuntimeError(
            f"model {model_id} is not registered for sleeve {sleeve_id!r}"
        )


def promotion_statuses() -> dict[str, str]:
    return {model.model_id: model.promotion_status for model in DEFAULT_MODELS}


def filter_models(
    *,
    sleeve_id: str | None = None,
    environment: str | None = None,
) -> Iterable[ModelRegistration]:
    for model in DEFAULT_MODELS:
        if sleeve_id is not None and str(sleeve_id).lower() not in model.allowed_sleeves:
            continue
        if environment is not None and str(environment).lower() not in model.allowed_environments:
            continue
        yield model
