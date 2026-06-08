import unittest

from src.model_registry import (
    assert_model_environment_allowed,
    get_model,
    models_for_sleeve,
)


class ModelRegistryTest(unittest.TestCase):
    def test_tournament_model_is_paper_only(self) -> None:
        model = get_model("tournament_alpha_model")
        self.assertTrue(model.paper_only)
        self.assertIn("tournament", model.allowed_sleeves)

    def test_models_for_core_sleeve(self) -> None:
        models = models_for_sleeve("core")
        self.assertTrue(any(m.model_id == "core_ai_score_model" for m in models))

    def test_live_blocks_tournament_model(self) -> None:
        with self.assertRaises(RuntimeError):
            assert_model_environment_allowed("tournament_alpha_model", "live")


if __name__ == "__main__":
    unittest.main()
