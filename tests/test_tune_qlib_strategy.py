import unittest

from src.tune_qlib_strategy import parse_float_list, parse_int_list


class TuneQlibStrategyTest(unittest.TestCase):
    def test_parse_float_list(self) -> None:
        self.assertEqual(parse_float_list("1.0, 2.5,3"), [1.0, 2.5, 3.0])

    def test_parse_int_list(self) -> None:
        self.assertEqual(parse_int_list("1, 2,3"), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
