from unittest.mock import create_autospec, sentinel

import pytest
from checkmatelib.exceptions import CheckmateException
from h_matchers import Any

from viahtml.views.blocklist import BlocklistView


class TestBlocklistView:
    def test_construction(self, CheckmateClient):
        view = BlocklistView(sentinel.checkmate_host)

        CheckmateClient.assert_called_once_with(sentinel.checkmate_host)
        assert view.checkmate == CheckmateClient.return_value

    @pytest.mark.parametrize(
        "path,expected",
        (
            ("/proxy/http://example.com", "http://example.com"),
            ("/static/something.jpg", None),
        ),
    )
    def test_it_extracts_the_url_correctly(self, path, expected):
        proxied_url = BlocklistView.get_proxied_url(path)
        assert proxied_url == expected

    def test_if_there_is_no_url_it_does_nothing(self, view, start_response):
        result = view("", {}, start_response)

        assert result is None
        view.checkmate.check_url.assert_not_called()

    def test_if_the_url_is_not_blocked_it_does_nothing(self, view, start_response):
        view.checkmate.check_url.return_value = None

        result = view("/proxy/http://example.com", {}, start_response)

        assert result is None
        view.checkmate.check_url.assert_called_once_with(
            "http://example.com", allow_all=True
        )

    def test_if_a_call_to_checkmate_fails_it_does_nothing(self, view, start_response):
        view.checkmate.check_url.side_effect = CheckmateException

        result = view("/proxy/http://example.com", {}, start_response)

        assert result is None

    @pytest.mark.parametrize(
        "block_reason,expected_heading",
        (
            ("malicious", "Deceptive site ahead"),
            ("publisher-blocked", "Content not available"),
            ("anything-else-at-all", "Content cannot be annotated"),
        ),
    )
    def test_blocking(self, view, block_reason, start_response, expected_heading):
        view.checkmate.check_url.return_value.reason_codes = [block_reason]

        result = view("/proxy/http://example.com", {}, start_response)

        start_response.assert_called_once_with(
            "403 Forbidden", [("Content-Type", "text/html; charset=utf-8")]
        )

        assert result == Any.list.of_size(1)
        assert expected_heading in result[0].decode("utf-8")

    @pytest.fixture
    def start_response(self):
        def start_response(message, headers):  # pragma: no cover
            ...

        return create_autospec(start_response, spec_set=True)

    @pytest.fixture
    def view(self):
        return BlocklistView(sentinel.checkmate_host)


@pytest.fixture(autouse=True)
def CheckmateClient(patch):
    return patch("viahtml.views.blocklist.CheckmateClient")
