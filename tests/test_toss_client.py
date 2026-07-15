import unittest
from unittest.mock import MagicMock, patch

from src.brokers import toss_client


class TossClientTest(unittest.TestCase):
    def setUp(self) -> None:
        toss_client.reset_token_cache()

    def tearDown(self) -> None:
        toss_client.reset_token_cache()

    def test_as_list_variants(self) -> None:
        self.assertEqual(toss_client._as_list([{"a": 1}]), [{"a": 1}])
        self.assertEqual(toss_client._as_list({"orders": [{"a": 1}]}, "orders"), [{"a": 1}])
        self.assertEqual(toss_client._as_list({"nope": []}, "orders"), [])
        self.assertEqual(toss_client._as_list(None), [])

    def test_as_list_envelope_and_nested(self) -> None:
        # accounts: result is a bare list
        self.assertEqual(
            toss_client._as_list({"result": [{"accountSeq": 1}]}),
            [{"accountSeq": 1}],
        )
        # holdings: list nested under result.items with sibling summary keys
        payload = {
            "result": {
                "totalPurchaseAmount": {"amount": "1"},
                "items": [{"symbol": "PALU"}, {"symbol": "OPEX"}],
            }
        }
        self.assertEqual(
            [h["symbol"] for h in toss_client._as_list(payload, "holdings")],
            ["PALU", "OPEX"],
        )

    @patch.dict("os.environ", {"TOSS_CLIENT_ID": "cid", "TOSS_SECRET_KEY": "sec"}, clear=False)
    def test_credentials_available(self) -> None:
        self.assertTrue(toss_client.credentials_available())

    @patch.dict("os.environ", {"TOSS_CLIENT_ID": "", "TOSS_SECRET_KEY": ""}, clear=False)
    def test_token_requires_credentials(self) -> None:
        with self.assertRaises(toss_client.TossAPIError):
            toss_client._get_token()

    @patch.dict(
        "os.environ",
        {"TOSS_CLIENT_ID": "cid", "TOSS_SECRET_KEY": "sec", "TOSS_ACCOUNT": "7"},
        clear=False,
    )
    def test_resolve_account_seq_prefers_env(self) -> None:
        self.assertEqual(toss_client.resolve_account_seq(), "7")

    @patch("src.brokers.toss_client.requests.post")
    @patch.dict("os.environ", {"TOSS_CLIENT_ID": "cid", "TOSS_SECRET_KEY": "sec"}, clear=False)
    def test_token_cached(self, mock_post) -> None:
        resp = MagicMock(status_code=200, content=b"{}")
        resp.json.return_value = {"access_token": "abc", "expires_in": 3600}
        mock_post.return_value = resp
        self.assertEqual(toss_client._get_token(), "abc")
        self.assertEqual(toss_client._get_token(), "abc")
        mock_post.assert_called_once()

    @patch("src.brokers.toss_client.requests.request")
    @patch("src.brokers.toss_client._get_token", return_value="tok")
    def test_error_envelope_raises(self, _mock_token, mock_request) -> None:
        resp = MagicMock(status_code=404, content=b"{}")
        resp.json.return_value = {"error": {"code": "stock-not-found", "message": "no"}}
        mock_request.return_value = resp
        with self.assertRaises(toss_client.TossAPIError) as ctx:
            toss_client.get_prices(["AAPL"])
        self.assertEqual(ctx.exception.code, "stock-not-found")

    @patch("src.brokers.toss_client._request")
    def test_get_stocks_normalizes_symbols(self, mock_request) -> None:
        mock_request.return_value = {
            "result": [{"symbol": "LNOK", "leverageFactor": "2"}]
        }

        rows = toss_client.get_stocks(["nok", "LNOK", "nok"])

        mock_request.assert_called_once_with(
            "GET",
            "/api/v1/stocks",
            params={"symbols": "NOK,LNOK"},
        )
        self.assertEqual(rows[0]["symbol"], "LNOK")


if __name__ == "__main__":
    unittest.main()
