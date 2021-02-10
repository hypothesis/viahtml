from http import HTTPStatus

import pytest
from h_matchers import Any
from h_vialib.exceptions import InvalidToken, MissingToken

from viahtml.views.authentication import AuthenticationView


class TestAuthenticationView:
    @pytest.mark.parametrize("http_mode", (True, False))
    def test_it_configures_security(
        self, TokenBasedCookie, ViaSecureURL, RandomSecureNonce, http_mode
    ):
        # This is mostly here to say that things are hooked up as we expect
        # and so we don't have to repeat ourselves in the tests. Bit of an MD5
        # type test

        AuthenticationView(secret="not_a_secret", required=True, http_mode=http_mode)

        ViaSecureURL.assert_called_once_with("not_a_secret")
        TokenBasedCookie.assert_called_once_with(
            AuthenticationView.COOKIE_NAME,
            token_provider=RandomSecureNonce.return_value,
            secure=not http_mode,
        )
        RandomSecureNonce.assert_called_once_with("not_a_secret")

    def test_it_reads_a_signed_path_with_no_cookie(
        self, view, context, TokenBasedCookie, ViaSecureURL
    ):
        TokenBasedCookie.return_value.verify.side_effect = MissingToken
        context.url = "http://via/proxy/http://example.com?via.sec=A_GOOD_TOKEN"

        result = view(context)

        assert result is None
        ViaSecureURL.return_value.verify.assert_called_once_with(context.url)
        secure_cookie = TokenBasedCookie.return_value
        secure_cookie.create.assert_called_once_with(
            max_age=AuthenticationView.COOKIE_MAX_AGE
        )
        context.add_header.assert_called_once_with(*secure_cookie.create.return_value)

    def test_it_blocks_if_the_path_is_signed_badly(
        self, view, context, ViaSecureURL, TokenBasedCookie
    ):
        context.url = "http://via/proxy/http://example.com?via.sec=A_BAD_TOKEN"
        TokenBasedCookie.return_value.verify.side_effect = MissingToken
        ViaSecureURL.return_value.verify.side_effect = InvalidToken("bad")

        result = view(context)

        self.assert_is_unauthorized_response(result, context)

    def test_it_allows_through_a_request_with_cookie(
        self, view, context, TokenBasedCookie
    ):
        context.url = "http://via/proxy/http://example.com"
        context.get_header.return_value = "A_GOOD_COOKIE"

        result = view(context)

        assert result is None

        context.get_header.assert_called_once_with("Cookie")
        TokenBasedCookie.return_value.verify.assert_called_once_with(
            context.get_header.return_value
        )

    def test_it_blocks_if_the_cookie_is_bad(self, view, context, TokenBasedCookie):
        context.url = "http://via/proxy/http://example.com"
        context.get_header.return_value = "A_BAD_COOKIE"
        TokenBasedCookie.return_value.verify.side_effect = InvalidToken("bad")

        result = view(context)

        self.assert_is_unauthorized_response(result, context)

    def test_it_allows_missing_tokens_if_required_is_False(
        self, context, ViaSecureURL, TokenBasedCookie
    ):
        context.url = "http://via/proxy/http://example.com"
        context.get_header.return_value = None
        ViaSecureURL.return_value.verify.side_effect = MissingToken("gone")
        TokenBasedCookie.return_value.verify.side_effect = MissingToken("gone")

        result = AuthenticationView(secret="not_a_secret", required=False)(context)

        assert result is None

    def assert_is_unauthorized_response(self, result, context):
        assert result is context.make_response.return_value
        context.make_response.assert_called_once_with(
            HTTPStatus.UNAUTHORIZED, lines=[Any.string.containing("401")]
        )

    @pytest.fixture
    def view(self):
        return AuthenticationView(secret="not_a_secret", required=True)

    @pytest.fixture(autouse=True)
    def TokenBasedCookie(self, patch):
        TokenBasedCookie = patch("viahtml.views.authentication.TokenBasedCookie")
        TokenBasedCookie.return_value.create.return_value = (
            "Set-Cookie",
            "some cookie value",
        )

        return TokenBasedCookie

    @pytest.fixture(autouse=True)
    def ViaSecureURL(self, patch):
        return patch("viahtml.views.authentication.ViaSecureURL")

    @pytest.fixture(autouse=True)
    def RandomSecureNonce(self, patch):
        return patch("viahtml.views.authentication.RandomSecureNonce")
