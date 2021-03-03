from http import HTTPStatus

import pytest
from h_matchers import Any
from h_vialib.exceptions import InvalidToken, MissingToken

from viahtml.views.authentication import AuthenticationView


class TestAuthenticationView:
    def test_it_configures_security(self, ViaSecureURL):
        # This is mostly here to say that things are hooked up as we expect
        # and so we don't have to repeat ourselves in the tests. Bit of an MD5
        # type test

        AuthenticationView(secret="not_a_secret", required=True)

        ViaSecureURL.assert_called_once_with("not_a_secret")

    def test_it_allows_through_a_signed_path(self, view, context, ViaSecureURL):
        context.url = "http://via/proxy/http://example.com?via.sec=A_GOOD_TOKEN"
        ViaSecureURL.return_value.verify.side_effect = None

        result = view(context)

        assert result is None
        ViaSecureURL.return_value.verify.assert_called_once_with(context.url)

    def test_it_blocks_if_the_path_is_signed_badly(self, view, context, ViaSecureURL):
        context.url = "http://via/proxy/http://example.com?via.sec=A_BAD_TOKEN"
        ViaSecureURL.return_value.verify.side_effect = InvalidToken("bad")

        result = view(context)

        self.assert_is_unauthorized_response(result, context)

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

    def test_it_allows_missing_tokens_if_required_is_False(self, context, ViaSecureURL):
        context.url = "http://via/proxy/http://example.com"

        result = AuthenticationView(secret="not_a_secret", required=False)(context)

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
        return AuthenticationView(
            secret="not_a_secret", required=True, allowed_referrers=["allowed-origin"]
        )

    @pytest.fixture(autouse=True)
    def ViaSecureURL(self, patch):
        ViaSecureURL = patch("viahtml.views.authentication.ViaSecureURL")

        ViaSecureURL.return_value.verify.side_effect = MissingToken
        return ViaSecureURL
