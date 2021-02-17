from http import HTTPStatus
from unittest.mock import sentinel

import pytest
from checkmatelib.exceptions import CheckmateException

from viahtml.views.blocklist import BlocklistView


class TestBlocklistView:
    def test_construction(self, CheckmateClient):
        view = BlocklistView(sentinel.checkmate_host, sentinel.checkmate_api_key)

        CheckmateClient.assert_called_once_with(
            sentinel.checkmate_host, sentinel.checkmate_api_key
        )
        assert view.checkmate == CheckmateClient.return_value

    def test_if_there_is_no_url_it_does_nothing(self, view, context):
        context.proxied_url = ""
        result = view(context)

        assert result is None
        view.checkmate.check_url.assert_not_called()

    def test_if_the_url_is_not_blocked_it_does_nothing(self, view, context):
        view.checkmate.check_url.return_value = None

        result = view(context)

        assert result is None
        view.checkmate.check_url.assert_called_once_with(
            context.proxied_url, allow_all=True
        )

    def test_if_a_call_to_checkmate_fails_it_does_nothing(self, view, context):
        view.checkmate.check_url.side_effect = CheckmateException

        result = view(context)

        assert result is None

    def test_blocking(self, view, context):
        blocked_response = view.checkmate.check_url.return_value
        blocked_response.reason_codes = ["some_reason"]

        result = view(context)

        context.make_response.assert_called_once_with(
            HTTPStatus.TEMPORARY_REDIRECT,
            headers={"Location": blocked_response.presentation_url},
        )

        assert result == context.make_response.return_value

    @pytest.fixture
    def view(self):
        return BlocklistView(sentinel.checkmate_host, sentinel.checkmate_api_key)


@pytest.fixture(autouse=True)
def CheckmateClient(patch):
    return patch("viahtml.views.blocklist.CheckmateClient")
