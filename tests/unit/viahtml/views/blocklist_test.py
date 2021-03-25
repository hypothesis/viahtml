from http import HTTPStatus
from unittest.mock import create_autospec, sentinel

import pytest
from checkmatelib import CheckmateClient, CheckmateException

from viahtml.views.blocklist import BlocklistView


class TestBlocklistView:
    def test_if_there_is_no_url_it_does_nothing(self, view, context, checkmate):
        context.proxied_url = ""
        result = view(context)

        assert result is None
        checkmate.check_url.assert_not_called()

    def test_if_the_url_is_not_blocked_it_does_nothing(self, view, context, checkmate):
        checkmate.check_url.return_value = None
        context.query_params.get.return_value = sentinel.blocked_for

        result = view(context)

        assert result is None
        checkmate.check_url.assert_called_once_with(
            context.proxied_url,
            allow_all=True,
            blocked_for=sentinel.blocked_for,
            ignore_reasons=None,
        )

    def test_if_a_call_to_checkmate_fails_it_does_nothing(
        self, view, context, checkmate
    ):
        checkmate.check_url.side_effect = CheckmateException

        result = view(context)

        assert result is None

    def test_blocking(self, view, context, checkmate):
        blocked_response = checkmate.check_url.return_value
        blocked_response.reason_codes = ["some_reason"]

        result = view(context)

        context.make_response.assert_called_once_with(
            HTTPStatus.TEMPORARY_REDIRECT,
            headers={"Location": blocked_response.presentation_url},
        )

        assert result == context.make_response.return_value

    @pytest.fixture
    def view(self, checkmate):
        return BlocklistView(checkmate)

    @pytest.fixture
    def checkmate(self):
        return create_autospec(CheckmateClient, instance=True, spec_set=True)
