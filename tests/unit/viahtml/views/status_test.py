from unittest.mock import create_autospec

import pytest
from checkmatelib import CheckmateClient, CheckmateException

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

        result = view(context)

        if responds:
            context.make_json_response.assert_called_once()
            assert result is not None
        else:
            context.make_json_response.assert_not_called()
            assert result is None

    @pytest.mark.parametrize(
        "checkmate_fails,checkmate_param,expected_body,expected_http_status",
        [
            # With no `checkmate` query param it doesn't check Checkmate.
            (False, False, {"status": "okay"}, 200),
            # With no `checkmate` query param the status endpoint still
            # succeeds even if Checkmate is failing.
            (True, False, {"status": "okay"}, 200),
            # If the `checkmate` query param is given then it checks Checkmate.
            (False, True, {"status": "okay", "okay": ["checkmate"]}, 200),
            # With the `checkmate` query param if Checkmate fails then the
            # status endpoint fails.
            (True, True, {"status": "down", "down": ["checkmate"]}, 500),
        ],
    )
    def test_it(
        self,
        context,
        view,
        checkmate,
        checkmate_fails,
        checkmate_param,
        expected_body,
        expected_http_status,
    ):  # pylint:disable=too-many-arguments
        if checkmate_fails:
            checkmate.check_url.side_effect = CheckmateException

        if checkmate_param:
            context.query_params = {"include-checkmate": [""]}

        response = view(context)

        if checkmate_param:
            checkmate.check_url.assert_called_once_with("https://example.com/")
        else:
            checkmate.check_url.assert_not_called()
        context.make_json_response.assert_called_once_with(
            expected_body,
            http_status=expected_http_status,
            headers={"Cache-Control": "max-age=0, must-revalidate, no-cache, no-store"},
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
