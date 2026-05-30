"""Champion file must not update when promotion is rejected ([AGY])."""

from pathlib import Path

from src.model_promotion import apply_champion_promotion_if_needed, should_update_champion


def test_should_update_champion_only_on_promote():
    assert should_update_champion("PROMOTE")
    assert not should_update_champion("RETAIN_CHAMPION")


def test_degraded_challenger_does_not_overwrite_champion_file(tmp_path):
    champion = tmp_path / "champion.joblib"
    champion.write_bytes(b"champion-v1")

    def promote():
        champion.write_bytes(b"challenger-would-win")

    result = apply_champion_promotion_if_needed("RETAIN_CHAMPION", promote)
    assert result["champion_updated"] is False
    assert champion.read_bytes() == b"champion-v1"


def test_promote_updates_champion_file(tmp_path):
    champion = tmp_path / "champion.joblib"
    champion.write_bytes(b"champion-v1")

    apply_champion_promotion_if_needed("PROMOTE", lambda: champion.write_bytes(b"champion-v2"))
    assert champion.read_bytes() == b"champion-v2"
