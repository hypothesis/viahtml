"""Token based security measures."""

from http import HTTPStatus
from urllib.parse import urlparse

from h_vialib.exceptions import TokenException
from h_vialib.secure import ViaSecureURL


class AuthenticationView:
    """A view for checking that this request came from a Hypothesis service.

    This will respond to tokens set in `via.sec` using `ViaSecureURLToken` or
    to a cookie that this class emits.

    When calling the view, if everything goes well, nothing will happen and the
    request can continue to the next stage. The class may add headers to the
    context, which should be honored for this to work.
    """

    def __init__(self, secret, required=True, allowed_referrers=None):
        """Initialize the view.

        :param secret: Secret used for signing and checking signatures
        :param required: Require auth
        :param allowed_referrers: A list of hosts allowed to route requests to this service
        """

        self._secure_url = ViaSecureURL(secret)
        self._required = required
        self._allowed_referrers = allowed_referrers or []

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
        if self._has_allowed_referrer(context) or self._has_signed_url(context):
            return

    def _has_allowed_referrer(self, context):
        """Check if the request came from an allowed referrer.

        When responses that Via proxies cause the browser to send subsequent
        requests to Via (e.g. if the page contains resources like images, CSS
        or JavaScript, or if the response is a redirect) we need to allow those
        subsequent requests to be proxied even though their URLs may not be on
        Checkmate's allow-list.

        We identify these subsequent requests from their Referer or
        Sec-Fetch-Site header and allow them.

        The Referer header can also be used to allow requests sent to Via from
        other Hypothesis apps (e.g. from the LMS app).
        """
        # The `Sec-Fetch-Site` header is set in some browsers (eg. Chrome) to
        # indicate where a request came from, without divulging the actual
        # origin.
        #
        # Testing this header in addition to `Referer` is needed because Chrome
        # does not set the `Referer` in some subresource requests. See
        # https://github.com/hypothesis/viahtml/issues/70.
        sec_fetch = context.get_header("Sec-Fetch-Site")
        if sec_fetch == "same-origin":
            # Request came from us.
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

        # Allow requests that came from Via or additional allowed referrers.
        return (
            parsed_referrer.netloc == context.host
            or parsed_referrer.netloc in self._allowed_referrers
        )

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
