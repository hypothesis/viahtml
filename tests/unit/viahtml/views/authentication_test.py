from http import HTTPStatus

import pytest
from h_matchers import Any

from viahtml.views.authentication import AuthenticationView


class TestAuthenticationView:
    @pytest.mark.parametrize(
        "header,value",
        (
            # Request from ourselves - always allowed.
            ("Referer", "http://via/some/path"),
            ("Sec-Fetch-Site", "same-origin"),
            # Request from a different, but allowed, origin.
            ("Referer", "http://allowed-origin/another/path"),
        ),
    )
    def test_it_allows_through_if_allowed_referrer(
        self, view, context, headers, header, value
    ):  # pylint: disable=too-many-arguments
        headers[header] = value

        result = view(context)

        assert result is None

    @pytest.mark.parametrize(
        "header,value",
        (
            ("Referer", "http://NOT_VIA/some/path"),
            # This is us, but it's a URL designed to crash URL parsing
            ("Referer", "http://via]"),
            ("Sec-Fetch-Site", "none"),
            ("Sec-Fetch-Site", "same-site"),
            ("Sec-Fetch-Site", "cross-origin"),
        ),
    )
    def test_it_blocks_if_not_self_referred(
        self, view, context, headers, header, value
    ):  # pylint: disable=too-many-arguments
        headers[header] = value

        result = view(context)

        self.assert_is_unauthorized_response(result, context)

    def test_is_allows_anything_if_authentication_is_disabled(self, context):
        view = AuthenticationView(required=False)

        result = view(context)

        assert result is None

    def assert_is_unauthorized_response(self, result, context):
        assert result is context.make_response.return_value
        context.make_response.assert_called_once_with(
            HTTPStatus.UNAUTHORIZED,
            lines=[Any.string.containing("401")],
            headers={"Content-Type": "text/html; charset=utf-8"},
        )

    @pytest.fixture
    def headers(self):
        return {"Referer": None}

    @pytest.fixture(autouse=True)
    def context(self, context, headers):
        context.host = "via"
        context.get_header.side_effect = headers.get
        return context

    @pytest.fixture
    def view(self):
        return AuthenticationView(required=True, allowed_referrers=["allowed-origin"])
