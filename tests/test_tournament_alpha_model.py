import unittest

from src.rank_ai_gate import RankAIGateScore
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

    def test_uses_percentile_from_rank_ai_gate_score(self) -> None:
        rank_scores = {
            "RBLX": RankAIGateScore(
                ticker="RBLX",
                score=0.55,
                percentile=0.99,
                allowed=True,
                reason="passed",
            ),
            "AMD": RankAIGateScore(
                ticker="AMD",
                score=0.60,
                percentile=0.70,
                allowed=False,
                reason="blocked",
            ),
        }
        picks = select_tournament_candidates(
            ["RBLX", "AMD"],
            rank_scores=rank_scores,
            max_picks=2,
        )
        self.assertEqual(list(picks.keys()), ["RBLX"])


if __name__ == "__main__":
    unittest.main()
