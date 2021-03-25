from unittest.mock import create_autospec

import pytest
from checkmatelib import CheckmateClient, CheckmateException
from h_matchers import Any

from viahtml.views.status import StatusView


class TestStatusView:
    @pytest.mark.parametrize(
        "path,responds",
        (
            ("/_status", True),
            ("/_status/", True),
            ("/http://example.com", False),
        ),
    )
    def test_it_responds_to_the_status_url(self, path, responds, context, view):
        context.path = path
        view(context)

        if responds:
            context.make_json_response.assert_called_once()
        else:
            context.make_json_response.assert_not_called()

    def test_it_returns_the_expected_response(self, context, view):
        response = view(context)

        context.make_json_response.assert_called_once_with(
            {"status": "okay"},
            headers={"Cache-Control": "max-age=0, must-revalidate, no-cache, no-store"},
        )
        assert response == context.make_json_response.return_value

    def test_if_calling_checkmate_fails_it_reports_a_failure(
        self, checkmate, context, view
    ):
        checkmate.check_url.side_effect = CheckmateException

        response = view(context)

        context.make_json_response.assert_called_once_with(
            {"status": "checkmate_failure"}, headers=Any.dict()
        )
        assert response == context.make_json_response.return_value

    @pytest.fixture
    def checkmate(self):
        return create_autospec(CheckmateClient, instance=True, spec_set=True)

    @pytest.fixture
    def context(self, context):
        context.path = "/_status"
        return context

    @pytest.fixture
    def view(self, checkmate):
        return StatusView(checkmate)
