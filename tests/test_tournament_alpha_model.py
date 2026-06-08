import unittest

from src.tournament_alpha_model import score_tournament_candidate, select_tournament_candidates


class TournamentAlphaModelTest(unittest.TestCase):
    def test_selects_high_rank_candidates(self) -> None:
        rank_scores = {
            "NVDA": {"score": 0.95},
            "AMD": {"score": 0.70},
            "MSFT": {"score": 0.92},
        }
        picks = select_tournament_candidates(
            ["NVDA", "AMD", "MSFT"],
            rank_scores=rank_scores,
            max_picks=2,
        )
        self.assertIn("NVDA", picks)
        self.assertLessEqual(len(picks), 2)

    def test_rejects_low_rank_candidate(self) -> None:
        signal = score_tournament_candidate(
            "AAA",
            rank_scores={"AAA": {"score": 0.40}},
        )
        self.assertIsNone(signal)


if __name__ == "__main__":
    unittest.main()
