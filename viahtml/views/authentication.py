"""Token based security measures."""
from datetime import timedelta
from http import HTTPStatus
from urllib.parse import urlparse

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
            self._check_for_authorization(context)

        except TokenException as err:
            return context.make_response(
                HTTPStatus.UNAUTHORIZED,
                lines=[self._error_template(err)],
                headers={"Content-Type": "text/html; charset=utf-8"},
            )

        # We might have added a header, but we don't want to handle the request
        return None

    def _check_for_authorization(self, context):
        if self._has_valid_browsing_cookie(context):
            return

        if self._is_referred_by_us(context) or self._has_signed_url(context):
            if not self._enable_cookie:
                return

            # Set a browsing cookie in this case
            cookie_header, cookie_value = self._secure_cookie.create(
                max_age=self.COOKIE_MAX_AGE
            )

            context.add_header(cookie_header, cookie_value)

    @classmethod
    def _is_referred_by_us(cls, context):
        """Check if the referrer is ourselves."""

        # This header is set by some browsers like Chrome to let you know
        # general information about where the request came from, without
        # directly divulging the origin URL for privacy reasons
        sec_fetch = context.get_header("Sec-Fetch-Site")
        if sec_fetch in ("same-origin", "same-site"):
            return True

        referrer = context.get_header("Referer")
        if not referrer:
            return False

        try:
            parsed_referrer = urlparse(referrer)
        except ValueError:
            # By rights this shouldn't be possible, as the browser shouldn't
            # send us broken URLs, but why leave it to chance?

            return False

        return parsed_referrer.netloc == context.host

    def _has_valid_browsing_cookie(self, context):
        try:
            return self._secure_cookie.verify(context.get_header("Cookie"))
        except MissingToken:
            return False

    def _has_signed_url(self, context):
        return self._secure_url.verify(context.url)

    @classmethod
    def _error_template(cls, exception):
        # We add a fake favicon here, to prevent the browser from requesting
        # one, as this can trigger `pywb` to issue a redirect which effectively
        # logs the user in by setting a `via.sec` cookie in the response.

        return f"""
        <html>
            <head>
                <link rel="icon" href="data:,">
            </head>
            <body>
                <h1>401 Unauthorized</h1>
                <p>{exception}</p>
            </body>
        </html>
        """
