import pytest
from requests.exceptions import ConnectionError as ConnectionError_
from requests.exceptions import HTTPError, InvalidURL, Timeout

from viahtml.checkmate import CheckmateClient
from viahtml.checkmate.exceptions import CheckmateException


class TestCheckmateClient:
    def test_it_with_an_unblocked_response(self, client, response):
        response.status_code = 204

        hits = client.check_url("http://good.example.com")

        assert not hits
        response.json.assert_not_called()

    def test_it_with_a_blocked_response(
        self, client, requests, response, BlockResponse
    ):
        hits = client.check_url("http://bad.example.com")

        requests.get.assert_called_once_with(
            "http://checkmate.example.com/api/check",
            params={"url": "http://bad.example.com"},
            timeout=1,
        )

        assert hits == BlockResponse.return_value
        BlockResponse.assert_called_once_with(response.json.return_value)

    @pytest.mark.parametrize(
        "exception,expected",
        (
            (ConnectionError_, CheckmateException),
            (Timeout, CheckmateException),
            (InvalidURL, InvalidURL),
        ),
    )
    def test_failed_connection(self, client, requests, exception, expected):
        requests.get.side_effect = exception
        with pytest.raises(expected):
            client.check_url("http://bad.example.com")

    def test_failed_response(self, client, response):
        response.raise_for_status.side_effect = HTTPError

        with pytest.raises(CheckmateException):
            client.check_url("http://bad.example.com")

    def test_it_with_a_bad_json_payload(self, client, response):
        response.json.side_effect = ValueError

        with pytest.raises(CheckmateException):
            client.check_url("http://bad.example.com")

    @pytest.fixture
    def client(self):
        return CheckmateClient(host="http://checkmate.example.com/")

    @pytest.fixture
    def response(self, requests):
        response = requests.get.return_value
        response.status_code = 200

        return response


@pytest.fixture(autouse=True)
def BlockResponse(patch):
    return patch("viahtml.checkmate.client.BlockResponse")


@pytest.fixture(autouse=True)
def requests(patch):
    requests = patch("viahtml.checkmate.client.requests")

    return requests
