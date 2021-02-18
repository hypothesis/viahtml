"""Token based security measures."""
from datetime import timedelta
from http import HTTPStatus

from h_vialib.exceptions import MissingToken, TokenException
from h_vialib.secure import RandomSecureNonce, TokenBasedCookie, ViaSecureURL


class AuthenticationView:
    """A view for checking that this request came from a Hypothesis service.

    This will respond to tokens set in `via.sec` using `ViaSecureURLToken` or
    to a cookie that this class emits.

    When calling the view, if everything goes well, nothing will happen and the
    request can continue to the next stage. The class may add headers to the
    context, which should be honored for this to work.
    """

    COOKIE_NAME = "via.sec"
    """The cookie name to store our random, but verifiable token."""

    COOKIE_MAX_AGE = timedelta(minutes=5)
    """The max age we should issue that token for.

    We ensure the token time is the same or longer than our local NGINX caching
    so that if NGINX re-issues the token it will still be valid during that
    time.
    """

    def __init__(self, secret, required=True, enable_cookie=True, http_mode=False):
        """Initialize the view.

        :param secret: Secret used for signing and checking signatures
        :param required: Require auth
        :param enable_cookie: Enable cookie based persistence of auth
        :param http_mode: Expect the service to run on HTTP rather than HTTPS
        """
        self._secure_cookie = TokenBasedCookie(
            self.COOKIE_NAME,
            token_provider=RandomSecureNonce(secret),
            secure=not http_mode,
        )
        self._secure_url = ViaSecureURL(secret)
        self._required = required
        self._enable_cookie = enable_cookie

    def __call__(self, context):
        """Provide a block page response if required.

        :param context: Context object relating to this call
        :return: An iterator of content if required or None
        """

        if not self._required:
            return None

        try:
            self._verify_tokens(context)

        except TokenException as err:
            return context.make_response(
                HTTPStatus.UNAUTHORIZED,
                lines=[f"<h1>401 Unauthorized</h1><p>{err}</p>"],
            )

        # We might have added a header, but we don't want to handle the request
        return None

    def _verify_tokens(self, context):
        # Look for cookies first
        try:
            return self._secure_cookie.verify(context.get_header("Cookie"))
        except MissingToken:
            pass

        # Looks like there's no cookie, so try the path
        self._secure_url.verify(context.url)

        if not self._enable_cookie:
            return None

        # Looks like we do have a signed URL, so add a cookie for future
        # surfing
        cookie_header, cookie_value = self._secure_cookie.create(
            max_age=self.COOKIE_MAX_AGE
        )

        return context.add_header(cookie_header, cookie_value)
